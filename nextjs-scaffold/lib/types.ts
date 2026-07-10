// TypeScript types mirroring data-spec.md v1.0

export type DataQualityFlag = {
  severity: "info" | "warning" | "error";
  message: string;
};

export type Period = { start: string; end: string };

export type DatasetEnvelope = {
  dataset_id: string;
  version: string;
  generated_at: string;
  source_files: string[];
  period: Period;
  data_quality_flags: DataQualityFlag[];
};

// ─── meta.json ───
export type DatasetIndexEntry = {
  id: string;
  label: string;
  route: string;
  icon: string;
  period_label: string;
  primary_kpi: { label: string; value_field: string };
};

export type Meta = {
  dashboard: {
    title: string;
    subtitle: string;
    organization: string;
    owner_email: string;
    url: string;
    version: string;
    last_updated: string;
  };
  datasets: DatasetIndexEntry[];
  color_palette: Record<string, string>;
};

// ─── shared/locations.json ───
export type Location = {
  label: string;
  type: string;
  campus?: string;
  lat?: number;
  lon?: number;
};
export type Locations = { version: string; locations: Record<string, Location> };

// ─── shared/regulations.json ───
export type Regulation = {
  full_name: string;
  short_name: string;
  scope: string;
  year?: number;
  has_class_split?: boolean;
  classes?: string[];
  raw_label_in_source?: string;
};
export type Regulations = { version: string; regulations: Record<string, Regulation> };

// ─── pengolahan_sampah.json ───
export type WasteCategory = "organik" | "anorganik" | "residu";
export type WasteMethod = "kompos" | "rdf" | "maggot" | "dumping";

export type WasteDailyItem = {
  category: WasteCategory;
  incoming_kg: number;
  processed_kg: number;
  residual_kg: number;
  method: WasteMethod | string | null;
  output_kg: number;
  status: string;
};

export type WasteDailyEntry = {
  date: string;
  date_corrected_from_md: boolean;
  items: WasteDailyItem[];
  totals: { incoming_kg: number; processed_kg: number; residual_kg: number };
};

export type WasteMonthlySummary = {
  month: string;
  label: string;
  incoming_kg: number;
  processed_kg: number;
  residual_kg: number;
  output: { kompos_kg: number; rdf_kg: number; maggot_kg: number };
  output_total_kg: number;
  processing_rate_pct: number;
  incoming_by_category_kg?: Record<WasteCategory, number>;
};

export type PengolahanSampah = DatasetEnvelope & {
  unit_default: "kg";
  categories: { id: string; label: string; color_key: string }[];
  processing_methods: { id: string; label: string; for_category: string; color_key: string }[];
  monthly_summary: WasteMonthlySummary[];
  daily_entries: WasteDailyEntry[];
};

// ─── timbulan.json ───
export type TimbulanMonthly = {
  month: string;
  label: string;
  total_kg: number | null;
  organik_kg: number;
  anorganik_residu_kg: number;
  sod_kg: number;
  days_active: number;
  days_in_month: number;
  avg_kg_per_active_day: number | null;
  avg_kg_per_calendar_day: number | null;
  category_breakdown_available: boolean;
};

export type TimbulanDaily = {
  date: string;
  day_of_week: string | null;
  total_kg: number;
  by_category_kg: { organik: number; anorganik_residu: number; sod: number } | null;
  note: string | null;
  quality_flag: string | null;
};

export type Timbulan = DatasetEnvelope & {
  unit_default: "kg";
  vehicle_sources: { id: string; label: string; operator: string; tare_kg: number | null; note?: string }[];
  container_tare_kg: Record<string, number>;
  categories: { id: string; label: string; color_key: string }[];
  monthly_summary: TimbulanMonthly[];
  daily_entries: TimbulanDaily[];
};

// ─── water_quality.json ───
export type Threshold =
  | { type: "max"; max: number }
  | { type: "min"; min: number }
  | { type: "range"; min: number; max: number }
  | { type: "deviation"; max_dev: number; reference?: string }
  | { type: "qualitative"; expected?: string };

export type Measurement = {
  parameter_id: string;
  parameter_label: string;
  category: string | null;
  unit: string | null;
  result: number | string | null;
  result_display: string;
  below_detection_limit: boolean;
  threshold: Threshold | null;
  compliant: boolean | null;
  source_flagged_exceedance: boolean;
  method: string | null;
  compliance_note?: string;
  threshold_gol_2?: Threshold | null;
  compliant_gol_2?: boolean | null;
};

export type WaterReport = {
  report_no: string;
  order_no: string | null;
  sample_code: string | null;
  sample_type: "air_permukaan" | "air_limbah" | "air_sumur";
  location_id: string | null;
  location_label_raw: string;
  coordinates_dms: string | null;
  regulation_id: string | null;
  regulation_raw: string | null;
  sampling_method: string | null;
  sampling_date: string | null;
  received_date: string | null;
  testing_period: { start: string | null; end: string | null } | null;
  report_date: string;
  ambient_temp_c: number | null;
  measurements: Measurement[];
  summary: {
    total_parameters: number;
    compliant_count: number;
    non_compliant_count: number;
    non_compliant_parameters: string[];
    compliance_pct: number | null;
  };
};

export type WaterQuality = DatasetEnvelope & {
  issuing_lab: { name: string; accreditation: string; address: string; head: string };
  parameter_dictionary: Record<string, { label: string; unit: string | null; category: string }>;
  reports: WaterReport[];
  aggregate_summary: {
    by_sample_type: Record<
      string,
      { reports: number; compliance_pct_avg: number | null; common_exceedances: string[] }
    >;
  };
};

// ─── tree_incidents.json ───
export type TreeEventType = "penebangan" | "pemangkasan" | "pohon_roboh" | "pohon_patah" | "unspecified";

export type TreeMonthlyTotal = {
  month: string;
  penebangan: number;
  pemangkasan: number;
  pohon_roboh: number;
  pohon_patah: number;
  total: number;
};

export type TreeLocationGroup = {
  location_id: string;
  monthly: { month: string; events: { type: TreeEventType; count: number }[] }[];
  total: number;
};

export type TreeIncidents = DatasetEnvelope & {
  event_types: { id: TreeEventType; label: string; severity: string }[];
  monthly_totals: TreeMonthlyTotal[];
  yearly_totals: {
    penebangan: number;
    pemangkasan: number;
    pohon_roboh: number;
    pohon_patah: number;
    unspecified: number;
    total: number;
  };
  incidents_by_location: TreeLocationGroup[];
};

// ─── traffic_accidents.json ───
export type VehicleType =
  | "tunggal_motor"
  | "tunggal_mobil"
  | "beam"
  | "tabrak_2roda"
  | "tabrak_2roda_beam"
  | "tabrak_2roda_4roda"
  | "tabrak_4roda_beam"
  | "pejalan_kaki";

export type TrafficYearly = {
  year: number;
  monthly: { month: string; by_type: Record<string, number>; total: number }[];
  total_yearly_computed: number;
  total_yearly_reported?: number;
  ytd_through_month?: string;
};

export type TrafficIncidentDetail = {
  no: number | null;
  year: number;
  month: string;
  type: string;
  location_id: string;
  location_label_raw: string;
  count: number;
  note?: string;
};

export type TrafficAccidents = DatasetEnvelope & {
  vehicle_types: { id: VehicleType; label: string }[];
  yearly: TrafficYearly[];
  incidents_detail: TrafficIncidentDetail[];
  /** @deprecated nama field spec 1.0; dipertahankan agar JSON lama tetap terbaca */
  incidents_detail_2026?: TrafficIncidentDetail[];
};
