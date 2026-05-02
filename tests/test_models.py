from datetime import datetime

from meshirc.core.models import Buffer, BufferKind, Message, Node


def test_buffer_ring_drops_oldest_when_full():
    buf = Buffer(kind=BufferKind.CHANNEL, name="#test", target=0, max_messages=3)
    for i in range(5):
        buf.append(Message(ts=datetime.now(), from_id=f"u{i}", text=f"msg{i}"))
    assert len(buf.messages) == 3
    assert [m.text for m in buf.messages] == ["msg2", "msg3", "msg4"]


def test_buffer_append_increments_unread():
    buf = Buffer(kind=BufferKind.DM, name="Bob", target="!abc")
    buf.append(Message(ts=datetime.now(), from_id="!abc", text="hi"))
    buf.append(Message(ts=datetime.now(), from_id="!abc", text="?"))
    assert buf.unread == 2


def test_buffer_mark_read_resets():
    buf = Buffer(kind=BufferKind.CHANNEL, name="#a", target=0)
    buf.append(Message(ts=datetime.now(), from_id="x", text="m", is_mention=True))
    buf.mark_read()
    assert buf.unread == 0
    assert buf.has_mention is False


def test_buffer_mention_flag_set_on_mention_message():
    buf = Buffer(kind=BufferKind.CHANNEL, name="#a", target=0)
    buf.append(Message(ts=datetime.now(), from_id="x", text="hi @me", is_mention=True))
    assert buf.has_mention is True


def test_node_dataclass_fields():
    n = Node(id="!a", long_name="Alice", short_name="ALI", last_heard=None)
    assert n.id == "!a"
    assert n.short_name == "ALI"
