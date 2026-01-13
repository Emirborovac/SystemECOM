import { useTranslations } from "next-intl";

import { AppShell } from "@/components/layout/AppShell";

export default function WorkerHomePage() {
  const t = useTranslations("nav");
  const p = useTranslations("pages.workerHome");

  return (
    <AppShell nav="worker" title={`${t("worker")} / ${t("home")}`}>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <a className="btn btn-primary" href="./receive">
          {p("receive")}
        </a>
        <a className="btn btn-ghost" href="./putaway">
          {p("putaway")}
        </a>
        <a className="btn btn-ghost" href="./pick">
          {p("pick")}
        </a>
        <a className="btn btn-ghost" href="./pack">
          {p("pack")}
        </a>
        <a className="btn btn-ghost" href="./dispatch">
          {p("dispatch")}
        </a>
        <a className="btn btn-ghost" href="./returns">
          {p("returns")}
        </a>
        <a className="btn btn-ghost" href="./discrepancy">
          {p("reportIssue")}
        </a>
      </div>
    </AppShell>
  );
}




