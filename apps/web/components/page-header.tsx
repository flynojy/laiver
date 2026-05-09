import { Badge } from "@/components/ui/badge";

export function PageHeader({
  eyebrow,
  title,
  description,
  badge
}: {
  eyebrow: string;
  title: string;
  description: string;
  badge?: string;
}) {
  return (
    <div className="mb-8 flex flex-col gap-2 border-b border-[color:var(--border)] pb-6 md:flex-row md:items-end md:justify-between">
      <div>
        <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--muted-foreground)]">{eyebrow}</p>
        <h1 className="mt-2 text-2xl font-medium tracking-tight md:text-[28px]">{title}</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--muted-foreground)]">{description}</p>
      </div>
      {badge ? (
        <Badge className="w-fit border-[color:var(--border-strong)] bg-[var(--card)] text-[var(--foreground)]">
          {badge}
        </Badge>
      ) : null}
    </div>
  );
}
