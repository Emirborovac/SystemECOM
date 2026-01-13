import { useTranslations } from "next-intl";

export default function LocaleIndexPage() {
  const t = useTranslations("pages.localeIndex");
  const app = useTranslations("app");
  const nav = useTranslations("nav");
  return (
    <main className="min-h-screen p-6">
      <div className="card mx-auto max-w-2xl p-6">
        <div className="text-xs uppercase tracking-widest text-muted">
          {app("name")}
        </div>
        <h1 className="mt-2 text-2xl font-semibold">{t("welcome")}</h1>
        <p className="mt-2 text-sm text-muted">
          {t("chooseEntry")}
        </p>
        <div className="mt-4 flex flex-wrap gap-3">
          <a className="btn btn-primary" href="./login">
            {t("login")}
          </a>
          <a className="btn btn-ghost" href="./admin/dashboard">
            {nav("admin")}
          </a>
          <a className="btn btn-ghost" href="./portal/dashboard">
            {nav("client")}
          </a>
          <a className="btn btn-ghost" href="./worker/home">
            {nav("worker")}
          </a>
        </div>
      </div>
    </main>
  );
}




