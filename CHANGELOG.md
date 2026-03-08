# Changelog

All notable changes to Sentinel-Coding will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] - 2026-03-08 

### Added

- 7 slash command skills: `/start`, `/routing`, `/boundary`, `/sentinel-loop`, `/progress`, `/export`, `/call-codex`
- Chain-trigger pipeline for automatic YAML header and directory manifest synchronization
- Compaction engine for promoting session discoveries to CLAUDE.md and ARCHITECTURE.md
- Compliance lint engine detecting 4 types of AI writing patterns
- Git pre-commit hook with soft documentation staleness warnings
- 7 document templates for project bootstrap
- Bilingual documentation (Chinese + English)
- Getting Started guide (`docs/getting-started.md`)

### Notes
- Requires Claude Code and Python 3.11+.
- Recommend install ralph-loop plugin for `/sentinel-loop`
- Recommend install codex-cli and pay for chatgpt subscription for `/call-codex`
