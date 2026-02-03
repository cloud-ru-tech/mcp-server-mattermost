# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2026-02-03

### Changed

- Reorganized README for better discoverability
- Added Quick Start page with tabbed installation instructions
- Clarified healthcheck behavior for stdio mode in documentation

### Removed

- Removed unused requirements.txt file

## [0.1.0] - 2026-02-02

### Added

- Initial release
- MCP server for Mattermost with 36 tools across 7 categories
- Channel management (list, create, join, leave, members)
- Message operations (post, search, edit, delete)
- Rich message attachments (Slack-style) with colors, fields, and images
- Reactions and pins
- Thread support
- User and team information
- File upload and download links
- Channel bookmarks
- Async HTTP client with retry and rate limit handling
- Docker support (stdio and HTTP modes)
