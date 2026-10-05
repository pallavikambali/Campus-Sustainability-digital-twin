import type { ReadingListItem } from '../api/types';

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
    <section className="activity-panel" id="readings">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Latest sensor activity</p>
          <h2>Recent readings</h2>
        </div>
        <span className="readings-unit">Latest first</span>
      </div>
      {readings.length === 0 ? (
        <div className="empty-list">
          <span className="empty-list__mark" aria-hidden="true">--</span>
          <div>
            <strong>No readings yet</strong>
            <p>Run a zone simulation to generate the first sensor sample.</p>
          </div>
        </div>
      ) : (
        <div className="readings-table-wrap">
          <table className="readings-table">
            <thead>
              <tr>
                <th>Zone / time</th>
                <th>Energy</th>
                <th>Water</th>
                <th>Occupancy</th>
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