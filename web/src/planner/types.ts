// Written with AI assistance (Claude Code). See AI_USE.md.
// Shapes of the packaged site (written by `ariadne package`, web/public/sites/<site>/).
import type { PlanStorm } from "../core/plan/storm";

export type Label = "MEASURED" | "DERIVED" | "MODELED" | "PLACEHOLDER";

export interface LegendEntry {
  value?: number;
  color: number[];
  label: string;
}

export interface Layer {
  id: string;
  title: string;
  file: string;
  file_detail?: string;
  bounds_detail_m?: [number, number, number, number];
  kind: "raster" | "vector";
  bounds_m?: [number, number, number, number];
  resolution_m: number | null;
  sources: string[];
  date: string;
  label: Label;
  legend: LegendEntry[] | null;
  group: string;
  description: string;
  default_visible: boolean;
  opacity: number;
  pattern?: string;
}

export interface Totals {
  transects: number;
  stations: number;
  science_value: number;
  minutes: number;
  consumables_min: number;
  relative_dose_min: number;
  distance_m: number;
  min_thread_margin_min: number;
  worst_minutes_to_shelter: number;
  longest_comm_shadow_min: number;
  rover_moves?: number;
  label: Label;
}

export interface RoverPlan {
  relays: { id: string; xy_m: [number, number]; drive_from_staging_min: number }[];
  moves: { before_transect: number; from_relay: number; to_relay: number; drive_min: number;
    when: string }[];
  ends_at: string;
  label: Label;
}

export interface Station {
  id: string;
  role: string;
  transect: string;
  xy_m: [number, number];
  value: number;
  service_min: number;
  label: Label;
  relay?: string;
  transect_source_id?: number;
}

export interface Leg {
  from: string;
  to: string;
  path_xy_m: [number, number][];
  minutes: number;
  consumables_min: number;
  relative_dose: number;
}

export interface Timeline {
  margin: { t_min: number; margin_min: number }[];
  stations: { id: string; start_min: number; end_min: number }[];
  comm_shadows: { start_min: number; end_min: number }[];
  sun_elevation_deg?: { t_min: number; deg: number }[];
}

export interface Plan {
  site: string;
  scenario: { preset: string; reserve_min: number; shelter_max_min: number; eva_max_min: number;
    start_utc: string | null; start_note?: string };
  stations: Station[];
  legs: Leg[];
  margins: { t_min: number; c_left: number; c_home: number | null; c_reserve: number;
    xy_m: [number, number]; minutes_to_rover?: number | null; leg?: number;
    station?: number | null }[];
  checks: Record<string, string>;
  totals: Totals;
  timeline: Timeline;
  rover?: RoverPlan;
  storm?: PlanStorm | null;
}

export interface Photo {
  imageid: string;
  instrument: string;
  sol: number;
  xy_m: [number, number];
  view_azimuth_deg: number;
  view_elevation_deg: number;
  file: string;
  credit: string;
  label: Label;
  show_top_fraction: number;
}

export interface TerrainChunk {
  rows_cols: [number, number, number, number];
  files: { fine: string; coarse: string };
  shapes: { fine: [number, number]; coarse: [number, number] };
}

export interface Terrain {
  bounds_m: [number, number, number, number];
  resolution_m: number;
  coarse_factor: number;
  chunk_cells: number;
  z0: number;
  scale: number;
  texture: string;
  chunks: TerrainChunk[];
  label: Label;
}

export interface Manifest {
  site: string;
  title: string;
  pipeline_version: string;
  bounds_m: [number, number, number, number];
  staging_xy_m: [number, number];
  layers: Layer[];
  plans: { preset: string; file: string; title: string; totals: Totals }[];
  terrain: Terrain;
  photos: Photo[];
  eye_height_m: { value: number; label: Label; source: string };
  assumptions?: Assumption[];
  site_notes?: SiteNote[];
  validation?: string;
}

export interface Assumption {
  group: string;
  key: string;
  title: string;
  value: number | string | number[];
  label: Label;
  note: string;
}

export interface SiteNote {
  id: string;
  site: string;
  title: string;
  text: string;
  label: Label;
  source: string;
}

export interface ValidationCheck {
  id: string;
  title: string;
  status: string;
  target?: string;
  reference?: string;
  label?: string;
  note?: string;
  reason?: string;
  phase?: number;
  result?: unknown;
}

export interface Validation {
  title: string;
  pipeline_version: string;
  generated_utc: string;
  note: string;
  site_notes?: SiteNote[];
  checks: ValidationCheck[];
}

export const PRESET_TITLES: Record<string, string> = {
  safest: "Safest",
  balanced: "Balanced",
  most_science: "Most science",
};
