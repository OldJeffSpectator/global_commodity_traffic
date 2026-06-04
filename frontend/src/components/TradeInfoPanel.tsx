import { useEffect, useState } from "react";
import type { TradeSummary, CommodityData } from "../types";
import { getTradeSummary } from "../services/api";

interface TradeInfoPanelProps {
  iso3: string;
  commodities: CommodityData[];
  onClose: () => void;
}

export default function TradeInfoPanel({
  iso3,
  commodities,
  onClose,
}: TradeInfoPanelProps) {
  const [summary, setSummary] = useState<TradeSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getTradeSummary(iso3)
      .then(setSummary)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [iso3]);

  const commodityMap = Object.fromEntries(
    commodities.map((c) => [c.hs2_code, c.name])
  );

  return (
    <div style={styles.panel}>
      <div style={styles.header}>
        <h3 style={styles.title}>
          {summary?.country.name || iso3} - Trade Info
        </h3>
        <button style={styles.closeBtn} onClick={onClose}>
          &times;
        </button>
      </div>

      {loading ? (
        <div style={styles.loading}>Loading...</div>
      ) : summary ? (
        <div style={styles.content}>
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

          <div style={styles.section}>
            <div style={styles.sectionTitle}>By Commodity</div>
            {summary.by_commodity.map((item) => (
              <div key={item.commodity_code} style={styles.row}>
                <span style={styles.rowName}>
                  {commodityMap[item.commodity_code] || item.commodity_code}
                </span>
                <span style={styles.rowValue}>
                  <span style={{ color: "#4ade80" }}>
                    ${formatValue(item.exports)}
                  </span>
                  {" / "}
                  <span style={{ color: "#f87171" }}>
                    ${formatValue(item.imports)}
                  </span>
                </span>
              </div>
            ))}
          </div>

          <div style={styles.section}>
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
    width: 320,
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
    padding: "16px 20px",
    borderBottom: "1px solid rgba(100, 150, 255, 0.15)",
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
    fontSize: 22,
    cursor: "pointer",
    lineHeight: 1,
  },
  loading: {
    padding: 20,
    textAlign: "center" as const,
    color: "#8899aa",
    fontSize: 13,
  },
  content: {
    padding: "12px 20px 20px",
  },
  totals: {
    display: "flex",
    gap: 12,
    marginBottom: 16,
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
  section: {
    marginBottom: 14,
  },
  sectionTitle: {
    fontSize: 11,
    color: "#8899aa",
    textTransform: "uppercase" as const,
    letterSpacing: "0.5px",
    marginBottom: 8,
    paddingBottom: 4,
    borderBottom: "1px solid rgba(100, 150, 255, 0.1)",
  },
  row: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "5px 0",
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
