# DECISIONS — portfolio-coach-hackathon

## ADR-001: Track Personal AI, read-only Binance, Web-Dashboard, English
- **Datum**: 2026-10-15
- **Status**: von User bestätigt (Fragerunde 1+2)

### Kontext
Nebius x NVIDIA Global AI Hackathon, Solo-Dev, 10–30 h Budget, Deadline 30. Okt 2026.

### Entscheidung
- Track: Personal AI
- Binance-Integration: ausschließlich read-only (Marktdaten + Portfolio-Sicht), keine Order-Ausführung
- Interface: Web-Dashboard (Chat + Portfolio), kein Telegram in V1
- Signale: BUY/SELL/HOLD-Ampel mit Begründung + Risikoeinordnung, Entscheidung bleibt beim User
- Memory: SQLite (Positionen, Trade-Historie, Risikoprofil, verfolgte Themen)
- Produkt-Sprache: Englisch (größere Jury-Reichweite)
- LLM: Nebius Token Factory + NVIDIA open source (Pflicht des Hackathons); lokale Qwen-Inferenz nur als Dev-Fallback

### Warum
- Read-only = geringstes Risiko (kein Geldbewegungs-Bug, keine Haftung) und juristisch sauberer (Entscheidungs­hilfe, keine Anlageberatung).
- Dashboard trifft Jury-Kriterium "Design" im Demo-Video besser als CLI/Telegram.
- Englisch maximiert Reichweite für Bewertung; "Average Joe" bleibt Design-Nordstern.

### Verworfene Alternativen
- Telegram-First (niedrigere Hürde, aber Video-Impact schwächer) → evtl. V2.
- Echte Order-Ausführung (beeindruckender, aber Risiko/Haftung/Tests sprengen 10–30 h).
- Deutsch-only (kleinere Jury-Perspektive).

### Konsequenzen
- Disclaimer + Beginner-Mode Pflichtbestandteil (S5).
- Deploy: Cloudflare-Tunnel (Plan A) oder Nebius Serverless (Plan B) — K3, braucht User-"los".

---

## ADR-002: Architektur — generischer MCP-Layer statt festverdrahtetem Binance-Adapter
- **Datum**: 2026-10-15
- **Status**: geplant (in S3 umzusetzen)

### Kontext
User will explizite Modularität: mehrere Provider über MCP hinzufügbar.

### Entscheidung
Backend mit generischem MCP-Client (stdio/SSE), Server via `mcp_servers.json`-Config registriert; Binance ist nur der erste Server.

### Warum
Erfüllt die Modularitäts-Anforderung direkt und ist ein judgebarer Differenzierungspunkt ("Quality of the Idea": non-obvious).

### Verworfene Alternativen
Fester Binance-Adapter im Code (schneller, aber Modularitäts-Story tot).

### Konsequenzen
Etwas mehr Aufwand in S3; zweiter Beispiel-Server (CoinGecko) als Beweis im Demo-Video.

---

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
- Lokales Qwen als Abgabe-Modell (regelwidrig — Disqualifikationsrisiko).

### Konsequenzen
- Kritischer Risikopunkt: lokales quant-4-Modell vs. Nebius-Modell müssen beide Function-Calling sauber können; Agent-Loop wird in S1/S2 gegen beide getestet, gegen Nebius spätestens in S8.
- Verhalten/Qualität-Diff zwischen den Modellen prüfen (S8), Prompt ggf. nachziehen — aber config-only bleibt.
