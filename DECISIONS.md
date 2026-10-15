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

---

## ADR-004: Cost-Basis-Methodik des CSV-Importers (Average Cost + dokumentierte Grenzen)
- **Datum**: 2026-10-15
- **Status**: implementiert (S4), durch 6 Tests abgesichert

### Kontext
User liefert Binance "Transaction History" CSV (8.448 Rows, 2021-2026) mit 30+ Operation-Typen (Buy/Sell/Fee/Convert/Earn/Staking/Auto-Invest/Airdrops). Kostenbasis pro Coin soll plug-and-play aus jedem standardmäßig exportierten Binance-CSV berechenbar sein — nicht maßgeschneidert auf den User.

### Entscheidung
- **Average-Cost-Methode**: Basis in USD; Cash-Legs (USDT/USDC/BUSD/TUSD/FDUSD/DAI ≈ 1.0, EUR ≈ 1.10 — Annahme, dokumentiert) definieren die Kosten.
- **Event-Semantik**: Earn-Subscription/Redemption = No-Op (Coin bleibt im Besitz — verhindert, dass gekaufte und sofort gestakte Coins ihre Basis verlieren). Echte Staking-Converts (SOL→BNSOL, ETH→BETH, Liquid Swap) = Transfer mit **Basis-Carryover**. Income (Rewards/Airdrops/Interest) = Basis 0. Withdraw/Spending = proportionaler Basisabzug. Crypto-Crypto-Converts ohne Cash-Leg = `basis_unknown` (ehrlich, nicht geraten).
- **Gruppierung**: Trade-Legs werden per 30s-Chain-Cluster gekoppelt (Binance schreibt Buy- und Fiat-Legs Sekunden auseinander, auch über Minuten-Grenzen).
- **Idempotenz**: Trades über SHA-1-Key dedupliziert; wiederholtes Importieren ändert nichts.
- **Auto-Invest-Deduct-Legs** ohne zurechenbarem Coin-Inflow: als `$ unpaired` im Summary gemeldet, NICHT geraten. Index-Redeems erhalten die avg-Basis des Coins (bestmögliche Approximation).

### Warum
Alle Alternativen (historische Kurse nachladen, per-Trade FIFO) sind >10× Aufwand für 10–30 h Budget; Average Cost ist konservativ, verständlich und bei Binance-Exports die übliche Heuristik. Die `basis_reliable_share`-Metrik im Output zeigt der Jury transparent, wie verlässlich jede Zahl ist.

### Verworfene Alternativen
- FIFO/LIFO-Steuer-Matching (zu komplex für Demo, Steuerlogik nicht Ziel).
- Historische FX-Kurse für EUR (Genauigkeit +2 %, Aufwand unverhältnismäßig).

### Konsequenzen
- S6-Dashboard braucht eine Help-Page: "How to export your Binance Transaction History" (Account → Transaction History → generate CSV → upload), damit der Import für jeden User plug-and-play ist.
- Onboarding-Frage in S5: Restliche unbekannte Basis kann der User manuell ergänzen.
