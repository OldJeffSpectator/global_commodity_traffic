export interface CountryData {
  iso3: string;
  name: string;
  centroid_lat: number;
  centroid_lng: number;
}

export interface CommodityData {
  hs2_code: string;
  name: string;
  category: string;
}

export interface TradeRecord {
  partner_iso3: string;
  partner_name: string;
  partner_lat: number;
  partner_lng: number;
  commodity_code: string;
  year: number;
  export_value_usd: number;
  import_value_usd: number;
  weight_kg: number;
}

export interface TradeResponse {
  country: {
    iso3: string;
    name: string;
    lat: number;
    lng: number;
  };
  trades: TradeRecord[];
}

export interface TradeSummary {
  country: { iso3: string; name: string };
  total_exports_usd: number;
  total_imports_usd: number;
  by_commodity: Array<{
    commodity_code: string;
    exports: number;
    imports: number;
  }>;
  top_partners: Array<{
    iso3: string;
    name: string;
    total_value: number;
  }>;
}

export interface ArcData {
  startLat: number;
  startLng: number;
  endLat: number;
  endLng: number;
  color: string;
  opacity: number;
  stroke: number;
  label: string;
  partner_iso3: string;
  value: number;
}

export interface RouteSegment {
  sequence: number;
  region_id: number;
  name: string;
  type: string;
  center_lat: number;
  center_lng: number;
}

export interface TradeRouteData {
  partner_iso3: string;
  partner_name: string;
  total_cost: number;
  transport_mode: string;
  region_names: string[];
  region_centers: Array<{ lat: number; lng: number }>;
  path_coords: Array<[number, number]>;
}

export interface RoutesResponse {
  country: string;
  routes: TradeRouteData[];
}

export interface PathData {
  points: Array<{ lat: number; lng: number }>;
  color: string;
  opacity: number;
  stroke: number;
  label: string;
  partner_iso3: string;
  value: number;
}
