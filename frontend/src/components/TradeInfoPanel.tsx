import { useEffect, useState } from "react";
import type { TradeSummary, CommodityData } from "../types";
import { getTradeSummary } from "../services/api";

interface TradeInfoPanelProps {
  iso3: string;
  commodities: CommodityData[];
  commodityFilter?: string | null;
  yearStart?: number;
  yearEnd?: number;
  onClose: () => void;
}

export default function TradeInfoPanel({
  iso3,
  commodities,
  commodityFilter,
  yearStart,
  yearEnd,
  onClose,
}: TradeInfoPanelProps) {
  const [summary, setSummary] = useState<TradeSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getTradeSummary(iso3, {
      yearStart,
      yearEnd,
      commodity: commodityFilter || undefined,
    })
      .then(setSummary)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [iso3, commodityFilter, yearStart, yearEnd]);

  const commodityMap = Object.fromEntries(
    commodities.map((c) => [c.hs2_code, c.name])
  );

  return (
    <div style={styles.panel}>
      <div style={styles.header}>
        <h3 style={styles.title}>
          {summary?.country.name || iso3}
        </h3>
        <button style={styles.closeBtn} onClick={onClose}>✕</button>
      </div>

      {loading ? (
        <div style={styles.loading}>Loading...</div>
      ) : summary ? (
        <div style={styles.content}>
          {/* Overview */}
          <div style={styles.totals}>
            <div style={styles.totalItem}>
              <div style={styles.totalLabel}>Total Exports</div>
              <div style={{ ...styles.totalValue, color: "#4ade80" }}>
                ${formatValue(summary.total_exports_usd)}
              </div>
            </div>
            <div style={styles.totalItem}>
              <div style={styles.totalLabel}>Total Imports</div>
              <div style={{ ...styles.totalValue, color: "#f87171" }}>
                ${formatValue(summary.total_imports_usd)}
              </div>
            </div>
          </div>
          <div style={styles.meta}>
            {yearStart}–{yearEnd}
            {commodityFilter && ` | ${commodityMap[commodityFilter] || commodityFilter}`}
          </div>

          {/* By Commodity */}
          <div style={styles.sectionTitle}>By Commodity</div>
          <div style={styles.tableHeader}>
            <span style={styles.tableHeaderName}>Commodity</span>
            <span style={styles.tableHeaderVal}>Export</span>
            <span style={styles.tableHeaderVal}>Import</span>
          </div>
          {summary.by_commodity.map((item) => (
            <div key={item.commodity_code} style={styles.tableRow}>
              <span style={styles.tableName}>
                {commodityMap[item.commodity_code] || item.commodity_code}
              </span>
              <span style={{ ...styles.tableVal, color: "#4ade80" }}>
                ${formatValue(item.exports)}
              </span>
              <span style={{ ...styles.tableVal, color: "#f87171" }}>
                ${formatValue(item.imports)}
              </span>
            </div>
          ))}

          {/* Top Partners */}
          <div style={styles.sectionTitle}>Top Partners</div>
          {summary.top_partners.map((partner) => (
            <div key={partner.iso3} style={styles.row}>
              <span style={styles.rowName}>{partner.name}</span>
              <span style={styles.rowValue}>
                ${formatValue(partner.total_value)}
              </span>
            </div>
          ))}
        </div>
      ) : (
        <div style={styles.loading}>No data available</div>
      )}
    </div>
  );
}

function formatValue(value: number): string {
  if (value >= 1e12) return `${(value / 1e12).toFixed(1)}T`;
  if (value >= 1e9) return `${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `${(value / 1e6).toFixed(1)}M`;
  if (value >= 1e3) return `${(value / 1e3).toFixed(1)}K`;
  return value.toFixed(0);
}

const styles: Record<string, React.CSSProperties> = {
  panel: {
    position: "absolute",
    top: 16,
    right: 16,
    width: 340,
    maxHeight: "calc(100vh - 32px)",
    overflowY: "auto",
    background: "rgba(10, 15, 30, 0.94)",
    borderRadius: 12,
    border: "1px solid rgba(100, 150, 255, 0.2)",
    backdropFilter: "blur(10px)",
    zIndex: 200,
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "14px 18px 8px",
  },
  title: {
    fontSize: 15,
    fontWeight: 600,
    color: "#e8f0ff",
    margin: 0,
  },
  closeBtn: {
    background: "transparent",
    border: "none",
    color: "#8899aa",
    fontSize: 18,
    cursor: "pointer",
    padding: "2px 6px",
  },
  loading: {
    padding: 20,
    textAlign: "center" as const,
    color: "#8899aa",
    fontSize: 13,
  },
  content: {
    padding: "8px 18px 18px",
  },
  meta: {
    fontSize: 11,
    color: "#6688aa",
    marginTop: 6,
    marginBottom: 4,
  },
  totals: {
    display: "flex",
    gap: 10,
  },
  totalItem: {
    flex: 1,
    padding: "10px 12px",
    background: "rgba(30, 40, 60, 0.6)",
    borderRadius: 8,
  },
  totalLabel: {
    fontSize: 10,
    color: "#8899aa",
    textTransform: "uppercase" as const,
    letterSpacing: "0.5px",
    marginBottom: 4,
  },
  totalValue: {
    fontSize: 16,
    fontWeight: 700,
  },
  sectionTitle: {
    fontSize: 11,
    color: "#8899aa",
    textTransform: "uppercase" as const,
    letterSpacing: "0.5px",
    marginTop: 14,
    marginBottom: 6,
    paddingTop: 10,
    borderTop: "1px solid rgba(100, 150, 255, 0.1)",
  },
  tableHeader: {
    display: "flex",
    gap: 6,
    marginBottom: 4,
    paddingBottom: 4,
    borderBottom: "1px solid rgba(100,150,255,0.08)",
  },
  tableHeaderName: {
    flex: 2,
    fontSize: 10,
    color: "#6688aa",
    textTransform: "uppercase" as const,
  },
  tableHeaderVal: {
    flex: 1,
    fontSize: 10,
    color: "#6688aa",
    textTransform: "uppercase" as const,
    textAlign: "right" as const,
  },
  tableRow: {
    display: "flex",
    gap: 6,
    padding: "4px 0",
    alignItems: "center",
  },
  tableName: {
    flex: 2,
    fontSize: 12,
    color: "#c0d0e0",
  },
  tableVal: {
    flex: 1,
    fontSize: 11,
    fontWeight: 500,
    textAlign: "right" as const,
  },
  row: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "4px 0",
    fontSize: 12,
  },
  rowName: {
    color: "#c0d0e0",
  },
  rowValue: {
    color: "#e0e8f0",
    fontWeight: 500,
    fontSize: 11,
  },
};
