"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Recycle,
  Trash2,
  Droplet,
  Trees,
  CarFront,
  Info,
  type LucideIcon,
} from "lucide-react";
import type { Meta } from "@/lib/types";
import { cn } from "@/lib/format";

const ICONS: Record<string, LucideIcon> = {
  recycle: Recycle,
  trash: Trash2,
  droplet: Droplet,
  tree: Trees,
  "car-crash": CarFront,
};

export function Sidebar({ meta }: { meta: Meta }) {
  const pathname = usePathname();
  return (
    <aside className="hidden lg:flex fixed left-0 top-0 h-screen w-64 flex-col border-r border-ink-200 bg-white">
      <div className="px-5 py-6 border-b border-ink-200">
        <div className="text-[11px] uppercase tracking-wide text-ink-400">PKBKKL UNPAD</div>
        <Link href="/" className="block mt-1 text-base font-semibold text-ink-900 leading-tight">
          Dashboard Pemantauan Lingkungan
        </Link>
      </div>
      <nav className="px-3 py-4 space-y-1">
        <NavItem href="/" icon={LayoutDashboard} active={pathname === "/"}>
          Ringkasan
        </NavItem>
        {meta.datasets.map((d) => {
          const Icon = ICONS[d.icon] ?? LayoutDashboard;
          return (
            <NavItem key={d.id} href={d.route} icon={Icon} active={pathname === d.route}>
              {d.label}
            </NavItem>
          );
        })}
        <NavItem href="/tentang" icon={Info} active={pathname === "/tentang"}>
          Tentang Data
        </NavItem>
      </nav>
      <div className="mt-auto px-5 py-4 border-t border-ink-200 text-xs text-ink-400">
        {meta.dashboard.organization}
      </div>
    </aside>
  );
}

function NavItem({
  href,
  icon: Icon,
  active,
  children,
}: {
  href: string;
  icon: LucideIcon;
  active: boolean;
  children: React.ReactNode;
}) {
  return (
    <Link href={href} className={cn("nav-link", active && "nav-link-active")}>
      <Icon className="h-4 w-4" />
      <span>{children}</span>
    </Link>
  );
}
