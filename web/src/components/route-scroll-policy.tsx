"use client";

import { usePathname } from "next/navigation";
import { useEffect, useLayoutEffect, useRef } from "react";


export function RouteScrollPolicy() {
  const pathname = usePathname() ?? "/";
  const previousPathname = useRef(pathname);
  const popstateUrl = useRef<string | null>(null);

  useEffect(() => {
    function rememberHistoryNavigation() {
      popstateUrl.current = window.location.href;
    }

    window.addEventListener("popstate", rememberHistoryNavigation);
    return () => window.removeEventListener("popstate", rememberHistoryNavigation);
  }, []);

  useLayoutEffect(() => {
    if (previousPathname.current === pathname) return;
    previousPathname.current = pathname;

    document.getElementById("private-main")?.focus({ preventScroll: true });

    const restoredUrl = popstateUrl.current;
    popstateUrl.current = null;
    if (restoredUrl === window.location.href) return;

    window.scrollTo(0, 0);
  }, [pathname]);

  return null;
}
