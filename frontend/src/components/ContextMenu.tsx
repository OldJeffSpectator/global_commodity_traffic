interface ContextMenuProps {
  x: number;
  y: number;
  countryIso3: string;
  onShowTradeInfo: (iso3: string) => void;
  onClose: () => void;
}

export default function ContextMenu({
  x,
  y,
  countryIso3,
  onShowTradeInfo,
  onClose,
}: ContextMenuProps) {
  return (
    <>
      <div style={styles.overlay} onClick={onClose} onContextMenu={(e) => { e.preventDefault(); onClose(); }} />
      <div style={{ ...styles.menu, left: x, top: y }}>
        <button
          style={styles.menuItem}
          onClick={() => {
            onShowTradeInfo(countryIso3);
            onClose();
          }}
        >
          Show Trade Info
        </button>
        <button style={styles.menuItem} onClick={onClose}>
          Cancel
        </button>
      </div>
    </>
  );
}

const styles: Record<string, React.CSSProperties> = {
  overlay: {
    position: "fixed",
    top: 0,
    left: 0,
    width: "100vw",
    height: "100vh",
    zIndex: 999,
  },
  menu: {
    position: "fixed",
    zIndex: 1000,
    background: "rgba(15, 20, 35, 0.95)",
    border: "1px solid rgba(100, 150, 255, 0.3)",
    borderRadius: 8,
    padding: 4,
    minWidth: 160,
    boxShadow: "0 8px 32px rgba(0, 0, 0, 0.5)",
  },
  menuItem: {
    display: "block",
    width: "100%",
    padding: "10px 14px",
    background: "transparent",
    border: "none",
    color: "#e0e8f0",
    fontSize: 13,
    textAlign: "left" as const,
    cursor: "pointer",
    borderRadius: 4,
    transition: "background 0.15s",
  },
};
