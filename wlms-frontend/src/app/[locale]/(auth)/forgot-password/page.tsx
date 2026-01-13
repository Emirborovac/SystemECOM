"use client";

import { useTranslations } from "next-intl";
import Link from "next/link";
import { useState } from "react";

import { api } from "@/lib/api/http";

export default function ForgotPasswordPage() {
  const t = useTranslations("auth");
  const [email, setEmail] = useState("");
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  return (
    <main className="min-h-screen p-6">
      <div className="card mx-auto max-w-md p-6">
        <h1 className="text-xl font-semibold">{t("forgotTitle")}</h1>
        <p className="mt-2 text-sm text-muted">{t("forgotHelp")}</p>

        <form
          className="mt-6 space-y-3"
          onSubmit={async (e) => {
            e.preventDefault();
            setError(null);
            setLoading(true);
            try {
              await api("/api/v1/auth/forgot-password", { method: "POST", auth: false, body: { email } });
              setDone(true);
            } catch {
              // still show success to avoid enumeration, but keep UX calm
              setDone(true);
            } finally {
              setLoading(false);
            }
          }}
        >
          <label className="block">
            <div className="text-xs uppercase tracking-widest text-muted">{t("email")}</div>
            <input className="input mt-2" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>

          {error ? (
            <div className="border border-border bg-surface px-3 py-2 text-sm shadow-brutal">{error}</div>
          ) : null}

          {done ? (
            <div className="border border-border bg-surface px-3 py-2 text-sm shadow-brutal">
              {t("forgotDone")}
            </div>
          ) : null}

          <button className="btn btn-primary w-full" type="submit" disabled={loading}>
            {loading ? "..." : t("sendReset")}
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


