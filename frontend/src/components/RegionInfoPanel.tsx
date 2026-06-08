import { useEffect, useState } from "react";
import type { RegionTradeStats } from "../types";
import { getRegionTradeStats } from "../services/api";

interface RegionInfoPanelProps {
  regionId: number;
  regionName: string;
  yearStart?: number;
  yearEnd?: number;
  commodityFilter?: string | null;
  onClose: () => void;
}

export default function RegionInfoPanel({
  regionId,
  regionName,
  yearStart,
  yearEnd,
  commodityFilter,
  onClose,
}: RegionInfoPanelProps) {
  const [stats, setStats] = useState<RegionTradeStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getRegionTradeStats(regionId, {
      yearStart,
      yearEnd,
      commodity: commodityFilter || undefined,
    })
      .then(setStats)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [regionId, yearStart, yearEnd, commodityFilter]);

  return (
    <div style={styles.panel}>
      <div style={styles.header}>
        <h3 style={styles.title}>{regionName}</h3>
        <button style={styles.closeBtn} onClick={onClose}>✕</button>
      </div>

      {loading ? (
        <div style={styles.loading}>Loading...</div>
      ) : stats ? (
        <>
          <div style={styles.statsRow}>
            <span style={styles.statLabel}>Routes passing through:</span>
            <span style={styles.statValue}>{stats.route_count}</span>
          </div>

          {stats.top_pairs.length > 0 && (
            <>
              <div style={styles.sectionTitle}>Top Trade Pairs</div>
              {stats.top_pairs.map((pair, i) => (
                <div key={i} style={styles.pairBlock}>
                  <div style={styles.pairRow}>
                    <span style={styles.pairNames}>
                      {pair.origin_name} ↔ {pair.destination_name}
                    </span>
                    <span style={styles.pairValue}>${formatValue(pair.total_value)}</span>
                  </div>
                  {pair.top_commodities && pair.top_commodities.length > 0 && (
                    <div style={styles.commodities}>
                      {pair.top_commodities.map((c, j) => (
                        <div key={j} style={styles.commodityRow}>
                          <span style={styles.commodityName}>{c.name}</span>
                          <span style={styles.commodityDir}>
                            <span style={{ color: "#4ade80" }}>
                              {pair.origin_name.slice(0, 3)}→{pair.destination_name.slice(0, 3)}{" "}
                              ${formatValue(c.fwd_value)}
                            </span>
                            {" | "}
                            <span style={{ color: "#f8a060" }}>
                              {pair.destination_name.slice(0, 3)}→{pair.origin_name.slice(0, 3)}{" "}
                              ${formatValue(c.rev_value)}
                            </span>
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </>
          )}
        </>
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
    width: 360,
    maxHeight: "80vh",
    overflowY: "auto",
    background: "rgba(10, 15, 30, 0.95)",
    borderRadius: 12,
    padding: 20,
    backdropFilter: "blur(10px)",
    border: "1px solid rgba(100, 200, 255, 0.3)",
    zIndex: 200,
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 14,
  },
  title: {
    fontSize: 15,
    fontWeight: 700,
    color: "#e8f0ff",
    margin: 0,
  },
  closeBtn: {
    background: "none",
    border: "none",
    color: "#8899aa",
    fontSize: 18,
    cursor: "pointer",
    padding: "2px 6px",
  },
  loading: {
    color: "#8899aa",
    fontSize: 13,
    textAlign: "center" as const,
    padding: 20,
  },
  statsRow: {
    display: "flex",
    justifyContent: "space-between",
    marginBottom: 8,
    fontSize: 13,
  },
  statLabel: { color: "#8899aa" },
  statValue: { color: "#e0e8f0", fontWeight: 600 },
  sectionTitle: {
    fontSize: 11,
    color: "#8899aa",
    marginTop: 12,
    marginBottom: 8,
    textTransform: "uppercase" as const,
    letterSpacing: "0.5px",
    borderTop: "1px solid rgba(100, 150, 255, 0.15)",
    paddingTop: 10,
  },
  pairBlock: {
    marginBottom: 10,
    padding: "8px 10px",
    background: "rgba(30, 40, 60, 0.4)",
    borderRadius: 6,
  },
  pairRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    fontSize: 12,
    marginBottom: 2,
  },
  pairNames: { color: "#b0c0d0", flex: 1 },
  pairValue: { color: "#66ccff", fontWeight: 600, marginLeft: 8, fontSize: 12 },
  commodities: {
    marginTop: 5,
    paddingTop: 5,
    borderTop: "1px solid rgba(100,150,255,0.1)",
  },
  commodityRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "3px 0",
    fontSize: 10,
    gap: 6,
  },
  commodityName: { color: "#99aacc", minWidth: 60, flex: "0 0 auto" },
  commodityDir: { color: "#8899aa", fontSize: 10, textAlign: "right" as const },
};
