"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";

import { getAccessToken } from "@/lib/auth/tokens";

export function useRequireAuth() {
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      const locale = pathname?.slice(1, 3) || "en";
      router.replace(`/${locale}/login`);
    }
  }, [router, pathname]);
}


