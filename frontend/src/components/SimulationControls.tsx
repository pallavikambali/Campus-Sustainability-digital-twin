import type { SimulationAction } from '../api/types';

interface SimulationControlsProps {
  busy: boolean;
  pendingAction: SimulationAction | null;
  onSimulate: (action: SimulationAction) => void;
}

const ACTIONS: { action: SimulationAction; label: string; marker: string }[] = [
  { action: 'energy-spike', label: 'Simulate energy spike', marker: 'E' },
  { action: 'water-leak', label: 'Simulate water leak', marker: 'W' },
  { action: 'occupancy-surge', label: 'Simulate occupancy surge', marker: 'O' },
  { action: 'reset', label: 'Reset zone', marker: 'R' },
];

export function SimulationControls({
  busy,
  pendingAction,
  onSimulate,
}: SimulationControlsProps) {
  return (
    <div className="simulation-controls" aria-label="Zone simulation controls">
      {ACTIONS.map(({ action, label, marker }) => (
        <button
          className={`simulation-button ${action === 'reset' ? 'simulation-button--reset' : ''}`}
          key={action}
          type="button"
          disabled={busy}
          onClick={() => onSimulate(action)}
          title={label}
          aria-label={`${label} for this zone`}
        >
          <span className="simulation-button__marker" aria-hidden="true">
            {pendingAction === action ? <span className="mini-spinner" /> : marker}
          </span>
          <span>{pendingAction === action ? 'Working...' : label}</span>
        </button>
      ))}
    </div>
  );
}