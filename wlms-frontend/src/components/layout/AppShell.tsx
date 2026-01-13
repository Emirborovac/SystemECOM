 "use client";

import type { ReactNode } from "react";

import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { ToastProvider } from "@/components/feedback/ToastProvider";

export function AppShell({
  nav,
  title,
  children
}: {
  nav: "admin" | "client" | "worker";
  title: string;
  children: ReactNode;
}) {
  return (
    <ToastProvider>
      <div className="min-h-screen">
        <TopBar />
        <main className="mx-auto max-w-6xl px-6 py-6">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-[220px_1fr]">
            <Sidebar nav={nav} />
            <div>
              <div className="text-xs uppercase tracking-widest text-muted">{title}</div>
              <div className="mt-4">{children}</div>
            </div>
          </div>
        </main>
      </div>
    </ToastProvider>
  );
}




