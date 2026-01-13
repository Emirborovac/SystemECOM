"use client";

import { useLocale, useTranslations } from "next-intl";

import type { Locale } from "@/lib/i18n/routing";

type NavKind = "admin" | "client" | "worker";

export function Sidebar({ nav }: { nav: NavKind }) {
  const locale = useLocale() as Locale;
  const t = useTranslations("nav");

  const links =
    nav === "admin"
      ? [
          { href: `/${locale}/admin/dashboard`, label: t("dashboard") },
          { href: `/${locale}/admin/clients`, label: t("clients") },
          { href: `/${locale}/admin/warehouses`, label: t("warehouses") },
          { href: `/${locale}/admin/products`, label: t("products") },
          { href: `/${locale}/admin/inbound`, label: t("inbound") },
          { href: `/${locale}/admin/putaway`, label: t("putaway") },
          { href: `/${locale}/admin/outbound`, label: t("outbound") },
          { href: `/${locale}/admin/picking`, label: t("picking") },
          { href: `/${locale}/admin/dispatch`, label: t("dispatch") },
          { href: `/${locale}/admin/returns`, label: t("returns") },
          { href: `/${locale}/admin/discrepancies`, label: t("discrepancies") },
          { href: `/${locale}/admin/invoices`, label: t("invoices") },
          { href: `/${locale}/admin/reports`, label: t("reports") },
          { href: `/${locale}/admin/audit`, label: t("audit") },
          { href: `/${locale}/admin/users`, label: t("users") },
          { href: `/${locale}/admin/settings`, label: t("settings") },
          { href: `/${locale}/admin/documents`, label: t("documents") }
        ]
      : nav === "client"
        ? [
            { href: `/${locale}/portal/dashboard`, label: t("dashboard") },
            { href: `/${locale}/portal/inventory`, label: t("inventory") },
            { href: `/${locale}/portal/inbound`, label: t("inbound") },
            { href: `/${locale}/portal/outbound`, label: t("createOutbound") },
            { href: `/${locale}/portal/orders`, label: t("orders") },
            { href: `/${locale}/portal/returns`, label: t("returns") },
            { href: `/${locale}/portal/invoices`, label: t("invoices") },
            { href: `/${locale}/portal/reports`, label: t("reports") },
            { href: `/${locale}/portal/documents`, label: t("documents") },
            { href: `/${locale}/portal/settings`, label: t("settings") }
          ]
        : [
            { href: `/${locale}/worker/home`, label: t("home") },
            { href: `/${locale}/worker/receive`, label: t("inbound") },
            { href: `/${locale}/worker/putaway`, label: t("putaway") },
            { href: `/${locale}/worker/pick`, label: t("picking") },
            { href: `/${locale}/worker/pack`, label: t("dispatch") },
            { href: `/${locale}/worker/dispatch`, label: t("dispatch") },
            { href: `/${locale}/worker/returns`, label: t("returns") },
            { href: `/${locale}/worker/discrepancy`, label: t("discrepancies") }
          ];

  return (
    <aside className="card p-4">
      <nav className="flex flex-col gap-2">
        {links.map((l) => (
          <a key={l.href} className="btn btn-ghost justify-start" href={l.href}>
            {l.label}
          </a>
        ))}
      </nav>
    </aside>
  );
}


