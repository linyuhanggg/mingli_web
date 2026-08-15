"use client";

import { Menu } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createContext, type MouseEvent, type ReactNode, useContext, useEffect, useState } from "react";

import { adminFetch, type AdminMeResponse, type StaffRole } from "@/lib/api";
import { ADMIN_ROUTE_CATALOG } from "@/lib/admin-route-catalog";
import { Drawer } from "./ui";
import { EnvBadge } from "./env-badge";
import styles from "./admin-shell.module.css";
import ui from "./ui.module.css";

const NAV_GROUPS = Array.from(
  ADMIN_ROUTE_CATALOG.filter(
    (route) => route.navigation !== false && !route.path.includes("["),
  ).reduce((groups, route) => {
    const routes = groups.get(route.group) ?? [];
    groups.set(route.group, [...routes, route]);
    return groups;
  }, new Map<string, (typeof ADMIN_ROUTE_CATALOG)[number][]>()).entries(),
).map(([group, routes]) => ({ group, routes }));

const AdminStaffContext = createContext<AdminMeResponse | null>(null);

export function useAdminStaff(): AdminMeResponse | null {
  return useContext(AdminStaffContext);
}

function NavigationLinks({
  pathname,
  onNavigate,
}: {
  pathname: string;
  onNavigate?: () => void;
}) {
  return NAV_GROUPS.map(({ group, routes }) => (
    <div className={styles.navGroup} key={group}>
      <p className={styles.navGroupLabel}>{group}</p>
      {routes.map((route) => {
        const current =
          route.path === "/"
            ? pathname === "/"
            : pathname === route.path || pathname.startsWith(`${route.path}/`);
        return (
          <Link
            key={route.path}
            href={route.path}
            aria-current={current ? "page" : undefined}
            onClick={onNavigate}
          >
            {route.label}
          </Link>
        );
      })}
    </div>
  ));
}

export function AdminShell({
  title,
  duty,
  demoRole,
  children,
}: {
  title: string;
  duty: string;
  demoRole?: StaffRole;
  children: ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [staff, setStaff] = useState<AdminMeResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [mobileNavigation, setMobileNavigation] = useState(false);

  useEffect(() => {
    if (demoRole) return;
    let cancelled = false;
    (async () => {
      const result = await adminFetch<AdminMeResponse>("/api/v1/admin/me");
      if (cancelled) return;
      if (!result.ok) {
        if (result.status === 401) {
          router.replace("/login");
          return;
        }
        setLoadError(result.title);
        return;
      }
      setStaff(result.data);
    })();
    return () => {
      cancelled = true;
    };
  }, [demoRole, router]);

  async function onLogout() {
    if (demoRole) {
      router.replace("/login");
      return;
    }
    await adminFetch("/api/v1/admin/auth/logout", { method: "POST" });
    router.replace("/login");
  }

  function onSkipToMain(event: MouseEvent<HTMLAnchorElement>) {
    const main = document.getElementById("main");
    if (!main) return;
    event.preventDefault();
    main.focus({ preventScroll: true });
    main.scrollIntoView({ block: "start" });
  }

  return (
    <AdminStaffContext.Provider value={staff}>
      <div className={styles.shell}>
        <a className={styles.skip} href="#main" onClick={onSkipToMain}>
          跳到主内容
        </a>
        <header className={styles.top}>
          <Link className={styles.brand} href="/">
            <span className={styles.mark} aria-hidden="true">
              管
            </span>
            <span>
              <strong>命理工具</strong>
              <small>运营台</small>
            </span>
          </Link>
          <div className={styles.topMeta}>
            <EnvBadge />
            <span className={styles.staff}>
              {demoRole
                ? `UI 演示 · ${demoRole}`
                : staff
                  ? `${staff.display_name} · ${staff.role}`
                  : "校验会话中…"}
            </span>
            <button className={`${ui.button} ${ui.secondary}`} type="button" onClick={onLogout}>
              {demoRole ? "结束演示" : "退出"}
            </button>
          </div>
          <div className={styles.mobileNavigation}>
            <Drawer
              open={mobileNavigation}
              onOpenChange={setMobileNavigation}
              side="right"
              title="运营导航"
              description="按六个一级组进入 Admin 页面。"
              trigger={
                <button className={styles.menuButton} type="button" aria-label="打开运营导航">
                  <Menu aria-hidden="true" size={20} />
                  <span>菜单</span>
                </button>
              }
            >
              <div className={styles.mobileSession}>
                <EnvBadge />
                <p>
                  {demoRole
                    ? `UI 演示 · ${demoRole}`
                    : staff
                      ? `${staff.display_name} · ${staff.role}`
                      : "校验会话中…"}
                </p>
              </div>
              <nav className={styles.nav} aria-label="移动运营导航">
                <NavigationLinks
                  pathname={pathname}
                  onNavigate={() => setMobileNavigation(false)}
                />
              </nav>
              <button
                className={`${ui.button} ${ui.secondary} ${styles.mobileLogout}`}
                type="button"
                onClick={onLogout}
              >
                {demoRole ? "结束演示" : "退出"}
              </button>
            </Drawer>
          </div>
        </header>
        <div className={styles.body}>
          <nav className={`${styles.nav} ${styles.desktopNavigation}`} aria-label="运营导航">
            <NavigationLinks pathname={pathname} />
          </nav>
          <main id="main" className={styles.main} tabIndex={-1}>
            <header className={styles.pageHead}>
              <h1>{title}</h1>
              <p>{duty}</p>
            </header>
            {loadError ? <p className={ui.alert} role="alert">{loadError}</p> : null}
            {children}
          </main>
        </div>
      </div>
    </AdminStaffContext.Provider>
  );
}
