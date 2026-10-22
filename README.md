# Rabi

**A voice companion for developers, through Alexa+.** Rabi figures out why your Mac is struggling and talks you through fixing it, and after a tough hackathon result it reminds you of your real record and points you at what's next.

> "Alexa, ask Rabi why my Mac is slow."
> "Xcode is using most of your memory and an iOS Simulator is running in the background. Want me to close the Simulator?"

Rabi is a self-hosted **MCP server** (Model Context Protocol, spec **2025-11-25** over **Streamable HTTP**) that runs on your Mac. Alexa+ calls its tools; Rabi runs read-only macOS checks and uses **Amazon Bedrock** to turn the raw numbers into a couple of friendly spoken sentences.

Built for the Amazon "Build, Ship, Shape" Developer Hackathon (Alexa+ track).

## Why

iCloud "Optimize Mac Storage" quietly offloaded the files in one of my Python virtual environments. `import torch` took **24 minutes** while macOS downloaded placeholders one by one. Nothing told me why. Rabi's `icloud_stuck_projects` tool exists so nobody else loses an evening to that.

## Architecture

```mermaid
flowchart LR
    U([You speaking]) --> A[Alexa+]
    A -- "MCP over Streamable HTTPS<br/>(Bearer token)" --> T[ngrok tunnel]
    T --> R[Rabi MCP server<br/>on your Mac<br/>127.0.0.1:8000/mcp]
    R --> M[macOS checks<br/>psutil, sysctl, git,<br/>st_flags, osascript]
    R --> B[Amazon Bedrock<br/>Converse API]
    R --> J[(data/journey.json)]
    B -- "2-4 spoken sentences" --> R
    R --> A --> U
```

## Tools

| Tool | What it does | Changes anything? |
|---|---|---|
| `ping` | Health check: `{status, server, time}` | No |
| `system_health` | CPU %, load vs cores, memory used, **memory pressure** (normal/warning/critical), swap | No |
| `heavy_apps` | Top apps by memory and CPU, helper processes grouped under their `.app` (all Chrome helpers count as Chrome) | No |
| `disk_space` | Free/used space on the main disk, low-space flag under 10 GB | No |
| `icloud_stuck_projects` | Finds code projects in `~/Desktop` and `~/Documents` (folders with `.git`, `pyproject.toml`, `requirements.txt` or `package.json`), samples up to 200 files each, and checks the `SF_DATALESS` flag to report the % offloaded to iCloud | No |
| `unpushed_work` | Git repos under `~/dev` (or `RABI_PROJECT_ROOTS`) with uncommitted changes or commits ahead of upstream. Never fetches | No |
| `why_is_my_mac_slow` | Runs health + heavy apps + disk, then explains via Bedrock in 2-4 spoken sentences | No |
| `explain_check` | Runs one named check and explains it aloud | No |
| `my_journey` | Encouragement after a loss, grounded only in `data/journey.json`, plus your next deadline | No |
| `close_app` | Quits an app like Cmd+Q, **only after a confirmation round trip** (see below) | Yes |

### `close_app` confirmation flow

1. `close_app(app_name="Simulator")` → returns what will be closed and a `confirm_token`. Nothing happens yet.
2. `close_app(app_name="Simulator", confirm_token="...")` → runs `osascript -e 'quit app "Simulator"'`.

Tokens are single-use, bound to that app, and expire after 60 seconds. Apps can still ask you to save; Rabi never force-kills. Finder, Dock, WindowServer, loginwindow, SystemUIServer, kernel_task, launchd, Terminal, Python and similar are refused.

## Setup (macOS, Apple Silicon)

Keep the project **outside iCloud** (that's the whole point):

```bash
mkdir -p ~/dev && cd ~/dev
git clone https://github.com/Valentinetemi/Rabi.git rabi
cd rabi
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt        # add -r requirements-dev.txt for tests
cp .env.example .env                   # then edit .env
cp data/journey.example.json data/journey.json   # then put in your real record
```

Requires Python 3.11+ (developed on 3.13; all pins verified to have macOS arm64 wheels for 3.11-3.13). Check with `python3 --version`; the Xcode-bundled 3.9 is too old, so use `brew install python@3.13` if needed. `data/journey.json` and `.env` are gitignored.

## Run

```bash
source .venv/bin/activate
python -m rabi.server
# INFO: Uvicorn running on http://127.0.0.1:8000
```

The MCP endpoint is `http://127.0.0.1:8000/mcp`. Quick check with the bundled client:

```bash
python scripts/smoke_test.py
# protocolVersion: 2025-11-25
# tools: ['close_app', 'disk_space', ..., 'why_is_my_mac_slow']
# ping: {"status": "ok", "server": "rabi", ...}
```

Run the tests (they mock macOS bits, so they also pass on Linux CI):

```bash
pip install -r requirements-dev.txt
pytest -q
```

## Test with MCP Inspector

The [MCP Inspector](https://github.com/modelcontextprotocol/inspector) is the official debugging client. The current release (v2) needs **Node 22.19 or newer** (`node --version`; `brew install node` if older).

With the server running in one terminal:

**Web UI**, pre-connected to Rabi:

```bash
npx @modelcontextprotocol/inspector --transport http --server-url http://127.0.0.1:8000/mcp
```

It opens in your browser. Connect, open the **Tools** tab, list tools, pick `ping` and run it. You should see `{"status": "ok", "server": "rabi", ...}`.

(If you start it with plain `npx @modelcontextprotocol/inspector`, add a server in the UI with transport **Streamable HTTP** and URL `http://127.0.0.1:8000/mcp`.)

**CLI** (no browser, good for quick checks):

```bash
npx @modelcontextprotocol/inspector --cli --transport http --server-url http://127.0.0.1:8000/mcp --method initialize
npx @modelcontextprotocol/inspector --cli --transport http --server-url http://127.0.0.1:8000/mcp --method tools/list
npx @modelcontextprotocol/inspector --cli --transport http --server-url http://127.0.0.1:8000/mcp --method tools/call --tool-name ping
```

If `RABI_AUTH_TOKEN` is set, add `--header "Authorization: Bearer <your token>"` to each command (put it after `--server-url ...`).

> Protocol note: Rabi negotiates **2025-11-25** in the `initialize` handshake (verified with the official Python client, see `scripts/smoke_test.py`). The MCP Python SDK 2.3.0 also speaks the newer stateless 2026-07-28 revision, so a v2 Inspector may pick that one; both satisfy the hackathon's "2025-11-25 or later" rule. Add `--protocol-era legacy` to force the 2025-11-25 handshake.

## How Amazon Bedrock is used

All Bedrock code is in [`rabi/explain.py`](rabi/explain.py).

1. A tool (`why_is_my_mac_slow` or `explain_check`) runs the real macOS checks and gets JSON.
2. `explain(topic, data)` creates a `boto3.client("bedrock-runtime", region_name=AWS_REGION)` and calls the **Converse API**:
   - `modelId` = `BEDROCK_MODEL_ID` from `.env`
   - `system` = a prompt telling the model to answer in 2-4 short spoken sentences, give exactly one concrete suggestion, use only facts in the JSON, and avoid markdown (it's read aloud)
   - `messages` = the topic plus the JSON from the checks
   - `inferenceConfig` = `maxTokens: 200`, `temperature: 0.3` (grounded, not creative)
3. The reply text goes back to Alexa+ with `"source": "bedrock"`.
4. If Bedrock isn't configured, or any AWS error happens (no credentials, model access not granted, throttling, network), Rabi logs a warning and returns a hand-written template from [`rabi/templates.py`](rabi/templates.py) with `"source": "template"`. The demo never breaks.

Setup:

```bash
aws configure            # or set AWS_PROFILE / keys in .env
```

In `.env`:

```
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=us.amazon.nova-lite-v1:0
```

Any model that supports Converse works. Make sure model access is enabled in the Bedrock console for that region. Some models need an inference profile ID (the `us.` prefix) instead of the bare model ID.

## Security: exposing Rabi to Alexa+

Rabi binds to `127.0.0.1` by default, so only your Mac can reach it. Alexa+ runs in the cloud, so you expose it through a tunnel such as [ngrok](https://ngrok.com):

```bash
# 1. Make a long random token and put it in .env as RABI_AUTH_TOKEN
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 2. Start the tunnel and note the hostname, e.g. abc123.ngrok-free.app
ngrok http 8000

# 3. In .env: RABI_PUBLIC_HOSTS=abc123.ngrok-free.app   then restart Rabi
python -m rabi.server
```

Give Alexa+ the URL `https://abc123.ngrok-free.app/mcp` and the header `Authorization: Bearer <RABI_AUTH_TOKEN>`.

Rules enforced in [`rabi/auth.py`](rabi/auth.py) and `rabi/server.py`:

- If `RABI_AUTH_TOKEN` is set, `RABI_PUBLIC_HOSTS` is set, or `RABI_HOST` isn't localhost, **every request needs the bearer token** (else `401`).
- If Rabi would be exposed but no token is set, it **refuses to start**.
- The SDK's DNS-rebinding protection stays on; only localhost and the hostnames in `RABI_PUBLIC_HOSTS` are accepted as `Host` headers (others get `400`/`421`).
- Tokens are compared in constant time. Never commit `.env`.
