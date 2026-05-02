# meshirc

Profanity-style TUI client for Meshtastic.

## Install

```bash
git clone <repo> meshirc
cd meshirc
python3.11 -m venv .venv
.venv/bin/pip install -e .
```

## Run

```bash
meshirc                           # uses ~/.config/meshirc/config.toml
meshirc --host 192.168.1.50       # override host
meshirc --config ./mycfg.toml     # alternate config file
```

## Config

`~/.config/meshirc/config.toml` (optional — defaults applied if missing):

```toml
[connection]
transport = "tcp"
host = "192.168.100.38"
port = 4403

[ui]
sidebar_default = false
scrollback = 2000
timestamp_format = "%H:%M"

[behavior]
mention_words = []
auto_open_dm = true
```

## Keys

| Key | Action |
|---|---|
| `Alt+1..9` | switch to buffer N |
| `Alt+B` | toggle sidebar |
| `Alt+←/→` | prev/next buffer |
| `PgUp/PgDn` | scroll buffer |
| `Tab` | autocomplete |
| `Ctrl+C` | quit |

## Commands

`/help` `/quit` `/win N` `/buffers` `/close` `/clear` `/me <action>` `/nodes`
`/msg <node> <text>` `/query <node>` `/join <#chan|N>` `/connect [host]`

## Develop

```bash
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest
.venv/bin/ruff check .
```
