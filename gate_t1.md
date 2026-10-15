# Portfolio-Coach: Multi-Portfolio-Kern + Portfolio-Tab-Redesign

## Ziel

Der Portfolio-Tab zeigt ALLE verbundenen Portfolios mit je einer eigenen Übersicht
(Total oben, einzelne Provider-Accounts darunter — Mercury-Pattern) und eine
aggregierte Asset-Tabelle mit Provider-Badges.

## Ist-Zustand

- Repo: `~/.hermes/projects/portfolio-coach-hackathon` (GitHub `Tanju42/portfolio-coach`, Branch `main`)
- Backend: FastAPI, `src/backend/app/` — `portfolio.py` `build_portfolio()` baut aktuell EIN Portfolio
  aus genau EINEM Account-Tool (`DEMO_ACCOUNT_TOOL` oder `LIVE_ACCOUNT_TOOL`), Endpunkt `GET /api/portfolio` in `main.py` (Zeile ~165)
- `src/backend/servers/mcp_servers.json`: Provider `binance`, `coingecko`, `demo-exchange`, `stocks`, `research`
- `demo-exchange` MCP bietet ZWEI Account-Tools: `get_demo_portfolio` (Crypto) UND
  `get_demo_broker_portfolio` (Aktien) — bisher wird nur einer genutzt
- Frontend: React (Vite), `src/frontend/src/components/PortfolioPanel.jsx` rendert EIN Portfolio
  (Stat-Cards + Donut + Tabelle); Tabs in `App.jsx`
- SQLite-Memory: `app/memory.py`, Tabellen positions, trades, signals, settings, tracked_topics

## Umsetzung (T1 von 3)

1. Backend `GET /api/portfolios` (neu): iteriert über ALLE verfügbaren Account-Tools der
   verbundenen MCP-Provider. Für jedes verbundene Portfolio: eigener Block mit
   `provider` (Name), `label`, `account_type`, Status (`ok`/`error`+Fehlermeldung),
   value/cost/pnl, Asset-Anzahl, Asset-Liste. Fehlerisolation: schlägt EIN Provider fehl,
   liefern die anderen trotzdem Daten (try/except je Provider, Fehler nur in dessen Block).
   Parallelisierung der Provider-Abrufe mit asyncio.gather.
2. Aggregation: `totals` über alle funktionierenden Portfolios; gemergte Asset-Rows
   (gleiches Asset über Provider hinweg = eine Zeile) mit `providers`-Liste je Row
   (Value-Split je Provider). Beibehalten von `basis_reliable_share` und Avg-Cost-Logik.
3. `GET /api/portfolio` bleibt als Alias/Compat auf die Aggregation (Frontend nutzt neu `/api/portfolios`).
4. Frontend Portfolio-Tab-Redesign (`PortfolioPanel.jsx` + neue Komponenten):
   - Aggregierte Hero-Zeile (Total über ALLE Portfolios, P&L)
   - Provider-Cards: je verbundenem Portfolio eine eigene Übersichtskarte
     (Name, Status-Badge ok/error, Value, P&L, Asset-Anzahl, Mini-Donut oder Top-3-Assets)
   - Einheitliche Asset-Tabelle mit Provider-Badge-Spalte, Sortier-Logik wie bisher
   - Provider-Filter-Chips (Alle / Crypto-Demo / Broker-Demo / Binance-Live wenn verbunden)
   - Skeleton-Loader je Provider-Karte (unterschiedliche Ladezeiten laut Recherche)
5. Status-Leiste für Market-Data-Provider (coingecko/stocks/research: erreichbar/nicht)
   kompakt am Tab-Boden — die "einzelnen Provider die hinterlegt sind".

## Constraints

- Kein neuer MCP-Server; bestehende Tools verwenden. Demo-Mode ist Default und muss
  E2E funktionieren (Live-Binance optional, Demo-Broker-Tool ist Bestandteil des Runs).
- Mobile-First (414px Phone-Frame), bestehende styles.css-Konventionen nutzen.
- Zero-Comment-Regel (/mnt/hermes-data/hermes-shared/rules/ZERO_COMMENT.md): Kommentare
  nur in den 5 erlaubten Kategorien.
- ADR für nicht-triviale Entscheidungen (z. B. Fehlerisolation-Design, Merge-Strategie)
  in DECISIONS.md nach DECISIONS_TEMPLATE.md (8 Pflichtfelder).

## Completed-Gate (je Punkt Verifikationsbefehl, Worker meldet Befehl+Output im Task-Kommentar)

1. `curl -s localhost:8000/api/portfolios | python3 -m json.tool` zeigt ≥2 Portfolio-Blöcke
   (demo crypto + demo broker) mit je eigenem Status/value/pnl/asset-count plus `totals`.
2. Fehlerisolation nachgewiesen: temporär einen Account-Tool-Call fehlschlagen lassen
   (z. B. Server-Stop im Test) → `curl /api/portfolios` liefert die restlichen Blöcke trotzdem (Test-Assert).
3. Frontend Portfolio-Tab zeigt im Browser: Hero über alle, ≥2 Provider-Cards, Asset-Tabelle
   mit Provider-Badges, Filter-Chips funktionieren (E2E-Screenshot/Playwright auf ai-kev oder headless).
4. Backend-Tests grün: `cd src/backend && uv run --with pytest python3 -m pytest tests/ -q`
   (neue Tests für /api/portfolios inkl. Fehlerisolation).
5. Frontend-Build grün: `cd src/frontend && npm run build` → exit 0.
6. Zero-Comment: `grep -rnE "#|/\*" src/backend/app src/frontend/src --include=*.py --include=*.jsx` → nur erlaubte Kategorien (Review gegen Regel-Datei).
7. `DECISIONS.md` um ADR erweitert; Vault-Spiegel `01_Projekte/portfolio-coach_Decisions.md` aktualisiert
   + Zeile in `00_Index/DECISIONS_Index.md`; hindsight_retain (1-2 Sätze, Tag profile:coder).
8. Git-Commit mit allen Quelldateien, Push auf `main` (`git push origin main`), Commit-Hash im Kommentar.
