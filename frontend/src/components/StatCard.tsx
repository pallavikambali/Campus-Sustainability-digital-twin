type StatTone = 'green' | 'mint' | 'amber' | 'red' | 'ink';

interface StatCardProps {
  label: string;
  value: number;
  detail: string;
  tone: StatTone;
}

export function StatCard({ label, value, detail, tone }: StatCardProps) {
  return (
    <article className={`stat-card stat-card--${tone}`}>
      <div className="stat-card__topline">
        <span>{label}</span>
        <span className="stat-card__tick" aria-hidden="true" />
      </div>
      <strong className="stat-card__value">{value.toLocaleString()}</strong>
      <span className="stat-card__detail">{detail}</span>
    </article>
  );
}