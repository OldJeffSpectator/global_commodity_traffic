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

## V2 Future TODOs

- [ ] Conflict/chokepoint simulation (block a chokepoint → show affected trade flows)
- [ ] Route visualization using MARNET maritime waypoint graph
- [ ] Chokepoint layer (IMF PortWatch 28 global chokepoints)
- [ ] State-level drill-down (US, Brazil, EU countries with subnational data)
- [ ] Land corridor visualization (~20 curated major rail/truck corridors)
- [ ] Time-series animation (trade flows year-by-year)

### V2 Architecture Note

For route generation, use the Eurostat MARNET maritime waypoint graph (nodes = sea waypoints, not countries). Shortest-path on this graph naturally traverses chokepoints. Avoid BFS on a country adjacency graph, which would produce unrealistic "hopping" routes.
