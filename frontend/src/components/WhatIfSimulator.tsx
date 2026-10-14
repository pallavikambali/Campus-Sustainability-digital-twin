import { useEffect, useMemo, useState } from 'react';

import type { ZoneSummary } from '../api/types';

type MetricKey = 'energy_kwh' | 'water_liters' | 'occupancy';

const METRICS: { key: MetricKey; label: string; unit: string; step: string }[] = [
  { key: 'energy_kwh', label: 'Energy', unit: 'kWh', step: 'any' },
  { key: 'water_liters', label: 'Water', unit: 'L', step: 'any' },
  { key: 'occupancy', label: 'Occupancy', unit: 'people', step: '1' },
];

function parseValue(value: number | string | null | undefined): number | null {
  if (value === null || value === undefined || value === '') return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function format(value: number | null, unit: string) {
  if (value === null) return 'Unavailable';
  return `${value.toLocaleString(undefined, { maximumFractionDigits: 1 })} ${unit}`;
}

function signed(value: number) {
  const prefix = value > 0 ? '+' : value < 0 ? '−' : '';
  return `${prefix}${Math.abs(value).toLocaleString(undefined, { maximumFractionDigits: 1 })}`;
}

function exportScenario(
  zone: ZoneSummary,
  proposed: Record<MetricKey, string>,
  baselines: Record<MetricKey, number | null>,
) {
  const capturedAt = zone.latest_reading?.timestamp ?? '';
  const rows = METRICS.map((metric) => {
    const baseline = baselines[metric.key];
    const next = parseValue(proposed[metric.key]);
    const difference = baseline !== null && next !== null ? next - baseline : null;
    const percent =
      baseline !== null && baseline !== 0 && difference !== null
        ? (difference / Math.abs(baseline)) * 100
        : null;
    return [
      'HYPOTHETICAL',
      capturedAt,
      zone.name,
      metric.label,
      metric.unit,
      baseline,
      next,
      difference,
      percent,
    ];
  });
  const headers = [
    'record_type',
    'baseline_timestamp',
    'zone',
    'measurement',
    'unit',
    'recorded_baseline',
    'hypothetical_value',
    'difference',
    'percent_change',
  ];
  const csv = [headers, ...rows]
    .map((row) => row.map((value) => `"${String(value ?? '').replaceAll('"', '""')}"`).join(','))
    .join('\r\n');
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `what-if-${zone.name.toLowerCase().replaceAll(/\s+/g, '-')}.csv`;
  anchor.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function WhatIfSimulator({ zone }: { zone: ZoneSummary | null }) {
  const baseline = useMemo<Record<MetricKey, number | null>>(
    () => ({
      energy_kwh: parseValue(zone?.latest_reading?.energy_kwh),
      water_liters: parseValue(zone?.latest_reading?.water_liters),
      occupancy: parseValue(zone?.latest_reading?.occupancy),
    }),
    [
      zone?.id,
      zone?.latest_reading?.timestamp,
      zone?.latest_reading?.energy_kwh,
      zone?.latest_reading?.water_liters,
      zone?.latest_reading?.occupancy,
    ],
  );
  const [proposed, setProposed] = useState<Record<MetricKey, string>>({
    energy_kwh: '',
    water_liters: '',
    occupancy: '',
  });
  const [previewActive, setPreviewActive] = useState(false);

  useEffect(() => {
    setProposed({
      energy_kwh: baseline.energy_kwh === null ? '' : String(baseline.energy_kwh),
      water_liters: baseline.water_liters === null ? '' : String(baseline.water_liters),
      occupancy: baseline.occupancy === null ? '' : String(baseline.occupancy),
    });
    setPreviewActive(false);
  }, [zone?.id, zone?.latest_reading?.timestamp]);

  function resetToBaseline() {
    setProposed({
      energy_kwh: baseline.energy_kwh === null ? '' : String(baseline.energy_kwh),
      water_liters: baseline.water_liters === null ? '' : String(baseline.water_liters),
      occupancy: baseline.occupancy === null ? '' : String(baseline.occupancy),
    });
    setPreviewActive(false);
  }

  const scenarioIsValid =
    zone !== null &&
    zone.latest_reading !== null &&
    METRICS.every((metric) => {
      const candidate = parseValue(proposed[metric.key]);
      return (
        baseline[metric.key] !== null &&
        candidate !== null &&
        candidate >= 0 &&
        (metric.key !== 'occupancy' || Number.isInteger(candidate))
      );
    });

  return (
    <article className="operations-panel what-if-panel" id="what-if">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Local, hypothetical only</p>
          <h2>What-if simulator</h2>
        </div>
        <span className="local-only-mark">No API writes</span>
      </div>
      {!zone ? (
        <div className="operations-empty">
          <strong>Choose a zone first</strong>
          <p>A scenario requires a zone and its real current reading.</p>
        </div>
      ) : (
        <>
          <p className="what-if-explainer">
            Adjust hypothetical readings for {zone.name}. Calculations update as you type and never
            change saved readings, incidents, or operational state.
          </p>
          {!zone.latest_reading && (
            <div className="inline-muted">
              No baseline reading is available for this zone. A scenario cannot be calculated yet.
            </div>
          )}
          <div className="what-if-metrics">
            {METRICS.map((metric) => {
              const before = baseline[metric.key];
              const rawValue = proposed[metric.key];
              const after = parseValue(rawValue);
              const isOccupancy = metric.key === 'occupancy';
              const valid =
                rawValue !== '' &&
                after !== null &&
                after >= 0 &&
                (!isOccupancy || Number.isInteger(after));
              const difference = before !== null && valid && after !== null ? after - before : null;
              const absoluteDifference = difference === null ? null : Math.abs(difference);
              const percent =
                before !== null && before !== 0 && difference !== null
                  ? (difference / Math.abs(before)) * 100
                  : null;
              const scaleMaximum = Math.max(before ?? 0, after ?? 0, 1);

              return (
                <section className="what-if-metric" key={metric.key}>
                  <div className="what-if-metric__heading">
                    <h3>{metric.label}</h3>
                    <span>{metric.unit}</span>
                  </div>
                  <label className="what-if-input">
                    <span>Hypothetical {metric.label.toLowerCase()}</span>
                    <input
                      type="number"
                      min="0"
                      step={metric.step}
                      value={rawValue}
                      disabled={before === null}
                      aria-label={`Hypothetical ${metric.label.toLowerCase()} for ${zone.name}`}
                      onChange={(event) => {
                        setProposed((current) => ({ ...current, [metric.key]: event.target.value }));
                        setPreviewActive(false);
                      }}
                    />
                  </label>
                  {rawValue !== '' && !valid && (
                    <p className="inline-error" role="alert">
                      Enter a non-negative {isOccupancy ? 'whole number' : 'number'}.
                    </p>
                  )}
                  {isOccupancy && valid && after !== null && after > zone.capacity && (
                    <p className="capacity-warning" role="status">
                      Hypothetical occupancy exceeds the API-provided capacity of {zone.capacity}.
                    </p>
                  )}
                  {isOccupancy && valid && after !== null && !Number.isInteger(after) && (
                    <p className="inline-error" role="alert">Occupancy must be a whole number.</p>
                  )}
                  <div className="what-if-comparison">
                    <div className="what-if-comparison__labels">
                      <span>Recorded baseline</span>
                      <strong>{format(before, metric.unit)}</strong>
                    </div>
                    <div className="what-if-bar" aria-label={`Recorded ${metric.label.toLowerCase()} baseline`}>
                      <span
                        className="what-if-bar__fill what-if-bar__fill--baseline"
                        style={{ width: `${before === null ? 0 : (before / scaleMaximum) * 100}%` }}
                      />
                    </div>
                    <div className="what-if-comparison__labels">
                      <span>Hypothetical</span>
                      <strong>{valid ? format(after, metric.unit) : 'Enter a valid value'}</strong>
                    </div>
                    <div className="what-if-bar" aria-label={`Hypothetical ${metric.label.toLowerCase()} value`}>
                      <span
                        className="what-if-bar__fill what-if-bar__fill--hypothetical"
                        style={{ width: `${valid && after !== null ? (after / scaleMaximum) * 100 : 0}%` }}
                      />
                    </div>
                  </div>
                  <div className="what-if-difference">
                    <span>Absolute difference</span>
                    <strong>{absoluteDifference === null ? 'Unavailable' : format(absoluteDifference, metric.unit)}</strong>
                    <span>Change</span>
                    <strong>{percent === null ? 'Not defined at a zero baseline' : `${signed(percent)}%`}</strong>
                  </div>
                </section>
              );
            })}
          </div>
          <div className="what-if-actions">
            <button
              className="button button--primary"
              type="button"
              disabled={!scenarioIsValid}
              onClick={() => setPreviewActive(true)}
            >
              Preview scenario
            </button>
            <button className="button button--secondary" type="button" onClick={resetToBaseline}>
              Reset
            </button>
            <button
              className="export-button"
              type="button"
              disabled={!scenarioIsValid}
              onClick={() => exportScenario(zone, proposed, baseline)}
            >
              Export scenario CSV
            </button>
            {previewActive && (
              <span className="what-if-preview-state" role="status">
                Preview active · hypothetical only
              </span>
            )}
          </div>
          <p className="data-provenance-note">
            The API does not provide a simulation duration or predictive rule result, so neither is
            included. This preview is separate from the zone’s Apply Simulation controls.
          </p>
        </>
      )}
    </article>
  );
}
