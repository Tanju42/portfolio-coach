# Portfolio Coach

An MCP-powered personal portfolio coach: connects to your Binance account
(read-only), researches current market topics, remembers your positions,
risk profile and interests in persistent memory — and gives beginner-friendly
BUY / SELL / HOLD signals with reasoning and a risk rating. **The decision is
always yours.** Educational support, not financial advice.

- Stack: FastAPI + generic MCP layer + SQLite memory + React dashboard
- LLM: pluggable via OpenAI-compatible endpoint (`LLM_BASE_URL` / `LLM_MODEL` / `LLM_API_KEY`)
  - local dev: Qwen3.8-Flash-Next (Infernix)
  - submission: NVIDIA open source model served on Nebius Token Factory

> Status: WIP — built for the Nebius x NVIDIA Global AI Hackathon (Oct 2026).

## Run the app (detached screens)

The runtime stack runs in named screens, independent of any agent session:

```bash
./coach-ctl start        # startet alle 3: pc-backend, pc-frontend, pc-preview
./coach-ctl status       # Screens + Health-Checks
./coach-ctl stop [backend|frontend|preview|all]
./coach-ctl restart [backend|frontend|preview|all]
```

| Screen       | Port | Was                                   |
|--------------|------|---------------------------------------|
| `pc-backend` | 8000 | FastAPI (uvicorn), lädt `.env` selbst |
| `pc-frontend`| 5173 | Vite dev server (HMR)                 |
| `pc-preview` | 4173 | Production-Build (vite preview)       |

Der Dev-Server proxyt `/api` an `127.0.0.1:8000`. Beide Frontends sind per
`--host 0.0.0.0` im LAN erreichbar. Der Backend-Port bleibt im LAN offen;
für die öffentliche Demo siehe S8 im PLAN.md.

## Quick start (ohne screens)
Coming with the first runnable milestone (S2).

## License
MIT — see [LICENSE](LICENSE).
