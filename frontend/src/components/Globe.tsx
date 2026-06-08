import { useRef, useState, useEffect, useCallback, useMemo } from "react";
import GlobeGL from "react-globe.gl";
import type { ArcData, PathData, RegionData } from "../types";
import type { ViewMode } from "../hooks/useTradeData";

function useThrottledState<T>(initial: T, ms: number): [T, (val: T) => void] {
  const [state, setState] = useState<T>(initial);
  const lastUpdate = useRef(0);
  const pending = useRef<ReturnType<typeof setTimeout> | null>(null);

  const throttledSet = useCallback((val: T) => {
    const now = Date.now();
    if (now - lastUpdate.current >= ms) {
      lastUpdate.current = now;
      setState(val);
    } else {
      if (pending.current) clearTimeout(pending.current);
      pending.current = setTimeout(() => {
        lastUpdate.current = Date.now();
        setState(val);
      }, ms - (now - lastUpdate.current));
    }
  }, [ms]);

  return [state, throttledSet];
}

interface GlobeProps {
  arcs: ArcData[];
  paths: PathData[];
  viewMode: ViewMode;
  selectedCountry: string | null;
  onCountryClick: (iso3: string | null) => void;
  onCountryRightClick: (iso3: string, x: number, y: number) => void;
  onRegionClick: (region: RegionData) => void;
  onRegionRightClick: (region: RegionData, x: number, y: number) => void;
}

interface GeoFeature {
  type: string;
  properties: Record<string, unknown>;
  geometry: Record<string, unknown>;
}

const REGION_TYPE_COLORS: Record<string, string> = {
  ocean: "rgba(60, 140, 200, 0.7)",
  sea: "rgba(80, 170, 220, 0.75)",
  strait: "rgba(255, 200, 80, 0.9)",
  canal: "rgba(255, 140, 60, 0.9)",
  land_corridor: "rgba(140, 220, 100, 0.7)",
};

const REGION_TYPE_SIZES: Record<string, number> = {
  ocean: 0.9,
  sea: 0.6,
  strait: 0.45,
  canal: 0.45,
  land_corridor: 0.4,
};

const POINT_COLORS: Record<string, string> = {
  ocean: "#1a3d5c",
  sea: "#1e4a5e",
  strait: "#5c4a10",
  canal: "#5c2e0a",
  land_corridor: "#2a4a1a",
};

const RING_SIZES: Record<string, number> = {
  ocean: 2.5,
  sea: 1.5,
  strait: 1.0,
  canal: 1.0,
  land_corridor: 0.8,
};

export default function Globe({
  arcs,
  paths,
  viewMode,
  selectedCountry,
  onCountryClick,
  onCountryRightClick,
  onRegionClick,
  onRegionRightClick,
}: GlobeProps) {
  const globeRef = useRef<any>(null);
  const [countries, setCountries] = useState<GeoFeature[]>([]);
  const [hoverCountry, setHoverCountry] = useThrottledState<GeoFeature | null>(null, 80);
  const [regions, setRegions] = useState<RegionData[]>([]);

  useEffect(() => {
    fetch("/api/countries-geojson")
      .catch(() => fetch("/countries.geojson"))
      .then((res) => {
        if (!res.ok) return fetch("/countries.geojson");
        return res;
      })
      .then((res) => res.json())
      .then((data) => setCountries(data.features))
      .catch(() => {
        fetch(
          "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson"
        )
          .then((r) => r.json())
          .then((data) => setCountries(data.features));
      });
  }, []);

  useEffect(() => {
    fetch("/api/regions")
      .then((res) => res.json())
      .then((data: RegionData[]) => setRegions(data))
      .catch(console.error);
  }, []);

  useEffect(() => {
    if (globeRef.current) {
      globeRef.current.pointOfView({ altitude: 2.5 }, 0);
      const controls = globeRef.current.controls();
      if (controls) {
        controls.autoRotate = false;
      }
    }
  }, []);

  const handlePolygonClick = useCallback(
    (polygon: object | null) => {
      if (!polygon) {
        onCountryClick(null);
        return;
      }
      const feat = polygon as GeoFeature;
      const iso3 =
        (feat.properties.ISO_A3 as string) ||
        (feat.properties.ADM0_A3 as string);
      if (iso3 && iso3 !== "-99") {
        onCountryClick(iso3);
      }
    },
    [onCountryClick]
  );

  const handlePolygonRightClick = useCallback(
    (polygon: object | null, event: MouseEvent) => {
      event.preventDefault();
      if (!polygon) return;
      const feat = polygon as GeoFeature;
      const iso3 =
        (feat.properties.ISO_A3 as string) ||
        (feat.properties.ADM0_A3 as string);
      if (iso3 && iso3 !== "-99") {
        onCountryRightClick(iso3, event.clientX, event.clientY);
      }
    },
    [onCountryRightClick]
  );

  const getPolygonColor = useCallback(
    (feat: object) => {
      const f = feat as GeoFeature;
      const iso3 =
        (f.properties.ISO_A3 as string) || (f.properties.ADM0_A3 as string);
      if (iso3 === selectedCountry) return "rgba(0, 200, 255, 0.6)";
      if (f === hoverCountry) return "rgba(100, 180, 255, 0.35)";
      return "rgba(60, 80, 120, 0.25)";
    },
    [selectedCountry, hoverCountry]
  );

  const getPolygonSideColor = useCallback(
    (feat: object) => {
      const f = feat as GeoFeature;
      const iso3 =
        (f.properties.ISO_A3 as string) || (f.properties.ADM0_A3 as string);
      if (iso3 === selectedCountry) return "rgba(0, 200, 255, 0.4)";
      if (f === hoverCountry) return "rgba(100, 180, 255, 0.2)";
      return "rgba(40, 60, 90, 0.15)";
    },
    [selectedCountry, hoverCountry]
  );

  const getPolygonStrokeColor = useCallback(
    (feat: object) => {
      const f = feat as GeoFeature;
      const iso3 =
        (f.properties.ISO_A3 as string) || (f.properties.ADM0_A3 as string);
      if (iso3 === selectedCountry) return "#00d4ff";
      if (f === hoverCountry) return "#6ab4ff";
      return "#334466";
    },
    [selectedCountry, hoverCountry]
  );

  // Memoize arcs data so hover doesn't restart animations
  const arcsDataStable = useMemo(
    () => (viewMode === "arcs" ? arcs : []),
    [arcs, viewMode]
  );

  // Memoize paths data so hover doesn't restart animations
  const pathsDataStable = useMemo(() => {
    if (viewMode !== "routes") return [];
    return paths.map((p) => ({
      coords: p.points.map((pt) => [pt.lat, pt.lng]),
      color: p.color,
      opacity: p.opacity,
      stroke: p.stroke,
      label: p.label,
    }));
  }, [paths, viewMode]);

  // Region rings data (water regions only - no land corridors)
  const ringsData = useMemo(
    () => regions.filter((r) => r.type !== "land_corridor"),
    [regions]
  );

  return (
    <GlobeGL
      ref={globeRef}
      globeImageUrl="//unpkg.com/three-globe/example/img/earth-dark.jpg"
      backgroundImageUrl="//unpkg.com/three-globe/example/img/night-sky.png"
      polygonsData={countries}
      polygonCapColor={getPolygonColor}
      polygonSideColor={getPolygonSideColor}
      polygonStrokeColor={getPolygonStrokeColor}
      polygonAltitude={(feat: object) => {
        const f = feat as GeoFeature;
        const iso3 =
          (f.properties.ISO_A3 as string) || (f.properties.ADM0_A3 as string);
        if (iso3 === selectedCountry) return 0.02;
        if (f === hoverCountry) return 0.01;
        return 0.005;
      }}
      polygonLabel={(feat: object) => {
        const f = feat as GeoFeature;
        return `<div style="background:rgba(0,0,0,0.8);padding:6px 10px;border-radius:4px;font-size:13px;">${f.properties.NAME || f.properties.ADMIN}</div>`;
      }}
      onPolygonClick={handlePolygonClick}
      onPolygonRightClick={handlePolygonRightClick}
      onPolygonHover={(polygon: object | null) =>
        setHoverCountry(polygon as GeoFeature | null)
      }
      // Arcs (parabola mode)
      arcsData={arcsDataStable}
      arcStartLat={(d: object) => (d as ArcData).startLat}
      arcStartLng={(d: object) => (d as ArcData).startLng}
      arcEndLat={(d: object) => (d as ArcData).endLat}
      arcEndLng={(d: object) => (d as ArcData).endLng}
      arcColor={(d: object) => {
        const arc = d as ArcData;
        return [`${arc.color}`, `${arc.color}`];
      }}
      arcDashLength={0.4}
      arcDashGap={0.2}
      arcDashAnimateTime={2000}
      arcStroke={(d: object) => (d as ArcData).stroke}
      arcLabel={(d: object) => {
        const arc = d as ArcData;
        return `<div style="background:rgba(0,0,0,0.85);padding:6px 10px;border-radius:4px;font-size:12px;">${arc.label}</div>`;
      }}
      // Paths (trade route mode)
      pathsData={pathsDataStable}
      pathPoints="coords"
      pathPointLat={(p: number[]) => p[0]}
      pathPointLng={(p: number[]) => p[1]}
      pathColor={(d: object) => (d as { color: string }).color}
      pathStroke={(d: object) => (d as { stroke: number }).stroke}
      pathDashLength={0.6}
      pathDashGap={0.3}
      pathDashAnimateTime={3000}
      pathLabel={(d: object) => {
        const path = d as { label: string };
        return `<div style="background:rgba(0,0,0,0.85);padding:6px 10px;border-radius:4px;font-size:12px;max-width:300px;">${path.label}</div>`;
      }}
      // Region points (clickable ocean/sea/strait markers)
      pointsData={ringsData}
      pointLat={(d: object) => (d as RegionData).center_lat}
      pointLng={(d: object) => (d as RegionData).center_lng}
      pointColor={(d: object) => POINT_COLORS[(d as RegionData).type] || "#1a3355"}
      pointRadius={(d: object) => RING_SIZES[(d as RegionData).type] || 1.0}
      pointAltitude={0.01}
      pointLabel={(d: object) => {
        const r = d as RegionData;
        return `<div style="background:rgba(0,0,0,0.85);padding:6px 10px;border-radius:4px;font-size:12px;">${r.name} <span style="color:#8899aa">(${r.type})</span><br/><span style="color:#66ccff;font-size:10px;">Click: show routes | Right-click: trade stats</span></div>`;
      }}
      onPointClick={(point: object) => {
        const r = point as RegionData;
        onRegionClick(r);
      }}
      onPointRightClick={(point: object, event: MouseEvent) => {
        event.preventDefault();
        const r = point as RegionData;
        onRegionRightClick(r, event.clientX, event.clientY);
      }}
      // Animated rings for visual effect around region points
      ringsData={ringsData}
      ringLat={(d: object) => (d as RegionData).center_lat}
      ringLng={(d: object) => (d as RegionData).center_lng}
      ringColor={(d: object) => {
        const colors: Record<string, string> = {
          ocean: "#3c8cc8", sea: "#50aaDc", strait: "#ffc850", canal: "#ff8c3c", land_corridor: "#8cdc64"
        };
        return colors[(d as RegionData).type] || "#66aaff";
      }}
      ringMaxRadius={(d: object) => RING_SIZES[(d as RegionData).type] || 1.5}
      ringPropagationSpeed={0.5}
      ringRepeatPeriod={3000}
      // Region labels (ocean/sea/strait/canal names)
      labelsData={regions}
      labelLat={(d: object) => (d as RegionData).center_lat}
      labelLng={(d: object) => (d as RegionData).center_lng}
      labelText={(d: object) => (d as RegionData).name}
      labelSize={(d: object) => REGION_TYPE_SIZES[(d as RegionData).type] || 0.5}
      labelColor={(d: object) => REGION_TYPE_COLORS[(d as RegionData).type] || "rgba(150,200,255,0.6)"}
      labelDotRadius={0}
      labelAltitude={0.025}
      labelResolution={3}
      width={window.innerWidth}
      height={window.innerHeight}
    />
  );
}
