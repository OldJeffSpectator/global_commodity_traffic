# Global Commodity Traffic

A Google Earth-like 3D globe visualization of international commodity trade flows. Click a country/region to see trade connections — choose between animated parabola arcs or realistic shipping/land routes through named oceans, straits, and canals. Uses "country/region" terminology to accommodate separate customs territories (e.g. Taiwan, Hong Kong) that report trade data independently.

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+

### One-Command Launch

```bash
# Windows
run_server.bat

# Linux/Mac
chmod +x run_server.sh
./run_server.sh
```

This auto-installs dependencies, seeds the database, and starts both servers.

- **Backend API:** http://localhost:16667
- **Frontend UI:** http://localhost:16668

### Manual Setup

#### Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate

pip install -r requirements.txt

# Initialize database with countries + commodities + demo data
python -c "from app.db.seed import init_db; init_db()"
python -m app.db.seed_demo_trades

# Start the API server
uvicorn app.main:app --host 0.0.0.0 --port 16667
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:16668 in your browser.

### Compute Trade Routes (V2)

After the backend DB has trade data, compute optimal routes:

```bash
cd backend
.venv\Scripts\python compute_routes.py
```

This builds a strategic maritime + land graph, runs Dijkstra for all country/region pairs (~564 routes in <1s), and stores results in the DB.

### Live Trade Data (Optional)

To fetch real data from UN Comtrade (takes several hours for full pull):

```bash
cd backend

# Set your API key (free at https://comtradedeveloper.un.org)
# Windows:
set COMTRADE_API_KEY=your_key_here
# Linux/Mac:
export COMTRADE_API_KEY=your_key_here

.venv\Scripts\python pull_data.py --from-year 2020 --to-year 2023
```

## Features

### V1 — Trade Flow Visualization
- **3D Globe** with country/region polygons (Natural Earth 110m)
- **Click a country/region** to show trade arcs to all partners
- **Arc opacity/thickness** scaled by trade value (major flows stand out)
- **Hover** for country/region name tooltip and highlight glow
- **Right-click** to open Trade Info panel
- **Trade Info Panel** showing exports, imports, top partners, breakdown by commodity
- **Commodity filter** to isolate specific commodity types

### V2 — Realistic Trade Routes
- **View mode toggle**: switch between "Parabola Arcs" and "Trade Routes"
- **Trade Routes** render animated dashed paths following actual shipping lanes through strategic maritime waypoints
- **Region labels** on the globe surface — ocean, sea, strait, canal, and railway corridor names always visible
- **Route hover labels** show partner name + full region sequence (e.g., "South China Sea → Strait of Malacca → Indian Ocean → Suez Canal")
- **Dijkstra routing** on a 226-node graph (54 maritime waypoints + 172 country/region ports + land borders + railway corridors)
- **Landlocked countries** correctly routed only via land borders (no phantom sea access)
- **Transit trade display** — countries on overland routes show trade flowing through them
- **Color-coded by trade volume** — high (cyan), medium (blue), low (dark blue)
- **Throttled hover** for smooth interaction without animation restarts

## Commodities Tracked

| HS2 | Category |
|-----|----------|
| 27 | Mineral fuels & oils |
| 10 | Cereals |
| 72 | Iron and steel |
| 26 | Ores, slag & ash |
| 31 | Fertilizers |
| 44 | Wood |
| 17 | Sugar |
| 76 | Aluminium |
| 74 | Copper |
| 39 | Plastics |

## Tech Stack

- **Frontend:** React 18, Vite, TypeScript, react-globe.gl (Three.js)
- **Backend:** Python FastAPI, SQLAlchemy, SQLite
- **Data:** UN Comtrade API, Natural Earth GeoJSON
- **Routing:** Dijkstra on strategic maritime graph + land borders + railway corridors

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/countries | List all countries/regions with centroids |
| GET | /api/commodities | List tracked commodities |
| GET | /api/trade/{iso3} | Bilateral trades for a country/region |
| GET | /api/trade/{iso3}/summary | Aggregated trade summary |
| GET | /api/route/{origin}/{dest} | Computed route between two countries/regions |
| GET | /api/routes/{iso3} | All routes for a country/region (visualization) |
| GET | /api/country/{iso3}/transit | Trade stats for routes transiting through |
| GET | /api/country/{iso3}/transit-routes | Route paths for transit display |
| GET | /api/regions | List all named geographic regions |
| GET | /api/countries-geojson | Country/region polygons GeoJSON |
| POST | /api/trade/sync | Trigger data sync from UN Comtrade |
| GET | /api/trade/sync/status | Check sync progress |

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── api/routes.py          # FastAPI endpoints
│   │   ├── db/models.py           # SQLAlchemy models
│   │   ├── db/seed.py             # DB initialization
│   │   ├── services/route_engine.py  # Dijkstra routing engine
│   │   └── main.py                # App entry point
│   ├── data/
│   │   ├── countries.geojson      # Natural Earth polygons
│   │   ├── regions.json           # Named ocean/sea/strait regions
│   │   ├── marnet_nodes.json      # MARNET maritime nodes (reference)
│   │   └── marnet_edges.json      # MARNET maritime edges (reference)
│   ├── compute_routes.py          # Route computation script
│   ├── pull_data.py               # UN Comtrade data pull script
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/Globe.tsx   # 3D globe with arcs/paths/labels
│   │   ├── components/ControlPanel.tsx
│   │   ├── hooks/useTradeData.ts  # Trade data + route fetching
│   │   └── App.tsx
│   └── package.json
├── vibe_prompt/vibe_prompt.md     # Design decisions & prompt history
├── run_server.bat                 # Windows launcher
└── run_server.sh                  # Linux/Mac launcher
```
