import { useState, useEffect, useCallback, useRef } from "react";
import type {
  CountryData,
  CommodityData,
  TradeResponse,
  ArcData,
  PathData,
  YearRange,
} from "../types";
import {
  getCountries,
  getCommodities,
  getTradeForCountry,
  getRoutesForCountry,
  getYearRange,
} from "../services/api";

const COMMODITY_COLORS: Record<string, string> = {
  "27": "#ff6600",
  "10": "#66cc33",
  "72": "#999999",
  "26": "#cc6633",
  "31": "#9933cc",
  "44": "#336600",
  "17": "#ff99cc",
  "76": "#c0c0c0",
  "74": "#cc6600",
  "39": "#3399ff",
};

export type ViewMode = "arcs" | "routes";

export function useTradeData() {
  const [countries, setCountries] = useState<CountryData[]>([]);
  const [commodities, setCommodities] = useState<CommodityData[]>([]);
  const [selectedCountry, setSelectedCountry] = useState<string | null>(null);
  const [tradeData, setTradeData] = useState<TradeResponse | null>(null);
  const [arcs, setArcs] = useState<ArcData[]>([]);
  const [paths, setPaths] = useState<PathData[]>([]);
  const [loading, setLoading] = useState(false);
  const [commodityFilter, setCommodityFilter] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("arcs");
  const [yearRange, setYearRange] = useState<YearRange>({ min_year: 2000, max_year: 2023 });
  const [selectedYearStart, setSelectedYearStart] = useState<number>(2020);
  const [selectedYearEnd, setSelectedYearEnd] = useState<number>(2023);

  // Refs to avoid stale closures in callbacks
  const filtersRef = useRef({ commodityFilter, selectedYearStart, selectedYearEnd });
  filtersRef.current = { commodityFilter, selectedYearStart, selectedYearEnd };

  const selectedCountryRef = useRef(selectedCountry);
  selectedCountryRef.current = selectedCountry;

  useEffect(() => {
    getCountries().then(setCountries).catch(console.error);
    getCommodities().then(setCommodities).catch(console.error);
    getYearRange().then((range) => {
      setYearRange(range);
      setSelectedYearStart(range.max_year - 3);
      setSelectedYearEnd(range.max_year);
    }).catch(console.error);
  }, []);

  const fetchCountryData = useCallback(async (iso3: string) => {
    const { commodityFilter: comm, selectedYearStart: ys, selectedYearEnd: ye } = filtersRef.current;
    setLoading(true);

    try {
      const trade = await getTradeForCountry(iso3, {
        yearStart: ys,
        yearEnd: ye,
        commodity: comm || undefined,
      });

      setTradeData(trade);

      const maxValue = Math.max(
        ...trade.trades.map((t) => t.export_value_usd + t.import_value_usd),
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
      const aggMax = Math.max(...finalArcs.map((a) => a.value), 1);
      for (const arc of finalArcs) {
        const norm = arc.value / aggMax;
        arc.opacity = Math.max(0.1, Math.min(0.9, norm));
        arc.stroke = Math.max(0.3, norm * 4);
      }
      setArcs(finalArcs);

      try {
        const routesResp = await getRoutesForCountry(iso3);
        const tradeValueByPartner = new Map<string, number>();
        for (const arc of finalArcs) {
          tradeValueByPartner.set(arc.partner_iso3, arc.value);
        }

        const routeMax = Math.max(
          ...Array.from(tradeValueByPartner.values()),
          1
        );

        const newPaths: PathData[] = routesResp.routes
          .filter((r) => r.path_coords && r.path_coords.length >= 2)
          .map((r) => {
            const value = tradeValueByPartner.get(r.partner_iso3) || 0;
            const norm = value / routeMax;
            return {
              points: r.path_coords.map(([lat, lng]) => ({ lat, lng })),
              color: norm > 0.5 ? "#00ffcc" : norm > 0.2 ? "#00aaff" : "#4488cc",
              opacity: Math.max(0.15, Math.min(0.85, norm)),
              stroke: Math.max(0.5, norm * 3),
              label: `${r.partner_name} (${r.region_names.join(" → ")})`,
              partner_iso3: r.partner_iso3,
              value,
            };
          });

        setPaths(newPaths);
      } catch {
        setPaths([]);
      }
    } catch (err) {
      console.error("Failed to fetch trade data:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  const selectCountry = useCallback(
    (iso3: string | null) => {
      if (!iso3 || iso3 === selectedCountryRef.current) {
        setSelectedCountry(null);
        setTradeData(null);
        setArcs([]);
        setPaths([]);
        return;
      }

      setSelectedCountry(iso3);
      fetchCountryData(iso3);
    },
    [fetchCountryData]
  );

  const updateCommodityFilter = useCallback(
    (code: string | null) => {
      setCommodityFilter(code);
    },
    []
  );

  const updateYearRange = useCallback(
    (start: number, end: number) => {
      setSelectedYearStart(start);
      setSelectedYearEnd(end);
    },
    []
  );

  // Re-fetch when filters change (debounced)
  useEffect(() => {
    const iso = selectedCountryRef.current;
    if (!iso) return;

    const timer = setTimeout(() => {
      fetchCountryData(iso);
    }, 300);
    return () => clearTimeout(timer);
  }, [selectedYearStart, selectedYearEnd, commodityFilter, fetchCountryData]);

  return {
    countries,
    commodities,
    selectedCountry,
    tradeData,
    arcs,
    paths,
    loading,
    commodityFilter,
    viewMode,
    yearRange,
    selectedYearStart,
    selectedYearEnd,
    setViewMode,
    selectCountry,
    setCommodityFilter: updateCommodityFilter,
    updateYearRange,
  };
}

function formatValue(value: number): string {
  if (value >= 1e12) return `${(value / 1e12).toFixed(1)}T`;
  if (value >= 1e9) return `${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `${(value / 1e6).toFixed(1)}M`;
  if (value >= 1e3) return `${(value / 1e3).toFixed(1)}K`;
  return value.toFixed(0);
}
