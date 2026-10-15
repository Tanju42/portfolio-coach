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
- 22.–25. Okt: S6, S7 (Frontend + E2E)
- 26.–27. Okt: S8 (Deploy + **Nebius-Swap** — Nebius-Key nötig spätestens hier!) + Buffer
- 28.–29. Okt: S9 (Video, Docs)
- 29.–30. Okt: S10 Submit (Ziel: 29. Okt Abend)

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
