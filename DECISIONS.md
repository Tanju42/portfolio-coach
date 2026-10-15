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

## ADR-005: Multi-Portfolio-Architektur — eine Gesamtansicht, je Provider ein eigener Block
- **Datum**: 2026-10-15
- **Status**: implementiert

### Kontext
Der Portfolio-Tab zeigte nur EIN Portfolio (Demo Crypto oder Live Binance). User-Anforderung: alle verbundenen Portfolios im Tab Portfolio mit je einer eigenen Übersicht; dazu 5 ausgereifte Features. Best-Practice-Recherche (Mercury-Pattern, Asset-Aggregatoren): Total oben, Accounts darunter, Fehlerisolation pro Provider, gleiche Assets über Accounts mergen.

### Entscheidung
- **`app/portfolios.py`**: Registry `ACCOUNT_SOURCES` (demo-exchange Crypto, demo-exchange Brokerage, binance Live). `build_all_portfolios()` fragt alle Provider parallel ab (asyncio.gather), jeder Block in try/except → Fehlerisolation (ein toter Provider killt die Gesamtansicht nicht). Live-Quelle in Demo-Mode als `not_connected` sichtbar.
- **Merge**: gleiches Asset über Provider = eine Zeile mit `providers`-Breakdown (Value-gewichtete Avg-Cost- und Basis-Reliability-Aggregation).
- **Snapshots**: Tabelle `portfolio_snapshots`, beim Abruf 300s-throttled je Provider; `/api/portfolio/history?range=24h|7d|all`. Kein synthetisches Backfill (ehrlich: Chart startet leer und füllt sich).
- **Allocation/Rebalance**: deterministische Engine (`app/analytics.py`): Gruppen-Targets (MAJOR/ALT/STABLES/STOCKS) + Einzel-Assets, Normalisierung auf 100 %, ±5 %-Drift-Toleranz, $10-Minimaltrade, Sell-before-Buy-Ordering. Keine Auto-Execution.
- **Risk-Score**: deterministische 0-100-Penalty-Formel (Konzentration >25 %, Stables-Buffer <10 %, Meme-Exposure, Diversifikation, Basis-Reliability) mit dokumentierten Penalty-Komponenten.
- **Realized P&L bewusst weggelassen**: CSV-Import speichert Trades ohne verlässliche Cost-Basis (ADR-004), ein Realized-Wert wäre geraten — nur Unrealized wird gezeigt.

### Warum
Fehlerisolation und Not-Connected-Sichtbarkeit sind Kern der User-Anforderung ("alle Provider, die hinterlegt sind"). Deterministische Rebalance-/Risk-Engine statt LLM-Output macht die Zahlen testbar (12 Unit-Tests) und erklären — der Agent erklärt im Chat, rechnet aber nichts Unnachprüfbares.

### Verworfene Alternativen
- LLM-generierte Rebalance-Vorschläge als einzige Quelle (nicht deterministisch prüfbar).
- Synthetisches History-Backfill (wäre fabrizierte Daten).
- Eigene Asset-Detail-Route (Mobile-First-App bleibt single-page, Inline-Detail reicht).

### Konsequenzen
- Frontend Portfolio-Tab: Provider-Cards, Filter-Chips, Provider-Badges in Tabelle, Performance-Chart, Asset-Detail, Rebalance-Coach, Risk-Sektion, Watchlist, Provider-Status-Footer.
- Neue Endpunkte: `/api/portfolios`, `/api/portfolio/history`, `/api/asset/{asset}`, `/api/allocation` (GET/POST), `/api/risk`, `/api/watchlist` (GET/POST/DELETE); `/api/portfolio` bleibt als Aggregate-Kompatibilitätsalias.
