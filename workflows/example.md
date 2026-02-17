---
name: example
title: Example Workflow
description: |
  This is an example agent workflow.
  Delete this file or modify it for your needs.

agent:
  model: claude-sonnet-4-20250514
  max_turns: 10
  allowed_tools:
    - Bash
    - Read
    - Write
    - Glob
    - Grep

guardrails:
  max_tokens: 100000
  max_time: 300

inputs:
  task: "Describe your task here"

tags: [example]
---

# Example Workflow

This is an example workflow. Customize it for your needs.

## Task

{{task}}

## Instructions

1. Analyze the request
2. Take appropriate action
3. Report results
