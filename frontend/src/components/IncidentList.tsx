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
  return (
    <section className="activity-panel" id="incidents">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Rule-based alerts</p>
          <h2>Active incidents</h2>
        </div>
        <span className="panel-count">{incidents.length}</span>
      </div>
      {incidents.length === 0 ? (
        <div className="empty-list">
          <span className="empty-list__mark empty-list__mark--calm" aria-hidden="true">OK</span>
          <div>
            <strong>No active incidents</strong>
            <p>All monitored conditions are within their current rules.</p>
          </div>
        </div>
      ) : (
        <ul className="incident-list">
          {incidents.map((incident) => (
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
                <time>{formatTime(incident.created_at)}</time>
                <RecommendationPanel incidentId={incident.id} />
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}