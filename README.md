# Global Commodity Traffic

A Google Earth-like 3D globe visualization of international commodity trade flows. Click a country to see animated parabola arcs representing bilateral trade with partners, scaled by trade value.

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

### Live Trade Data (Optional)

To fetch real data from UN Comtrade, set your API key:

```bash
# Get a free key at https://comtradedeveloper.un.org
export COMTRADE_API_KEY=your_key_here
```

Then click "Re-pull Trade Data" in the UI, or call the API directly:

```bash
curl -X POST http://localhost:16667/api/trade/sync
```

## Features

- **3D Globe** with country polygons (Natural Earth 110m)
- **Click a country** to show trade arcs to all partners
- **Arc opacity/thickness** scaled by trade value (major flows stand out)
- **Hover** for country name tooltip and highlight glow
- **Right-click** for context menu with "Show Trade Info"
- **Trade Info Panel** showing exports, imports, top partners, breakdown by commodity
- **Commodity filter** to show only specific commodity types
- **Re-pull button** to sync latest data from UN Comtrade API

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

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/countries | List all countries with centroids |
| GET | /api/commodities | List tracked commodities |
| GET | /api/trade/{iso3} | Bilateral trades for a country |
| GET | /api/trade/{iso3}/summary | Aggregated trade summary |
| POST | /api/trade/sync | Trigger data sync from UN Comtrade |
| GET | /api/trade/sync/status | Check sync progress |
| GET | /api/countries-geojson | Country polygons GeoJSON |
