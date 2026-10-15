
## ADR-003: Local-First — Dev auf Qwen3.8-Flash-Next, Nebius-Swap erst zur Abgabe
- **Datum**: 2026-10-15
- **Status**: von User bestätigt

### Kontext
User will das Projekt NUR auf seinem lokalen Qwen3.8-Flash-Next (Infernix, 5090, quant 4) entwickeln und erst bei der Vorstellung auf ein gleich gutes Nebius-Modell umstellen. Hackathon-Regeln verlangen aber für die Abgabe: läuft auf Token Factory/AI Cloud + NVIDIA open source Modell.

### Entscheidung
LLM-Client ist OpenAI-kompatibel und endpoint-agnostisch: LLM_BASE_URL / LLM_MODEL / LLM_API_KEY in .env. Dev = lokal (http://192.168.178.57:30000/v1, Qwen3.8-Flash-Next — Live-Check 2026-10-15: erreichbar, Key in Env). Abgabe = Swap auf Nebius Token Factory + NVIDIA-Modell (S8).

### Warum
Entwicklungskosten 0 Credits, volle Geschwindigkeit, keine Rate-Limits beim Iterieren. Die Abgabe bleibt regelkonform, weil der finale Demo-Swap config-only ist und in S8 verifiziert wird.

### Verworfene Alternativen
- Direkt auf Nebius entwickeln (kostet Credits, langsames Iterieren).
- Lokales Qwen als Abgabe-Modell (regelwidrig — wären Disqualifikationsrisiko).

### Konsequenzen
- Kritischer Risikopunkt: lokales quant-4-Modell vs. Nebius-Modell müssen beide Function-Calling sauber können; Agent-Loop wird in S1/S2 gegen beide getestet, gegen Nebius spätestens in S8.
- Verhalten/Qualität-Diff zwischen den Modellen prüfen (S8), Prompt ggf. nachziehen — aber config-only bleibt.
