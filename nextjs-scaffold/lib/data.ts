// Server-side data loader. Imports JSON at build time.
// All reads happen in Server Components.

import { promises as fs } from "node:fs";
import path from "node:path";
import type {
  Locations,
  Meta,
  PengolahanSampah,
  Regulations,
  Timbulan,
  TrafficAccidents,
  TreeIncidents,
  WaterQuality,
} from "./types";

const DATA_DIR = path.join(process.cwd(), "data");

async function readJson<T>(rel: string): Promise<T> {
  const p = path.join(DATA_DIR, rel);
  const raw = await fs.readFile(p, "utf-8");
  return JSON.parse(raw) as T;
}

export const getMeta = () => readJson<Meta>("meta.json");
export const getLocations = () => readJson<Locations>("shared/locations.json");
export const getRegulations = () => readJson<Regulations>("shared/regulations.json");
export const getPengolahanSampah = () => readJson<PengolahanSampah>("pengolahan_sampah.json");
export const getTimbulan = () => readJson<Timbulan>("timbulan.json");
export const getWaterQuality = () => readJson<WaterQuality>("water_quality.json");
export const getTreeIncidents = () => readJson<TreeIncidents>("tree_incidents.json");
export const getTrafficAccidents = () => readJson<TrafficAccidents>("traffic_accidents.json");
