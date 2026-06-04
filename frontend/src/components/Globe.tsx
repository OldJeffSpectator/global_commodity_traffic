import { useRef, useState, useEffect, useCallback } from "react";
import GlobeGL from "react-globe.gl";
import type { ArcData } from "../types";

interface GlobeProps {
  arcs: ArcData[];
  selectedCountry: string | null;
  onCountryClick: (iso3: string | null) => void;
  onCountryRightClick: (iso3: string, x: number, y: number) => void;
}

interface GeoFeature {
  type: string;
  properties: Record<string, unknown>;
  geometry: Record<string, unknown>;
}

export default function Globe({
  arcs,
  selectedCountry,
  onCountryClick,
  onCountryRightClick,
}: GlobeProps) {
  const globeRef = useRef<any>(null);
  const [countries, setCountries] = useState<GeoFeature[]>([]);
  const [hoverCountry, setHoverCountry] = useState<GeoFeature | null>(null);

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
        // Fallback: load from static public folder
        fetch(
          "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson"
        )
          .then((r) => r.json())
          .then((data) => setCountries(data.features));
      });
  }, []);

  useEffect(() => {
    if (globeRef.current) {
      globeRef.current.pointOfView({ altitude: 2.5 }, 0);
      const controls = globeRef.current.controls();
      if (controls) {
        controls.autoRotate = true;
        controls.autoRotateSpeed = 0.3;
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
        // Stop auto-rotation when a country is selected
        if (globeRef.current) {
          const controls = globeRef.current.controls();
          if (controls) controls.autoRotate = false;
        }
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

      if (iso3 === selectedCountry) {
        return "rgba(0, 200, 255, 0.6)";
      }
      if (f === hoverCountry) {
        return "rgba(100, 180, 255, 0.35)";
      }
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
      arcsData={arcs}
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
      width={window.innerWidth}
      height={window.innerHeight}
    />
  );
}
