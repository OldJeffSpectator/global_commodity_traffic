import type { CommodityData, YearRange } from "../types";
import type { ViewMode } from "../hooks/useTradeData";

interface ControlPanelProps {
  commodities: CommodityData[];
  commodityFilter: string | null;
  onCommodityFilterChange: (code: string | null) => void;
  selectedCountryName: string | null;
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
  yearRange: YearRange;
  selectedYearStart: number;
  selectedYearEnd: number;
  onYearRangeChange: (start: number, end: number) => void;
}

export default function ControlPanel({
  commodities,
  commodityFilter,
  onCommodityFilterChange,
  selectedCountryName,
  viewMode,
  onViewModeChange,
  yearRange,
  selectedYearStart,
  selectedYearEnd,
  onYearRangeChange,
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
        <label style={styles.label}>View Mode</label>
        <div style={styles.toggleGroup}>
          <button
            style={{
              ...styles.toggleBtn,
              ...(viewMode === "arcs" ? styles.toggleActive : {}),
            }}
            onClick={() => onViewModeChange("arcs")}
          >
            Parabola Arcs
          </button>
          <button
            style={{
              ...styles.toggleBtn,
              ...(viewMode === "routes" ? styles.toggleActive : {}),
            }}
            onClick={() => onViewModeChange("routes")}
          >
            Trade Routes
          </button>
        </div>
      </div>

      <div style={styles.section}>
        <label style={styles.label}>
          Year Range: {selectedYearStart} – {selectedYearEnd}
        </label>
        <div style={styles.sliderContainer}>
          <span style={styles.sliderLabel}>{yearRange.min_year}</span>
          <div style={styles.sliderPair}>
            <input
              type="range"
              min={yearRange.min_year}
              max={yearRange.max_year}
              value={selectedYearStart}
              onChange={(e) => {
                const v = Number(e.target.value);
                if (v <= selectedYearEnd) onYearRangeChange(v, selectedYearEnd);
              }}
              style={styles.slider}
            />
            <input
              type="range"
              min={yearRange.min_year}
              max={yearRange.max_year}
              value={selectedYearEnd}
              onChange={(e) => {
                const v = Number(e.target.value);
                if (v >= selectedYearStart) onYearRangeChange(selectedYearStart, v);
              }}
              style={styles.slider}
            />
          </div>
          <span style={styles.sliderLabel}>{yearRange.max_year}</span>
        </div>
      </div>

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
        <div style={styles.legendTitle}>
          {viewMode === "arcs" ? "Commodity Colors" : "Route Intensity"}
        </div>
        {viewMode === "arcs" ? (
          LEGEND_ITEMS.map(([code, color, name]) => (
            <div key={code} style={styles.legendItem}>
              <span style={{ ...styles.legendDot, backgroundColor: color }} />
              <span style={styles.legendText}>{name}</span>
            </div>
          ))
        ) : (
          ROUTE_LEGEND.map(([color, label]) => (
            <div key={label} style={styles.legendItem}>
              <span style={{ ...styles.legendDot, backgroundColor: color }} />
              <span style={styles.legendText}>{label}</span>
            </div>
          ))
        )}
      </div>

      <div style={styles.legend}>
        <div style={styles.legendTitle}>Region Markers</div>
        {REGION_LEGEND.map(([color, label]) => (
          <div key={label} style={styles.legendItem}>
            <span style={{ ...styles.legendRing, borderColor: color }} />
            <span style={styles.legendText}>{label}</span>
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

const ROUTE_LEGEND: [string, string][] = [
  ["#00ffcc", "High trade volume"],
  ["#00aaff", "Medium trade volume"],
  ["#4488cc", "Low trade volume"],
];

const REGION_LEGEND: [string, string][] = [
  ["#3c8cc8", "Ocean (click for routes)"],
  ["#50aaDc", "Sea"],
  ["#ffc850", "Strait"],
  ["#ff8c3c", "Canal"],
];

const styles: Record<string, React.CSSProperties> = {
  panel: {
    position: "absolute",
    top: 16,
    left: 16,
    width: 260,
    maxHeight: "calc(100vh - 32px)",
    overflowY: "auto",
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
  sliderContainer: {
    display: "flex",
    alignItems: "center",
    gap: 6,
  },
  sliderPair: {
    flex: 1,
    display: "flex",
    flexDirection: "column" as const,
    gap: 10,
  },
  slider: {
    width: "100%",
    height: 4,
    accentColor: "#00aaff",
    cursor: "pointer",
  },
  sliderLabel: {
    fontSize: 10,
    color: "#6688aa",
    minWidth: 28,
    textAlign: "center" as const,
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
  legendRing: {
    width: 10,
    height: 10,
    borderRadius: "50%",
    marginRight: 8,
    flexShrink: 0,
    border: "2px dashed",
    background: "transparent",
  },
  legendText: {
    fontSize: 11,
    color: "#b0c0d0",
  },
  toggleGroup: {
    display: "flex",
    gap: 4,
  },
  toggleBtn: {
    flex: 1,
    padding: "6px 8px",
    fontSize: 11,
    fontWeight: 600,
    border: "1px solid rgba(100, 150, 255, 0.3)",
    borderRadius: 6,
    background: "rgba(30, 40, 60, 0.9)",
    color: "#8899aa",
    cursor: "pointer",
  },
  toggleActive: {
    background: "rgba(0, 150, 255, 0.25)",
    borderColor: "rgba(0, 200, 255, 0.6)",
    color: "#e0f0ff",
  },
};
