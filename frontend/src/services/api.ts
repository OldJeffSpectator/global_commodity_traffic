import type {
  CountryData,
  CommodityData,
  TradeResponse,
  TradeSummary,
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
  year?: number,
  commodity?: string
): Promise<TradeResponse> {
  const params = new URLSearchParams();
  if (year) params.set("year", String(year));
  if (commodity) params.set("commodity", commodity);
  const qs = params.toString();
  return fetchJSON<TradeResponse>(`/trade/${iso3}${qs ? `?${qs}` : ""}`);
}

export async function getTradeSummary(
  iso3: string,
  year?: number
): Promise<TradeSummary> {
  const params = new URLSearchParams();
  if (year) params.set("year", String(year));
  const qs = params.toString();
  return fetchJSON<TradeSummary>(`/trade/${iso3}/summary${qs ? `?${qs}` : ""}`);
}

