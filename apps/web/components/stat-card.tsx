export function StatCard({
  title,
  value,
  description
}: {
  title: string;
  value: string;
  description: string;
}) {
  return (
    <div className="group relative overflow-hidden rounded-[12px] border border-[color:var(--border)] bg-[var(--surface)] p-5 shadow-panel transition hover:shadow-hover">
      <span className="absolute left-0 top-0 h-full w-[3px] bg-[var(--accent)]" />
      <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-[var(--foreground-muted)]">
        {title}
      </p>
      <p className="mt-3 font-mono text-[36px] font-semibold leading-none tracking-tight text-[var(--foreground)]">
        {value}
      </p>
      <p className="mt-4 text-xs leading-5 text-[var(--foreground-muted)]">{description}</p>
    </div>
  );
}
