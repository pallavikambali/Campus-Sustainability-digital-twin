import type { ZoneSummary } from '../api/types';
import { StatusPill } from './StatusPill';
import { useTheme } from '../ThemeContext';

const MAP_POSITIONS = [
  'map-zone--academic',
  'map-zone--library',
  'map-zone--hostel',
];

function formatReading(value: number | string | undefined, unit: string) {
  return value === undefined
    ? '--'
    : `${Number(value).toLocaleString(undefined, {
        maximumFractionDigits: 1,
      })} ${unit}`;
}

export function DigitalTwin({ zones }: { zones: ZoneSummary[] }) {
  const { theme } = useTheme();
  return (
    <section className="content-section twin-section" id="digital-twin">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Spatial system view</p>
          <h2>Digital twin</h2>
        </div>

        <div className="map-legend" aria-label="Zone status legend">
          <span>
            <i className="legend-dot legend-dot--normal" />
            Normal
          </span>
          <span>
            <i className="legend-dot legend-dot--warning" />
            Warning
          </span>
          <span>
            <i className="legend-dot legend-dot--critical" />
            Critical
          </span>
        </div>
      </div>

      <div
  className={`campus-map ${
  theme === 'dark'
    ? 'campus-map--dark-twin'
    : theme === 'eco'
      ? 'campus-map--eco-twin'
      : ''
}`}
  aria-label="Digital twin view of monitored campus zones"
>
        <div className="map-caption map-caption--north">
          NORTH CAMPUS
        </div>

        <div className="map-caption map-caption--quad">
          CENTRAL QUAD
        </div>

        <div className="map-walkway map-walkway--horizontal" />
        <div className="map-walkway map-walkway--vertical" />

        <div className="map-green-space map-green-space--left" />
        <div className="map-green-space map-green-space--right" />

        <div className="map-waterline" />

        <div className="map-road-label">
          CAMPUS LOOP
        </div>

        {zones.map((zone, index) => (
          <article
            key={zone.id}
            className={`map-zone ${
              MAP_POSITIONS[index] ?? ''
            } map-zone--${zone.status.toLowerCase()}`}
          >
            <div className="map-building" aria-hidden="true">
              <span />
              <span />
              <span />
              <span />
              <span />
              <span />
            </div>

            <div className="map-zone__info">
              <strong>{zone.name}</strong>

              <StatusPill status={zone.status} />

              <span>
                {formatReading(
                  zone.latest_reading?.energy_kwh,
                  'kWh',
                )}{' '}
                energy
                <b aria-hidden="true"> / </b>
                {zone.active_incident_count} active
              </span>
            </div>
          </article>
        ))}

        <div className="map-scale">
          <span /> 100 m
        </div>
      </div>

      <p className="map-footnote">
        Zone conditions update with the latest sensor readings from
        PostgreSQL.
      </p>
    </section>
  );
}