export interface Road {
  id: string;
  name: string;
  location: string;
  coords: [number, number][];
  last_updated: string;
  ai_verdict: {
    label: 'Healthy' | 'Warning' | 'Critical';
    confidence: number;
  };
  metrics: {
    estimated_impact_force_N: number;
    structural_health_score: number;
    overload_alert: boolean;
    accel_peak_g?: number; // Make existing peak optional
    accel_rms_g: number;
    loadcell_force_kg: number;
    accel_x_g?: number; // <-- ADD THIS
    accel_y_g?: number; // <-- ADD THIS
    accel_z_g?: number; // <-- ADD THIS
  };
  timeseries: TimeSeriesData[];
}

export interface TimeSeriesData {
  ts: string;
  estimated_impact_force_N: number;
  structural_health_score: number;
  accel_peak_g?: number; // Make existing peak optional
  accel_rms_g: number;
  loadcell_force_kg: number;
  accel_x_g?: number; // <-- ADD THIS
  accel_y_g?: number; // <-- ADD THIS
  accel_z_g?: number; // <-- ADD THIS
}

export interface RoadsData {
  roads: Road[];
}
