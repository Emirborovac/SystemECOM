"use client";

import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { useState } from "react";

import { api } from "@/lib/api/http";

export default function ResetPasswordPage() {
  const t = useTranslations("auth");
  const params = useSearchParams();
  const token = params.get("token") ?? "";

  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  return (
    <main className="min-h-screen p-6">
      <div className="card mx-auto max-w-md p-6">
        <h1 className="text-xl font-semibold">{t("resetTitle")}</h1>
        <p className="mt-2 text-sm text-muted">{t("resetHelp")}</p>

        <form
          className="mt-6 space-y-3"
          onSubmit={async (e) => {
            e.preventDefault();
            setError(null);
            setLoading(true);
            try {
              await api("/api/v1/auth/reset-password", {
                method: "POST",
                auth: false,
                body: { token, new_password: password }
              });
              setDone(true);
            } catch {
              setError(t("resetFailed"));
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
            <div className="text-xs uppercase tracking-widest text-muted">{t("newPassword")}</div>
            <input className="input mt-2" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </label>

          {error ? (
            <div className="border border-border bg-surface px-3 py-2 text-sm shadow-brutal">{error}</div>
          ) : null}
          {done ? (
            <div className="border border-border bg-surface px-3 py-2 text-sm shadow-brutal">{t("resetDone")}</div>
          ) : null}

          <button className="btn btn-primary w-full" type="submit" disabled={loading || !token}>
            {loading ? "..." : t("reset")}
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


