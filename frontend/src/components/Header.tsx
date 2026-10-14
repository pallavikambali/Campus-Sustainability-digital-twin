import type { SystemState } from '../api/types';

interface HeaderProps {
  systemState: SystemState;
  lastUpdated: Date | null;
}

const SYSTEM_LABELS: Record<SystemState, string> = {
  connecting: 'Connecting',
  online: 'System live',
  offline: 'Backend unavailable',
};

export function Header({ systemState, lastUpdated }: HeaderProps) {
  return (
    <aside className="sidebar">
      <a
        className="brand"
        href="#overview"
        aria-label="Campus Sustainability Digital Twin home"
      >
        <span className="brand-mark" aria-hidden="true">
          <i /><i /><i /><i />
        </span>

        <span className="brand-copy">
          <strong>Campus Twin</strong>
          <span>Sustainability operations</span>
        </span>
      </a>

      <nav className="top-navigation" aria-label="Dashboard sections">
        <a href="#overview">Overview</a>
        <a href="#operations">Operations</a>
        <a href="#zones">Zones</a>
        <a href="#waste-detection">Waste detection</a>
        <a href="#incidents">Incidents</a>
        <a href="#readings">Readings</a>
        <a href="#notifications">Notifications</a>
      </nav>

      <div className={`system-indicator system-indicator--${systemState}`}>
        <span className="system-indicator__dot" aria-hidden="true" />
        <span>{SYSTEM_LABELS[systemState]}</span>

        {lastUpdated && (
          <time>
            {lastUpdated.toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </time>
        )}
      </div>
    </aside>
  );
}