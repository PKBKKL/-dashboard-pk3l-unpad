import { AlertTriangle, Info, AlertOctagon } from "lucide-react";
import { cn } from "@/lib/format";
import type { DataQualityFlag as Flag } from "@/lib/types";

const STYLE: Record<Flag["severity"], { bg: string; text: string; Icon: typeof Info; label: string }> = {
  info: { bg: "bg-blue-50 border-blue-200", text: "text-blue-800", Icon: Info, label: "Info" },
  warning: { bg: "bg-amber-50 border-amber-200", text: "text-amber-800", Icon: AlertTriangle, label: "Peringatan" },
  error: { bg: "bg-red-50 border-red-200", text: "text-red-800", Icon: AlertOctagon, label: "Error" },
};

export function DataQualityFlags({ flags, title = "Catatan Integritas Data" }: { flags: Flag[]; title?: string }) {
  if (!flags?.length) return null;
  return (
    <section className="mt-8">
      <h2 className="text-sm font-semibold text-ink-700 mb-3">{title}</h2>
      <ul className="space-y-2">
        {flags.map((f, i) => {
          const s = STYLE[f.severity];
          return (
            <li
              key={i}
              className={cn("rounded-lg border px-3 py-2.5 flex gap-2.5 text-sm", s.bg, s.text)}
            >
              <s.Icon className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <div>
                <span className="font-medium mr-1.5">{s.label}.</span>
                {f.message}
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
