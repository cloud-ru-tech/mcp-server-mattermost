"""Integration tests for file tools via MCP protocol."""

import tempfile
from pathlib import Path

import pytest

from tests.integration.utils import to_dict


class TestFileHappyPath:
    """Basic successful file operations through MCP protocol."""

    async def test_upload_file(self, mcp_client, test_channel):
        """upload_file: uploads file successfully."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test file content")
            temp_path = f.name

        try:
            result = await mcp_client.call_tool(
                "upload_file",
                {
                    "channel_id": test_channel["id"],
                    "file_path": temp_path,
                },
            )

            data = to_dict(result)
            assert "file_infos" in data
            assert len(data["file_infos"]) == 1
            assert data["file_infos"][0]["name"].endswith(".txt")
        finally:
            Path(temp_path).unlink()

    async def test_upload_file_returns_file_id(self, mcp_client, test_channel):
        """upload_file: returns file ID."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Content for ID test")
            temp_path = f.name

        try:
            result = await mcp_client.call_tool(
                "upload_file",
                {"channel_id": test_channel["id"], "file_path": temp_path},
            )

            data = to_dict(result)
            file_info = data["file_infos"][0]
            assert "id" in file_info
            assert len(file_info["id"]) == 26  # Mattermost ID length
        finally:
            Path(temp_path).unlink()

    async def test_get_file_info(self, mcp_client, test_channel):
        """get_file_info: returns file metadata (id, name, size)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Metadata test content")
            temp_path = f.name

        try:
            upload_result = await mcp_client.call_tool(
                "upload_file",
                {"channel_id": test_channel["id"], "file_path": temp_path},
            )
            file_id = to_dict(upload_result.data)["file_infos"][0]["id"]

            result = await mcp_client.call_tool(
                "get_file_info",
                {"file_id": file_id},
            )

            info = to_dict(result)
            assert info["id"] == file_id
            assert "name" in info
            assert "size" in info
        finally:
            Path(temp_path).unlink()

    async def test_get_file_link(self, mcp_client, test_channel):
        """get_file_link: returns downloadable link."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Link test content")
            temp_path = f.name

        try:
            upload_result = await mcp_client.call_tool(
                "upload_file",
                {"channel_id": test_channel["id"], "file_path": temp_path},
            )
            file_id = to_dict(upload_result.data)["file_infos"][0]["id"]

            try:
                result = await mcp_client.call_tool(
                    "get_file_link",
                    {"file_id": file_id},
                )
            except Exception as e:
                if "Public links have been disabled" in str(e):
                    pytest.skip("Public links disabled on server")
                raise

            link_data = to_dict(result)
            assert "link" in link_data
            assert link_data["link"].startswith("http")
        finally:
            Path(temp_path).unlink()

    async def test_post_message_with_file(self, mcp_client, test_channel):
        """post_message with file_ids: attaches file to message."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Attachment content")
            temp_path = f.name

        try:
            upload_result = await mcp_client.call_tool(
                "upload_file",
                {"channel_id": test_channel["id"], "file_path": temp_path},
            )
            file_id = to_dict(upload_result.data)["file_infos"][0]["id"]

            post_result = await mcp_client.call_tool(
                "post_message",
                {
                    "channel_id": test_channel["id"],
                    "message": "Message with attachment",
                    "file_ids": [file_id],
                },
            )

            post = to_dict(post_result.data)
            assert file_id in post.get("file_ids", [])

            await mcp_client.call_tool("delete_message", {"post_id": post["id"]})
        finally:
            Path(temp_path).unlink()


class TestFileValidation:
    """File validation through MCP protocol."""

    async def test_upload_nonexistent_file(self, mcp_client, test_channel):
        """upload_file: error for non-existent path."""
        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool(
                "upload_file",
                {
                    "channel_id": test_channel["id"],
                    "file_path": "/nonexistent/path/to/file.txt",
                },
            )

        error_msg = str(exc_info.value).lower()
        assert "not found" in error_msg or "no such file" in error_msg or "validation" in error_msg

    async def test_upload_directory(self, mcp_client, test_channel):
        """upload_file: error for directory path."""
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            pytest.raises(Exception, match=r"(?i)directory|not a file|is a directory|validation"),
        ):
            await mcp_client.call_tool(
                "upload_file",
                {
                    "channel_id": test_channel["id"],
                    "file_path": temp_dir,
                },
            )
