import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "./_components/Sidebar";
import { getMeta } from "@/lib/data";

export const metadata: Metadata = {
  title: "Dashboard Pemantauan Lingkungan UNPAD",
  description: "Pusat Keselamatan, Keamanan dan Ketertiban Lingkungan (PK3L) Universitas Padjadjaran",
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const meta = await getMeta();
  return (
    <html lang="id">
      <body>
        <div className="min-h-screen flex">
          <Sidebar meta={meta} />
          <main className="flex-1 ml-0 lg:ml-64 px-6 py-6 lg:px-10 lg:py-8 max-w-[1400px]">
            {children}
            <footer className="mt-16 pt-6 border-t border-ink-200 text-xs text-ink-400 flex flex-wrap items-center justify-between gap-2">
              <span>
                {meta.dashboard.organization} · {meta.dashboard.subtitle}
              </span>
              <span>
                v{meta.dashboard.version} · diperbarui {meta.dashboard.last_updated}
              </span>
            </footer>
          </main>
        </div>
      </body>
    </html>
  );
}
