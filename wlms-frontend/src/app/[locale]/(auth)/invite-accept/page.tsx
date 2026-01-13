"use client";

import { useLocale, useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { useState } from "react";

import { api } from "@/lib/api/http";
import { type Locale, locales } from "@/lib/i18n/routing";

export default function InviteAcceptPage() {
  const t = useTranslations("auth");
  const currentLocale = useLocale() as Locale;
  const params = useSearchParams();
  const token = params.get("token") ?? "";

  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [languagePref, setLanguagePref] = useState<Locale>(currentLocale);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  return (
    <main className="min-h-screen p-6">
      <div className="card mx-auto max-w-md p-6">
        <h1 className="text-xl font-semibold">{t("inviteTitle")}</h1>
        <p className="mt-2 text-sm text-muted">{t("inviteHelp")}</p>

        <form
          className="mt-6 space-y-3"
          onSubmit={async (e) => {
            e.preventDefault();
            setError(null);
            setLoading(true);
            try {
              await api("/api/v1/users/invite/accept", {
                method: "POST",
                auth: false,
                body: { token, full_name: fullName, password, language_pref: languagePref }
              });
              setDone(true);
            } catch {
              setError(t("inviteFailed"));
            } finally {
              setLoading(false);
            }
          }}
        >
          <label className="block">
            <div className="text-xs uppercase tracking-widest text-muted">{t("token")}</div>
            <input className="input mt-2 font-mono text-xs" value={token} readOnly />
          </label>
          <label className="block">
            <div className="text-xs uppercase tracking-widest text-muted">{t("fullName")}</div>
            <input className="input mt-2" value={fullName} onChange={(e) => setFullName(e.target.value)} />
          </label>
          <label className="block">
            <div className="text-xs uppercase tracking-widest text-muted">{t("newPassword")}</div>
            <input className="input mt-2" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </label>
          <label className="block">
            <div className="text-xs uppercase tracking-widest text-muted">{t("languagePref")}</div>
            <select className="input mt-2" value={languagePref} onChange={(e) => setLanguagePref(e.target.value as Locale)}>
              {locales.map((l) => (
                <option key={l} value={l}>
                  {l.toUpperCase()}
                </option>
              ))}
            </select>
          </label>

          {error ? (
            <div className="border border-border bg-surface px-3 py-2 text-sm shadow-brutal">{error}</div>
          ) : null}
          {done ? (
            <div className="border border-border bg-surface px-3 py-2 text-sm shadow-brutal">{t("inviteDone")}</div>
          ) : null}

          <button className="btn btn-primary w-full" type="submit" disabled={loading || !token}>
            {loading ? "..." : t("acceptInvite")}
          </button>
        </form>

        <div className="mt-4 text-sm">
          <Link className="underline" href="./login">
            {t("backToLogin")}
          </Link>
        </div>
      </div>
    </main>
  );
}


