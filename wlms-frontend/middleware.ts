import createMiddleware from "next-intl/middleware";

import { defaultLocale, locales } from "@/lib/i18n/routing";

export default createMiddleware({
  locales: [...locales],
  defaultLocale
});

export const config = {
  matcher: ["/((?!api|_next|.*\\..*).*)"]
};




