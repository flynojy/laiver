import { cn } from "@/lib/utils";

export function SyncBars({ className }: { className?: string }) {
  return (
    <div className={cn("inline-flex h-3 items-end gap-[2px]", className)} aria-hidden>
      {[0, 1, 2, 3, 4].map((i) => (
        <span
          key={i}
          className="block w-[3px] origin-bottom bg-current"
          style={{
            height: "100%",
            animation: `sync-bar 1.4s ease-in-out ${i * 0.15}s infinite`,
            transform: `scaleY(${0.4 + ((i % 3) * 0.25)})`
          }}
        />
      ))}
    </div>
  );
}
