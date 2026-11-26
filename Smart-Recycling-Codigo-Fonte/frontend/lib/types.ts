export const BASE = "/smart_recycling";
export type Reading = {
  id: number | string;
  event_type?: string;
  object_id?: string;
  data_current?: boolean;
  organic_bin_distance_cm?: number | null;
  recyclable_bin_distance_cm?: number | null;
  timestamp: string;
  device_id: string;
  material: "organico" | "reciclavel" | "indefinido";
  confidence: number | null;
  metal: boolean | null;
  infrared: number | null;
  color_r: number | null;
  color_g: number | null;
  color_b: number | null;
  distance_cm: number | null;
  organic_fill_pct: number | null;
  recyclable_fill_pct: number | null;
  organic_weight_g: number | null;
  recyclable_weight_g: number | null;
  conveyor_running: boolean | null;
  servo_position_deg: number | null;
};
export type Summary = {
  total: number;
  organic: number;
  recyclable: number;
  undefined: number;
  latest: Reading | null;
  latest_classification?: Reading | null;
  legacy_readings?: number;
  simulation_mode: boolean;
};
export type DeviceState = {
  device_id: string;
  role: string;
  last_seen: string;
  online: boolean;
  component_status?: Record<string, boolean | null>;
  components_current?: boolean;
};
export type BinState = {
  codigo: "organicos" | "reciclaveis";
  ocupacao_pct: number | null;
  peso_gramas: number | null;
  distancia_cm: number | null;
  timestamp: string | null;
  estado: string;
};
export type DashboardData = {
  bins?: BinState[];
  summary: Summary;
  readings: Reading[];
  devices?: DeviceState[];
};
export const materials: Record<string, string> = {
  organico: "Orgânico",
  reciclavel: "Reciclável",
  indefinido: "Não identificado",
};
export const number = (value: number | null | undefined, unit = "") =>
  value == null
    ? "Indisponível"
    : value.toLocaleString("pt-BR", { maximumFractionDigits: 1 }) + unit;
export const timestamp = (value: string | undefined) =>
  value
    ? new Date(value).toLocaleString("pt-BR", {
        timeZone: "America/Sao_Paulo",
        day: "2-digit",
        month: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      })
    : "—:—:—";
