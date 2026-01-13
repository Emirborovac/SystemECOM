"use client";

import { useTranslations } from "next-intl";

import { AppShell } from "@/components/layout/AppShell";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";

export default function ClientSettingsPage() {
  useRequireAuth();
  const nav = useTranslations("nav");
  const t = useTranslations("pages.clientSettings");
  return (
    <AppShell nav="client" title={`${nav("client")} / ${nav("settings")}`}>
      <div className="card p-5">
        <div className="text-xs uppercase tracking-widest text-muted">{t("title")}</div>
        <div className="mt-3 text-sm text-muted">
          {t("hint")}
        </div>
      </div>
    </AppShell>
  );
}



