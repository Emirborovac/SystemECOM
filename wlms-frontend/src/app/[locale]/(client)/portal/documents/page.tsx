"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";

import { AppShell } from "@/components/layout/AppShell";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";
import { api, apiBaseUrl } from "@/lib/api/http";

type FileItem = {
  id: string;
  file_type: string;
  original_name: string;
  mime_type: string;
  size_bytes: number;
  created_at: string;
};

export default function ClientDocumentsPage() {
  useRequireAuth();
  const nav = useTranslations("nav");
  const t = useTranslations("pages.adminDocuments");
  const c = useTranslations("common");
  const [items, setItems] = useState<FileItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [fileType, setFileType] = useState("");
  const [createdAfter, setCreatedAfter] = useState("");
  const [createdBefore, setCreatedBefore] = useState("");

  async function load() {
    setError(null);
    try {
      const qs = new URLSearchParams();
      if (fileType) qs.set("file_type", fileType);
      if (createdAfter) qs.set("created_after", createdAfter);
      if (createdBefore) qs.set("created_before", createdBefore);
      const data = await api<FileItem[]>(`/api/v1/files${qs.toString() ? `?${qs.toString()}` : ""}`);
      setItems(data);
    } catch {
      setError(t("loadFailed"));
    }
  }

  useEffect(() => {
    void load();
  }, [fileType, createdAfter, createdBefore]);

  return (
    <AppShell nav="client" title={`${nav("client")} / ${nav("documents")}`}>
      <div className="card p-5">
        <div className="flex items-center justify-between">
          <div className="text-xs uppercase tracking-widest text-muted">{t("files")}</div>
          <button className="btn btn-ghost" type="button" onClick={() => void load()}>
            {c("refresh")}
          </button>
        </div>
        <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3">
          <input
            className="input"
            placeholder={t("fileType")}
            value={fileType}
            onChange={(e) => setFileType(e.target.value)}
          />
          <input
            className="input"
            placeholder={t("createdAfter")}
            value={createdAfter}
            onChange={(e) => setCreatedAfter(e.target.value)}
          />
          <input
            className="input"
            placeholder={t("createdBefore")}
            value={createdBefore}
            onChange={(e) => setCreatedBefore(e.target.value)}
          />
        </div>
        {error ? <div className="mt-3 text-sm">{error}</div> : null}
        <div className="mt-3 overflow-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="py-2 text-left">{t("type")}</th>
                <th className="py-2 text-left">{t("name")}</th>
                <th className="py-2 text-left"></th>
              </tr>
            </thead>
            <tbody>
              {items.map((f) => (
                <tr key={f.id} className="border-b border-border">
                  <td className="py-2">{f.file_type}</td>
                  <td className="py-2">{f.original_name}</td>
                  <td className="py-2">
                    <a className="btn btn-primary" href={`${apiBaseUrl()}/api/v1/files/${f.id}/download`}>
                      {c("download")}
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </AppShell>
  );
}



