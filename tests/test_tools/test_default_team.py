"""Default team selection at the MCP and Mattermost HTTP boundaries."""

import json
import logging

import pytest
import respx
from fastmcp import Client


DEFAULT_TEAM = "o5w8h47pdfbzjc4d8w7dhnhren"
OTHER_TEAM = "tm123456789012345678901234"
BASE_URL = "https://test.mattermost.com/api/v4"
TOOL_CASES = [
    ("list_public_channels", {}, "GET", "/teams/{team}/channels", []),
    ("list_my_channels", {}, "GET", "/users/me/teams/{team}/channels", []),
    (
        "get_channel_by_name",
        {"channel_name": "general"},
        "GET",
        "/teams/{team}/channels/name/general",
        "channel",
    ),
    ("create_channel", {"name": "general", "display_name": "General"}, "POST", "/channels", "channel"),
    ("search_messages", {"terms": "release"}, "POST", "/teams/{team}/posts/search", {"order": [], "posts": {}}),
    ("get_team", {}, "GET", "/teams/{team}", "team"),
    ("get_team_members", {}, "GET", "/teams/{team}/members", []),
]


@pytest.fixture
def tool_logs(caplog, monkeypatch):
    """Capture actual application records, including when propagation is disabled."""
    from mcp_server_mattermost.logging import logger, request_id_var

    caplog.set_level(logging.INFO, logger=logger.name)
    monkeypatch.setattr(logger, "propagate", False)
    logger.addHandler(caplog.handler)
    token = request_id_var.set(None)
    try:
        yield caplog
    finally:
        request_id_var.reset(token)
        logger.removeHandler(caplog.handler)


@pytest.mark.parametrize("case", TOOL_CASES, ids=[case[0] for case in TOOL_CASES])
@pytest.mark.parametrize("selection", ["omitted", "null", "explicit", "explicit-no-default"])
@respx.mock
async def test_default_team_http_selection(mock_settings, monkeypatch, case, selection, tool_logs):
    """Every team-scoped tool resolves omission and honors an explicit override without discovery."""
    from tests.test_tools.test_channels import make_channel_data
    from tests.test_tools.test_teams import make_team_data

    tool_name, arguments, method, path, response = case
    if response == "channel":
        response = make_channel_data()
    elif response == "team":
        response = make_team_data()
    if selection != "explicit-no-default":
        monkeypatch.setenv("MATTERMOST_DEFAULT_TEAM_ID", DEFAULT_TEAM)
    from mcp_server_mattermost.middleware import LoggingMiddleware
    from mcp_server_mattermost.server import _create_mcp

    server = _create_mcp()
    server.add_middleware(LoggingMiddleware())
    expected_team = OTHER_TEAM if selection.startswith("explicit") else DEFAULT_TEAM
    args = dict(arguments)
    if selection != "omitted":
        args["team_id"] = OTHER_TEAM if selection.startswith("explicit") else None
    route = respx.request(method, BASE_URL + path.format(team=expected_team)).respond(200, json=response)
    if tool_name == "list_my_channels":
        respx.get(f"{BASE_URL}/users/me/teams/{expected_team}/channels/members").respond(200, json=[])

    async with Client(server) as client:
        result = await client.call_tool(tool_name, args)

    from mcp_server_mattermost.logging import JSONFormatter

    resolved = [record for record in tool_logs.records if getattr(record, "event", None) == "default_team_resolved"]
    if selection in {"omitted", "null"}:
        assert len(resolved) == 1
        start = next(record for record in tool_logs.records if getattr(record, "event", None) == "tool_call_start")
        record = resolved[0]
        assert record.team_id == expected_team
        assert record.request_id == start.request_id
        assert record.request_id is not None
        assert record.levelno == logging.INFO
        payload = json.loads(JSONFormatter().format(record))
        assert payload["team_id"] == expected_team
        assert payload["request_id"] == start.request_id
        assert payload["event"] == "default_team_resolved"
        assert expected_team in logging.Formatter("%(message)s").format(record)
    else:
        assert not resolved

    assert not result.is_error
    assert route.call_count == 1
    assert len(respx.calls) == (2 if tool_name == "list_my_channels" else 1)
    if tool_name == "create_channel":
        assert json.loads(route.calls.last.request.content)["team_id"] == expected_team


@pytest.mark.parametrize("case", TOOL_CASES, ids=[case[0] for case in TOOL_CASES])
@pytest.mark.parametrize("invalid", ["missing", "null", "empty", "malformed"])
@respx.mock
async def test_invalid_team_never_calls_mattermost(mock_settings, monkeypatch, case, invalid, tool_logs):
    """Missing configuration and invalid explicit IDs fail before any Mattermost request."""
    tool_name, arguments, *_ = case
    if invalid not in {"missing", "null"}:
        monkeypatch.setenv("MATTERMOST_DEFAULT_TEAM_ID", DEFAULT_TEAM)
    from mcp_server_mattermost.server import _create_mcp

    server = _create_mcp()
    args = dict(arguments)
    if invalid == "null":
        args["team_id"] = None
    elif invalid != "missing":
        args["team_id"] = "" if invalid == "empty" else "invalid"
    async with Client(server) as client:
        result = await client.call_tool(tool_name, args, raise_on_error=False)

    assert result.is_error
    error = result.content[0].text
    if invalid in {"missing", "null"}:
        assert "MATTERMOST_DEFAULT_TEAM_ID" in error
        assert "list_teams" in error
    else:
        assert "Invalid Mattermost ID" in error
    assert not respx.calls
    assert not any(getattr(record, "event", None) == "default_team_resolved" for record in tool_logs.records)


@pytest.mark.parametrize("raw", [None, " \t\n", DEFAULT_TEAM, f" \t{DEFAULT_TEAM}\n"])
async def test_default_team_schema_and_instructions(mock_settings, monkeypatch, raw):
    """Clients can omit team_id and learn the deployment default without a discovery call."""
    from jsonschema import Draft202012Validator

    from mcp_server_mattermost.config import Settings

    if raw is not None:
        monkeypatch.setenv("MATTERMOST_DEFAULT_TEAM_ID", raw)
    from mcp_server_mattermost.server import _create_mcp

    server = _create_mcp()
    async with Client(server) as client:
        tools = {tool.name: tool for tool in await client.list_tools()}
        instructions = client.initialize_result.instructions or ""

    configured = Settings().default_team_id is not None
    assert (DEFAULT_TEAM in instructions) is configured
    settings_field = Settings.model_json_schema()["properties"]["default_team_id"]
    assert settings_field["default"] is None
    for name, arguments, *_ in TOOL_CASES:
        schema = tools[name].inputSchema
        assert "team_id" not in schema.get("required", [])
        assert set(arguments) == set(schema.get("required", []))
        field = schema["properties"]["team_id"]
        assert field == tools["list_public_channels"].inputSchema["properties"]["team_id"]
        assert field["default"] is None
        for candidate in (field, settings_field):
            validator = Draft202012Validator(candidate)
            for value in (DEFAULT_TEAM, OTHER_TEAM, None):
                assert validator.is_valid(value)
            for value in (0, True, [], {}):
                assert not validator.is_valid(value)
        # Python 3.10 can wrap nullable Annotated parameters in an additional anyOf.
        description = json.dumps(field)
        assert "Omit or pass null to use MATTERMOST_DEFAULT_TEAM_ID" in description
        assert "an explicit ID overrides the default" in description


@pytest.mark.parametrize("tool_name", ["get_channel_by_name", "create_channel", "search_messages"])
async def test_reordered_tools_reject_positional_calls(mock_settings, tool_name):
    """Legacy positional arguments fail before they can be sent under the wrong parameter names."""
    from mcp_server_mattermost.client import MattermostClient
    from mcp_server_mattermost.config import Settings
    from mcp_server_mattermost.tools import channels, messages
    from tests.test_tools.test_channels import make_channel_data

    cases = {
        "get_channel_by_name": (channels.get_channel_by_name, (DEFAULT_TEAM, "general"), make_channel_data()),
        "create_channel": (channels.create_channel, (DEFAULT_TEAM, "general", "General"), make_channel_data()),
        "search_messages": (messages.search_messages, (DEFAULT_TEAM, "release"), {"order": [], "posts": {}}),
    }
    function, arguments, response = cases[tool_name]
    with respx.mock(assert_all_called=False) as router:
        router.route().respond(200, json=response)
        async with MattermostClient(Settings()).lifespan() as client:
            with pytest.raises(TypeError, match="positional"):
                await function(*arguments, client=client)
        assert not router.calls


@pytest.mark.parametrize("case", TOOL_CASES, ids=[case[0] for case in TOOL_CASES])
@respx.mock
async def test_imported_tools_use_client_specific_settings(mock_settings, monkeypatch, case, tool_logs):
    """Imported tools honor their client's default and token even when global settings disagree."""
    from mcp_server_mattermost.client import MattermostClient
    from mcp_server_mattermost.config import Settings, get_settings
    from mcp_server_mattermost.exceptions import ValidationError
    from mcp_server_mattermost.tools import channels, messages, teams
    from tests.test_tools.test_channels import make_channel_data
    from tests.test_tools.test_teams import make_team_data

    monkeypatch.setenv("MATTERMOST_DEFAULT_TEAM_ID", DEFAULT_TEAM)
    assert get_settings().default_team_id == DEFAULT_TEAM
    functions = {
        function.__name__: function
        for function in (
            channels.list_public_channels,
            channels.list_my_channels,
            channels.get_channel_by_name,
            channels.create_channel,
            messages.search_messages,
            teams.get_team,
            teams.get_team_members,
        )
    }
    tool_name, arguments, method, path, response = case
    if response == "channel":
        response = make_channel_data()
    elif response == "team":
        response = make_team_data()
    for team in (DEFAULT_TEAM, OTHER_TEAM):
        respx.request(method, BASE_URL + path.format(team=team)).respond(200, json=response)
        if tool_name == "list_my_channels":
            respx.get(f"{BASE_URL}/users/me/teams/{team}/channels/members").respond(200, json=[])

    settings = Settings(default_team_id=OTHER_TEAM, token="library-token")
    async with MattermostClient(settings).lifespan() as client:
        for selection, expected in (
            ({"team_id": DEFAULT_TEAM}, DEFAULT_TEAM),
            ({}, OTHER_TEAM),
            ({"team_id": None}, OTHER_TEAM),
        ):
            start = len(respx.calls)
            await functions[tool_name](**arguments, **selection, client=client)
            calls = respx.calls[start:]
            assert len(calls) == (2 if tool_name == "list_my_channels" else 1)
            for call in calls:
                assert call.request.headers["Authorization"] == "Bearer library-token"
            request = calls[0].request
            assert request.url.path == "/api/v4" + path.format(team=expected)
            if tool_name == "create_channel":
                assert json.loads(request.content)["team_id"] == expected

    resolved = [record for record in tool_logs.records if getattr(record, "event", None) == "default_team_resolved"]
    assert len(resolved) == 2
    assert all(record.team_id == OTHER_TEAM and record.request_id is None for record in resolved)

    start = len(respx.calls)
    async with MattermostClient(Settings(default_team_id=None)).lifespan() as client:
        with pytest.raises(ValidationError, match="MATTERMOST_DEFAULT_TEAM_ID"):
            await functions[tool_name](**arguments, client=client)
    assert len(respx.calls) == start


@pytest.mark.parametrize("status", [403, 404])
@respx.mock
async def test_inaccessible_default_does_not_select_another_team(mock_settings, monkeypatch, status):
    """An inaccessible configured team remains an upstream error, without discovery or fallback."""
    monkeypatch.setenv("MATTERMOST_DEFAULT_TEAM_ID", DEFAULT_TEAM)
    from mcp_server_mattermost.server import _create_mcp

    route = respx.get(f"{BASE_URL}/teams/{DEFAULT_TEAM}").respond(status, json={"message": "Team unavailable"})
    async with Client(_create_mcp()) as client:
        result = await client.call_tool("get_team", {}, raise_on_error=False)
    assert result.is_error
    assert "Team unavailable" in result.content[0].text
    assert route.call_count == 1
    assert len(respx.calls) == 1


@pytest.mark.parametrize("selection", ["omitted", "null", "explicit"])
@respx.mock
async def test_search_users_keeps_optional_filter(mock_settings, monkeypatch, selection, tool_logs):
    """A default team never narrows user search unless the caller explicitly supplies a filter."""
    monkeypatch.setenv("MATTERMOST_DEFAULT_TEAM_ID", DEFAULT_TEAM)
    from mcp_server_mattermost.server import _create_mcp

    args = {"term": "alice"}
    if selection != "omitted":
        args["team_id"] = OTHER_TEAM if selection.startswith("explicit") else None
    route = respx.post(f"{BASE_URL}/users/search").respond(200, json=[])
    async with Client(_create_mcp()) as client:
        await client.call_tool("search_users", args)
    payload = json.loads(route.calls.last.request.content)
    assert payload == ({"term": "alice", "team_id": OTHER_TEAM} if selection == "explicit" else {"term": "alice"})
    assert not any(getattr(record, "event", None) == "default_team_resolved" for record in tool_logs.records)
