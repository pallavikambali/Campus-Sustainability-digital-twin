import { useEffect, useState } from 'react';

import { getDashboardData, runSimulation } from './api/client';
import type { DashboardData, SimulationAction, SystemState } from './api/types';
import { DigitalTwin } from './components/DigitalTwin';
import { Header } from './components/Header';
import { IncidentList } from './components/IncidentList';
import { SensorReadings } from './components/SensorReadings';
import { StatCard } from './components/StatCard';
import { WasteDetectionPanel } from './components/WasteDetectionPanel';
import { ZoneCard } from './components/ZoneCard';
import { ThemeSelector } from './components/ThemeSelector';

const POLL_INTERVAL_MS = 4_000;
const ZONE_ORDER = ['Academic Block', 'Library', 'Hostel Block'];

function App() {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [systemState, setSystemState] = useState<SystemState>('connecting');
  const [isLoading, setIsLoading] = useState(true);
  const [pageError, setPageError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [pending, setPending] = useState<{ zoneId: string; action: SimulationAction } | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  async function refreshDashboard(showLoading = false) {
  if (showLoading) setIsLoading(true);

  try {
    const data = await getDashboardData();

    setDashboard(data);
    setSystemState('online');
    setPageError(null);
    setLastUpdated(new Date());
  } catch (error) {
    setSystemState('offline');
    setPageError(
      error instanceof Error
        ? error.message
        : 'Unable to reach the campus API.',
    );
  } finally {
    setIsLoading(false);
  }
}  

  useEffect(() => {
    void refreshDashboard(true);
    const interval = window.setInterval(() => void refreshDashboard(), POLL_INTERVAL_MS);
    return () => window.clearInterval(interval);
  }, []);

  async function handleSimulation(zoneId: string, action: SimulationAction) {
    if (pending) return;
    setPending({ zoneId, action });
    setActionMessage(null);
    try {
      await runSimulation(zoneId, action);
      await refreshDashboard();
      setActionMessage(
        action === 'reset'
          ? 'Zone reset. Latest readings and incident state are updated.'
          : 'Scenario complete. Latest readings and incidents are updated.',
      );
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : 'Simulation request failed.');
    } finally {
      setPending(null);
    }
  }

  const zones = [...(dashboard?.summary.zones ?? [])].sort(
    (left, right) => ZONE_ORDER.indexOf(left.name) - ZONE_ORDER.indexOf(right.name),
  );

  return (
    <div className="app-shell">
      <Header systemState={systemState} lastUpdated={lastUpdated} />
      <main className="dashboard-main">
        <div className="page-heading" id="overview">
          <div>
            <p className="eyebrow">Campus operations / Live overview</p>
            <h1>Campus overview</h1>
            <p className="page-subtitle">
              A live view of resource use and conditions across the campus.
            </p>
          </div>
          <div className="page-heading__actions">
  <ThemeSelector />

  <div className="refresh-note">
    <span className="refresh-mark" aria-hidden="true" />
    Refreshes every 4 seconds
  </div>
</div>
        </div>

        {pageError && (
          <div className={`connection-banner ${dashboard ? 'is-stale' : 'is-error'}`} role="alert">
            <span className="connection-banner__mark" aria-hidden="true" />
            <div>
              <strong>{dashboard ? 'Live connection interrupted' : 'Campus API unavailable'}</strong>
              <p>
                {dashboard
                  ? `Showing the last successful data. ${pageError}`
                  : pageError}
              </p>
            </div>
            <button className="text-button" onClick={() => void refreshDashboard(true)}>
              Retry connection
            </button>
          </div>
        )}

        {isLoading && !dashboard ? (
          <div className="loading-state" role="status">
            <span className="loading-state__spinner" aria-hidden="true" />
            <div>
              <strong>Connecting to campus sensors</strong>
              <p>Loading zones, readings, and active incidents.</p>
            </div>
          </div>
        ) : dashboard ? (
          <>
            <section className="overview-stats" aria-label="Campus overview statistics">
              <StatCard label="Total zones" value={dashboard.summary.total_zones} detail="Monitored areas" tone="green" />
              <StatCard label="Normal" value={dashboard.summary.normal_zones} detail="Within expected range" tone="mint" />
              <StatCard label="Warning" value={dashboard.summary.warning_zones} detail="Needs attention" tone="amber" />
              <StatCard label="Critical" value={dashboard.summary.critical_zones} detail="Immediate attention" tone="red" />
              <StatCard label="Active incidents" value={dashboard.summary.active_incidents} detail="Open rule alerts" tone="ink" />
            </section>

            {actionMessage && (
              <div className="action-message" role="status">
                <span aria-hidden="true">{pending ? '...' : 'OK'}</span>
                {actionMessage}
                <button
                  className="action-message__close"
                  aria-label="Dismiss message"
                  onClick={() => setActionMessage(null)}
                >
                  Close
                </button>
              </div>
            )}

            <section className="content-section" id="zones">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Monitor and simulate</p>
                  <h2>Campus zones</h2>
                </div>
                <span className="section-count">{zones.length} monitored locations</span>
              </div>
              <div className="zone-grid">
                {zones.map((zone) => (
                  <ZoneCard
                    key={zone.id}
                    zone={zone}
                    pendingAction={pending && pending.zoneId === zone.id ? pending.action : null}
                    controlsDisabled={pending !== null}
                    onSimulate={(action) => void handleSimulation(zone.id, action)}
                  />
                ))}
              </div>
            </section>

            <DigitalTwin zones={zones} />

            <WasteDetectionPanel
              zones={zones}
              detections={dashboard.wasteDetections}
              onUploaded={() => refreshDashboard()}
            />

            <div className="activity-grid">
              <IncidentList incidents={dashboard.incidents} />
              <SensorReadings readings={dashboard.readings} />
            </div>

            <footer className="dashboard-footer">
              <span>Campus Sustainability Digital Twin</span>
              <span>
                {lastUpdated
                  ? `Last updated ${lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}`
                  : 'Waiting for first update'}
              </span>
            </footer>
          </>
        ) : !isLoading ? (
          <div className="empty-connection">
            <div className="empty-connection__symbol" aria-hidden="true">!</div>
            <h2>Dashboard data is unavailable</h2>
            <p>Check that the backend API and PostgreSQL are running, then retry.</p>
            <button className="button button--primary" onClick={() => void refreshDashboard(true)}>
              Retry connection
            </button>
          </div>
        ) : null}
      </main>
    </div>
  );
}

export default App;
