import { useEffect, useState } from 'react';

import { getDashboardData, getZone, runSimulation } from './api/client';
import type { DashboardData, Incident, SimulationAction, SystemState, ZoneSummary } from './api/types';
import { Header } from './components/Header';
import { DigitalTwin } from './components/DigitalTwin';
import { SensorReadings } from './components/SensorReadings';
import { WasteDetectionPanel } from './components/WasteDetectionPanel';
import { ZoneCard } from './components/ZoneCard';
import { ThemeSelector } from './components/ThemeSelector';
import { OperationsWorkspace } from './components/OperationsWorkspace';
import { NotificationCenter } from './components/NotificationCenter';

const POLL_INTERVAL_MS = 15_000;
const ZONE_ORDER = ['Academic Block', 'Library', 'Canteen'];

function App() {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [systemState, setSystemState] = useState<SystemState>('connecting');
  const [isLoading, setIsLoading] = useState(true);
  const [pageError, setPageError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [pending, setPending] = useState<{ zoneId: string; action: SimulationAction } | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [selectedZoneId, setSelectedZoneId] = useState('');
  const [selectedZoneDetail, setSelectedZoneDetail] = useState<(ZoneSummary & { active_incidents: Incident[] }) | null>(null);
  const [zoneDetailLoading, setZoneDetailLoading] = useState(false);
  const [zoneDetailError, setZoneDetailError] = useState<string | null>(null);

  async function refreshDashboard(showLoading = false) {
    if (showLoading) setIsLoading(true);
    try {
      const data = await getDashboardData();
      setDashboard(data);
      setSystemState('online');
      setPageError(null);
      setLastUpdated(new Date());
      return true;
    } catch (error) {
      setSystemState('offline');
      setPageError(error instanceof Error ? error.message : 'Unable to reach the campus API.');
      return false;
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    let cancelled = false;
    let timeout: number | undefined;
    async function poll() {
      if (cancelled) return;
      await refreshDashboard();
      if (!cancelled) timeout = window.setTimeout(() => void poll(), POLL_INTERVAL_MS);
    }
    void refreshDashboard(true).then(() => {
      if (!cancelled) timeout = window.setTimeout(() => void poll(), POLL_INTERVAL_MS);
    });
    return () => {
      cancelled = true;
      if (timeout !== undefined) window.clearTimeout(timeout);
    };
  }, []);

  const zones = [...(dashboard?.summary.zones ?? [])].sort((left, right) => {
    const leftOrder = ZONE_ORDER.indexOf(left.name);
    const rightOrder = ZONE_ORDER.indexOf(right.name);
    if (leftOrder === -1 && rightOrder === -1) return left.name.localeCompare(right.name);
    if (leftOrder === -1) return 1;
    if (rightOrder === -1) return -1;
    return leftOrder - rightOrder;
  });
  const activeZoneId = zones.some((zone) => zone.id === selectedZoneId)
    ? selectedZoneId
    : zones[0]?.id ?? '';
  const zoneFromSummary = zones.find((zone) => zone.id === activeZoneId) ?? null;
  const zoneDetail = selectedZoneDetail?.id === activeZoneId ? selectedZoneDetail : null;
  const selectedZone = zoneFromSummary
    ? {
        ...zoneFromSummary,
        ...(zoneDetail ?? {}),
        active_incident_count: zoneDetail?.active_incidents.length ?? zoneFromSummary.active_incident_count,
      }
    : null;

  useEffect(() => {
    if (!activeZoneId) {
      setSelectedZoneDetail(null);
      setZoneDetailError(null);
      setZoneDetailLoading(false);
      return;
    }
    let cancelled = false;
    let timeout: number | undefined;
    async function loadZoneDetail() {
      setZoneDetailLoading(true);
      setZoneDetailError(null);
      try {
        const detail = await getZone(activeZoneId);
        if (!cancelled) setSelectedZoneDetail(detail);
      } catch (error) {
        if (!cancelled) {
          setSelectedZoneDetail(null);
          setZoneDetailError(error instanceof Error ? error.message : 'Zone detail is unavailable.');
        }
      } finally {
        if (!cancelled) setZoneDetailLoading(false);
      }
    }
    async function pollZoneDetail() {
      await loadZoneDetail();
      if (!cancelled) {
        timeout = window.setTimeout(() => void pollZoneDetail(), POLL_INTERVAL_MS);
      }
    }
    // Poll again only after the prior request completes, avoiding overlapping
    // detail calls when the API is slow.
    void pollZoneDetail();
    return () => {
      cancelled = true;
      if (timeout !== undefined) window.clearTimeout(timeout);
    };
  }, [activeZoneId]);

  async function handleSimulation(zoneId: string, action: SimulationAction) {
    if (pending) return;
    setPending({ zoneId, action });
    setActionMessage(null);
    try {
      await runSimulation(zoneId, action);
      const refreshed = await refreshDashboard();
      setActionMessage(refreshed
        ? 'Simulation request completed. Dashboard data refreshed from the API.'
        : 'Simulation request completed, but the dashboard refresh failed. Displayed readings may be stale.');
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : 'Simulation request failed.');
    } finally {
      setPending(null);
    }
  }

  return(
    <div className="app-shell">
  <Header systemState={systemState} lastUpdated={lastUpdated} />

  <div className="dashboard-content">
    <main className="dashboard-main">
        <div className="page-heading" id="overview">
          <div>
            <p className="eyebrow">Campus sustainability / Operations console</p>
            <h1>Campus operations</h1>
            <p className="page-subtitle">
              Live readings and rule-generated incidents from monitored campus zones.
            </p>
          </div>
          <div className="page-heading__actions">
  <ThemeSelector />

  <div className="refresh-note">
    <span className="refresh-mark" aria-hidden="true" />
    Refreshes every 15 seconds
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
            <span className="loading-skeleton-mark" aria-hidden="true" />
            <div>
              <strong>Connecting to campus sensors</strong>
              <p>Loading zones, readings, and active incidents.</p>
              <div className="loading-skeleton-lines" aria-hidden="true">
                <i /><i /><i />
              </div>
            </div>
          </div>
        ) : dashboard ? (
          <>
            <OperationsWorkspace
              zones={zones}
              selectedZone={selectedZone}
              selectedZoneId={activeZoneId}
              onSelectZone={setSelectedZoneId}
              readings={dashboard.readings}
              incidents={dashboard.incidents}
              activeIncidentCount={dashboard.summary.active_incidents}
              detailIncidents={zoneDetail?.active_incidents ?? null}
              detailLoading={zoneDetailLoading}
              detailError={zoneDetailError}
            />
            <DigitalTwin
              zones={zones}
              selectedZoneId={activeZoneId}
              onSelectZone={setSelectedZoneId}
            />

            {actionMessage && (
              <div className="action-message" role="status">
                <span aria-hidden="true">{pending ? '…' : 'i'}</span>
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
                <span className="section-count">{zones.length} locations returned by API</span>
              </div>
              <div className="zone-grid">
                {zones.length === 0 ? (
                  <div className="operations-empty">
                    <strong>No monitored zones returned</strong>
                    <p>Zone readings and simulation controls are unavailable until the API returns real locations.</p>
                  </div>
                ) : zones.map((zone) => (
                  <ZoneCard
                    key={zone.id}
                    zone={zone}
                    pendingAction={pending && pending.zoneId === zone.id ? pending.action : null}
                    controlsDisabled={pending !== null}
                    onSimulate={(action) => void handleSimulation(zone.id, action)}
                    isSelected={activeZoneId === zone.id}
                    onSelect={() => setSelectedZoneId(zone.id)}
                  />
                ))}
              </div>
            </section>

            <WasteDetectionPanel
              zones={zones}
              detections={dashboard.wasteDetections}
              onUploaded={() => refreshDashboard()}
            />

            <div className="activity-grid">
              <SensorReadings readings={dashboard.readings} />
              <NotificationCenter
                status={dashboard.notificationStatus}
                history={dashboard.notifications}
                error={dashboard.notificationError}
              />
            </div>

            <footer className="dashboard-footer">
              <span>Campus sustainability operations</span>
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
  </div>
);
}

export default App;
