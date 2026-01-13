"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";

import { AppShell } from "@/components/layout/AppShell";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";
import { api } from "@/lib/api/http";

export default function ClientOutboundCreatePage() {
  useRequireAuth();
  const nav = useTranslations("nav");
  const t = useTranslations("pages.clientOutbound");
  const [clientId, setClientId] = useState("");
  const [warehouseId, setWarehouseId] = useState("");
  const [destName, setDestName] = useState("");
  const [destAddress, setDestAddress] = useState("");
  const [productId, setProductId] = useState("");
  const [qty, setQty] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [createdId, setCreatedId] = useState<string | null>(null);

  return (
    <AppShell nav="client" title={`${nav("client")} / ${nav("createOutbound")}`}>
      <div className="card p-5">
        <div className="text-xs uppercase tracking-widest text-muted">{t("title")}</div>
        <form
          className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2"
          onSubmit={async (e) => {
            e.preventDefault();
            setError(null);
            setCreatedId(null);
            try {
              const o = await api<{ id: string }>("/api/v1/outbound", {
                method: "POST",
                body: {
                  client_id: clientId,
                  warehouse_id: warehouseId,
                  destination: { name: destName, address: destAddress },
                  lines: [{ product_id: productId, qty }]
                }
              });
              setCreatedId(o.id);
            } catch {
              setError(t("createFailed"));
            }
          }}
        >
          <input className="input" placeholder={t("clientId")} value={clientId} onChange={(e) => setClientId(e.target.value)} />
          <input className="input" placeholder={t("warehouseId")} value={warehouseId} onChange={(e) => setWarehouseId(e.target.value)} />
          <input className="input" placeholder={t("destinationName")} value={destName} onChange={(e) => setDestName(e.target.value)} />
          <input className="input" placeholder={t("destinationAddress")} value={destAddress} onChange={(e) => setDestAddress(e.target.value)} />
          <input className="input" placeholder={t("productId")} value={productId} onChange={(e) => setProductId(e.target.value)} />
          <input className="input" type="number" min={1} value={qty} onChange={(e) => setQty(Number(e.target.value))} />
          <button className="btn btn-primary md:col-span-2" type="submit">{t("submit")}</button>
        </form>
        {createdId ? <div className="mt-3 text-sm">{t("createdOutbound")}: {createdId}</div> : null}
        {error ? <div className="mt-3 text-sm">{error}</div> : null}
      </div>
    </AppShell>
  );
}



