# Vibe Prompt - Global Commodity Traffic

## Original User Prompt

> In this repo, I want to build a system showing the global international (and between states within countries, or between states and states in another country) commodity trading on a google-earth like globe view, highlighting the trade route, and show the impact of regional conflict on types of commodity trading (for example, disabling Strait of Hormuz region cease the trade of oil, farm commodities going in and out)
>
> So I need you to:
> 1. Fetch global trade data, and update DB
> 2. Store trading data in format (only covering large commodities like oil, wheat, steel, and etc.):
>    a) state level total in, and total out
>    b) country level total in and total out
>    c) trading route level:
>       i) land (train and trucks) all destinations and total in and out at each of them (in geographical sequence)
>       ii) water (ships), all destinations, and regions passed (name of oceans, rivers, straits, canals) and total in and out at each of destinations (in geographical sequence)
>    d) list of states, list of countries, list of regions (oceans, rivers, straits, canals)
>    e) these tables should be linked by the id or international code of states, countries, regions
> 3. Visualize above data in a globe view, just like google-earth
> 4. I need to see the UI on a browser
> 5. Interactions:
>    a) re-pull the global trade data
>    b) highlight the region based on mouse position
>    c) right-click to choose: show regional-trade info (total in and total out)
>    d) left-click and drag: rotate the globe
> 6. Detail level: country to state level for land, and world map name level for river and ocean, including Straits

---

## V1 Scope Decisions

After design critique, the following scope was agreed for V1:

- **Country-level only** -- no state/province data (not available globally as open data)
- **No route-level detail** -- no shipping lanes, waypoints, or geographical sequences
- **No conflict simulation** -- deferred to V2
- **Parabola arcs** represent trade flows between countries when one is click-selected
- **Opacity/thickness scaled by trade value** -- minor flows fade, major flows are prominent
- **Click to select** a country (persistent), hover for glow/outline highlight only

---

## V1 Feature Set

1. **Data Pipeline:** Fetch bilateral trade data from UN Comtrade API (free tier) for 10 major commodity categories
2. **Database:** SQLite with 3 tables (Country, Commodity, BilateralTrade)
3. **Globe Visualization:** react-globe.gl (ThreeJS-based 3D globe)
4. **Interactions:**
   - Click country → show parabola arcs to all trade partners (opacity = trade value)
   - Hover → glow/outline on country polygon
   - Right-click → context menu → trade info panel
   - Drag → rotate globe
   - Scroll → zoom
   - Commodity filter in control panel
   - "Re-pull Data" button to sync latest from UN Comtrade

---

## Technology Stack

- **Frontend:** React 18 + Vite + TypeScript + react-globe.gl
- **Backend:** Python FastAPI
- **Database:** SQLite
- **Data Source:** UN Comtrade API (comtradeapicall Python package)
- **Country Polygons:** Natural Earth 110m GeoJSON

---

## Commodities Tracked (HS2 Level)

| HS2 Code | Category |
|----------|----------|
| 27 | Mineral fuels, oils (crude oil, LNG, coal) |
| 10 | Cereals (wheat, rice, corn) |
| 72 | Iron and steel |
| 26 | Ores, slag, ash |
| 31 | Fertilizers |
| 44 | Wood |
| 17 | Sugar |
| 76 | Aluminium |
| 74 | Copper |
| 39 | Plastics |

---

## V2 Implementation (Completed)

### Design

V2 adds realistic trade route visualization showing the actual path goods travel between countries (sea lanes, straits, canals, land borders, railway corridors) as an alternative to the simple parabola arcs.

### Architecture

1. **Strategic Maritime Graph** -- 54 key waypoints along major shipping lanes (Atlantic, Pacific, Indian Ocean, Mediterranean, Arctic) connected by ~85 edges. This replaces the full 56k-node MARNET graph which was too slow for pure-Python Dijkstra on hundreds of pairs.

2. **Land Border Graph** -- ~66 curated land border connections between major trading nations.

3. **Railway Corridors** -- Reduced cost on specific routes:
   - China-Europe Railway Express (CHN → KAZ → RUS → BLR → POL → DEU)
   - NAFTA Corridor (USA ↔ CAN, USA ↔ MEX)

4. **Cost Model** (relative per km):
   | Segment Type | Cost/km |
   |---|---|
   | Ocean | 0.5 |
   | Strait | 0.6 |
   | Canal | 1.5 |
   | Port access | 1.0 |
   | Railway corridor | 2.0 |
   | Land border | 5.0 |

5. **Route Computation** -- Dijkstra on ~226 node graph (54 waypoints + 172 country ports). Computes all 564 unique country pairs in <1 second.

6. **Region Labeling** -- Each route path is annotated with named regions (oceans, seas, straits, canals) by checking point-in-bounding-box against 41 defined regions (from `regions.json`).

7. **Database Models Added:**
   - `Region` -- named geographic regions with center coordinates
   - `TradeRoute` -- origin/destination pair with total cost and path coordinates
   - `TradeRouteSegment` -- ordered region list for each route

8. **API Endpoints Added:**
   - `GET /api/route/{origin}/{dest}` -- single route with full path and region segments
   - `GET /api/routes/{iso3}` -- all routes for a country (for visualization)
   - `GET /api/regions` -- list all named regions

9. **Frontend Mode Toggle:**
   - "Parabola Arcs" (V1 default) -- direct arcs between countries
   - "Trade Routes" (V2) -- paths following shipping lanes through waypoints, color-coded by trade volume intensity

10. **Region Labels on Globe:**
    - All 41 named regions (oceans, seas, straits, canals, land corridors) are rendered as text labels on the globe surface
    - Color-coded by type: oceans (blue), seas (cyan), straits (yellow), canals (orange), corridors (green)
    - Sized by importance: oceans largest, straits/canals smallest
    - Labels float above country polygons (altitude 0.025) to avoid being obscured

11. **Performance Optimization:**
    - Hover state is throttled (80ms) to prevent rapid-fire React re-renders
    - Arc/path data is memoized (`useMemo`) so hover interactions don't restart route animations
    - Route animations persist until a new country is clicked

### Critique & Limitations

- Strategic waypoints are manually curated; real routing would use port-to-port distances
- Cost model is static (no seasonal/geopolitical variation)
- Path coordinates are straight-line segments between waypoints (not true geodesic curves)
- Railway corridors only cover 2 major routes; more exist globally
- No inland waterway routing (Rhine, Yangtze, Mississippi)
- Region boundaries are defined as bounding boxes, not precise polygon outlines

---

## V3 Future TODOs

- [ ] Conflict/chokepoint simulation (block a chokepoint → show affected trade flows)
- [ ] Chokepoint layer (IMF PortWatch 28 global chokepoints)
- [ ] State-level drill-down (US, Brazil, EU countries with subnational data)
- [ ] More railway/inland corridors (Trans-Siberian, Middle Corridor, Rhine)
- [ ] Time-series animation (trade flows year-by-year)
- [ ] Dynamic cost model (geopolitical events adjust routing weights)
