import pytest

from meshirc.core.models import BufferKind
from meshirc.core.router import BufferRouter
from tests.fixtures.sample_packets import (
    BOB_ID,
    BOB_NUM,
    MY_NODE_ID,
    MY_NODE_NUM,
    MY_SHORT,
    channel_msg,
    dm_from_me,
    dm_to_me,
)


@pytest.fixture
def router():
    r = BufferRouter(my_node_id=MY_NODE_ID, my_node_num=MY_NODE_NUM, my_short_name=MY_SHORT)
    r.ensure_channel(0, "#default")
    return r


def test_console_buffer_exists_at_index_1(router):
    bufs = router.buffers()
    assert bufs[0].kind == BufferKind.CONSOLE
    assert bufs[0].name == "console"


def test_channel_message_routes_to_channel_buffer(router):
    buf = router.on_text(channel_msg("hello", channel=0))
    assert buf.kind == BufferKind.CHANNEL
    assert buf.name == "#default"
    assert buf.messages[-1].text == "hello"


def test_dm_to_me_creates_dm_buffer_keyed_by_sender(router):
    buf = router.on_text(dm_to_me("hi"))
    assert buf.kind == BufferKind.DM
    assert buf.target == BOB_ID
    assert buf.messages[-1].text == "hi"


def test_dm_to_me_reuses_buffer_on_subsequent_messages(router):
    buf1 = router.on_text(dm_to_me("a", packet_id=1))
    buf2 = router.on_text(dm_to_me("b", packet_id=2))
    assert buf1 is buf2
    assert len(buf1.messages) == 2


def test_echo_of_my_dm_routes_to_recipient_buffer(router):
    buf = router.on_text(dm_from_me("ping", to_num=BOB_NUM))
    assert buf.kind == BufferKind.DM
    assert buf.target == BOB_ID


def test_mention_of_my_short_name_sets_flag(router):
    buf = router.on_text(channel_msg("hey ME how are you"))
    assert buf.messages[-1].is_mention is True
    assert buf.has_mention is True


def test_mention_is_case_insensitive(router):
    buf = router.on_text(channel_msg("yo me!"))
    assert buf.messages[-1].is_mention is True


def test_mention_requires_word_boundary(router):
    buf = router.on_text(channel_msg("something_ME_else"))
    assert buf.messages[-1].is_mention is False


def test_mention_of_full_node_id(router):
    buf = router.on_text(channel_msg(f"hi {MY_NODE_ID}"))
    assert buf.messages[-1].is_mention is True


def test_local_echo_records_packet_id_and_skips_pubsub_duplicate(router):
    router.record_local_echo(packet_id=42)
    buf = router.on_text(dm_from_me("dup", to_num=BOB_NUM, packet_id=42))
    assert buf is None
    assert router.was_local_echo(42) is True


def test_unknown_channel_index_creates_fallback_name(router):
    buf = router.on_text(channel_msg("yo", channel=3))
    assert buf.name == "#chan3"


def test_on_system_appends_to_console(router):
    router.on_system("connected")
    console = router.buffers()[0]
    assert console.messages[-1].text == "connected"
    assert console.messages[-1].from_id == "system"


def test_node_to_id_resolves_known_num(router):
    router.on_node_seen(BOB_NUM, "Bob's Beam", "BOB")
    assert router.resolve_node_id(BOB_NUM) == BOB_ID
