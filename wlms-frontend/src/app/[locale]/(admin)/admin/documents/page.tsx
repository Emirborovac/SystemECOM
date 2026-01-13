"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";

import { AppShell } from "@/components/layout/AppShell";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";
import { api, apiBaseUrl } from "@/lib/api/http";
import { getAccessToken } from "@/lib/auth/tokens";
import { DataTable } from "@/components/table/DataTable";
import { useToast } from "@/components/feedback/ToastProvider";

type FileItem = {
  id: string;
  file_type: string;
  original_name: string;
  mime_type: string;
  size_bytes: number;
  created_at: string;
};

export default function AdminDocumentsPage() {
  useRequireAuth();
  const t = useTranslations("pages.adminDocuments");
  const c = useTranslations("common");
  const [items, setItems] = useState<FileItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const { push } = useToast();
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
      push({ title: t("loadFailed"), variant: "error" });
    }
  }

  useEffect(() => {
    void load();
  }, [fileType, createdAfter, createdBefore]);

  return (
    <AppShell nav="admin" title={t("title")}>
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
        <div className="mt-3">
          <DataTable<FileItem>
            rows={items}
            rowKey={(f) => f.id}
            filterPlaceholder={t("name")}
            filterFn={(f, q) => `${f.file_type} ${f.original_name}`.toLowerCase().includes(q)}
            columns={[
              { header: t("type"), cell: (f) => f.file_type },
              { header: t("name"), cell: (f) => f.original_name },
              { header: t("size"), cell: (f) => String(f.size_bytes) },
              { header: t("created"), cell: (f) => f.created_at },
              {
                header: "",
                cell: (f) => (
                  <button
                    className="btn btn-primary"
                    type="button"
                    onClick={async () => {
                      setError(null);
                      try {
                        const token = getAccessToken();
                        const res = await fetch(`${apiBaseUrl()}/api/v1/files/${f.id}/download`, {
                          headers: token ? { Authorization: `Bearer ${token}` } : undefined,
                        });
                        if (!res.ok) throw new Error(await res.text());
                        const blob = await res.blob();
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement("a");
                        a.href = url;
                        a.download = f.original_name || `${f.id}`;
                        document.body.appendChild(a);
                        a.click();
                        a.remove();
                        URL.revokeObjectURL(url);
                        push({ title: t("download"), variant: "success" });
                      } catch {
                        setError(t("downloadFailed"));
                        push({ title: t("downloadFailed"), variant: "error" });
                      }
                    }}
                  >
                    {t("download")}
                  </button>
                ),
              },
            ]}
          />
        </div>
      </div>
    </AppShell>
  );
}


