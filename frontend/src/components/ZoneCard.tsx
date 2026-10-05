import type { SimulationAction, ZoneSummary } from '../api/types';
import { SimulationControls } from './SimulationControls';
import { StatusPill } from './StatusPill';

interface ZoneCardProps {
  zone: ZoneSummary;
  pendingAction: SimulationAction | null;
  controlsDisabled: boolean;
  onSimulate: (action: SimulationAction) => void;
}

function displayValue(value: number | string | undefined, unit: string) {
  if (value === undefined) return '--';
  return `${Number(value).toLocaleString(undefined, { maximumFractionDigits: 1 })} ${unit}`;
}

export function ZoneCard({ zone, pendingAction, controlsDisabled, onSimulate }: ZoneCardProps) {
  const reading = zone.latest_reading;
  const occupancy = reading?.occupancy ?? null;
  const occupancyRatio = occupancy === null ? 0 : Math.min(100, (occupancy / zone.capacity) * 100);

  return (
    <article className={`zone-card zone-card--${zone.status.toLowerCase()}`}>
      <div className="zone-card__header">
        <div>
          <span className="zone-card__type">{zone.type.replaceAll('_', ' ')}</span>
          <h3>{zone.name}</h3>
        </div>
        <StatusPill status={zone.status} />
      </div>

      <div className="zone-card__metrics">
        <div className="zone-metric zone-metric--energy">
          <span className="zone-metric__label">Energy</span>
          <strong>{displayValue(reading?.energy_kwh, 'kWh')}</strong>
        </div>
        <div className="zone-metric zone-metric--water">
          <span className="zone-metric__label">Water</span>
          <strong>{displayValue(reading?.water_liters, 'L')}</strong>
        </div>
      </div>

      <div className="occupancy-row">
        <div>
          <span className="zone-metric__label">Occupancy</span>
          <strong>
            {occupancy === null ? '--' : occupancy.toLocaleString()} <span>/ {zone.capacity}</span>
          </strong>
        </div>
        <span className="occupancy-percent">
          {occupancy === null ? 'No reading' : `${Math.round((occupancy / zone.capacity) * 100)}%`}
        </span>
      </div>
      <div
        className="occupancy-track"
        role="meter"
        aria-label={`${zone.name} occupancy`}
        aria-valuemin={0}
        aria-valuemax={zone.capacity}
        aria-valuenow={occupancy ?? 0}
      >
        <span style={{ width: `${occupancyRatio}%` }} />
      </div>

      <div className="zone-card__incident-row">
        <span className="incident-mini-mark" aria-hidden="true">!</span>
        <span>Active incidents</span>
        <strong>{zone.active_incident_count}</strong>
      </div>

      <div className="zone-waste-row">
        <span className="zone-waste-row__mark" aria-hidden="true">CV</span>
        <span>Latest waste scan</span>
        {zone.latest_waste_detection ? (
          <strong>
            {zone.latest_waste_detection.waste_level}
            <small>
              {zone.latest_waste_detection.waste_object_count} waste /{' '}
              {zone.latest_waste_detection.detected_object_count} detected
              {zone.latest_waste_detection.is_mock ? ' / mock' : ''}
            </small>
          </strong>
        ) : (
          <strong className="zone-waste-row__empty">None</strong>
        )}
      </div>

      <div className="zone-card__controls">
        <div className="zone-card__controls-heading">
          <span>Simulation controls</span>
          {pendingAction && <span>Sending</span>}
        </div>
        <SimulationControls
          busy={controlsDisabled}
          pendingAction={pendingAction}
          onSimulate={onSimulate}
        />
      </div>
    </article>
  );
}