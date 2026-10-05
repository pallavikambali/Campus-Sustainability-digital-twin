export type ZoneStatus = 'NORMAL' | 'WARNING' | 'CRITICAL';
export type IncidentSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type SimulationAction = 'energy-spike' | 'water-leak' | 'occupancy-surge' | 'reset';
export type SystemState = 'connecting' | 'online' | 'offline';

export interface SensorReading {
  id: string;
  zone_id: string;
  timestamp: string;
  energy_kwh: number | string;
  water_liters: number | string;
  occupancy: number;
}

export interface DetectedObject {
  class_name: string;
  confidence: number | null;
  bounding_box: Record<string, number> | null;
}

export interface WasteDetectionSummary {
  id: string;
  waste_level: string;
  waste_object_count: number;
  detected_object_count: number;
  model_name: string;
  is_mock: boolean;
  created_at: string;
}

export interface ZoneSummary {
  id: string;
  name: string;
  type: string;
  capacity: number;
  status: ZoneStatus;
  active_incident_count: number;
  latest_reading: SensorReading | null;
  latest_waste_detection: WasteDetectionSummary | null;
}

export interface DashboardSummary {
  total_zones: number;
  normal_zones: number;
  warning_zones: number;
  critical_zones: number;
  active_incidents: number;
  zones: ZoneSummary[];
}

export interface Incident {
  id: string;
  zone_id: string;
  zone_name: string;
  type: string;
  severity: IncidentSeverity;
  current_value: number | string | null;
  expected_range: string | null;
  description: string;
  status: 'ACTIVE' | 'RESOLVED';
  source: string;
  created_at: string;
  resolved_at: string | null;
}

export interface EvidenceFact {
  id: string;
  label: string;
  value: string;
  source: string;
}

export interface RecommendationAction {
  title: string;
  action: string;
  rationale: string;
  supporting_fact_ids: string[];
}

export interface IncidentRecommendation {
  id: string;
  incident_id: string;
  provider: string;
  model: string;
  mode: 'ai' | 'fallback';
  fallback_reason: string | null;
  generated_at: string;
  facts: EvidenceFact[];
  explanation: string;
  recommendations: RecommendationAction[];
}

export interface ReadingListItem extends SensorReading {
  zone_name: string;
}

export interface WasteDetection extends WasteDetectionSummary {
  zone_id: string;
  zone_name: string;
  image_path: string | null;
  detected_objects: DetectedObject[];
}

export interface WasteDetectionResult extends WasteDetection {
  zone_status: ZoneStatus;
  incident_created: boolean;
  incident_updated: boolean;
  incident: Incident | null;
}

export interface DashboardData {
  summary: DashboardSummary;
  incidents: Incident[];
  readings: ReadingListItem[];
  wasteDetections: WasteDetection[];
}