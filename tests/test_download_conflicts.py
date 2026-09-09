"""Collision policies preserve every attachment, including concurrent downloads."""

# ruff: noqa: ASYNC240 — assertions inspect small local test files synchronously

import asyncio
import errno
import os
from pathlib import Path
from threading import Barrier

import pytest
import respx

from mcp_server_mattermost.client import MattermostClient
from mcp_server_mattermost.config import get_settings
from mcp_server_mattermost.exceptions import FileValidationError


@pytest.fixture(params=[False, True], ids=["hardlink", "exclusive-fallback"])
def publication(request, monkeypatch):
    """Exercise real disk writes with and without hard-link support."""
    if request.param:

        def unsupported(self, target):
            raise OSError(errno.EOPNOTSUPP, "Hard links unavailable")

        monkeypatch.setattr(Path, "hardlink_to", unsupported)


def attachment(file_id, name, content):
    base = f"https://test.mattermost.com/api/v4/files/{file_id}"
    respx.get(f"{base}/info").respond(200, json={"name": name, "size": len(content)})
    return respx.get(base).respond(200, content=content)


@respx.mock
async def test_rename_preserves_attachments(mock_settings, tmp_path, publication):
    routes = [attachment(str(i), "скриншот.PNG", str(i).encode()) for i in range(3)]
    async with MattermostClient(get_settings()).lifespan() as client:
        results = [await client.download_file(str(i), str(tmp_path), on_conflict="rename") for i in range(3)]
        repeated = await client.download_file("0", str(tmp_path), on_conflict="rename")
    assert [r["name"] for r in results] == ["скриншот.PNG", "скриншот (1).PNG", "скриншот (2).PNG"]
    for i, result in enumerate(results):
        assert result["file_id"] == str(i)
        assert Path(result["path"]).read_bytes() == str(i).encode()
    assert repeated["name"] == "скриншот (3).PNG"
    assert Path(repeated["path"]).read_bytes() == b"0"
    assert [route.call_count for route in routes] == [2, 1, 1]
    assert len(list(tmp_path.iterdir())) == 4


@respx.mock
async def test_concurrent_rename(mock_settings, tmp_path, publication, monkeypatch):
    from mcp_server_mattermost import client as client_module

    count = 5
    barrier = Barrier(count, timeout=10)
    original_write = client_module._write_download

    def synchronized_write(*args, **kwargs):
        barrier.wait()
        return original_write(*args, **kwargs)

    monkeypatch.setattr(client_module, "_write_download", synchronized_write)
    routes = [attachment(str(i), "image.PNG", str(i).encode()) for i in range(count)]
    async with MattermostClient(get_settings()).lifespan() as client:
        results = await asyncio.gather(
            *(client.download_file(str(i), str(tmp_path), on_conflict="rename") for i in range(count)),
        )
    assert len({r["path"] for r in results}) == count
    for i, result in enumerate(results):
        assert Path(result["path"]).read_bytes() == str(i).encode()
    assert all(route.call_count == 1 for route in routes)
    assert len(list(tmp_path.iterdir())) == count


@pytest.mark.parametrize("name", ["image.PNG", "README", ".env", "archive.tar.gz"])
@respx.mock
async def test_custom_names_and_occupied_entries(mock_settings, tmp_path, publication, name):
    original = tmp_path / name
    original.mkdir()
    numbered = original.with_name(f"{original.stem} (1){original.suffix}")
    numbered.symlink_to(tmp_path / "missing")
    later = original.with_name(f"{original.stem} (3){original.suffix}")
    later.write_bytes(b"keep")
    attachment("a", "server.txt", b"new")
    async with MattermostClient(get_settings()).lifespan() as client:
        result = await client.download_file("a", str(tmp_path), filename=name, on_conflict="rename")
    assert result["name"] == f"{original.stem} (2){original.suffix}"
    assert Path(result["path"]).read_bytes() == b"new"
    assert original.is_dir()
    assert numbered.is_symlink()
    assert later.read_bytes() == b"keep"


@pytest.mark.parametrize("base", ["😀" * 62, "я" * 124])
@respx.mock
async def test_long_names_and_double_digit_suffix(mock_settings, tmp_path, base):
    name = base + ".PNG"
    (tmp_path / name).write_bytes(b"original")
    attachment("a", name, b"new")
    async with MattermostClient(get_settings()).lifespan() as client:
        results = [await client.download_file("a", str(tmp_path), on_conflict="rename") for _ in range(10)]
    for i, result in enumerate(results, 1):
        assert result["name"].endswith(f" ({i}).PNG")
        assert len(os.fsencode(result["name"])) <= 255
        assert Path(result["path"]).read_bytes() == b"new"
    assert (tmp_path / name).read_bytes() == b"original"


@pytest.mark.parametrize(
    ("overwrite", "policy", "replaces"),
    [
        (False, None, False),
        (True, None, True),
        (False, "error", False),
        (False, "overwrite", True),
        (True, "overwrite", True),
    ],
)
@respx.mock
async def test_legacy_compatibility(mock_settings, tmp_path, overwrite, policy, replaces):
    target = tmp_path / "file.txt"
    target.write_bytes(b"old")
    route = attachment("a", target.name, b"new")
    async with MattermostClient(get_settings()).lifespan() as client:
        if replaces:
            result = await client.download_file("a", str(tmp_path), overwrite=overwrite, on_conflict=policy)
            assert result["path"] == str(target)
        else:
            with pytest.raises(FileValidationError, match="already exists"):
                await client.download_file("a", str(tmp_path), overwrite=overwrite, on_conflict=policy)
    assert target.read_bytes() == (b"new" if replaces else b"old")
    assert route.call_count == int(replaces)


@pytest.mark.parametrize(("overwrite", "policy"), [(True, "error"), (True, "rename"), (False, "invalid"), (False, "")])
@respx.mock
async def test_invalid_policy_has_no_side_effects(mock_settings, tmp_path, overwrite, policy):
    destination = tmp_path / "not-created"
    async with MattermostClient(get_settings()).lifespan() as client:
        with pytest.raises(FileValidationError, match="on_conflict"):
            await client.download_file("a", str(destination), overwrite=overwrite, on_conflict=policy)
    assert not destination.exists()
    assert respx.calls.call_count == 0


@pytest.mark.parametrize("limit", [32, -1, None])
@respx.mock
async def test_filesystem_name_limit(mock_settings, tmp_path, monkeypatch, limit):
    def pathconf(path, key):
        assert key == "PC_NAME_MAX"
        if limit is None:
            raise OSError(errno.EINVAL, "Unsupported")
        return limit

    monkeypatch.setattr(os, "pathconf", pathconf)
    name = "я" * 124 + ".PNG"
    (tmp_path / name).write_bytes(b"old")
    attachment("a", name, b"new")
    async with MattermostClient(get_settings()).lifespan() as client:
        result = await client.download_file("a", str(tmp_path), on_conflict="rename")
    assert len(os.fsencode(result["name"])) <= (limit if limit and limit > 0 else 255)
    assert result["name"].endswith(" (1).PNG")
    assert Path(result["path"]).read_bytes() == b"new"


@respx.mock
async def test_unrepresentable_numbered_name_cleans_temporary_file(mock_settings, tmp_path, monkeypatch):
    monkeypatch.setattr(os, "pathconf", lambda *_args: 8)
    target = tmp_path / "a.longext"
    target.write_bytes(b"old")
    attachment("a", target.name, b"new")
    async with MattermostClient(get_settings()).lifespan() as client:
        with pytest.raises(FileValidationError, match="name limit"):
            await client.download_file("a", str(tmp_path), on_conflict="rename")
    assert list(tmp_path.iterdir()) == [target]
    assert target.read_bytes() == b"old"


@respx.mock
async def test_partial_renamed_write_preserves_existing_file(mock_settings, tmp_path, monkeypatch):
    def unsupported(self, target):
        raise OSError(errno.EOPNOTSUPP, "Hard links unavailable")

    original_open = Path.open

    class PartialWriter:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.stream.close()

        def write(self, content):
            self.stream.write(content[:1])
            raise OSError(errno.ENOSPC, "Disk full")

    def partial_open(path, *args, **kwargs):
        stream = original_open(path, *args, **kwargs)
        return PartialWriter(stream) if path.name == "file (1).txt" else stream

    target = tmp_path / "file.txt"
    target.write_bytes(b"old")
    attachment("a", target.name, b"new")
    monkeypatch.setattr(Path, "hardlink_to", unsupported)
    monkeypatch.setattr(Path, "open", partial_open)
    async with MattermostClient(get_settings()).lifespan() as client:
        with pytest.raises(FileValidationError, match="Cannot write file"):
            await client.download_file("a", str(tmp_path), on_conflict="rename")
    assert list(tmp_path.iterdir()) == [target]
    assert target.read_bytes() == b"old"


@respx.mock
async def test_collision_after_precheck(mock_settings, tmp_path, publication, monkeypatch):
    from mcp_server_mattermost import client as client_module

    original_publish = client_module._publish_download
    target = tmp_path / "file.txt"
    original_lexists = os.path.lexists
    raced = False

    def race(path):
        nonlocal raced
        exists = original_lexists(path)
        if Path(path) == target and not raced:
            raced = True
            target.write_bytes(b"winner")
        return exists

    def publish_with_race(*args):
        with monkeypatch.context() as scoped:
            scoped.setattr(os.path, "lexists", race)
            return original_publish(*args)

    monkeypatch.setattr(client_module, "_publish_download", publish_with_race)
    route = attachment("a", target.name, b"new")
    async with MattermostClient(get_settings()).lifespan() as client:
        result = await client.download_file("a", str(tmp_path), on_conflict="rename")
    assert target.read_bytes() == b"winner"
    assert result["name"] == "file (1).txt"
    assert Path(result["path"]).read_bytes() == b"new"
    assert route.call_count == 1


@respx.mock
async def test_mcp_rename_and_schema(mock_settings, tmp_path):
    from fastmcp import Client, FastMCP
    from jsonschema import Draft202012Validator

    from mcp_server_mattermost.server import app_lifespan
    from mcp_server_mattermost.tools.files import download_file

    server = FastMCP("Download conflicts", lifespan=app_lifespan)
    server.add_tool(download_file)
    identifiers = [str(i) * 26 for i in range(3)]
    for i, file_id in enumerate(identifiers):
        attachment(file_id, "скриншот.PNG", str(i).encode())

    async with Client(server) as client:
        tool = next(t for t in await client.list_tools() if t.name == "download_file")
        policy = tool.inputSchema["properties"]["on_conflict"]
        assert policy["default"] is None
        validator = Draft202012Validator(policy)
        for value in ("error", "rename", "overwrite", None):
            assert validator.is_valid(value), f"Schema rejected supported policy: {value!r}"
        for value in ("invalid", "", True, 0, [], {}):
            assert not validator.is_valid(value), f"Schema accepted invalid policy: {value!r}"
        assert "on_conflict" not in tool.inputSchema.get("required", [])
        for i, file_id in enumerate(identifiers):
            result = await client.call_tool(
                "download_file",
                {"file_id": file_id, "destination_dir": str(tmp_path), "on_conflict": "rename"},
            )
            data = result.structured_content
            assert data["file_id"] == file_id
            assert data["name"] == ("скриншот.PNG" if i == 0 else f"скриншот ({i}).PNG")
            assert Path(data["path"]).read_bytes() == str(i).encode()


@pytest.mark.parametrize(
    "options",
    [
        {"on_conflict": "invalid"},
        {"overwrite": True, "on_conflict": "rename"},
        {"overwrite": True, "on_conflict": "error"},
    ],
)
@respx.mock
async def test_mcp_rejects_invalid_policy_without_side_effects(mock_settings, tmp_path, options):
    from fastmcp import Client, FastMCP

    from mcp_server_mattermost.server import app_lifespan
    from mcp_server_mattermost.tools.files import download_file

    server = FastMCP("Download validation", lifespan=app_lifespan)
    server.add_tool(download_file)
    destination = tmp_path / "not-created"
    async with Client(server) as client:
        result = await client.call_tool(
            "download_file",
            {"file_id": "a" * 26, "destination_dir": str(destination), **options},
            raise_on_error=False,
        )
    assert result.is_error
    assert "on_conflict" in str(result.content)
    assert not destination.exists()
    assert respx.calls.call_count == 0
