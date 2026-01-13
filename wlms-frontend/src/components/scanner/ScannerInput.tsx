"use client";

import { useEffect, useMemo, useRef, useState } from "react";

type Props = {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  expectedValue?: string;
};

type BarcodeDetectorLike = {
  detect: (video: HTMLVideoElement) => Promise<Array<{ rawValue: string }>>;
};

function getBarcodeDetector(): BarcodeDetectorLike | null {
  // BarcodeDetector is supported in Chromium-based browsers.
  const w = window as unknown as { BarcodeDetector?: new (opts?: unknown) => BarcodeDetectorLike };
  if (!w.BarcodeDetector) return null;
  try {
    return new w.BarcodeDetector();
  } catch {
    return null;
  }
}

function feedbackOk() {
  try {
    if (navigator.vibrate) navigator.vibrate(60);
  } catch {
    // ignore
  }
  try {
    const Ctx = window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Ctx) return;
    const ctx = new Ctx();
    const o = ctx.createOscillator();
    const g = ctx.createGain();
    o.type = "square";
    o.frequency.value = 880;
    g.gain.value = 0.03;
    o.connect(g);
    g.connect(ctx.destination);
    o.start();
    o.stop(ctx.currentTime + 0.08);
    o.onended = () => void ctx.close();
  } catch {
    // ignore
  }
}

export function ScannerInput({ label, value, onChange, placeholder, expectedValue }: Props) {
  const [open, setOpen] = useState(false);
  const [scanError, setScanError] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const detector = useMemo(() => (typeof window === "undefined" ? null : getBarcodeDetector()), []);

  const matchState =
    expectedValue && value
      ? value.trim() === expectedValue.trim()
        ? { ok: true, text: "OK" }
        : { ok: false, text: "Mismatch" }
      : null;

  useEffect(() => {
    if (!open) return;
    let stream: MediaStream | null = null;
    let stopped = false;

    (async () => {
      setScanError(null);
      if (!detector) {
        setScanError("Camera scan not supported in this browser. Use manual entry.");
        return;
      }
      try {
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" }, audio: false });
        if (stopped) return;
        const v = videoRef.current;
        if (!v) return;
        v.srcObject = stream;
        await v.play();

        const loop = async () => {
          if (stopped) return;
          try {
            const codes = await detector.detect(v);
            if (codes && codes.length > 0) {
              const raw = codes[0].rawValue ?? "";
              if (raw) {
                onChange(raw);
                feedbackOk();
                setOpen(false);
                return;
              }
            }
          } catch {
            // ignore per-frame detection errors
          }
          requestAnimationFrame(() => void loop());
        };
        void loop();
      } catch {
        setScanError("Camera permission denied or unavailable.");
      }
    })();

    return () => {
      stopped = true;
      try {
        if (stream) stream.getTracks().forEach((t) => t.stop());
      } catch {
        // ignore
      }
    };
  }, [open, detector, onChange]);

  return (
    <div className="grid gap-2">
      <div className="flex items-center justify-between">
        <div className="text-xs uppercase tracking-widest text-muted">{label}</div>
        {matchState ? (
          <div className={`text-xs uppercase tracking-widest ${matchState.ok ? "text-accent" : "text-muted"}`}>
            {matchState.text}
          </div>
        ) : null}
      </div>
      <div className="flex gap-2">
        <input
          className="input flex-1 font-mono text-xs"
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
        <button className="btn btn-ghost" type="button" onClick={() => setOpen(true)}>
          Scan
        </button>
      </div>

      {open ? (
        <div className="card p-4">
          <div className="flex items-center justify-between">
            <div className="text-xs uppercase tracking-widest text-muted">Camera scan</div>
            <button className="btn btn-ghost" type="button" onClick={() => setOpen(false)}>
              Close
            </button>
          </div>
          {scanError ? <div className="mt-3 text-sm">{scanError}</div> : null}
          <video ref={videoRef} className="mt-3 w-full border border-border bg-black" playsInline />
          <div className="mt-2 text-xs text-muted">
            Tip: for v1, scan values must match the exact IDs/barcodes expected by the API.
          </div>
        </div>
      ) : null}
    </div>
  );
}


