 "use client";

import { useLocale, useTranslations } from "next-intl";
import { usePathname, useRouter } from "next/navigation";

import { clearTokens } from "@/lib/auth/tokens";
import { api } from "@/lib/api/http";
import { locales, type Locale } from "@/lib/i18n/routing";

export function TopBar() {
  const locale = useLocale() as Locale;
  const t = useTranslations("common");
  const appT = useTranslations("app");
  const pathname = usePathname();
  const router = useRouter();

  // remove "/{locale}" prefix from current path so language switch preserves route
  const restPath = pathname && pathname.length > 3 ? pathname.slice(3) : "";

  return (
    <header className="border-b border-border">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <div className="text-xs uppercase tracking-widest text-muted">
          {appT("name")}
        </div>

        <div className="flex items-center gap-3">
          <a
            className="btn btn-ghost px-2 py-1"
            href={`/${locale}/login`}
            onClick={() => clearTokens()}
          >
            {t("logout")}
          </a>
          <div className="text-xs uppercase tracking-widest text-muted">
            {t("language")}
          </div>
          <div className="flex gap-1">
            {locales.map((l) => (
              <a
                key={l}
                className={`btn px-2 py-1 ${l === locale ? "btn-primary" : "btn-ghost"}`}
                href={`/${l}${restPath}`}
                onClick={(e) => {
                  e.preventDefault();
                  if (l === locale) return;
                  void api("/api/v1/users/me", { method: "PATCH", body: { language_pref: l } })
                    .catch(() => {})
                    .finally(() => {
                      router.push(`/${l}${restPath}`);
                    });
                }}
              >
                {l.toUpperCase()}
              </a>
            ))}
          </div>
        </div>
      </div>
    </header>
  );
}




