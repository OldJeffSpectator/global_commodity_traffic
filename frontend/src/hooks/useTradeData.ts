import { useState, useEffect, useCallback } from "react";
import type {
  CountryData,
  CommodityData,
  TradeResponse,
  TradeSummary,
  ArcData,
} from "../types";
import {
  getCountries,
  getCommodities,
  getTradeForCountry,
  getTradeSummary,
} from "../services/api";

const COMMODITY_COLORS: Record<string, string> = {
  "27": "#ff6600", // Energy - orange
  "10": "#66cc33", // Cereals - green
  "72": "#999999", // Iron/steel - gray
  "26": "#cc6633", // Ores - brown
  "31": "#9933cc", // Fertilizers - purple
  "44": "#336600", // Wood - dark green
  "17": "#ff99cc", // Sugar - pink
  "76": "#c0c0c0", // Aluminium - silver
  "74": "#cc6600", // Copper - copper
  "39": "#3399ff", // Plastics - blue
};

export function useTradeData() {
  const [countries, setCountries] = useState<CountryData[]>([]);
  const [commodities, setCommodities] = useState<CommodityData[]>([]);
  const [selectedCountry, setSelectedCountry] = useState<string | null>(null);
  const [tradeData, setTradeData] = useState<TradeResponse | null>(null);
  const [tradeSummary, setTradeSummary] = useState<TradeSummary | null>(null);
  const [arcs, setArcs] = useState<ArcData[]>([]);
  const [loading, setLoading] = useState(false);
  const [commodityFilter, setCommodityFilter] = useState<string | null>(null);

  useEffect(() => {
    getCountries().then(setCountries).catch(console.error);
    getCommodities().then(setCommodities).catch(console.error);
  }, []);

  const selectCountry = useCallback(
    async (iso3: string | null) => {
      if (!iso3 || iso3 === selectedCountry) {
        setSelectedCountry(null);
        setTradeData(null);
        setTradeSummary(null);
        setArcs([]);
        return;
      }

      setSelectedCountry(iso3);
      setLoading(true);

      try {
        const [trade, summary] = await Promise.all([
          getTradeForCountry(iso3, undefined, commodityFilter || undefined),
          getTradeSummary(iso3),
        ]);

        setTradeData(trade);
        setTradeSummary(summary);

        const maxValue = Math.max(
          ...trade.trades.map(
            (t) => t.export_value_usd + t.import_value_usd
          ),
          1
        );

        const newArcs: ArcData[] = trade.trades
          .filter((t) => t.partner_lat !== 0 && t.partner_lng !== 0)
          .map((t) => {
            const totalValue = t.export_value_usd + t.import_value_usd;
            const normalized = totalValue / maxValue;
            const color = COMMODITY_COLORS[t.commodity_code] || "#ffffff";

            return {
              startLat: trade.country.lat,
              startLng: trade.country.lng,
              endLat: t.partner_lat,
              endLng: t.partner_lng,
              color,
              opacity: Math.max(0.08, Math.min(0.9, normalized)),
              stroke: Math.max(0.3, normalized * 3),
              label: `${t.partner_name}: $${formatValue(totalValue)}`,
              partner_iso3: t.partner_iso3,
              value: totalValue,
            };
          });

        // Aggregate by partner (sum across commodities)
        const aggregated = new Map<string, ArcData>();
        for (const arc of newArcs) {
          const existing = aggregated.get(arc.partner_iso3);
          if (existing) {
            existing.value += arc.value;
            existing.opacity = Math.max(existing.opacity, arc.opacity);
            existing.stroke = Math.max(existing.stroke, arc.stroke);
            existing.label = `${arc.label.split(":")[0]}: $${formatValue(existing.value)}`;
          } else {
            aggregated.set(arc.partner_iso3, { ...arc });
          }
        }

        const finalArcs = Array.from(aggregated.values());

        // Re-normalize after aggregation
        const aggMax = Math.max(...finalArcs.map((a) => a.value), 1);
        for (const arc of finalArcs) {
          const norm = arc.value / aggMax;
          arc.opacity = Math.max(0.1, Math.min(0.9, norm));
          arc.stroke = Math.max(0.3, norm * 4);
        }

        setArcs(finalArcs);
      } catch (err) {
        console.error("Failed to fetch trade data:", err);
      } finally {
        setLoading(false);
      }
    },
    [selectedCountry, commodityFilter]
  );

  const updateCommodityFilter = useCallback(
    (code: string | null) => {
      setCommodityFilter(code);
      if (selectedCountry) {
        selectCountry(null);
        setTimeout(() => selectCountry(selectedCountry), 50);
      }
    },
    [selectedCountry, selectCountry]
  );

  return {
    countries,
    commodities,
    selectedCountry,
    tradeData,
    tradeSummary,
    arcs,
    loading,
    commodityFilter,
    selectCountry,
    setCommodityFilter: updateCommodityFilter,
  };
}

function formatValue(value: number): string {
  if (value >= 1e12) return `${(value / 1e12).toFixed(1)}T`;
  if (value >= 1e9) return `${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `${(value / 1e6).toFixed(1)}M`;
  if (value >= 1e3) return `${(value / 1e3).toFixed(1)}K`;
  return value.toFixed(0);
}
