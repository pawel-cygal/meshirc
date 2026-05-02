from dataclasses import dataclass


class ParseError(Exception):
    pass


@dataclass(frozen=True)
class SendCmd:
    text: str


@dataclass(frozen=True)
class QuitCmd:
    pass


@dataclass(frozen=True)
class HelpCmd:
    pass


@dataclass(frozen=True)
class WinCmd:
    index: int


@dataclass(frozen=True)
class BuffersCmd:
    pass


@dataclass(frozen=True)
class CloseCmd:
    pass


@dataclass(frozen=True)
class ClearCmd:
    pass


@dataclass(frozen=True)
class MeCmd:
    text: str


@dataclass(frozen=True)
class NodesCmd:
    pass


@dataclass(frozen=True)
class ConnectCmd:
    host: str | None


@dataclass(frozen=True)
class MsgCmd:
    target: str
    text: str


@dataclass(frozen=True)
class QueryCmd:
    target: str


@dataclass(frozen=True)
class JoinCmd:
    target: str


Command = (
    SendCmd | QuitCmd | HelpCmd | WinCmd | BuffersCmd | CloseCmd | ClearCmd
    | MeCmd | NodesCmd | ConnectCmd | MsgCmd | QueryCmd | JoinCmd
)


def _split(rest: str, n: int) -> list[str]:
    """Split rest into at most n parts (last part keeps spaces)."""
    return rest.split(maxsplit=n - 1) if rest else []


def parse(line: str) -> Command:
    if not line.startswith("/"):
        return SendCmd(text=line)

    parts = line.split(maxsplit=1)
    cmd = parts[0][1:].lower()
    rest = parts[1] if len(parts) > 1 else ""

    match cmd:
        case "quit":
            return QuitCmd()
        case "help":
            return HelpCmd()
        case "buffers" | "buf":
            return BuffersCmd()
        case "close":
            return CloseCmd()
        case "clear":
            return ClearCmd()
        case "nodes":
            return NodesCmd()
        case "win" | "w":
            if not rest:
                raise ParseError("usage: /win <N>")
            try:
                return WinCmd(index=int(rest.strip()))
            except ValueError as e:
                raise ParseError("usage: /win <N>") from e
        case "me":
            if not rest:
                raise ParseError("usage: /me <action>")
            return MeCmd(text=rest)
        case "connect":
            host = rest.strip() or None
            return ConnectCmd(host=host)
        case "msg":
            args = _split(rest, 2)
            if len(args) < 2:
                raise ParseError("usage: /msg <node> <text>")
            return MsgCmd(target=args[0], text=args[1])
        case "query" | "q":
            args = _split(rest, 1)
            if not args:
                raise ParseError("usage: /query <node>")
            return QueryCmd(target=args[0])
        case "join":
            args = _split(rest, 1)
            if not args:
                raise ParseError("usage: /join <#channel|N>")
            return JoinCmd(target=args[0])
        case _:
            raise ParseError(f"unknown command: /{cmd}")


@dataclass(frozen=True)
class CompletionContext:
    commands: list[str]
    nodes: list[str]
    channels: list[str]
    recent_in_buffer: list[str]


def _ci_prefix(candidates: list[str], prefix: str) -> list[str]:
    p = prefix.lower()
    return [c for c in candidates if c.lower().startswith(p)]


def complete(line: str, cursor: int, ctx: CompletionContext) -> list[str]:
    """Return completion candidates for the word at `cursor` in `line`."""
    head = line[:cursor]

    if head.startswith("/") and " " not in head:
        return _ci_prefix(ctx.commands, head)

    for prefix_cmd, pool in (
        ("/msg ", ctx.nodes),
        ("/query ", ctx.nodes),
        ("/q ", ctx.nodes),
        ("/join ", ctx.channels),
    ):
        if head.startswith(prefix_cmd):
            target_prefix = head[len(prefix_cmd):]
            return _ci_prefix(pool, target_prefix)

    at = head.rfind("@")
    if at != -1 and (at == 0 or head[at - 1].isspace()):
        return _ci_prefix(ctx.recent_in_buffer, head[at + 1:])

    return []
