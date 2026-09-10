---
title: "Return attachment content directly through MCP"
summary: "download_file writes to the server filesystem, so a remote HTTP client may receive a path it cannot access to inspect an attachment."
category: feature
created: 2026-09-10
files:
  - src/mcp_server_mattermost/tools/files.py
  - src/mcp_server_mattermost/client.py
---

## Problem and use case

A remote agent asked to inspect an attached log or screenshot cannot necessarily
read the path returned by download_file: that path belongs to the MCP server's
filesystem. The operation needs a transport-independent way to deliver content.

## Expected behavior

Add a read-only attachment tool accepting a Mattermost file ID. Return bounded
text for supported text formats and native MCP image content for supported image
formats. Include file ID, filename, MIME type, and size metadata. Preserve the
existing download_file operation for workflows requiring files on disk.

Define supported MIME types and text encodings, including how invalid byte
sequences are reported. Separate the download byte limit from the text output
limit. Stop reading when the download limit is exceeded, even if metadata reports
a smaller size. Text truncation must be explicit and must not split encoded
characters. Oversized images must receive a clear result rather than partial
image data.

Unsupported binaries should produce useful metadata and an explanation of the
supported retrieval path. Do not embed arbitrary binary files as base64 text.
Reading must use the caller's Mattermost permissions and create no local files.

## Acceptance criteria

- An HTTP client without a shared filesystem can inspect text and an image.
- Image output is native MCP image content, not a base64 string in text JSON.
- Text output reports truncation and its applicable limit.
- Tests cover unsupported formats, invalid encoding, oversized content, incorrect
  declared size, permission denial, and download interruption.
- The tool has read capability and read-only annotations; download_file retains
  its existing filesystem behavior.
