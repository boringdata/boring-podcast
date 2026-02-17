import { useState, useEffect, useCallback } from 'react'

const API_BASE = '/api/x/podcast'

function StatusBadge({ status }) {
  const colors = {
    done: { bg: '#22c55e20', color: '#22c55e', label: 'Done' },
    start: { bg: '#eab30820', color: '#eab308', label: 'Running' },
    fail: { bg: '#ef444420', color: '#ef4444', label: 'Failed' },
  }
  const s = colors[status] || { bg: '#6b728020', color: '#6b7280', label: status || 'Pending' }
  return (
    <span style={{
      padding: '2px 8px',
      borderRadius: 4,
      fontSize: 11,
      fontWeight: 600,
      background: s.bg,
      color: s.color,
    }}>
      {s.label}
    </span>
  )
}

function AssetChip({ name, exists }) {
  return (
    <span style={{
      display: 'inline-block',
      padding: '2px 6px',
      borderRadius: 3,
      fontSize: 11,
      marginRight: 4,
      background: exists ? '#3b82f620' : '#6b728015',
      color: exists ? '#3b82f6' : '#6b7280',
      border: `1px solid ${exists ? '#3b82f630' : '#6b728020'}`,
    }}>
      {name}
    </span>
  )
}

function EpisodeCard({ episode, onPublish }) {
  const [publishing, setPublishing] = useState(false)

  const handlePublish = async () => {
    setPublishing(true)
    try {
      await onPublish(episode.slug)
    } finally {
      setPublishing(false)
    }
  }

  const steps = episode.pipeline_steps || {}
  const pipelineSteps = ['audio', 'transcript', 'show_notes', 'rss']

  return (
    <div style={{
      border: '1px solid var(--dv-separator-border, #333)',
      borderRadius: 6,
      padding: 12,
      marginBottom: 8,
      background: 'var(--dv-group-view-background-color, #1e1e1e)',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ fontWeight: 600, fontSize: 14 }}>
            {episode.number != null && <span style={{ color: '#6b7280', marginRight: 6 }}>#{episode.number}</span>}
            {episode.title}
          </div>
          {episode.description && (
            <div style={{ fontSize: 12, color: '#9ca3af', marginTop: 4 }}>
              {episode.description}
            </div>
          )}
        </div>
        <button
          onClick={handlePublish}
          disabled={publishing}
          style={{
            padding: '4px 12px',
            borderRadius: 4,
            border: '1px solid #3b82f6',
            background: publishing ? '#3b82f620' : 'transparent',
            color: '#3b82f6',
            fontSize: 12,
            cursor: publishing ? 'wait' : 'pointer',
            whiteSpace: 'nowrap',
          }}
        >
          {publishing ? 'Publishing...' : 'Publish'}
        </button>
      </div>

      <div style={{ marginTop: 8 }}>
        <AssetChip name="audio" exists={episode.assets?.audio} />
        <AssetChip name="video" exists={episode.assets?.video} />
        <AssetChip name="transcript" exists={episode.assets?.transcript} />
        <AssetChip name="notes" exists={episode.assets?.show_notes} />
      </div>

      <div style={{ marginTop: 8, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {pipelineSteps.map((step) => (
          <div key={step} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12 }}>
            <span style={{ color: '#9ca3af' }}>{step}:</span>
            <StatusBadge status={steps[step]} />
          </div>
        ))}
      </div>
    </div>
  )
}

export default function PodcastPanel() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  const fetchEpisodes = useCallback(async () => {
    try {
      setLoading(true)
      const res = await fetch(`${API_BASE}/episodes`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const json = await res.json()
      setData(json)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchEpisodes()
  }, [fetchEpisodes])

  const handlePublish = async (slug) => {
    try {
      const res = await fetch(`${API_BASE}/publish`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slug }),
      })
      const result = await res.json()
      if (!res.ok) throw new Error(result.detail || 'Publish failed')
      // Refresh episode list after publish
      await fetchEpisodes()
    } catch (err) {
      console.error('[Podcast] Publish error:', err)
    }
  }

  const podcast = data?.podcast || {}
  const episodes = data?.episodes || []

  return (
    <div style={{
      height: '100%',
      overflow: 'auto',
      padding: 16,
      fontFamily: 'inherit',
      color: 'var(--dv-activegroup-visiblepanel-tab-color, #ccc)',
    }}>
      <div style={{ marginBottom: 16 }}>
        <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>
          {podcast.title || 'Podcast'}
        </h2>
        {podcast.description && (
          <p style={{ margin: '4px 0 0', fontSize: 12, color: '#9ca3af' }}>
            {podcast.description}
          </p>
        )}
      </div>

      {loading && <div style={{ color: '#6b7280', fontSize: 13 }}>Loading episodes...</div>}
      {error && <div style={{ color: '#ef4444', fontSize: 13 }}>Error: {error}</div>}

      {!loading && episodes.length === 0 && (
        <div style={{ color: '#6b7280', fontSize: 13 }}>
          No episodes found. Add episodes to the <code>episodes/</code> directory.
        </div>
      )}

      {episodes.map((ep) => (
        <EpisodeCard key={ep.slug} episode={ep} onPublish={handlePublish} />
      ))}

      <div style={{ marginTop: 16, textAlign: 'center' }}>
        <button
          onClick={fetchEpisodes}
          style={{
            padding: '4px 12px',
            borderRadius: 4,
            border: '1px solid #6b7280',
            background: 'transparent',
            color: '#9ca3af',
            fontSize: 11,
            cursor: 'pointer',
          }}
        >
          Refresh
        </button>
      </div>
    </div>
  )
}
