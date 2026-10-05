import type {
  DashboardData,
  DashboardSummary,
  Incident,
  IncidentRecommendation,
  ReadingListItem,
  SimulationAction,
  WasteDetection,
  WasteDetectionResult,
  ZoneSummary,
} from './types';

const API_BASE_URL = 'http://localhost:8002/api/v1';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: { Accept: 'application/json', ...init?.headers },
    });
  } catch {
    throw new Error('Cannot connect to the API. Check that the backend is running.');
  }

  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail =
      body && typeof body === 'object' && 'detail' in body
        ? (body as { detail: unknown }).detail
        : null;
    throw new Error(
      typeof detail === 'string'
        ? detail
        : `The API returned an error (${response.status}).`,
    );
  }
  return body as T;
}

export function getZones() {
  return request<ZoneSummary[]>('/zones');
}

export function getZone(zoneId: string) {
  return request<ZoneSummary & { active_incidents: Incident[] }>(
    `/zones/${encodeURIComponent(zoneId)}`,
  );
}

export function getDashboardSummary() {
  return request<DashboardSummary>('/dashboard/summary');
}

export function getReadings(limit = 8) {
  return request<ReadingListItem[]>(`/readings?limit=${limit}`);
}

export function getIncidents(limit = 8) {
  return request<Incident[]>(`/incidents?active_only=true&limit=${limit}`);
}

export function getIncident(incidentId: string) {
  return request<Incident>(`/incidents/${encodeURIComponent(incidentId)}`);
}

export function getIncidentRecommendation(incidentId: string) {
  return request<IncidentRecommendation | null>(
    `/incidents/${encodeURIComponent(incidentId)}/recommendation`,
  );
}

export function generateIncidentRecommendation(incidentId: string) {
  return request<IncidentRecommendation>(
    `/incidents/${encodeURIComponent(incidentId)}/recommendation`,
    { method: 'POST' },
  );
}

export function getWasteDetections(zoneId?: string, limit = 8) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (zoneId) params.set('zone_id', zoneId);
  return request<WasteDetection[]>(`/waste-detections?${params.toString()}`);
}

export function uploadWasteImage(zoneId: string, image: File) {
  const form = new FormData();
  form.set('zone_id', zoneId);
  form.set('image', image);
  return request<WasteDetectionResult>('/waste-detections', {
    method: 'POST',
    body: form,
  });
}

export async function getDashboardData(): Promise<DashboardData> {
  const [summary, incidents, readings, wasteDetections] = await Promise.all([
    getDashboardSummary(),
    getIncidents(),
    getReadings(),
    getWasteDetections(),
  ]);
  return { summary, incidents, readings, wasteDetections };
}

export function runSimulation(zoneId: string, action: SimulationAction) {
  return request<unknown>(
    `/simulation/${encodeURIComponent(zoneId)}/${action}`,
    { method: 'POST' },
  );
}