"use client";

import { FlaskConical } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { AdminCatalogSurface } from "@/components/admin-catalog-surface";
import type { StaffRole } from "@/lib/api";
import type { AdminCapabilityState, AdminCatalogState } from "@/lib/admin-catalog";
import {
  getAdminPermissionArea,
  getAdminRouteAccess,
} from "@/lib/admin-permissions";
import { ADMIN_ROUTE_CATALOG } from "@/lib/admin-route-catalog";
import {
  ADMIN_CAPABILITY_STATES,
  ADMIN_ROLE_MATRIX,
  ADMIN_UI_LAB_STATES,
  ADMIN_WRITE_OPERATION_STATES,
  buildAdminUiLabCatalogViewModel,
  type AdminWriteOperationState,
} from "@/lib/admin-ui-lab";

import styles from "./admin-ui-lab-workbench.module.css";

const previewRoutes = ADMIN_ROUTE_CATALOG.filter(
  (route) => !["/", "/login", "/dashboard"].includes(route.path),
);

const stateLabels: Readonly<Record<AdminCatalogState, string>> = {
  ready: "就绪",
  loading: "载入中",
  empty: "空列表",
  error: "读取失败",
  forbidden: "无权限",
  unavailable: "能力待接入",
  maintenance: "维护中",
};

const viewports = ["360", "768", "1024", "1440"] as const;
type PreviewViewport = (typeof viewports)[number];

export function AdminUiLabWorkbench() {
  const workbenchRef = useRef<HTMLDivElement>(null);
  const [routePath, setRoutePath] = useState("/users");
  const [state, setState] = useState<AdminCatalogState>("ready");
  const [viewport, setViewport] = useState<PreviewViewport>("1024");
  const [role, setRole] = useState<StaffRole>("support");
  const [capabilityState, setCapabilityState] =
    useState<AdminCapabilityState>("INTERNAL_TEST");
  const [writeState, setWriteState] = useState<AdminWriteOperationState>("确认");

  const route =
    ADMIN_ROUTE_CATALOG.find((candidate) => candidate.path === routePath) ?? previewRoutes[0];
  const model = buildAdminUiLabCatalogViewModel(route, {
    state,
    role,
    capabilityState,
    writeState,
  });
  const roleDefinition = ADMIN_ROLE_MATRIX.find((candidate) => candidate.role === role);
  const routeAccess = getAdminRouteAccess(role, route, capabilityState);
  const previewKey = [routePath, state, role, capabilityState, writeState].join(":");

  useEffect(() => {
    workbenchRef.current?.setAttribute("data-ui-lab-ready", "true");
  }, []);

  return (
    <div ref={workbenchRef} className={styles.workbench} data-ui-lab-ready="false">
      <aside className={styles.demoBanner} aria-label="UI 演示数据">
        <FlaskConical aria-hidden="true" size={20} />
        <div>
          <strong>UI 演示数据</strong>
          <p>本页姓名、编号、金额、状态和审计结果全是 Fixture；不会写入真实服务。</p>
        </div>
      </aside>

      <section className={styles.controls} aria-labelledby="ui-lab-controls-title">
        <div className={styles.controlsHeading}>
          <h2 id="ui-lab-controls-title">演示控制台</h2>
          <p>按路由、状态、视口、角色与能力边界复现 Admin 页面族。</p>
        </div>
        <div className={styles.controlGrid}>
          <label>
            <span>路由</span>
            <select
              aria-label="演示路由"
              name="demo-route"
              value={routePath}
              onChange={(event) => setRoutePath(event.target.value)}
            >
              {previewRoutes.map((candidate) => (
                <option key={candidate.path} value={candidate.path}>
                  {candidate.label} · {candidate.path}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>页面状态</span>
            <select
              aria-label="页面状态"
              name="demo-state"
              value={state}
              onChange={(event) => setState(event.target.value as AdminCatalogState)}
            >
              {ADMIN_UI_LAB_STATES.map((candidate) => (
                <option key={candidate} value={candidate}>
                  {stateLabels[candidate]}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>预览视口</span>
            <select
              aria-label="预览视口"
              name="demo-viewport"
              value={viewport}
              onChange={(event) => setViewport(event.target.value as PreviewViewport)}
            >
              {viewports.map((candidate) => (
                <option key={candidate} value={candidate}>
                  {candidate}px
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>员工角色</span>
            <select
              aria-label="员工角色"
              name="demo-role"
              value={role}
              onChange={(event) => setRole(event.target.value as StaffRole)}
            >
              {ADMIN_ROLE_MATRIX.map((candidate) => (
                <option key={candidate.role} value={candidate.role}>
                  {candidate.label} · {candidate.role}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>能力状态</span>
            <select
              aria-label="能力状态"
              name="demo-capability"
              value={capabilityState}
              onChange={(event) =>
                setCapabilityState(event.target.value as AdminCapabilityState)
              }
            >
              {ADMIN_CAPABILITY_STATES.map((candidate) => (
                <option key={candidate} value={candidate}>
                  {candidate}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>写操作状态</span>
            <select
              aria-label="写操作状态"
              name="demo-write-state"
              value={writeState}
              onChange={(event) =>
                setWriteState(event.target.value as AdminWriteOperationState)
              }
            >
              {ADMIN_WRITE_OPERATION_STATES.map((candidate) => (
                <option key={candidate} value={candidate}>
                  {candidate}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className={styles.matrixSummary}>
          <div>
            <h3>{roleDefinition?.label ?? role}权限演示</h3>
            <p className={styles.routePermission}>
              当前路由：{getAdminPermissionArea(route)} · 查看 {routeAccess.read} · 写入 {routeAccess.write}
            </p>
            <ul>
              {roleDefinition
                ? Object.entries(roleDefinition.permissions).map(([area, permission]) => (
                    <li key={area}>
                      {area}：{permission}
                    </li>
                  ))
                : null}
            </ul>
          </div>
          <div>
            <h3>写操作状态矩阵</h3>
            <ul className={styles.stateList}>
              {ADMIN_WRITE_OPERATION_STATES.map((candidate) => (
                <li key={candidate} aria-current={candidate === writeState ? "true" : undefined}>
                  {candidate}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      <section className={styles.previewRegion} aria-labelledby="ui-lab-preview-title">
        <div className={styles.previewHeading}>
          <h2 id="ui-lab-preview-title">业务内层响应式预览</h2>
          <p>此区域只验业务内层；顶栏、侧栏与移动抽屉继续在真实 Admin 路由验收。</p>
          <p className={styles.viewportStatus} role="status" aria-live="polite">
            当前业务内层预览：{viewport}px
          </p>
        </div>
        <div className={styles.previewScroller}>
          <div
            className={styles.preview}
            data-preview-viewport={viewport}
            data-preview-scope="business-surface"
          >
            <AdminCatalogSurface
              key={previewKey}
              model={model}
              role={role}
              writeState={writeState}
            />
          </div>
        </div>
      </section>
    </div>
  );
}
