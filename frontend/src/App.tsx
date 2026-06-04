import { useState, useCallback } from "react";
import Globe from "./components/Globe";
import ControlPanel from "./components/ControlPanel";
import ContextMenu from "./components/ContextMenu";
import TradeInfoPanel from "./components/TradeInfoPanel";
import { useTradeData } from "./hooks/useTradeData";

export default function App() {
  const {
    countries,
    commodities,
    selectedCountry,
    tradeSummary,
    arcs,
    commodityFilter,
    selectCountry,
    setCommodityFilter,
  } = useTradeData();

  const [contextMenu, setContextMenu] = useState<{
    x: number;
    y: number;
    iso3: string;
  } | null>(null);

  const [tradeInfoIso3, setTradeInfoIso3] = useState<string | null>(null);

  const handleCountryClick = useCallback(
    (iso3: string | null) => {
      setContextMenu(null);
      selectCountry(iso3);
    },
    [selectCountry]
  );

  const handleCountryRightClick = useCallback(
    (iso3: string, x: number, y: number) => {
      setContextMenu({ x, y, iso3 });
    },
    []
  );

  const handleShowTradeInfo = useCallback((iso3: string) => {
    setTradeInfoIso3(iso3);
  }, []);

  const selectedName =
    countries.find((c) => c.iso3 === selectedCountry)?.name || null;

  return (
    <div style={{ width: "100vw", height: "100vh", position: "relative" }}>
      <Globe
        arcs={arcs}
        selectedCountry={selectedCountry}
        onCountryClick={handleCountryClick}
        onCountryRightClick={handleCountryRightClick}
      />

      <ControlPanel
        commodities={commodities}
        commodityFilter={commodityFilter}
        onCommodityFilterChange={setCommodityFilter}
        selectedCountryName={selectedName}
      />

      {contextMenu && (
        <ContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          countryIso3={contextMenu.iso3}
          onShowTradeInfo={handleShowTradeInfo}
          onClose={() => setContextMenu(null)}
        />
      )}

      {tradeInfoIso3 && (
        <TradeInfoPanel
          iso3={tradeInfoIso3}
          commodities={commodities}
          onClose={() => setTradeInfoIso3(null)}
        />
      )}
    </div>
  );
}
