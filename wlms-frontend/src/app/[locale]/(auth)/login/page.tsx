"use client";

import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState } from "react";
import Link from "next/link";

export default function LoginPage() {
  const t = useTranslations("auth");
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  return (
    <main className="min-h-screen p-6">
      <div className="card mx-auto max-w-md p-6">
        <h1 className="text-xl font-semibold">{t("loginTitle")}</h1>
        <form
          className="mt-6 space-y-3"
          onSubmit={async (e) => {
            e.preventDefault();
            setError(null);
            setLoading(true);
            try {
              const { api } = await import("@/lib/api/http");
              const { setTokens } = await import("@/lib/auth/tokens");
              const data = await api<{
                access_token: string;
                refresh_token: string;
                user: { role: string };
              }>("/api/v1/auth/login", {
                method: "POST",
                auth: false,
                body: { username, password }
              });
              setTokens(data.access_token, data.refresh_token);
              // Default landing (admin for now). We’ll route by role later.
              router.push("./admin/dashboard");
            } catch (err) {
              setError(t("loginFailed"));
            } finally {
              setLoading(false);
            }
          }}
        >
          <label className="block">
            <div className="text-xs uppercase tracking-widest text-muted">
              {t("username")}
            </div>
            <input
              className="input mt-2"
              type="text"
              name="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </label>
          <label className="block">
            <div className="text-xs uppercase tracking-widest text-muted">
              {t("password")}
            </div>
            <input
              className="input mt-2"
              type="password"
              name="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          {error ? (
            <div className="border border-border bg-surface px-3 py-2 text-sm shadow-brutal">
              {error}
            </div>
          ) : null}
          <button className="btn btn-primary w-full" type="submit" disabled={loading}>
            {loading ? "…" : t("login")}
          </button>
        </form>

        <div className="mt-4 flex items-center justify-between text-sm">
          <Link className="underline" href="./forgot-password">
            {t("forgotLink")}
          </Link>
          <Link className="underline" href="./invite-accept">
            {t("inviteLink")}
          </Link>
        </div>
      </div>
    </main>
  );
}




