"""Helpers for constructing TextMessage events in tests."""
from datetime import datetime

from meshirc.transport.events import BROADCAST_NUM, TextMessage

MY_NODE_NUM = 0x11111111
MY_NODE_ID = "!11111111"
MY_SHORT = "ME"

BOB_NUM = 0x22222222
BOB_ID = "!22222222"


def channel_msg(
    text: str, channel: int = 0, from_id: str = BOB_ID, packet_id: int = 1
) -> TextMessage:
    return TextMessage(
        packet_id=packet_id,
        ts=datetime(2026, 5, 3, 12, 0, 0),
        from_id=from_id,
        to_id=BROADCAST_NUM,
        channel=channel,
        text=text,
    )


def dm_to_me(text: str, from_id: str = BOB_ID, packet_id: int = 1) -> TextMessage:
    return TextMessage(
        packet_id=packet_id,
        ts=datetime(2026, 5, 3, 12, 0, 0),
        from_id=from_id,
        to_id=MY_NODE_NUM,
        channel=0,
        text=text,
    )


def dm_from_me(text: str, to_num: int = BOB_NUM, packet_id: int = 1) -> TextMessage:
    return TextMessage(
        packet_id=packet_id,
        ts=datetime(2026, 5, 3, 12, 0, 0),
        from_id=MY_NODE_ID,
        to_id=to_num,
        channel=0,
        text=text,
    )
