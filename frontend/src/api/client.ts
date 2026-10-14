import type {
  DashboardData,
  DashboardSummary,
  Incident,
  IncidentRecommendation,
  NotificationConfigStatus,
  NotificationDelivery,
  ReadingListItem,
  SimulationAction,
  WasteDetection,
  WasteDetectionResult,
  ZoneSummary,
} from './types';

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.DEV
    ? '/api/v1'
    : 'https://campus-sustainability-backend-flg0.onrender.com/api/v1')
).replace(/\/$/, '');

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

export function getReadings(limit = 200, zoneId?: string) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (zoneId) params.set('zone_id', zoneId);
  return request<ReadingListItem[]>(`/readings?${params.toString()}`);
}

export function getIncidents(limit = 200, activeOnly = false) {
  const params = new URLSearchParams({
    active_only: String(activeOnly),
    limit: String(limit),
  });
  return request<Incident[]>(`/incidents?${params.toString()}`);
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

export function getNotificationStatus() {
  return request<NotificationConfigStatus>('/notifications/status');
}

export function getNotificationHistory(limit = 50) {
  return request<NotificationDelivery[]>(`/notifications?limit=${limit}`);
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
    getIncidents(200, false),
    getReadings(200),
    getWasteDetections(),
  ]);
  const [historyResult, statusResult] = await Promise.allSettled([
    getNotificationHistory(50),
    getNotificationStatus(),
  ]);
  const notifications =
    historyResult.status === 'fulfilled' ? historyResult.value : null;
  const notificationStatus =
    statusResult.status === 'fulfilled' ? statusResult.value : null;
  const notificationError =
    historyResult.status === 'rejected'
      ? historyResult.reason instanceof Error
        ? historyResult.reason.message
        : 'Notification history is unavailable.'
      : statusResult.status === 'rejected'
        ? statusResult.reason instanceof Error
          ? statusResult.reason.message
          : 'Notification configuration is unavailable.'
        : null;
  return {
    summary,
    incidents,
    readings,
    wasteDetections,
    notifications,
    notificationStatus,
    notificationError,
  };
}

export function runSimulation(zoneId: string, action: SimulationAction) {
  return request<unknown>(
    `/simulation/${encodeURIComponent(zoneId)}/${action}`,
    { method: 'POST' },
  );
}