import type { ZoneStatus } from '../api/types';

const STATUS_LABELS: Record<ZoneStatus, string> = {
  NORMAL: 'Normal',
  WARNING: 'Warning',
  CRITICAL: 'Critical',
};

export function StatusPill({ status }: { status: ZoneStatus }) {
  return (
    <span className={`status-pill status-pill--${status.toLowerCase()}`}>
      <span className="status-pill__dot" aria-hidden="true" />
      {STATUS_LABELS[status]}
    </span>
  );
}