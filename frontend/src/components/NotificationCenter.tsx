import type {
  NotificationConfigStatus,
  NotificationDelivery,
} from '../api/types';

function formatTime(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString([], {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
}

export function NotificationCenter({
  status,
  history,
  error,
}: {
  status: NotificationConfigStatus | null | undefined;
  history: NotificationDelivery[] | null | undefined;
  error?: string | null;
}) {
  return (
    <section className="activity-panel notification-center" id="notifications">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Critical incident alerts</p>
          <h2>Notification center</h2>
        </div>
        <span className="panel-count">{history?.length ?? '—'}</span>
      </div>

      {!status ? (
        <div className="notification-config-state" role="status">
          <strong>Notification configuration is unavailable</strong>
          <p>
            {error ??
              'The API did not return channel configuration. The dashboard cannot confirm delivery setup.'}
          </p>
          <p>Email status is unknown. WhatsApp delivery is not confirmed.</p>
        </div>
      ) : (
        <div className="notification-channel-grid">
          <div className="notification-channel">
            <span>Email</span>
            <strong className={status.email.enabled ? 'is-ready' : 'is-unconfigured'}>
              {status.email.enabled ? 'Configured' : 'Not configured'}
            </strong>
            <small>
              {status.email.enabled
                ? 'Critical-zone alerts are enabled on the backend.'
                : 'Configure SMTP and a recipient on the backend before email alerts can be sent.'}
            </small>
          </div>
          <div className="notification-channel">
            <span>WhatsApp</span>
            <strong className="is-unconfigured">Not configured</strong>
            <small>Official Cloud API delivery has not been enabled.</small>
          </div>
        </div>
      )}

      {history === null ? (
        <p className="notification-history-empty" role="status">
          Notification attempt history could not be loaded
          {error ? `: ${error}` : '.'}
        </p>
      ) : history?.length ? (
        <ul className="notification-history">
          {history.map((item) => (
            <li key={item.id}>
              <div className="notification-history__headline">
                <strong>{item.incident_type.replaceAll('_', ' ')}</strong>
                <span className={`notification-state notification-state--${item.status.toLowerCase()}`}>
                  {item.status === 'ACCEPTED' ? 'Accepted by SMTP relay' : 'Failed'}
                </span>
              </div>
              <p>
                {item.zone_name} · {item.severity} · {item.channel}
              </p>
              <time>{formatTime(item.attempted_at)}</time>
              {item.status === 'ACCEPTED' && (
                <small>Provider acceptance does not confirm delivery to the recipient’s inbox.</small>
              )}
              {item.error && <p className="notification-error">{item.error}</p>}
            </li>
          ))}
        </ul>
      ) : (
        <p className="notification-history-empty">
          No notification attempts have been recorded.
        </p>
      )}

      <p className="data-provenance-note">
        Hypothetical What-if previews never trigger alerts. Recipient settings are backend
        environment configuration; this app has no authorized settings-management flow yet.
      </p>
    </section>
  );
}
