import type {
  CountryData,
  CommodityData,
  TradeResponse,
  TradeSummary,
  RoutesResponse,
  RegionRoutesResponse,
  RegionTradeStats,
  YearRange,
  TransitTradeStats,
  TransitRoutesResponse,
} from "../types";

const BASE_URL = "/api";

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${url}`, options);
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export async function getCountries(): Promise<CountryData[]> {
  return fetchJSON<CountryData[]>("/countries");
}

export async function getCommodities(): Promise<CommodityData[]> {
  return fetchJSON<CommodityData[]>("/commodities");
}

export async function getTradeForCountry(
  iso3: string,
  options?: { year?: number; yearStart?: number; yearEnd?: number; commodity?: string }
): Promise<TradeResponse> {
  const params = new URLSearchParams();
  if (options?.year) params.set("year", String(options.year));
  if (options?.yearStart) params.set("year_start", String(options.yearStart));
  if (options?.yearEnd) params.set("year_end", String(options.yearEnd));
  if (options?.commodity) params.set("commodity", options.commodity);
  const qs = params.toString();
  return fetchJSON<TradeResponse>(`/trade/${iso3}${qs ? `?${qs}` : ""}`);
}

export async function getTradeSummary(
  iso3: string,
  options?: { year?: number; yearStart?: number; yearEnd?: number; commodity?: string }
): Promise<TradeSummary> {
  const params = new URLSearchParams();
  if (options?.year) params.set("year", String(options.year));
  if (options?.yearStart) params.set("year_start", String(options.yearStart));
  if (options?.yearEnd) params.set("year_end", String(options.yearEnd));
  if (options?.commodity) params.set("commodity", options.commodity);
  const qs = params.toString();
  return fetchJSON<TradeSummary>(`/trade/${iso3}/summary${qs ? `?${qs}` : ""}`);
}

export async function getRoutesForCountry(iso3: string): Promise<RoutesResponse> {
  return fetchJSON<RoutesResponse>(`/routes/${iso3}`);
}

export async function getRegionRoutes(regionId: number): Promise<RegionRoutesResponse> {
  return fetchJSON<RegionRoutesResponse>(`/region/${regionId}/routes`);
}

export async function getRegionTradeStats(
  regionId: number,
  options?: { yearStart?: number; yearEnd?: number; commodity?: string }
): Promise<RegionTradeStats> {
  const params = new URLSearchParams();
  if (options?.yearStart) params.set("year_start", String(options.yearStart));
  if (options?.yearEnd) params.set("year_end", String(options.yearEnd));
  if (options?.commodity) params.set("commodity", options.commodity);
  const qs = params.toString();
  return fetchJSON<RegionTradeStats>(`/region/${regionId}/trade-stats${qs ? `?${qs}` : ""}`);
}

export async function getYearRange(): Promise<YearRange> {
  return fetchJSON<YearRange>("/trade/year-range");
}

export async function getTransitTradeStats(
  iso3: string,
  options?: { yearStart?: number; yearEnd?: number; commodity?: string }
): Promise<TransitTradeStats> {
  const params = new URLSearchParams();
  if (options?.yearStart) params.set("year_start", String(options.yearStart));
  if (options?.yearEnd) params.set("year_end", String(options.yearEnd));
  if (options?.commodity) params.set("commodity", options.commodity);
  const qs = params.toString();
  return fetchJSON<TransitTradeStats>(`/country/${iso3}/transit${qs ? `?${qs}` : ""}`);
}

export async function getTransitRoutes(iso3: string): Promise<TransitRoutesResponse> {
  return fetchJSON<TransitRoutesResponse>(`/country/${iso3}/transit-routes`);
}

