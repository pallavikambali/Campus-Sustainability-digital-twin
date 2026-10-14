import type { Incident } from '../api/types';
import { RecommendationPanel } from './RecommendationPanel';

const TYPE_LABELS: Record<string, string> = {
  HIGH_ENERGY_CONSUMPTION: 'High energy consumption',
  POSSIBLE_WATER_LEAKAGE: 'Possible water leakage',
  ABNORMAL_OCCUPANCY: 'Abnormal occupancy',
  WASTE_ACCUMULATION: 'Waste accumulation',
};

function formatTime(value: string) {
  return new Date(value).toLocaleString([], {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function IncidentList({ incidents }: { incidents: Incident[] }) {
  const chronological = [...incidents].sort(
    (left, right) => new Date(right.created_at).getTime() - new Date(left.created_at).getTime(),
  );
  return (
    <section className="activity-panel" id="incident-feed">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Rule-based alerts</p>
          <h2>Incident feed</h2>
        </div>
        <span className="panel-count">{incidents.length}</span>
      </div>
      {chronological.length === 0 ? (
        <div className="empty-list">
          <span className="empty-list__mark" aria-hidden="true">—</span>
          <div>
            <strong>No incident records returned</strong>
            <p>The incident feed is empty; this is not an inferred all-clear state.</p>
          </div>
        </div>
      ) : (
        <ul className="incident-list">
          {chronological.map((incident) => (
            <li className="incident-row" key={incident.id}>
              <span
                className={`incident-severity incident-severity--${incident.severity.toLowerCase()}`}
                aria-label={`${incident.severity.toLowerCase()} severity`}
              >
                !
              </span>
              <div className="incident-row__body">
                <div className="incident-row__title">
                  <strong>{TYPE_LABELS[incident.type] ?? incident.type.replaceAll('_', ' ')}</strong>
                  <span className={`severity-label severity-label--${incident.severity.toLowerCase()}`}>
                    {incident.severity}
                  </span>
                </div>
                <p>{incident.zone_name} <span aria-hidden="true">/</span> {incident.description}</p>
                <div className="incident-feed-meta">
                  <span className={`incident-state incident-state--${incident.status.toLowerCase()}`}>{incident.status}</span>
                  <span>Source: {incident.source || 'Unavailable'}</span>
                  <span>Value: {incident.current_value === null ? 'Unavailable' : String(incident.current_value)}</span>
                  <span>Expected: {incident.expected_range ?? 'Unavailable'}</span>
                </div>
                <time>{formatTime(incident.created_at)}{incident.resolved_at ? ` / Resolved ${formatTime(incident.resolved_at)}` : ''}</time>
                <RecommendationPanel incidentId={incident.id} />
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}