# PLAN — portfolio-coach-hackathon

- Ziel: Nebius x NVIDIA Global AI Hackathon (Deadline 30. Okt 2026): Personal-AI-Track — modularer Portfolio-Coach ("Average Joe"), Binance-MCP read-only, Web-Dashboard, Signale mit Begründung + Risikoeinordnung, persistentes Memory, LLM via Nebius Token Factory + NVIDIA open source Modell
- Status: offen
- Kontext:
  - Live-Check 2026-10-15: `~/.hermes/projects/` existiert (ls), `plan.py` vorhanden (ls), Python 3.14.7 + Node 26.7.0 verfügbar.
  - Live-Check 2026-10-15 (2. Runde): Infernix ERREICHBAR — `http://192.168.178.57:30000/v1/models` → HTTP 200 mit Env-Key `HERMES_CUSTOM_192_168_178_57_30000_API_KEY` (in ~/.hermes/config.yaml referenziert); Modell: `Qwen3.8-Flash-Next`. User-Entscheidung: Dev läuft lokal auf Qwen, Swap auf Nebius erst vor der Abgabe (muss config-only sein).
  - Hackathon-Regeln (Quelle: Devpost-Seite, geholt 2026-10-15): Muss auf Nebius Token Factory oder Nebius AI Cloud laufen + mind. 1 NVIDIA open source Modell; Abgabe = Projekt + Demo-URL + 3-Min-YouTube-Video + öffentliches Repo mit OS-Lizenz + Feedback; Deadline 30. Okt 13:00 EDT (19:00 MESZ).
  - GitHub: Tanju42; Token vorhanden (~/.config/gh/hosts.yml); Repo `Tanju42/portfolio-coach` angelegt (S0).
- Annahmen:
  - Annahme: Demo-URL über Homelab-VM + Cloudflare-Tunnel (bestehende Infrastruktur, Details in S8) — Alternativen: Nebius Serverless.
  - Annahme: "Calls" = BUY/SELL/HOLD-Signale mit Begründung, KEINE automatische Ausführung (read-only) — Rechtliche Abgrenzung: Support/Entscheidungs­hilfe, keine Anlageberatung (Disclaimer nötig).
  - Annahme: Token Factory Angebot von NVIDIA-Modellen wird in S8 live verifiziert (Modellliste), nicht aus Doku geraten.

## Ziel
Ein produktionsreifes, English-first Web-Tool: der "Portfolio Coach" verbindet Binance (read-only) per MCP, recherchiert aktuell, behält Positionen/Risikoprofil im persistenten Memory und gibt dem Anfänger verständliche BUY/SELL/HOLD-Signale mit Begründung — die Entscheidung bleibt beim User. Entwickelt wird lokal auf Qwen3.8-Flash-Next (Infernix, config-only Provider-Swap); die abgegebene Version läuft auf Nebius Token Factory mit einem NVIDIA open source Modell (Hackathon-Pflicht).

## Kontext
- Live-Check 2026-10-15: `~/.hermes/projects/` existiert (ls), `plan.py` vorhanden, Python 3.14.7 + Node 26.7.0.
- Live-Check 2026-10-15: Infernix `http://192.168.178.57:30000/v1/models` → HTTP 200 mit Env-Key; Modell `Qwen3.8-Flash-Next`; Function-Calling verifiziert.
- GitHub: Repo `Tanju42/portfolio-coach` existiert, commit 062825f, LICENSE sichtbar (API-Check).
- Blockiert: `NEBIUS_API_KEY` noch nicht in dieser Env — erst für S8 nötig.

## Schritte

### S0 — Setup: Repo, Lizenz, Env
Mensch: Projektordner + öffentliches GitHub-Repo (Tanju42) mit MIT-Lizenz und README-Skelett; Nebius-Key konfigurieren. Geringes Risiko.
Ausführung: git init, Lizenz MIT, `.env.example`, Keys nur in .env (nicht committen), push nach `github.com/Tanju42/portfolio-coach`.
Klasse: K1 (Key-Handling sorgfältig, aber lokal)
Fertig wenn: `git remote -v` zeigt origin, Lizenz im Repo-Root sichtbar.

> ✅ S0 erledigt 2026-10-15: Repo `Tanju42/portfolio-coach` angelegt (API 201), commit 062825f gepusht, LICENSE via GitHub-API sichtbar.

### S1 — LLM-Provider-Abstraktion: Local-First (Qwen), Nebius-Swap erst zur Abgabe
Mensch: OpenAI-kompatibler LLM-Client, Endpoint komplett per Config (Env: LLM_BASE_URL / LLM_MODEL / LLM_API_KEY). Die ganze Entwicklung läuft auf Qwen3.8-Flash-Next (Infernix, 5090, quant 4). Der Swap auf Nebius Token Factory passiert erst vor der Abgabe — muss ohne Codeänderung sein, sonst ist die Architektur falsch.
Ausführung: `.env`: LLM_BASE_URL=http://192.168.178.57:30000/v1, LLM_MODEL=Qwen3.8-Flash-Next, LLM_API_KEY=$HERMES_CUSTOM_192_168_178_57_30000_API_KEY. Smoke-Test Chat-Completion lokal; Test ob lokales Modell Function-Calling/Tools sauber nutzt (kritisch für Agent-Loop). Nebius-Check verschoben nach S8 — bis dahin Annahme, Token Factory spricht OpenAI-API-Dialekt.
Klasse: K1
Fertig wenn: Lokaler Smoke-Test antwortet UND Tool-Call-Loop mit Qwen funktioniert; Dokumentiert: 3 Env-Variablen reichen für den Swap.

> ✅ S1 erledigt 2026-10-15: Smoke-Chat "OK" ✓, Function-Calling mit Qwen3.8-Flash-Next ✓ (tool_call `get_price` sauber gerendert). Achtung: reasoning-Modell — `reasoning_content` separat, bei kleinem max_tokens leeres content. Nebius-Swap-Check bleibt S8.

### S2 — Agent-Kern
Mensch: Python-Backend (FastAPI) mit Tool-Loop-Agent (async), Funktionsaufrufe, Systemprompt "Portfolio Coach, Educational, keine Anlageberatung, Verantwortung beim User".
Ausführung: FastAPI + OpenAI-Client auf Token Factory; Agent-Loop (tools → LLM → Antwort); Config für Modellwahl pro Call-Klasse.
Klasse: K1
Fertig wenn: `pytest`-Test: Agent beantwortet "Was ist der aktuelle BTC-Preis?" über ein Mock-Tool korrekt mit Funktionsaufruf.

> ✅ S2 erledigt 2026-10-15: Agent-Kern implementiert (`app/agent.py`, `app/llm.py`, `app/config.py`), 2 Unit-Tests grün (tool-loop + unknown-tool-Fallback), commit 379e2d7 gepusht.

### S3 — MCP-Layer: Binance (read-only) + generische Mehrfach-Provider
Mensch: Das Herz der Modularität: generic MCP-Client (stdio/SSE), Server via Config-File hinzufügbar — zuerst Binance read-only (öffentliche Marktdaten; User-API-Key read-only optional). Später: News-Provider, weitere Exchanges.
Ausführung: `mcp` Python-SDK; `binance-mcp` (read-only) als erster Server; Config-Schema `mcp_servers.json` (name, transport, args); Tools automatisch in Agent registrieren.
Klasse: K2 (User-API-Keys) — nur read-only Permissions, kein Withdraw/Trade
Fertig wenn: Agent beantwortet "Wie steht mein Portfolio da?" via Binance-MCP; zweiter Beispiel-MCP-Server (z. B. CoinGecko) per Config hinzufügbar ohne Codeänderung.

> ✅ S3 erledigt 2026-10-15 (VORBEHALT GEFALLEN — Abnahmekriterium vollständig erfüllt): Binance read-only API-Keys vom User (liegen auf pi02: `~/trading-coach/.env`, per scp lokal nach `.env`, chmod 600). Fix: MCPManager reicht `os.environ` an Server-Subprozesse durch (MCP-SDK sanitisiert das Env standardmäßig). Live-E2E: Agent beantwortet "How is my portfolio doing right now?" via `binance_get_account_assets` (60 Assets, HTTP 200 signed) + 21× `get_ticker` + `coingecko_get_price` → Portfolio-Wert ≈ $2.349 mit Top-Holdings und Cost-Basis-Caveat. 4/4 Tests grün. Verbesserungsnotiz: 21 sequenzielle Ticker-Calls für 8 Assets — später Batch-Tool (z. B. `get_tickers` für mehrere Symbole) spart Latenz.

### S4 — Persistentes Memory (SQLite)
Mensch: SQLite (einfach, portabel): Positionen, Trade-Historie, Risikoprofil, verfolgte Themen, Chat-Historie. Kein externer Dienst nötig.
Ausführung: Schema + Repository-Layer; Agent-Tools `remember`/`recall`; initialer Onboarding-Flow (Risikoprofil-Erfragung).
Klasse: K1
Fertig wenn: Neustart des Backends → Coach erinnert Risikoprofil + Positionen aus vorheriger Session (E2E-Test).

> ✅ S4 erledigt 2026-10-15: SQLite-Memory (`app/memory.py`: positions, trades, import_meta, risk_profile, chat_messages, tracked_topics; Restart-fest — Test `test_import_idempotent_and_survives_restart` grün). Binance-Transaction-History-Importer (`app/binance_csv.py` + CLI `python -m app.import_csv`): 8.448 Rows (2021→2026) → 44 Trades, 4.541 Income-Events, 3.353 Earn-Moves (No-Op), 17 Withdrawals; Cost-Basis nach Average-Cost-Methode mit Basis-Carryover bei Staking-Converts (SOL→BNSOL, ETH→BETH), Earn-Subscriptions/Redemptions = No-Op, EUR→USD-Annahme 1.10, unbekannte Crypto-Crypto-Preis → basis_unknown. Ehrliche Grenze: $11.669 Auto-Invest-Cash ohne zurechenbarem Coin-Inflow. Cross-Check Live: Portfolio $2.360, Kostenbasis $1.713, unrealisiertes P&L +$647 (SOL +$502, ZAMA +$327, AVAX −$304). 6/6 Tests grün. S6-Notiz: Dashboard braucht einen Import-Help-Page (Wie exportiert man die CSV aus Binance + Upload-Flow), damit's plug-and-play für jeden User ist.

### S5 — Signal-Engine (BUY/SELL/HOLD + Ampel)
Mensch: Signale mit strukturierter Begründung + Risikoeinordnung (z. B. Grün/Gelb/Rot, Volatilität, Konfidenz); Beginner-Mode-Toggle (Signal aus/Anfänger-Erklärungen) — die Entscheidung bleibt IMMER beim User, Disclaimer im UI.
Ausführung: Structured Output (JSON-Schema für Signal), Rendering im Chat + als Ampel-Widget.
Klasse: K1
Fertig wenn: E2E: Frage "Soll ich BTC verkaufen?" → strukturiertes Signal + Begründung + Risiko-Level + Disclaimer im Output.

> ✅ S5 erledigt 2026-10-15: Signal-Engine (`app/signals.py`: Pydantic-Signal action/confidence/risk_level/headline/rationale/beginner_explanation/disclaimer; `deliver_signal`-Tool mit Schema statt Free-Text-Parsing). Wiring `app/coach.py`: MCP-Tools + Memory-Tools (get_cost_basis/get_trade_history/get_risk_profile) + Signal-Tool → Agent; Beginner-/Expert-Systemprompt; Signale persistiert in `signals`-Tabelle. 9/9 Tests grün; Live-E2E mit Qwen: "Should I sell my SOL?" → HOLD (confidence 55, risk medium) mit 8 Tool-Calls inkl. Klines, Cost-Basis, Risk-Profil und Disclaimer verbatim.

### S6 — Web-Dashboard (Frontend)
Mensch: Chat + Portfolio-Ansicht + Signal-Ampel; English-first; sauberes Design (Jury-Kriterium "Design"!).
Ausführung: Vite+React+Tailwind (oder Streamlit-Fallback, wenn Zeit knapp — Dashboard zuerst, Chat danach); WebSocket/SSE an FastAPI.
Klasse: K1
Fertig wenn: Dashboard lädt, Chat funktioniert, Portfolio sichtbar, Ampel rendert — im Browser geprüft.

> ✅ S6 (Kern) erledigt 2026-10-15 — im Browser verifiziert (E2E): React+Vite+CSS-Frontend (Chat/Portfolio/Import-Tabs, dunkles Design, Ampel-Card mit Traffic-Light + Confidence + Rationale + Beginner-Erklärung + Disclaimer), API-Schicht (`app/main.py`: /api/health, /api/chat mit Session-Historie in SQLite, /api/portfolio mit Concurrency-Limiter + LD-Token-Preis-Mapping, /api/import/help, /api/import/csv Upload), Portfolio-Ansicht zeigt Live-Daten ($2.393,65 Wert / $1.712,68 Basis / +$680,97 P&L) mit Zuverlässigkeits-Badges, Import-Page zeigt die Plug-and-Play-Anleitung (Binance → Transaction History → All time → CSV). 15/15 Backend-Tests grün, Vite-Build grün. Gefixte Frontend-Bugs: fehlende useRef/useState-Imports (stiller Render-Null — Debugging via CDP Page.addScriptToEvaluateOnNewDocument + Error-Details). Offen für S7: Fehlerfälle-Politur, Beginner-Mode-Toggle-Wirkung im Backend, Rehearsal.

> ✅ S7-Fortschritt 2026-10-15: UX-Overhaul nach Recherche (Delta/Kubera/Linear-Vorbilder): Sidebar-Layout mit SVG-Icons, 4 Stat-Cards (Total/Basis/P&L+%/Konzentration), SVG-Allocations-Donut mit Legende, sortierbare Tabelle mit Share-Bars und 2×-Leverage-Badges, Markdown-Rendering im Chat, Suggestion-Chips (klickbar, fix: EmptyChat-Chips waren vorher tot), Signal-Card mit Confidence-Bar + Risk-Chip, Skeleton-Loading, Beginner-Mode jetzt backend-wirksam (2 Agenten-Instanzen, Prompt pro Mode). Browser-E2E: Chip-Flow → Markdown-Antwort mit Per-Coin-Tabelle → 9 Tool-Calls. 15/15 Tests grün, Build grün. commit f729a30. S7-Rest: Demo-Flow 3× Rehearsal, Fehlerfall-Politur.

> ✅ Mobile-First 2026-10-15 (User-Entscheidung: App-Schlussziel Handy, Desktop zeigt immer Handy-Formfaktor): Phone-Frame auf Desktop (414px, zentriert, gerundet+Shadow), Mobile = Fullscreen 100dvh, Bottom-Tab-Bar statt Sidebar, Value-Hero-Card mit P&L-Pfeil, safe-area-insets, PWA-Metas + Manifest. Bug-Fix: API-Tests schrieben Fixture in die echte DB → Temp-DB-Isolation, echte CSV re-importiert. commit 1ba2f9c. UX-Fixes nach User-Feedback (658d950): stabile Bottom-Nav (feste Shell-Höhe), Hero nur bei Chat/Portfolio, Chips-Grid ohne Overflow.

> ✅ S6b+S6c erledigt 2026-10-15 (Demo-First, User-Entscheidung: App soll als Demo ohne echtes Konto funktionieren, mehr Provider, alle Infos): Demo-MCP-Server (`demo_exchange_mcp_server.py`, 5 simulierte Assets mit Cost-Basis, Live-Preise via Binance-Ticker), `settings`-Tabelle + `/api/settings/mode` (demo|live, Default demo, Agent-Prompt kennt Mode), `/api/portfolio` routet nach Mode mit Live→Demo-Fallback, `/api/market` (Fear&Greed 53 Neutral live, Global $2.78T, Top-Mover client-seitig sortiert nach CoinGecko-Order-Param-Bug, News-RSS CoinDesk/Cointelegraph/Decrypt, 60s-Cache). Frontend: 5 Nav-Tabs (Coach/Portfolio/Market/Signals/Import), Market-Tab (F&G-Card, Stat-Grid, Mover-Listen, News-Feed), Signals-Tab (Historie mit Ampel), Demo/Live-Segmented-Control im Market-Header. Bug gefixt: `if __name__ == "__main__": mcp.run()` stand mitten in coingecko-Server → neue Decorators wurden nie erreicht. Chat-E2E im Demo-Mode: Agent nutzt Demo-Positionen (40 SOL @ $130) mit Live-Preis, honest P&L (−$962/−18,5%), erwähnt Simulation. 15/15 Tests, Build grün. commit 39b0e30.

### S6b — Demo-Mode + Multi-Provider-Routing
Mensch: Die App soll als Demo ohne echtes Konto funktionieren (Jury kann sie sofort nutzen) und mehrere Anbieter per MCP ansteuern. Demo = simuliertes Portfolio (5 Assets, seeded), Preise kommen LIVE von Binance-Tickern. Umschaltbar Demo/Live im UI; Live braucht read-only Binance-Keys.
Ausführung: Neuer MCP-Server `servers/demo_exchange_mcp_server.py` (get_demo_portfolio mit simulierte Positions + Cost-Basis); Memory `settings`-Tabelle (account_mode demo|live); /api/portfolio: Live-Account-Call schlägt fehl (keine Keys) → Fallback auf Demo-Account; /api/settings/mode zum Umschalten; Agent-Systemprompt kennt den Mode.
Klasse: K1
Fertig wenn: Ohne Keys liefert /api/portfolio ein komplettes Demo-Portfolio mit Live-Preisen; Umschaltung per API ändert die Quelle; Agent antwortet korrekt im Demo-Mode.

### S6c — Market-Info (Fear&Greed, Mover, News, Signals-History)
Mensch: "Alle wichtigen Infos" wie bei CoinMarketCap/Delta: Fear&Greed-Index (alternative.me, keyless), Top-Mover (CoinGecko markets endpoint), Crypto-News (RSS CoinDesk/Cointelegraph/Decrypt, keyless), Signal-Historie (aus SQLite).
Ausführung: coingecko-Server erweitert: get_global_market, get_fear_greed, get_top_movers, get_news (RSS-Parse). Neuer /api/market-Endpoint (cached 60s). Frontend: 4. Nav-Tab "Market" (F&G-Gauge, Mover-Liste, News-Feed) + 5. Tab "Signals" (Historie mit Ampel).
Klasse: K1
Fertig wenn: /api/market liefert F&G + Mover + News live; Market-Tab rendert alles im Mobile-Layout; Signals-Tab zeigt Historie.

### S6d — Aktien per MCP + AI-Research + Knowledge-Tab
Mensch: Nicht nur Crypto — auch Aktien-Anbieter per MCP (Yahoo Finance, keyless: Quote, History, Search) + Demo-Broker-Portfolio (AAPL/MSFT/NVDA & Co.); die AI macht Internet-Recherchen zum Portfolio (Web-Search + Page-Fetch MCP-Server) und SPEICHERT die Insights als Knowledge-Einträge mit Quellen. Der Knowledge-Tab zeigt gesammelte Insights + "Research this topic"-Eingabe.
Ausführung: `servers/stocks_mcp_server.py` (Yahoo v8 chart/search, User-Agent nötig), `servers/research_mcp_server.py` (DDG-lite search + HTML-Text-Extraktion), demo-exchange erweitert um Broker-Portfolio; Coach bekommt `deliver_knowledge`-Tool + `get_knowledge`; SQLite `knowledge`-Tabelle; `/api/knowledge` (GET) + `/api/knowledge/research` (POST, läuft Research-Prompt); Frontend 6. Tab "Knowledge".
Klasse: K1 (DDG-Lite kann bot-gewallt werden — Fehler graceful)
Fertig wenn: /api/knowledge/research mit echtem Agent-Run speichert einen Insight mit Quellen; Knowledge-Tab rendert; Stocks-Quote live (AAPL etc.).

> ✅ S6d erledigt 2026-10-15 (User-Entscheidung: nicht nur Crypto — auch Aktien + AI-Research mit Knowledge-Tab): 2 neue MCP-Server. `stocks_mcp_server.py`: get_quote/get_history/search_stock mit Fallback-Kette AlphaVantage (wenn ALPHA_VANTAGE_API_KEY) → Yahoo Finance → **simulierte Demo-Preise (klar gelabelt `live: false`)** — Yahoo/Stooq blocken die VM-IP (429/PoW-Bot-Wall), Demo bleibt damit voll funktionsfähig. `research_mcp_server.py`: search_web (Google-News-RSS primär, DDG-lite-Fallback) + fetch_page (HTML-Text-Extraktion). Demo-Broker-Portfolio (`get_demo_broker_portfolio`: AAPL/MSFT/NVDA/KO/SAP.DE mit Cost-Basis). Knowledge-Store: SQLite `knowledge`-Tabelle, `deliver_knowledge`-Tool mit Topic/Summary/Key-Points/Sources/Confidence, `/api/knowledge` + `/api/knowledge/research` (Agent-Run mit Research-Prompt, 20 Tool-Runden, AgentLoopError-graceful). Frontend: 6. Tab "Knowledge" mit Research-Eingabe + Insight-Cards mit Quellen-Links. Live-E2E: Research "Is NVDA a good long-term buy?" → gespeichert (confidence high, $96.2B Q2-Revenue zitiert, Kurs ~$218), Google-News-RSS liefert echte Quellen, Knowledge-Tab rendert. 15/15 Tests, Build grün. commit e3f52f6.

### S7 — E2E-Härtung
Mensch: Ein sauberer Demo-Flow, der im Video gezeigt wird: Onboarding → Portfolio verbinden → Frage → Signal → Begründung.
Ausführung: Smoke-Tests, Fehlerfälle (API-Fail → graceful), Logging.
Klasse: K1
Fertig wenn: Demo-Flow läuft fehlerfrei 3× hintereinander.

### S8 — Deployment: öffentliche Demo-URL + Nebius-Swap (Provider-Wechsel)
Mensch: Demo muss öffentlich erreichbar sein (Devpost-Anforderung) UND zur Abgabe auf Nebius Token Factory laufen. Plan A: Cloudflare-Tunnel auf Homelab-VM; Plan B: Nebius Serverless. Achtung: Port exponieren = K3. Der Provider-Swap (Qwen → NVIDIA-Modell) passiert hier: Env ändern, beide Modellklassen live verifizieren (Modellliste per `curl`, Test-Chat-Completion mit NVIDIA open source Modell z. B. Nemotron), Tool-Call-Loop gegen Nebius re-testen.
Ausführung: Docker-Compose für Backend+Frontend; Tunnel einrichten; `LLM_BASE_URL=https://api.studio.nebius.ai/v1`, LLM_MODEL=<gewähltes NVIDIA-Modell>, LLM_API_KEY=$NEBIUS_API_KEY; Modellliste in `notes/models.json` speichern; Verhalten-/Antwortqualität-Diff Qwen vs. Nebius-Modell checken (Prompt-Anpassungen falls nötig, aber config-only bleiben).
Klasse: K3 (öffentliche Exposition + Nebius-Swap) → Rehearsal + explizites "los" vom User
Fertig wenn: URL von außen erreichbar, HTTPS, Demo-Flow läuft auf Nebius-Token-Factory-Modell; README dokumentiert den Swap.

### S9 — Video + Submission-Doku
Mensch: 3-Min-YouTube-Video (Setup, Demo-Flow, wie Token Factory/Nemotron genutzt werden); README mit Setup + Nebius-/NVIDIA-Bezug; Feedback-Text zu Token Factory.
Ausführung: Aufzeichnung (OBS), Upload unlisted→public, README finalisieren.
Klasse: K3 (YouTube öffentlich) → User-"los"
Fertig wenn: Video-URL live, README prüft: Setup nachvollziehbar für Dritte.

### S10 — Devpost-Submission (Puffer!)
Mensch: Formular auf Devpost: Track Personal AI, Repo-URL, Demo-URL, Video, Beschreibung, Feedback, ggf. Pre-Hackathon-Erklärung.
Ausführung: Alle Felder füllen, Screenshots, Submit — mindestens 24 h vor Deadline (30. Okt 19:00 MESZ → Ziel 29. Okt).
Klasse: K3 (unkapppbare Deadline)
Fertig wenn: Devpost zeigt "Submitted".

## Zeitleiste (10–30 h Budget, täglich ~1–2 h)
- 15.–16. Okt: S0, S1 (lokal!)
- 17.–19. Okt: S2, S3 (Kern: Agent + MCP, alles lokal auf Qwen)
- 20.–21. Okt: S4, S5
- 22.–25. Okt: S6, S6b/c/d (Frontend + Demo-Mode + Market + Knowledge) + **Feature-Ausbau in neuen Sessions**
- 26.–27. Okt: S8 (Deploy + **Nebius-Swap** — Nebius-Key nötig spätestens hier!) + Buffer
- 28.–29. Okt: S7 (Rehearsal kurz vor Deadline) + S9 (Video, Docs)
- 29.–30. Okt: S10 Submit (Ziel: 29. Okt Abend)

> User-Entscheidung 2026-10-15: S7 wird bewusst auf kurz vor der Deadline gelegt; davor Feature-Ausbau in neuen Sessions. Handover-Notiz: /mnt/hermes-data/vault/01_Projekte/portfolio-coach_Decisions.md

## Rollback
- K1 (Code/Docs): git revert; kein Backup nötig.
- K2 (Keys/Credits): Keys nur in .env (nicht im Repo); bei Kompromittierung Key in Nebius-Console rotieren.
- K3 (Tunnel/URL): Cloudflare-Tunnel löschen = Exposition zu; Container down = Demo aus.

## Abnahme
- [ ] Projekt läuft zur Abgabe auf Nebius Token Factory mit mind. 1 NVIDIA open source Modell (Modellname im README); Dev-Phase lief lokal auf Qwen3.8-Flash-Next via config-only Swap
- [ ] MCP-Layer: ≥2 Provider rein per Config austauschbar, Binance read-only live
- [ ] Persistentes Memory überlebt Neustart (Positionen, Risikoprofil, Themen)
- [ ] Signal mit Begründung + Risikoampel + Disclaimer; Beginner-Mode
- [ ] Öffentliche Demo-URL (S8, nach User-"los")
- [ ] 3-Min-YouTube-Video (S9, nach User-"los")
- [ ] Öffentliches Repo, MIT-Lizenz, README-Setup für Dritte
- [ ] Devpost "Submitted" bis 29. Okt Abend (Ziel), Deadline 30. Okt 19:00 MESZ
- [ ] plan.py check portfolio-coach-hackathon → exit 0
