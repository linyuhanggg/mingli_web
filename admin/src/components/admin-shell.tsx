"use client";

import { ChevronDown, Menu } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  createContext,
  type MouseEvent,
  type ReactNode,
  useContext,
  useEffect,
  useId,
  useRef,
  useState,
} from "react";

import { adminFetch, type AdminMeResponse, type StaffRole } from "@/lib/api";
import { ADMIN_ROUTE_CATALOG } from "@/lib/admin-route-catalog";
import { Button, Drawer } from "./ui";
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
  mode,
}: {
  pathname: string;
  onNavigate?: () => void;
  mode: "desktop" | "mobile";
}) {
  const navigationId = useId().replaceAll(":", "");
  const activeGroup = NAV_GROUPS.find(({ routes }) =>
    routes.some((route) =>
      route.path === "/"
        ? pathname === "/"
        : pathname === route.path || pathname.startsWith(`${route.path}/`),
    ),
  )?.group;
  const [desktopGroups, setDesktopGroups] = useState<Set<string>>(
    () => new Set(activeGroup ? [activeGroup] : []),
  );
  const [mobileGroup, setMobileGroup] = useState<string | null>(activeGroup ?? null);
  const firstLinkRefs = useRef<Record<string, HTMLAnchorElement | null>>({});

  function toggleGroup(group: string, expanded: boolean) {
    const willExpand = !expanded;
    if (mode === "mobile") {
      setMobileGroup(willExpand ? group : null);
    } else {
      setDesktopGroups((current) => {
        const next = new Set(current);
        if (willExpand) next.add(group);
        else next.delete(group);
        return next;
      });
    }

    if (willExpand) {
      window.setTimeout(() => firstLinkRefs.current[group]?.focus(), 0);
    }
  }

  return NAV_GROUPS.map(({ group, routes }, groupIndex) => {
    const expanded = mode === "mobile" ? mobileGroup === group : desktopGroups.has(group);
    const routesId = `${navigationId}-group-${groupIndex}`;

    return (
      <div className={styles.navGroup} key={group}>
        <Button
          className={styles.navGroupButton}
          variant="ghost"
          aria-controls={routesId}
          aria-expanded={expanded}
          onClick={() => toggleGroup(group, expanded)}
        >
          <span>{group}</span>
          <ChevronDown
            className={styles.navGroupIcon}
            data-expanded={expanded ? "true" : undefined}
            aria-hidden="true"
            size={16}
          />
        </Button>
        <div className={styles.navRoutes} id={routesId} hidden={!expanded}>
          {routes.map((route, routeIndex) => {
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
                ref={(element) => {
                  if (routeIndex === 0) firstLinkRefs.current[group] = element;
                }}
              >
                {route.label}
              </Link>
            );
          })}
        </div>
      </div>
    );
  });
}

export function AdminShell({
  title,
  duty,
  actions,
  demoRole,
  children,
}: {
  title: string;
  duty: string;
  actions?: ReactNode;
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
          <div className={styles.brandCluster}>
            <Link className={styles.brand} href="/">
              运营台
            </Link>
            <EnvBadge />
          </div>
          <div className={styles.topMeta}>
            <span className={styles.staff}>
              {demoRole
                ? `UI 演示 · ${demoRole}`
                : staff
                  ? `${staff.display_name} · ${staff.role}`
                  : "校验会话中…"}
            </span>
            <Button variant="secondary" onClick={onLogout}>
              {demoRole ? "结束演示" : "退出"}
            </Button>
          </div>
          <div className={styles.mobileNavigation}>
            <Drawer
              open={mobileNavigation}
              onOpenChange={setMobileNavigation}
              side="right"
              title="运营导航"
              description="按六个一级组进入 Admin 页面。"
              trigger={
                <Button
                  className={styles.menuButton}
                  variant="secondary"
                  aria-label="打开运营导航"
                >
                  <Menu aria-hidden="true" size={20} />
                  <span>菜单</span>
                </Button>
              }
            >
              <div className={styles.mobileSession}>
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
                  key={`mobile-${pathname}`}
                  pathname={pathname}
                  onNavigate={() => setMobileNavigation(false)}
                  mode="mobile"
                />
              </nav>
              <Button
                className={styles.mobileLogout}
                variant="secondary"
                onClick={onLogout}
              >
                {demoRole ? "结束演示" : "退出"}
              </Button>
            </Drawer>
          </div>
        </header>
        <div className={styles.body}>
          <nav className={`${styles.nav} ${styles.desktopNavigation}`} aria-label="运营导航">
            <NavigationLinks key={`desktop-${pathname}`} pathname={pathname} mode="desktop" />
          </nav>
          <main id="main" className={styles.main} tabIndex={-1}>
            <header className={styles.pageHead}>
              <div className={styles.pageHeading}>
                <h1>{title}</h1>
                <p title={duty}>{duty}</p>
              </div>
              {actions ? <div className={styles.pageActions}>{actions}</div> : null}
            </header>
            {loadError ? (
              <div className={styles.loadError}>
                <p className={ui.alert} role="alert">
                  {loadError}
                </p>
              </div>
            ) : (
              children
            )}
          </main>
        </div>
      </div>
    </AdminStaffContext.Provider>
  );
}
