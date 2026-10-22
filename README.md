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
