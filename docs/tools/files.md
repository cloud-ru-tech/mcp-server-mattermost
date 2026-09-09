# File Tools

Tools for uploading and downloading files and getting download links in Mattermost.

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
| `capability` | write |

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `channel_id` | string | ✓ | — | Channel ID to upload to |
| `file_path` | string | ✓ | — | Local path to the file to upload; a leading `~` is expanded |
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
| `capability` | read |

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
| `capability` | read |

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `file_id` | string | ✓ | — | File ID |

### Returns

Object with `link` (public URL to download the file).

### Mattermost API

[GET /api/v4/files/{file_id}/link](https://api.mattermost.com/#tag/files/operation/GetFileLink)

---

## download_file

Download a file attachment and save it to a local directory.

Counterpart of `upload_file`: fetches the content of a file by its ID (from a post's
`file_ids` or `get_file_info`) and writes it to disk, so the file can be read or
processed further. Only the base name of the file is used. Publication is atomic
when the destination supports hard links. Otherwise, new files use a race-safe
exclusive-write fallback; requested overwrites still use atomic replacement. Files
larger than 100 MB are refused.

### Example prompts

- "Download the attachment from that message to ~/Downloads"
- "Save the PDF from the thread into ./incoming"
- "Fetch the file and summarize it"

### Annotations

| Hint | Value |
|------|-------|
| `destructiveHint` | true (default) |
| `capability` | write |

A read on the Mattermost side, but it writes to the host filesystem, so it is
declared as a write — a reader profile does not get it. The tool is destructive
because `overwrite=true` irreversibly replaces an existing file's contents.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `file_id` | string | ✓ | — | File ID (26-character alphanumeric) |
| `destination_dir` | string | ✓ | — | Local directory to save into (created if missing); a leading `~` is expanded |
| `filename` | string | — | server-side name | Override the saved file name |
| `overwrite` | boolean | — | false | Replace an existing file with the same name |
| `on_conflict` | string or null | — | null | `error`, `rename`, or `overwrite`; null uses the `overwrite` flag |

### Saving same-named attachments

Call `download_file` once per attachment with `on_conflict="rename"` to keep every
file. For example:

```json
{
  "file_id": "o5w8h47pdfbzjc4d8w7dhnhren",
  "destination_dir": "~/Downloads/attachments",
  "on_conflict": "rename"
}
```

Same-named attachments are saved as `screenshot.PNG`, `screenshot (1).PNG`,
`screenshot (2).PNG`, and so on. Existing files, directories, and symlinks are
left intact. The rule also applies to a custom `filename`. Numbers go before the
last extension (`archive.tar (1).gz`); names without an extension, including
`.env`, get the number at the end. Long stems are shortened at character boundaries
to leave room for the number and extension within the filesystem's name limit.
If those cannot fit, the call returns an error.

Parallel calls claim distinct paths exclusively, including on filesystems without
hard links. Their numbering order is unspecified. Always use the returned `path`
and `name`, alongside `file_id`, to identify the saved attachment. Repeating a call
with the same `file_id` creates another copy; this mode does not deduplicate files.

With `on_conflict` omitted or null, the existing behavior is preserved:
`overwrite=false` rejects an occupied path and `overwrite=true` replaces it.
An explicit `on_conflict="overwrite"` also enables replacement. Combining
`overwrite=true` with `on_conflict="error"` or `"rename"` is rejected before
creating a directory or contacting Mattermost.

### Returns

Object with `file_id`, `path` (absolute local path), `name`, `size` (bytes) and `mime_type`.

### Mattermost API

[GET /api/v4/files/{file_id}/info](https://api.mattermost.com/#tag/files/operation/GetFileInfo),
[GET /api/v4/files/{file_id}](https://api.mattermost.com/#tag/files/operation/GetFile)
