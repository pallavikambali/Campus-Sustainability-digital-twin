import type { ReadingListItem } from '../api/types';

function exportReadings(readings: ReadingListItem[]) {
  const headers = ['timestamp', 'zone', 'energy_kwh', 'water_liters', 'occupancy'];
  const rows = readings.map((reading) => [
    reading.timestamp,
    reading.zone_name,
    reading.energy_kwh,
    reading.water_liters,
    reading.occupancy,
  ]);
  const csv = [headers, ...rows]
    .map((row) => row.map((value) => `"${String(value).replaceAll('"', '""')}"`).join(','))
    .join('\r\n');
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = 'visible-sensor-readings.csv';
  anchor.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function formatTime(value: string) {
  return new Date(value).toLocaleString([], {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatNumber(value: number | string) {
  return Number(value).toLocaleString(undefined, { maximumFractionDigits: 1 });
}

export function SensorReadings({ readings }: { readings: ReadingListItem[] }) {
  return (
    <section className="activity-panel" id="recent-readings">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Latest sensor activity</p>
          <h2>Recent readings</h2>
        </div>
        <div className="panel-tools">
          <span className="readings-unit">Latest first</span>
          <button
            className="export-button"
            type="button"
            disabled={readings.length === 0}
            onClick={() => exportReadings(readings)}
            aria-label="Export visible sensor readings as CSV"
          >
            Export CSV
          </button>
        </div>
      </div>
      {readings.length === 0 ? (
        <div className="empty-list">
          <span className="empty-list__mark" aria-hidden="true">--</span>
          <div>
            <strong>No readings yet</strong>
            <p>No sensor readings have been returned by the API yet.</p>
          </div>
        </div>
      ) : (
        <div className="readings-table-wrap">
          <table className="readings-table">
            <thead>
              <tr>
                <th scope="col">Zone / time</th>
                <th scope="col">Energy</th>
                <th scope="col">Water</th>
                <th scope="col">Occupancy</th>
              </tr>
            </thead>
            <tbody>
              {readings.map((reading) => (
                <tr key={reading.id}>
                  <td>
                    <strong>{reading.zone_name}</strong>
                    <time>{formatTime(reading.timestamp)}</time>
                  </td>
                  <td>{formatNumber(reading.energy_kwh)} <span>kWh</span></td>
                  <td>{formatNumber(reading.water_liters)} <span>L</span></td>
                  <td>{reading.occupancy.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}