import { useMemo, useState } from 'react';
import type { Incident, ReadingListItem, ZoneSummary } from '../api/types';
import { RecommendationPanel } from './RecommendationPanel';
import { WhatIfSimulator } from './WhatIfSimulator';

type MetricKey = 'energy_kwh' | 'water_liters' | 'occupancy';

function numeric(value: number | string | null | undefined): number | null {
  if (value === null || value === undefined || value === '') return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatValue(value: number | string | null | undefined, unit: string) {
  const parsed = numeric(value);
  if (parsed === null) return 'Unavailable';
  return `${parsed.toLocaleString(undefined, { maximumFractionDigits: 1 })} ${unit}`;
}

function formatDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function downloadCsv(filename: string, headers: string[], rows: (string | number | null)[][]) {
  const cell = (value: string | number | null) => {
    const raw = value === null ? '' : String(value);
    const safe = typeof value === 'string' && /^[=+\-@]/.test(raw) ? `'${raw}` : raw;
    return `"${safe.replaceAll('"', '""')}"`;
  };
  const csv = [headers, ...rows].map((row) => row.map(cell).join(',')).join('\r\n');
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function MetricTrend({
  label,
  unit,
  metric,
  readings,
  zoneName,
}: {
  label: string;
  unit: string;
  metric: MetricKey;
  readings: ReadingListItem[];
  zoneName: string;
}) {
  const values = readings
    .map((reading) => ({ reading, value: numeric(reading[metric]) }))
    .filter((point): point is { reading: ReadingListItem; value: number } => point.value !== null);
  const minimum = values.length ? Math.min(...values.map((point) => point.value)) : 0;
  const maximum = values.length ? Math.max(...values.map((point) => point.value)) : 0;
  const spread = maximum - minimum || 1;
  const points = values.map((point, index) => ({
    ...point,
    x: values.length === 1 ? 350 : 28 + (index / (values.length - 1)) * 644,
    y: 142 - ((point.value - minimum) / spread) * 112,
  }));
  const chartPath = points
    .map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`)
    .join(' ');

  return (
    <section className="trend-chart-card" aria-label={`${label} trend for ${zoneName}`}>
      <div className="trend-chart-legend">
        <strong>{label}</strong>
        <span>{values.length} recorded {values.length === 1 ? 'sample' : 'samples'}</span>
      </div>
      {points.length === 0 ? (
        <div className="operations-empty">
          <strong>No recorded {label.toLowerCase()} readings</strong>
          <p>A trend is unavailable until the API returns actual historical samples.</p>
        </div>
      ) : (
        <>
          <svg
            className="trend-chart"
            viewBox="0 0 700 170"
            role="img"
            aria-label={`${label} samples for ${zoneName}, plotted from recorded values only`}
          >
            <line x1="28" y1="30" x2="672" y2="30" />
            <line x1="28" y1="86" x2="672" y2="86" />
            <line x1="28" y1="142" x2="672" y2="142" />
            {points.length > 1 && <path className="trend-chart__line" d={chartPath} />}
            {points.map((point) => (
              <circle key={point.reading.id} cx={point.x} cy={point.y} r="4.5">
                <title>
                  {`${formatDate(point.reading.timestamp)} — ${formatValue(point.value, unit)}`}
                </title>
              </circle>
            ))}
          </svg>
          <div className="trend-chart-scale">
            <span>High in sample: {formatValue(maximum, unit)}</span>
            <span>Low in sample: {formatValue(minimum, unit)}</span>
          </div>
          {points.length === 1 && (
            <p className="inline-muted">One recorded point is available; no historical trend can be inferred.</p>
          )}
          <div className="trend-chart-coverage">
            <time>{formatDate(points[0].reading.timestamp)}</time>
            {points.length > 1 && <time>{formatDate(points[points.length - 1].reading.timestamp)}</time>}
          </div>
        </>
      )}
    </section>
  );
}

function formatDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString([], {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
}

interface OperationsWorkspaceProps {
  zones: ZoneSummary[];
  selectedZone: ZoneSummary | null;
  selectedZoneId: string;
  onSelectZone: (zoneId: string) => void;
  readings: ReadingListItem[];
  incidents: Incident[];
  activeIncidentCount: number;
  detailIncidents: Incident[] | null;
  detailLoading: boolean;
  detailError: string | null;
}

export function OperationsWorkspace({
  zones,
  selectedZone,
  selectedZoneId,
  onSelectZone,
  readings,
  incidents,
  activeIncidentCount,
  detailIncidents,
  detailLoading,
  detailError,
}: OperationsWorkspaceProps) {
  const [incidentStatusFilter, setIncidentStatusFilter] = useState<'ALL' | 'ACTIVE' | 'RESOLVED'>('ALL');
  const [incidentZoneFilter, setIncidentZoneFilter] = useState('ALL');
  const zoneReadings = useMemo(
    () => readings
      .filter((reading) => reading.zone_id === selectedZoneId)
      .sort((left, right) => new Date(left.timestamp).getTime() - new Date(right.timestamp).getTime()),
    [readings, selectedZoneId],
  );
  const latestReadings = zones.filter((zone) => zone.latest_reading !== null);
  const energyValues = latestReadings.map((zone) => numeric(zone.latest_reading?.energy_kwh));
  const energyTotal = energyValues.reduce<number>((sum, value) => sum + (value ?? 0), 0);
  const energyDistributionAvailable = latestReadings.length > 0
    && energyValues.every((value) => value !== null && value >= 0)
    && energyTotal > 0;
  const energySamples = latestReadings
    .map((zone) => numeric(zone.latest_reading?.energy_kwh))
    .filter((value): value is number => value !== null);
  const waterSamples = latestReadings
    .map((zone) => numeric(zone.latest_reading?.water_liters))
    .filter((value): value is number => value !== null);
  const occupancySamples = latestReadings
    .map((zone) => numeric(zone.latest_reading?.occupancy))
    .filter((value): value is number => value !== null);
  const visibleIncidents = incidents
    .filter((incident) => incidentStatusFilter === 'ALL' || incident.status === incidentStatusFilter)
    .filter((incident) => incidentZoneFilter === 'ALL' || incident.zone_id === incidentZoneFilter)
    .sort(
      (left, right) =>
        new Date(right.created_at).getTime() - new Date(left.created_at).getTime(),
    );
  const energyDistribution = zones
    .map((zone) => ({
      zone,
      value: numeric(zone.latest_reading?.energy_kwh),
    }))
    .filter(
      (item): item is { zone: ZoneSummary; value: number } =>
        item.zone.latest_reading !== null && item.value !== null && item.value >= 0,
    );
  const maximumEnergy =
    Math.max(0, ...energyDistribution.map((item) => item.value));
  const selectedActiveIncidents = selectedZone
    ? detailIncidents ??
      incidents.filter(
        (incident) =>
          incident.zone_id === selectedZone.id && incident.status === 'ACTIVE',
      )
    : [];

  function exportReadings() {
    const coverageStart = zoneReadings[0]?.timestamp ?? '';
    const coverageEnd = zoneReadings.at(-1)?.timestamp ?? '';
    downloadCsv(
      `readings-${selectedZone?.name.toLowerCase().replaceAll(/\s+/g, '-') ?? 'zone'}.csv`,
      ['reporting_period_start', 'reporting_period_end', 'timestamp', 'zone', 'energy_kwh', 'water_liters', 'occupancy'],
      zoneReadings.map((reading) => [
        coverageStart,
        coverageEnd,
        reading.timestamp,
        reading.zone_name,
        numeric(reading.energy_kwh),
        numeric(reading.water_liters),
        reading.occupancy,
      ]),
    );
  }

  function exportComparisons() {
    downloadCsv(
      'latest-zone-readings.csv',
      ['zone', 'status', 'latest_timestamp', 'energy_kwh', 'water_liters', 'occupancy', 'active_incidents'],
      zones.map((zone) => [
        zone.name,
        zone.status,
        zone.latest_reading?.timestamp ?? null,
        numeric(zone.latest_reading?.energy_kwh),
        numeric(zone.latest_reading?.water_liters),
        zone.latest_reading?.occupancy ?? null,
        zone.active_incident_count,
      ]),
    );
  }

  function exportIncidents() {
    const period = visibleIncidents.length
      ? [
          visibleIncidents[visibleIncidents.length - 1].created_at,
          visibleIncidents[0].created_at,
        ]
      : ['', ''];
    downloadCsv(
      'incident-activity.csv',
      ['reporting_period_start', 'reporting_period_end', 'created_at', 'zone', 'type', 'severity', 'status', 'source', 'current_value', 'expected_range', 'description', 'resolved_at'],
      visibleIncidents.map((incident) => [
        period[0],
        period[1],
        incident.created_at,
        incident.zone_name,
        incident.type,
        incident.severity,
        incident.status,
        incident.source,
        incident.current_value === null ? null : String(incident.current_value),
        incident.expected_range,
        incident.description,
        incident.resolved_at,
      ]),
    );
  }

  return (
    <>
      <section className="operations-overview" id="operations" aria-labelledby="operations-title">
        <div className="operations-overview__heading">
          <div>
            <p className="eyebrow">Live instruments</p>
            <h2 id="operations-title">Current resource picture</h2>
          </div>
          <span className="live-data-note">Latest zone readings only</span>
        </div>
        <div className="resource-strip">
          {[
            {
              label: 'Energy',
              value: energySamples.length
                ? `${energySamples.reduce((sum, value) => sum + value, 0).toLocaleString(undefined, { maximumFractionDigits: 1 })} kWh`
                : 'Unavailable',
              note: `Sum of latest samples · ${energySamples.length} of ${zones.length} zones`,
              tone: 'energy',
            },
            {
              label: 'Water',
              value: waterSamples.length
                ? `${waterSamples.reduce((sum, value) => sum + value, 0).toLocaleString(undefined, { maximumFractionDigits: 1 })} L`
                : 'Unavailable',
              note: `Sum of latest samples · ${waterSamples.length} of ${zones.length} zones`,
              tone: 'water',
            },
            {
              label: 'Occupancy',
              value: occupancySamples.length
                ? occupancySamples.reduce((sum, value) => sum + value, 0).toLocaleString()
                : 'Unavailable',
              note: `Latest samples · ${occupancySamples.length} of ${zones.length} zones`,
              tone: 'occupancy',
            },
            {
              label: 'Active incidents',
              value: String(activeIncidentCount),
              note: 'Current dashboard summary',
              tone: 'incidents',
            },
          ].map((item) => (
            <article className={`resource-readout resource-readout--${item.tone}`} key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
              <small>{item.note}</small>
            </article>
          ))}
        </div>
        <div className="zone-status-summary" aria-label="Current zone status counts">
          <strong>Zone status</strong>
          {(['NORMAL', 'WARNING', 'CRITICAL'] as const).map((status) => (
            <span className={`incident-state incident-state--${status.toLowerCase()}`} key={status}>
              {status} · {zones.filter((zone) => zone.status === status).length}
            </span>
          ))}
        </div>
      </section>

      <section className="operations-grid" aria-label="Zone operations and resource analysis">
        <article className="operations-panel zone-detail-panel" id="zone-detail">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Selected location</p>
              <h2>Zone detail</h2>
            </div>
            <label className="zone-picker">
              <span className="sr-only">Select a campus zone</span>
              <select value={selectedZoneId} onChange={(event) => onSelectZone(event.target.value)}>
                {zones.map((zone) => <option value={zone.id} key={zone.id}>{zone.name}</option>)}
              </select>
            </label>
          </div>
          {!selectedZone ? (
            <div className="operations-empty">
              <strong>No zones are available</strong>
              <p>Zone details will appear when the campus API returns monitored locations.</p>
            </div>
          ) : (
            <>
              <div className="zone-detail-identity">
                <div>
                  <span>{selectedZone.type.replaceAll('_', ' ')}</span>
                  <h3>{selectedZone.name}</h3>
                </div>
                <span className={`status-pill status-pill--${selectedZone.status.toLowerCase()}`}>
                  <i className="status-pill__dot" aria-hidden="true" />
                  {selectedZone.status}
                </span>
              </div>
              <div className="detail-readings">
                <div><span>Energy</span><strong>{formatValue(selectedZone.latest_reading?.energy_kwh, 'kWh')}</strong></div>
                <div><span>Water</span><strong>{formatValue(selectedZone.latest_reading?.water_liters, 'L')}</strong></div>
                <div><span>Occupancy</span><strong>{formatValue(selectedZone.latest_reading?.occupancy, 'people')}</strong></div>
              </div>
              <p className="reading-timestamp">
                Latest sample: {selectedZone.latest_reading ? formatDate(selectedZone.latest_reading.timestamp) : 'No reading available'}
              </p>
              <div className="zone-waste-detail">
                <div className="zone-incident-summary__heading">
                  <strong>Latest waste detection</strong>
                  <span>
                    {selectedZone.latest_waste_detection
                      ? selectedZone.latest_waste_detection.waste_level
                      : 'No scan returned'}
                  </span>
                </div>
                {selectedZone.latest_waste_detection ? (
                  <p>
                    {selectedZone.latest_waste_detection.waste_object_count} waste objects of{' '}
                    {selectedZone.latest_waste_detection.detected_object_count} detected ·{' '}
                    {selectedZone.latest_waste_detection.model_name}
                    {selectedZone.latest_waste_detection.is_mock ? ' · mock detector' : ''}
                    {' · '}{formatDate(selectedZone.latest_waste_detection.created_at)}
                  </p>
                ) : (
                  <p className="inline-muted">No waste detection record is available for this zone.</p>
                )}
              </div>
              <div className="zone-incident-summary">
                <div className="zone-incident-summary__heading">
                  <strong>Active incidents</strong>
                  <span>{detailLoading ? 'Refreshing' : `${selectedActiveIncidents.length} reported`}</span>
                </div>
                {detailError && <p className="inline-error" role="status">Zone detail refresh failed. Showing available dashboard data. {detailError}</p>}
                {detailLoading && !detailIncidents ? (
                  <p className="inline-muted" role="status">Loading zone incident detail…</p>
                ) : selectedActiveIncidents.length === 0 ? (
                  <p className="inline-muted">No incident records are available for this zone.</p>
                ) : (
                  <ul>
                    {selectedActiveIncidents
                      .slice()
                      .sort((left, right) => new Date(right.created_at).getTime() - new Date(left.created_at).getTime())
                      .slice(0, 4)
                      .map((incident) => (
                        <li key={incident.id}>
                          <span className={`incident-state incident-state--${incident.status.toLowerCase()}`}>{incident.status}</span>
                          <span>{incident.type.replaceAll('_', ' ')}</span>
                          <strong>{incident.severity}</strong>
                          <p>{incident.description}</p>
                          <RecommendationPanel incidentId={incident.id} />
                        </li>
                      ))}
                  </ul>
                )}
              </div>
            </>
          )}
        </article>

        <article className="operations-panel trend-panel" id="readings">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Recorded measurements</p>
              <h2>{selectedZone?.name ?? 'Selected zone'} trends</h2>
            </div>
            <div className="panel-tools">
              <button
                className="export-button"
                type="button"
                onClick={exportReadings}
                disabled={zoneReadings.length === 0}
                aria-label="Export selected zone readings as CSV"
              >
                Export CSV
              </button>
            </div>
          </div>
          {selectedZone ? (
            <>
              <div className="trend-chart-grid">
                <MetricTrend
                  label="Energy"
                  unit="kWh"
                  metric="energy_kwh"
                  readings={zoneReadings}
                  zoneName={selectedZone.name}
                />
                <MetricTrend
                  label="Water"
                  unit="L"
                  metric="water_liters"
                  readings={zoneReadings}
                  zoneName={selectedZone.name}
                />
              </div>
              <p className="data-provenance-note">
                Charts use only readings returned by the API for this zone ({zoneReadings.length}
                {' '}records currently loaded); each metric has its own unit and scale.
              </p>
            </>
          ) : (
            <div className="operations-empty">
              <strong>Select a zone to view trends</strong>
              <p>Only recorded energy and water readings are shown.</p>
            </div>
          )}
        </article>

        <article className="operations-panel comparison-panel" id="zone-comparison">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Latest readings</p>
              <h2>Zone comparison</h2>
            </div>
            <button className="export-button" type="button" onClick={exportComparisons} disabled={zones.length === 0} aria-label="Export current zone comparison as CSV">
              Export CSV
            </button>
          </div>
          {zones.length === 0 ? (
            <div className="operations-empty"><strong>No zones returned</strong><p>Comparison is unavailable.</p></div>
          ) : (
            <>
              <div className="energy-share-heading">
                <strong>Energy reading distribution</strong>
                <span>Latest readings · {energyDistribution.length} zones represented</span>
              </div>
              {energyDistributionAvailable ? (
                <div className="energy-distribution">
                  <div className="energy-donut-wrap">
                    <svg
                      className="energy-donut"
                      viewBox="0 0 160 160"
                      role="img"
                      aria-label={`Distribution of ${energyTotal.toLocaleString()} kilowatt-hours across the latest available zone readings`}
                    >
                      <circle className="energy-donut__track" cx="80" cy="80" r="56" />
                      {(() => {
                        const circumference = 2 * Math.PI * 56;
                        let offset = 0;
                        return energyDistribution.map(({ zone, value }, index) => {
                          const segment = (value / energyTotal) * circumference;
                          const circle = (
                            <circle
                              key={zone.id}
                              className={`energy-donut__segment energy-donut__segment--${index % 3}`}
                              cx="80"
                              cy="80"
                              r="56"
                              strokeDasharray={`${segment} ${circumference - segment}`}
                              strokeDashoffset={-offset}
                              transform="rotate(-90 80 80)"
                            >
                              <title>
                                {`${zone.name}: ${formatValue(value, 'kWh')} (${((value / energyTotal) * 100).toFixed(1)}%)`}
                              </title>
                            </circle>
                          );
                          offset += segment;
                          return circle;
                        });
                      })()}
                    </svg>
                    <span className="energy-donut-total">
                      {energyTotal.toLocaleString(undefined, { maximumFractionDigits: 1 })} kWh
                      <small>sum of latest samples</small>
                    </span>
                  </div>
                  <ul className="energy-share-list">
                    {energyDistribution.map(({ zone, value }, index) => {
                      const share = (value / energyTotal) * 100;
                    return (
                      <li key={zone.id}>
                        <div className="energy-share-row">
                          <span>{zone.name}</span>
                            <strong>{formatValue(value, 'kWh')}<small>{share.toFixed(1)}%</small></strong>
                        </div>
                          <div className={`energy-share-track energy-share-track--${index % 3}`} aria-hidden="true"><span style={{ width: `${share}%` }} /></div>
                      </li>
                    );
                  })}
                </ul>
                </div>
              ) : (
                <p className="inline-muted">Energy distribution unavailable: complete, non-negative latest readings with a positive total are required.</p>
              )}
              <div className="zone-energy-chart" aria-label="Energy comparison by zone">
                <strong>Latest energy by zone</strong>
                {zones.map((zone) => {
                  const value = numeric(zone.latest_reading?.energy_kwh);
                  const width = value !== null && maximumEnergy > 0 ? (value / maximumEnergy) * 100 : 0;
                  return (
                    <div className="zone-energy-chart__row" key={zone.id}>
                      <button
                        type="button"
                        className="table-zone-select"
                        onClick={() => onSelectZone(zone.id)}
                        aria-label={`Select ${zone.name} for zone details`}
                      >
                        {zone.name}
                      </button>
                      <div
                        className="zone-energy-chart__track"
                        role="meter"
                        aria-label={`${zone.name} latest energy`}
                        aria-valuemin={0}
                        aria-valuemax={maximumEnergy || 1}
                        aria-valuenow={value ?? 0}
                      >
                        <span style={{ width: `${width}%` }} />
                      </div>
                      <span>{formatValue(value, 'kWh')}</span>
                    </div>
                  );
                })}
              </div>
              <div className="comparison-table-wrap">
                <table className="comparison-table">
                  <thead><tr><th scope="col">Zone</th><th scope="col">Status</th><th scope="col">Energy</th><th scope="col">Water</th><th scope="col">Occupancy</th><th scope="col">Incidents</th></tr></thead>
                  <tbody>
                    {zones.map((zone) => (
                      <tr key={zone.id} className={zone.id === selectedZoneId ? 'is-selected' : ''}>
                        <th scope="row">
                          <button type="button" className="table-zone-select" onClick={() => onSelectZone(zone.id)} aria-label={`Select ${zone.name} for zone details`}>
                            {zone.name}
                          </button>
                        </th>
                        <td>{zone.status}</td>
                        <td>{formatValue(zone.latest_reading?.energy_kwh, 'kWh')}</td>
                        <td>{formatValue(zone.latest_reading?.water_liters, 'L')}</td>
                        <td>{formatValue(zone.latest_reading?.occupancy, 'people')}</td>
                        <td>{zone.active_incident_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="data-provenance-note">Values are the latest sensor reading returned for each zone, not an accumulated period total.</p>
            </>
          )}
        </article>

        <WhatIfSimulator zone={selectedZone} />
      </section>

      <section className="content-section incident-history-section" id="incidents">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Rule-generated records</p>
            <h2>Incident history</h2>
            <p className="section-description">Up to 200 actual records, newest first. Detection and resolution timestamps are shown; the API does not record a recovery-reading history.</p>
          </div>
          <div className="incident-history-tools">
            <label>
              <span className="sr-only">Filter incidents by zone</span>
              <select value={incidentZoneFilter} onChange={(event) => setIncidentZoneFilter(event.target.value)}>
                <option value="ALL">All zones</option>
                {zones.map((zone) => <option value={zone.id} key={zone.id}>{zone.name}</option>)}
              </select>
            </label>
            <label>
              <span className="sr-only">Filter incidents by status</span>
              <select value={incidentStatusFilter} onChange={(event) => setIncidentStatusFilter(event.target.value as 'ALL' | 'ACTIVE' | 'RESOLVED')}>
                <option value="ALL">All statuses</option>
                <option value="ACTIVE">Active</option>
                <option value="RESOLVED">Resolved</option>
              </select>
            </label>
            <button className="export-button" type="button" onClick={exportIncidents} disabled={visibleIncidents.length === 0} aria-label="Export filtered incident history as CSV">
              Export filtered CSV
            </button>
          </div>
        </div>
        <IncidentHistory incidents={visibleIncidents} />
      </section>
    </>
  );
}

function IncidentHistory({ incidents }: { incidents: Incident[] }) {
  if (incidents.length === 0) {
    return (
      <div className="incident-history-empty">
        <strong>No incident records returned</strong>
        <p>The current API feed has no incidents to display. This is not an inferred all-clear state.</p>
      </div>
    );
  }

  return (
    <div className="incident-history-list">
      {incidents.map((incident) => (
        <article className="history-incident" key={incident.id}>
          <div className="history-incident__rail">
            <span className={`incident-severity incident-severity--${incident.severity.toLowerCase()}`} aria-label={`${incident.severity} severity`}>!</span>
            <span className="history-incident__line" aria-hidden="true" />
          </div>
          <div className="history-incident__body">
            <div className="history-incident__top">
              <div>
                <span className="history-incident__zone">{incident.zone_name}</span>
                <h3>{incident.type.replaceAll('_', ' ')}</h3>
              </div>
              <div className="history-incident__tags">
                <span className={`incident-state incident-state--${incident.status.toLowerCase()}`}>{incident.status}</span>
                <span className={`severity-label severity-label--${incident.severity.toLowerCase()}`}>{incident.severity}</span>
              </div>
            </div>
            <p>{incident.description}</p>
            <dl className="incident-evidence">
              <div><dt>Detection source</dt><dd>{incident.source || 'Unavailable'}</dd></div>
              <div><dt>Current value</dt><dd>{incident.current_value === null ? 'Unavailable' : String(incident.current_value)}</dd></div>
              <div><dt>Expected range</dt><dd>{incident.expected_range ?? 'Unavailable'}</dd></div>
            </dl>
            <div className="history-incident__timestamps">
              <span><span>Detected</span><time>{formatDate(incident.created_at)}</time></span>
              {incident.resolved_at && <span><span>Resolved</span><time>{formatDate(incident.resolved_at)}</time></span>}
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}
