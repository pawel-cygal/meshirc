import pytest

from meshirc.core.commands import (
    BuffersCmd,
    ClearCmd,
    CloseCmd,
    CompletionContext,
    ConnectCmd,
    CopyCmd,
    HelpCmd,
    HistoryCmd,
    JoinCmd,
    MeCmd,
    MsgCmd,
    NodesCmd,
    ParseError,
    QueryCmd,
    QuitCmd,
    SendCmd,
    WinCmd,
    complete,
    parse,
)


def test_quit():
    assert parse("/quit") == QuitCmd()


def test_help():
    assert parse("/help") == HelpCmd()


def test_win_short_alias():
    assert parse("/w 3") == WinCmd(index=3)


def test_win_long():
    assert parse("/win 5") == WinCmd(index=5)


def test_win_requires_int():
    with pytest.raises(ParseError, match="usage: /win"):
        parse("/win abc")


def test_win_no_arg():
    with pytest.raises(ParseError, match="usage: /win"):
        parse("/win")


def test_buffers_toggle():
    assert parse("/buffers") == BuffersCmd()
    assert parse("/buf") == BuffersCmd()


def test_close_active():
    assert parse("/close") == CloseCmd()


def test_copy():
    assert parse("/copy") == CopyCmd()


def test_clear():
    assert parse("/clear") == ClearCmd()


def test_me_action():
    assert parse("/me waves") == MeCmd(text="waves")


def test_me_requires_text():
    with pytest.raises(ParseError, match="usage: /me"):
        parse("/me")


def test_nodes():
    assert parse("/nodes") == NodesCmd()


def test_connect_no_host():
    assert parse("/connect") == ConnectCmd(target=None)


def test_connect_with_host():
    assert parse("/connect 10.0.0.5") == ConnectCmd(target="10.0.0.5")


def test_msg_with_text():
    assert parse("/msg BOB hello there") == MsgCmd(target="BOB", text="hello there")


def test_msg_requires_target():
    with pytest.raises(ParseError, match="usage: /msg"):
        parse("/msg")


def test_msg_requires_text():
    with pytest.raises(ParseError, match="usage: /msg"):
        parse("/msg BOB")


def test_query_alias_q():
    assert parse("/q BOB") == QueryCmd(target="BOB")
    assert parse("/query BOB") == QueryCmd(target="BOB")


def test_join_by_index():
    assert parse("/join 2") == JoinCmd(target="2")


def test_join_by_name():
    assert parse("/join #ogol") == JoinCmd(target="#ogol")


def test_parse_history():
    assert parse("/history") == HistoryCmd(limit=20)
    assert parse("/history 5") == HistoryCmd(limit=5)


def test_plain_text_is_send():
    assert parse("hello world") == SendCmd(text="hello world")


def test_unknown_command():
    with pytest.raises(ParseError, match="unknown command: /xyz"):
        parse("/xyz")


def test_empty_string_send():
    assert parse("") == SendCmd(text="")


# ---- completion tests ----


@pytest.fixture
def ctx():
    return CompletionContext(
        commands=[
            "/help",
            "/quit",
            "/msg",
            "/me",
            "/win",
            "/buffers",
            "/join",
            "/close",
            "/clear",
            "/connect",
            "/nodes",
            "/history",
            "/query",
            "/buf",
            "/w",
            "/q",
        ],
        nodes=["BOB", "ALICE", "ALI3", "!22222222"],
        channels=["#default", "#ogol", "#trasa"],
        recent_in_buffer=["BOB", "ALICE"],
    )


def test_complete_command_prefix_returns_matching_commands(ctx):
    # order = order in ctx.commands; "/quit" comes before "/query" before "/q"
    assert complete("/q", 2, ctx) == ["/quit", "/query", "/q"]


def test_complete_empty_command_returns_all_commands(ctx):
    res = complete("/", 1, ctx)
    assert "/quit" in res and "/msg" in res


def test_complete_msg_target_lists_nodes(ctx):
    assert complete("/msg B", 6, ctx) == ["BOB"]


def test_complete_msg_target_case_insensitive(ctx):
    assert complete("/msg ali", 8, ctx) == ["ALICE", "ALI3"]


def test_complete_query_target_lists_nodes(ctx):
    assert complete("/q AL", 5, ctx) == ["ALICE", "ALI3"]


def test_complete_join_lists_channels_and_indexes(ctx):
    res = complete("/join #o", 8, ctx)
    assert res == ["#ogol"]


def test_complete_at_mention_in_text_lists_recent(ctx):
    assert complete("hello @B", 8, ctx) == ["BOB"]


def test_complete_at_mention_empty_lists_all_recent(ctx):
    assert complete("hello @", 7, ctx) == ["BOB", "ALICE"]


def test_complete_no_candidates_returns_empty(ctx):
    assert complete("/msg ZZZ", 8, ctx) == []


def test_complete_plain_text_no_at_returns_empty(ctx):
    assert complete("hello", 5, ctx) == []
