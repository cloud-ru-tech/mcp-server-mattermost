# File Tools

Tools for uploading files and getting download links in Mattermost.

---

## upload_file

Upload a file to a channel.

The file will be attached to messages in the specified channel.
Returns file ID that can be used when posting messages with file_ids parameter.

### Example prompts

- "Upload report.pdf to #general"
- "Attach this file to the engineering channel"
- "Send the screenshot to the thread"

### Annotations

| Hint | Value |
|------|-------|
| `destructiveHint` | false |

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `channel_id` | string | ✓ | — | Channel ID to upload to |
| `file_path` | string | ✓ | — | Local path to the file to upload |
| `filename` | string | — | — | Override filename (uses original name if not specified) |

### Returns

Object with `file_infos` array containing uploaded file metadata with `id`, `name`, `size`, `mime_type`.

### Mattermost API

[POST /api/v4/files](https://api.mattermost.com/#tag/files/operation/UploadFile)

---

## get_file_info

Get metadata about an uploaded file.

Returns file name, size, type, and upload information.
Use to check file details before downloading or sharing.

### Example prompts

- "What is this file?"
- "Get info about the uploaded document"
- "Check the file size"

### Annotations

| Hint | Value |
|------|-------|
| `readOnlyHint` | true |
| `idempotentHint` | true |

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `file_id` | string | ✓ | — | File ID (26-character alphanumeric) |

### Returns

File info object with `id`, `name`, `size`, `mime_type`, `create_at`, `post_id`.

### Mattermost API

[GET /api/v4/files/{file_id}/info](https://api.mattermost.com/#tag/files/operation/GetFileInfo)

---

## get_file_link

Get a public link to download a file.

Link can be shared with users who don't have Mattermost access.
Link may expire based on server settings.

### Example prompts

- "Get a download link for that file"
- "Share the document with external users"
- "Create a public link to the report"

### Annotations

| Hint | Value |
|------|-------|
| `readOnlyHint` | true |
| `idempotentHint` | true |

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `file_id` | string | ✓ | — | File ID |

### Returns

Object with `link` (public URL to download the file).

### Mattermost API

[GET /api/v4/files/{file_id}/link](https://api.mattermost.com/#tag/files/operation/GetFileLink)
