import Link from "next/link";
import { ArrowRight, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/format";

export function KpiCard({
  label,
  value,
  unit,
  trend,
  icon: Icon,
  href,
  accent = "brand",
}: {
  label: string;
  value: string;
  unit?: string;
  trend?: string;
  icon?: LucideIcon;
  href?: string;
  accent?: "brand" | "blue" | "amber" | "red" | "slate";
}) {
  const accentMap: Record<string, string> = {
    brand: "bg-brand-50 text-brand-700",
    blue: "bg-blue-50 text-blue-700",
    amber: "bg-amber-50 text-amber-700",
    red: "bg-red-50 text-red-700",
    slate: "bg-ink-100 text-ink-700",
  };
  const inner = (
    <div className="card card-pad h-full flex flex-col">
      <div className="flex items-start justify-between">
        <div className="text-xs font-medium uppercase tracking-wide text-ink-400">{label}</div>
        {Icon && (
          <div className={cn("rounded-lg p-2", accentMap[accent])}>
            <Icon className="h-4 w-4" />
          </div>
        )}
      </div>
      <div className="mt-3 flex items-baseline gap-1.5">
        <div className="text-2xl font-semibold text-ink-900 tabular-nums">{value}</div>
        {unit && <div className="text-sm text-ink-400">{unit}</div>}
      </div>
      {trend && <div className="mt-2 text-xs text-ink-600">{trend}</div>}
      {href && (
        <div className="mt-auto pt-3">
          <span className="text-xs text-brand-700 font-medium inline-flex items-center gap-1">
            Detail <ArrowRight className="h-3 w-3" />
          </span>
        </div>
      )}
    </div>
  );
  return href ? (
    <Link href={href} className="block hover:scale-[1.005] transition-transform">
      {inner}
    </Link>
  ) : (
    inner
  );
}
