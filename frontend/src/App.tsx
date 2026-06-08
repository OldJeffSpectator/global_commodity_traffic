import { useState, useCallback } from "react";
import Globe from "./components/Globe";
import ControlPanel from "./components/ControlPanel";
import TradeInfoPanel from "./components/TradeInfoPanel";
import RegionInfoPanel from "./components/RegionInfoPanel";
import { useTradeData } from "./hooks/useTradeData";
import type { RegionData, PathData } from "./types";
import { getRegionRoutes } from "./services/api";

export default function App() {
  const {
    countries,
    commodities,
    selectedCountry,
    tradeSummary,
    arcs,
    paths,
    commodityFilter,
    viewMode,
    yearRange,
    selectedYearStart,
    selectedYearEnd,
    setViewMode,
    selectCountry,
    setCommodityFilter,
    updateYearRange,
  } = useTradeData();


  const [tradeInfoIso3, setTradeInfoIso3] = useState<string | null>(null);

  const [regionInfo, setRegionInfo] = useState<{
    id: number;
    name: string;
  } | null>(null);

  // Paths that include region-clicked routes
  const [regionPaths, setRegionPaths] = useState<PathData[]>([]);

  const handleCountryClick = useCallback(
    (iso3: string | null) => {
      setRegionPaths([]);
      selectCountry(iso3);
    },
    [selectCountry]
  );

  const handleCountryRightClick = useCallback(
    (iso3: string, _x: number, _y: number) => {
      setRegionInfo(null);
      setTradeInfoIso3(iso3);
    },
    []
  );

  const handleRegionClick = useCallback(async (region: RegionData) => {
    // Show all routes passing through this region
    try {
      const resp = await getRegionRoutes(region.id);
      const routePaths: PathData[] = resp.routes
        .filter((r) => r.path_coords && r.path_coords.length >= 2)
        .map((r, i) => ({
          points: r.path_coords.map(([lat, lng]) => ({ lat, lng })),
          color: "#ffcc00",
          opacity: Math.max(0.3, 0.8 - i * 0.02),
          stroke: Math.max(0.5, 2 - i * 0.05),
          label: `${r.origin_name} → ${r.destination_name}`,
          partner_iso3: r.destination_iso3,
          value: 0,
        }));
      setRegionPaths(routePaths);
      // Clear country selection so routes show clearly
      selectCountry(null);
    } catch (err) {
      console.error("Failed to fetch region routes:", err);
    }
  }, [selectCountry]);

  const handleRegionRightClick = useCallback(
    (region: RegionData, _x: number, _y: number) => {
      setTradeInfoIso3(null);
      setRegionInfo({ id: region.id, name: region.name });
    },
    []
  );


  const selectedName =
    countries.find((c) => c.iso3 === selectedCountry)?.name || null;

  // Merge paths: show region routes if active, otherwise country paths
  const activePaths = regionPaths.length > 0 ? regionPaths : paths;

  return (
    <div style={{ width: "100vw", height: "100vh", position: "relative" }}>
      <Globe
        arcs={arcs}
        paths={activePaths}
        viewMode={regionPaths.length > 0 ? "routes" : viewMode}
        selectedCountry={selectedCountry}
        onCountryClick={handleCountryClick}
        onCountryRightClick={handleCountryRightClick}
        onRegionClick={handleRegionClick}
        onRegionRightClick={handleRegionRightClick}
      />

      <ControlPanel
        commodities={commodities}
        commodityFilter={commodityFilter}
        onCommodityFilterChange={setCommodityFilter}
        selectedCountryName={selectedName}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        yearRange={yearRange}
        selectedYearStart={selectedYearStart}
        selectedYearEnd={selectedYearEnd}
        onYearRangeChange={updateYearRange}
      />

      {tradeInfoIso3 && (
        <TradeInfoPanel
          iso3={tradeInfoIso3}
          commodities={commodities}
          commodityFilter={commodityFilter}
          yearStart={selectedYearStart}
          yearEnd={selectedYearEnd}
          onClose={() => setTradeInfoIso3(null)}
        />
      )}

      {regionInfo && (
        <RegionInfoPanel
          regionId={regionInfo.id}
          regionName={regionInfo.name}
          yearStart={selectedYearStart}
          yearEnd={selectedYearEnd}
          commodityFilter={commodityFilter}
          onClose={() => setRegionInfo(null)}
        />
      )}
    </div>
  );
}
