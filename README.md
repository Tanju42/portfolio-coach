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

## Quick start
Coming with the first runnable milestone (S2).

## License
MIT — see [LICENSE](LICENSE).
