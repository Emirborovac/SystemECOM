\"use client\";

import { useTranslations } from "next-intl";

import { AppShell } from "@/components/layout/AppShell";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";

export default function ClientDashboardPage() {
  const t = useTranslations("nav");
  useRequireAuth();

  return (
    <AppShell nav="client" title={`${t("client")} / ${t("dashboard")}`}>
      <div className="card p-5">
        <div className="text-xs uppercase tracking-widest text-muted">
          Client dashboard (placeholder)
        </div>
        <div className="mt-2 text-sm text-muted">
          Inventory, orders, invoices, and documents will live here.
        </div>
      </div>
    </AppShell>
  );
}




