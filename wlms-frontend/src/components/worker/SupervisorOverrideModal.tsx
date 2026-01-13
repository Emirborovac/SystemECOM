"use client";

import { useState } from "react";

import { api } from "@/lib/api/http";

export function SupervisorOverrideModal({
  open,
  onClose,
  onSuccess
}: {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/70 p-6">
      <div className="card w-full max-w-md p-5">
        <div className="flex items-center justify-between">
          <div className="text-xs uppercase tracking-widest text-muted">Supervisor override</div>
          <button className="btn btn-ghost" type="button" onClick={onClose}>
            Close
          </button>
        </div>
        <div className="mt-3 text-sm text-muted">
          Supervisor/Admin credentials are required to override a wrong scan and proceed.
        </div>

        <form
          className="mt-4 grid gap-3"
          onSubmit={async (e) => {
            e.preventDefault();
            setError(null);
            setLoading(true);
            try {
              await api("/api/v1/auth/verify-supervisor", { method: "POST", auth: false, body: { email, password } });
              onSuccess();
              onClose();
            } catch {
              setError("Override denied");
            } finally {
              setLoading(false);
            }
          }}
        >
          <input className="input" placeholder="Supervisor email" value={email} onChange={(e) => setEmail(e.target.value)} />
          <input className="input" placeholder="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          {error ? <div className="text-sm">{error}</div> : null}
          <button className="btn btn-primary" type="submit" disabled={loading}>
            {loading ? "..." : "Verify + override"}
          </button>
        </form>
      </div>
    </div>
  );
}


