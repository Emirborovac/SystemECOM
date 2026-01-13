"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";

import { AppShell } from "@/components/layout/AppShell";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";
import { api } from "@/lib/api/http";

export default function ClientInboundCreatePage() {
  useRequireAuth();
  const nav = useTranslations("nav");
  const t = useTranslations("pages.clientInbound");
  const [clientId, setClientId] = useState("");
  const [warehouseId, setWarehouseId] = useState("");
  const [supplier, setSupplier] = useState("");
  const [notes, setNotes] = useState("");

  const [productId, setProductId] = useState("");
  const [expectedQty, setExpectedQty] = useState(1);

  const [error, setError] = useState<string | null>(null);
  const [createdId, setCreatedId] = useState<string | null>(null);

  return (
    <AppShell nav="client" title={`${nav("client")} / ${nav("inbound")}`}>
      <div className="card p-5">
        <div className="text-xs uppercase tracking-widest text-muted">{t("title")}</div>
        <form
          className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2"
          onSubmit={async (e) => {
            e.preventDefault();
            setError(null);
            setCreatedId(null);
            try {
              const res = await api<{ id: string }>("/api/v1/inbound", {
                method: "POST",
                body: {
                  client_id: clientId,
                  warehouse_id: warehouseId,
                  supplier,
                  notes,
                  lines: [{ product_id: productId, expected_qty: expectedQty }]
                }
              });
              setCreatedId(res.id);
            } catch {
              setError(t("createFailed"));
            }
          }}
        >
          <input className="input" placeholder={t("clientId")} value={clientId} onChange={(e) => setClientId(e.target.value)} />
          <input className="input" placeholder={t("warehouseId")} value={warehouseId} onChange={(e) => setWarehouseId(e.target.value)} />
          <input className="input" placeholder={t("supplier")} value={supplier} onChange={(e) => setSupplier(e.target.value)} />
          <input className="input" placeholder={t("notes")} value={notes} onChange={(e) => setNotes(e.target.value)} />
          <input className="input" placeholder={t("productId")} value={productId} onChange={(e) => setProductId(e.target.value)} />
          <input className="input" type="number" min={1} value={expectedQty} onChange={(e) => setExpectedQty(Number(e.target.value))} />
          <button className="btn btn-primary md:col-span-2" type="submit">{t("submitInbound")}</button>
        </form>
        {createdId ? <div className="mt-3 text-sm">{t("createdInbound")}: {createdId}</div> : null}
        {error ? <div className="mt-3 text-sm">{error}</div> : null}
      </div>
    </AppShell>
  );
}


