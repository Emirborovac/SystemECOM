"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";

import { AppShell } from "@/components/layout/AppShell";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";
import { api } from "@/lib/api/http";
import { useToast } from "@/components/feedback/ToastProvider";
import { DataTable } from "@/components/table/DataTable";

type Client = { id: string; name: string };
type User = { id: string; email: string; full_name: string; role: string; language_pref: string; client_id: string | null };

export default function AdminUsersPage() {
  useRequireAuth();
  const nav = useTranslations("nav");
  const t = useTranslations("pages.adminUsersPage");
  const [users, setUsers] = useState<User[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const { push } = useToast();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState("WAREHOUSE_WORKER");
  const [languagePref, setLanguagePref] = useState("en");
  const [clientId, setClientId] = useState("");

  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteClientId, setInviteClientId] = useState("");
  const [inviteLanguage, setInviteLanguage] = useState("en");

  async function load() {
    const [u, c] = await Promise.all([api<User[]>("/api/v1/users"), api<Client[]>("/api/v1/clients")]);
    setUsers(u);
    setClients(c);
    if (!clientId && c[0]?.id) setClientId(c[0].id);
    if (!inviteClientId && c[0]?.id) setInviteClientId(c[0].id);
  }

  useEffect(() => {
    void load().catch(() => setError(t("loadFailed")));
  }, []);

  return (
    <AppShell nav="admin" title={`${nav("admin")} / ${nav("users")}`}>
      <div className="grid gap-4">
        <div className="card p-5">
          <div className="text-xs uppercase tracking-widest text-muted">{t("createDirect")}</div>
          <form
            className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3"
            onSubmit={async (e) => {
              e.preventDefault();
              setError(null);
              setOk(null);
              if (!email.trim() || !password.trim()) {
                setError(t("createFailed"));
                push({ title: t("createFailed"), variant: "error" });
                return;
              }
              try {
                await api<User>("/api/v1/users", {
                  method: "POST",
                  body: {
                    email,
                    password,
                    full_name: fullName,
                    role,
                    language_pref: languagePref,
                    client_id: role === "CLIENT_USER" ? clientId : null
                  }
                });
                setOk(t("created"));
                push({ title: t("created"), variant: "success" });
                setEmail("");
                setPassword("");
                setFullName("");
                await load();
              } catch {
                setError(t("createFailed"));
                push({ title: t("createFailed"), variant: "error" });
              }
            }}
          >
            <input className="input" placeholder={t("email")} value={email} onChange={(e) => setEmail(e.target.value)} />
            <input className="input" placeholder={t("password")} type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
            <input className="input" placeholder={t("fullName")} value={fullName} onChange={(e) => setFullName(e.target.value)} />
            <select className="input" value={role} onChange={(e) => setRole(e.target.value)}>
              <option value="WAREHOUSE_ADMIN">WAREHOUSE_ADMIN</option>
              <option value="WAREHOUSE_SUPERVISOR">WAREHOUSE_SUPERVISOR</option>
              <option value="WAREHOUSE_WORKER">WAREHOUSE_WORKER</option>
              <option value="DRIVER">DRIVER</option>
              <option value="CLIENT_USER">CLIENT_USER</option>
            </select>
            <select className="input" value={languagePref} onChange={(e) => setLanguagePref(e.target.value)}>
              <option value="en">en</option>
              <option value="bs">bs</option>
              <option value="de">de</option>
            </select>
            <select className="input" value={clientId} onChange={(e) => setClientId(e.target.value)} disabled={role !== "CLIENT_USER"}>
              {clients.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
            <button className="btn btn-primary md:col-span-3" type="submit">
              {t("create")}
            </button>
          </form>
          {ok ? <div className="mt-3 text-sm">{ok}</div> : null}
          {error ? <div className="mt-3 text-sm">{error}</div> : null}
        </div>

        <div className="card p-5">
          <div className="text-xs uppercase tracking-widest text-muted">{t("inviteClientUser")}</div>
          <form
            className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3"
            onSubmit={async (e) => {
              e.preventDefault();
              setError(null);
              setOk(null);
              if (!inviteEmail.trim() || !inviteClientId) {
                setError(t("inviteFailed"));
                push({ title: t("inviteFailed"), variant: "error" });
                return;
              }
              try {
                await api("/api/v1/users/invite", {
                  method: "POST",
                  body: { email: inviteEmail, client_id: inviteClientId, language: inviteLanguage }
                });
                setOk(t("invited"));
                push({ title: t("invited"), variant: "success" });
                setInviteEmail("");
              } catch {
                setError(t("inviteFailed"));
                push({ title: t("inviteFailed"), variant: "error" });
              }
            }}
          >
            <input className="input" placeholder={t("email")} value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)} />
            <select className="input" value={inviteClientId} onChange={(e) => setInviteClientId(e.target.value)}>
              {clients.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
            <select className="input" value={inviteLanguage} onChange={(e) => setInviteLanguage(e.target.value)}>
              <option value="en">en</option>
              <option value="bs">bs</option>
              <option value="de">de</option>
            </select>
            <button className="btn btn-primary md:col-span-3" type="submit">
              {t("sendInvite")}
            </button>
          </form>
        </div>

        <div className="card p-5">
          <div className="flex items-center justify-between">
            <div className="text-xs uppercase tracking-widest text-muted">{t("users")}</div>
            <button className="btn btn-ghost" type="button" onClick={() => void load().catch(() => setError(t("reloadFailed")))}>
              {t("refresh")}
            </button>
          </div>
          <div className="mt-3">
            <DataTable<User>
              rows={users}
              rowKey={(u) => u.id}
              filterPlaceholder={t("email")}
              filterFn={(u, q) => `${u.email} ${u.full_name} ${u.role}`.toLowerCase().includes(q)}
              columns={[
                { header: t("email"), cell: (u) => u.email },
                { header: t("role"), cell: (u) => u.role },
                { header: t("lang"), cell: (u) => u.language_pref },
                { header: t("client"), cell: (u) => <span className="font-mono text-xs">{u.client_id ?? "—"}</span> },
                { header: t("id"), cell: (u) => <span className="font-mono text-xs">{u.id}</span> },
              ]}
            />
          </div>
        </div>
      </div>
    </AppShell>
  );
}


