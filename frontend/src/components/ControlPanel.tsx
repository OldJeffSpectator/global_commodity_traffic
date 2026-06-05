import type { CommodityData } from "../types";

interface ControlPanelProps {
  commodities: CommodityData[];
  commodityFilter: string | null;
  onCommodityFilterChange: (code: string | null) => void;
  selectedCountryName: string | null;
}

export default function ControlPanel({
  commodities,
  commodityFilter,
  onCommodityFilterChange,
  selectedCountryName,
}: ControlPanelProps) {
  return (
    <div style={styles.panel}>
      <h2 style={styles.title}>Global Commodity Traffic</h2>

      {selectedCountryName && (
        <div style={styles.selected}>
          Selected: <strong>{selectedCountryName}</strong>
        </div>
      )}

      <div style={styles.section}>
        <label style={styles.label}>Commodity Filter</label>
        <select
          style={styles.select}
          value={commodityFilter || ""}
          onChange={(e) =>
            onCommodityFilterChange(e.target.value || null)
          }
        >
          <option value="">All Commodities</option>
          {commodities.map((c) => (
            <option key={c.hs2_code} value={c.hs2_code}>
              {c.name}
            </option>
          ))}
        </select>
      </div>

      <div style={styles.legend}>
        <div style={styles.legendTitle}>Commodity Colors</div>
        {LEGEND_ITEMS.map(([code, color, name]) => (
          <div key={code} style={styles.legendItem}>
            <span
              style={{ ...styles.legendDot, backgroundColor: color }}
            />
            <span style={styles.legendText}>{name}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

const LEGEND_ITEMS: [string, string, string][] = [
  ["27", "#ff6600", "Mineral fuels & oils"],
  ["10", "#66cc33", "Cereals"],
  ["72", "#999999", "Iron & steel"],
  ["26", "#cc6633", "Ores & minerals"],
  ["31", "#9933cc", "Fertilizers"],
  ["44", "#336600", "Wood"],
  ["17", "#ff99cc", "Sugar"],
  ["76", "#c0c0c0", "Aluminium"],
  ["74", "#cc6600", "Copper"],
  ["39", "#3399ff", "Plastics"],
];

const styles: Record<string, React.CSSProperties> = {
  panel: {
    position: "absolute",
    top: 16,
    left: 16,
    width: 260,
    background: "rgba(10, 15, 30, 0.92)",
    borderRadius: 12,
    padding: 20,
    backdropFilter: "blur(10px)",
    border: "1px solid rgba(100, 150, 255, 0.2)",
    zIndex: 100,
  },
  title: {
    fontSize: 16,
    fontWeight: 700,
    marginBottom: 12,
    color: "#e8f0ff",
  },
  selected: {
    fontSize: 13,
    marginBottom: 12,
    padding: "6px 8px",
    background: "rgba(0, 200, 255, 0.1)",
    borderRadius: 6,
    border: "1px solid rgba(0, 200, 255, 0.3)",
  },
  section: {
    marginBottom: 14,
  },
  label: {
    display: "block",
    fontSize: 11,
    color: "#8899aa",
    marginBottom: 4,
    textTransform: "uppercase" as const,
    letterSpacing: "0.5px",
  },
  select: {
    width: "100%",
    padding: "8px 10px",
    background: "rgba(30, 40, 60, 0.9)",
    border: "1px solid rgba(100, 150, 255, 0.3)",
    borderRadius: 6,
    color: "#e0e8f0",
    fontSize: 13,
    outline: "none",
  },
  legend: {
    marginTop: 16,
    paddingTop: 12,
    borderTop: "1px solid rgba(100, 150, 255, 0.15)",
  },
  legendTitle: {
    fontSize: 11,
    color: "#8899aa",
    marginBottom: 8,
    textTransform: "uppercase" as const,
    letterSpacing: "0.5px",
  },
  legendItem: {
    display: "flex",
    alignItems: "center",
    marginBottom: 4,
  },
  legendDot: {
    width: 10,
    height: 10,
    borderRadius: "50%",
    marginRight: 8,
    flexShrink: 0,
  },
  legendText: {
    fontSize: 11,
    color: "#b0c0d0",
  },
};
