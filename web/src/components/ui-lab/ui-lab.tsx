"use client";

import { useEffect, useRef, useState } from "react";

import { PreviewShell } from "@/components/ui-lab/preview-shells";
import { UI_LAB_FIXTURES, type UiLabFixtureId } from "@/fixtures/ui-lab";
import {
  UI_LAB_CAPABILITIES,
  UI_LAB_ROUTE_CATEGORIES,
  UI_LAB_ROUTE_CATEGORY_LABELS,
  UI_LAB_ROLES,
  UI_LAB_ROLE_LABELS,
  UI_LAB_STATE_DETAILS,
  UI_LAB_STATE_GROUPS,
  UI_LAB_VIEWPORTS,
  uiLabCapabilityGate,
  uiLabRendersFullProductionPage,
  uiLabRendersProductionSurface,
  type UiLabCapabilityId,
  type UiLabRole,
  type UiLabState,
  type UiLabViewport,
} from "@/lib/ui-lab-contract";

import styles from "./ui-lab.module.css";

type UiLabProps = {
  demoLabel: string;
};

export function UiLab({ demoLabel }: UiLabProps) {
  const labRef = useRef<HTMLDivElement>(null);
  const [fixtureId, setFixtureId] = useState<UiLabFixtureId>("bazi-input");
  const [state, setState] = useState<UiLabState>("pristine");
  const [role, setRole] = useState<UiLabRole>("guest");
  const [capabilityId, setCapabilityId] = useState<UiLabCapabilityId>("ui-prebuilt");
  const [viewport, setViewport] = useState<UiLabViewport>(1024);

  const fixture = UI_LAB_FIXTURES.find((item) => item.id === fixtureId) ?? UI_LAB_FIXTURES[0];
  const capability =
    UI_LAB_CAPABILITIES.find((item) => item.id === capabilityId) ?? UI_LAB_CAPABILITIES[0];
  const stateDetails = UI_LAB_STATE_DETAILS[state];
  const capabilityGate = (uiLabRendersProductionSurface(fixture.previewKind, state)
    || (fixture.previewKind === "relationship-status" && state === "pristine"))
    ? uiLabCapabilityGate(fixture.previewKind, role, capabilityId)
    : null;
  const rendersFullProductionPage = uiLabRendersFullProductionPage(fixture.previewKind, state)
    && !capabilityGate;

  useEffect(() => {
    labRef.current?.setAttribute("data-ui-lab-ready", "true");
  }, []);

  return (
    <div ref={labRef} className={styles.page} data-ui-lab-ready="false">
      <a className={styles.skipLink} href="#ui-lab-preview-title">跳到演示预览</a>

      <div className={styles.demoBoundary} aria-label="演示数据边界">
        <strong>{demoLabel}</strong>
        <span>Fixture 只存在于本验收台，不代表真实算法、支付或权益</span>
      </div>

      <header className={styles.intro}>
        <div>
          <h1>Web UI Lab</h1>
          <p>
            在一个页面内检查路线、状态、身份、能力阶段与四档响应式。正常产品路由不会读取这里的数据。
          </p>
        </div>

        <dl className={styles.completionFacts} aria-label="UI 与算法完成度">
          <div>
            <dt>UI 完成度</dt>
            <dd>{capability.uiStatus}</dd>
            <p>页面壳可点击，仍需真实浏览器与用户验收。</p>
          </div>
          <div>
            <dt>算法接入度</dt>
            <dd>{capability.algorithmStatus}</dd>
            <p>{capability.description}</p>
          </div>
        </dl>
      </header>

      <div className={styles.labWorkspace}>
        <aside className={styles.controls} aria-labelledby="ui-lab-controls-title">
          <div className={styles.controlHeading}>
            <h2 id="ui-lab-controls-title">预览控制</h2>
            <p>切换不会创建真实任务。</p>
          </div>

          <label className={styles.field}>
            <span>页面与场景</span>
            <select
              aria-label="页面与场景"
              onChange={(event) => setFixtureId(event.target.value as UiLabFixtureId)}
              value={fixtureId}
            >
              {UI_LAB_ROUTE_CATEGORIES.map((category) => (
                <optgroup key={category} label={UI_LAB_ROUTE_CATEGORY_LABELS[category]}>
                  {UI_LAB_FIXTURES.filter((item) => item.category === category).map((item) => (
                    <option key={item.id} value={item.id}>{item.routePattern} · {item.title}</option>
                  ))}
                </optgroup>
              ))}
            </select>
          </label>

          <nav aria-label="完整 Web 路由库存" className={styles.routeInventory}>
            <h3>冻结路由库存</h3>
            <p>点击任一路由模式，将同一组状态与视口控制应用到正式组件。</p>
            {UI_LAB_ROUTE_CATEGORIES.map((category) => (
              <details key={category} open>
                <summary>{UI_LAB_ROUTE_CATEGORY_LABELS[category]}</summary>
                <ul>
                  {UI_LAB_FIXTURES.filter((item) => item.category === category).map((item) => (
                    <li key={item.id}>
                      <button
                        aria-label={`预览路由 ${item.routePattern}`}
                        aria-pressed={fixture.id === item.id}
                        onClick={() => setFixtureId(item.id)}
                        type="button"
                      >
                        <code>{item.routePattern}</code>
                        <span>{item.title}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              </details>
            ))}
          </nav>

          <label className={styles.field}>
            <span>状态</span>
            <select
              aria-label="状态"
              onChange={(event) => setState(event.target.value as UiLabState)}
              value={state}
            >
              {UI_LAB_STATE_GROUPS.map((group) => (
                <optgroup key={group.label} label={group.label}>
                  {group.states.map((item) => (
                    <option key={item} value={item}>
                      {UI_LAB_STATE_DETAILS[item].label} · {item}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
          </label>

          <label className={styles.field}>
            <span>查看身份</span>
            <select
              aria-label="查看身份"
              onChange={(event) => setRole(event.target.value as UiLabRole)}
              value={role}
            >
              {UI_LAB_ROLES.map((item) => (
                <option key={item} value={item}>{UI_LAB_ROLE_LABELS[item]}</option>
              ))}
            </select>
          </label>

          <label className={styles.field}>
            <span>能力阶段</span>
            <select
              aria-label="能力阶段"
              onChange={(event) => setCapabilityId(event.target.value as UiLabCapabilityId)}
              value={capabilityId}
            >
              {UI_LAB_CAPABILITIES.map((item) => (
                <option key={item.id} value={item.id}>{item.label}</option>
              ))}
            </select>
          </label>

          <fieldset className={styles.viewportFieldset}>
            <legend>预览宽度</legend>
            <div className={styles.viewportButtons}>
              {UI_LAB_VIEWPORTS.map((item) => (
                <button
                  aria-label={`${item} 像素`}
                  aria-pressed={viewport === item}
                  className={viewport === item ? styles.selectedViewport : styles.viewportButton}
                  key={item}
                  onClick={() => setViewport(item)}
                  type="button"
                >
                  <strong>{item}</strong>
                  <span>px</span>
                </button>
              ))}
            </div>
          </fieldset>

          <p className={styles.controlNote}>宽画布只在下方容器内滚动，不会让整页横向溢出。</p>
        </aside>

        <section className={styles.previewStage} aria-labelledby="ui-lab-stage-title">
          <div className={styles.stageHeading}>
            <div>
              <h2 id="ui-lab-stage-title">预览画布</h2>
              <p>{viewport} px · {fixture.title} · {stateDetails.label}</p>
            </div>
            <span>{capability.label}</span>
          </div>

          <div className={styles.previewRail} aria-label={`${viewport} 像素预览画布`} tabIndex={0}>
            <div
              aria-labelledby="ui-lab-preview-title"
              className={styles.previewFrame}
              data-testid="ui-lab-preview"
              data-viewport={viewport}
              role={rendersFullProductionPage ? undefined : "main"}
              style={{ width: `${viewport}px` }}
            >
              <header className={styles.previewMeta}>
                <div>
                  <span className={styles.fixtureBadge}>演示 Fixture</span>
                  <h2 id="ui-lab-preview-title">预览：{fixture.title}</h2>
                  <p className={styles.previewDescription}>{fixture.description}</p>
                </div>

                <dl className={styles.metaList}>
                  <div><dt>Route</dt><dd><code>{fixture.routePattern}</code></dd></div>
                  <div><dt>Schema</dt><dd><code>{fixture.schemaVersion}</code></dd></div>
                  <div><dt>来源</dt><dd>{fixture.schemaSource === "view-model-registry" ? "正式 ViewModel registry" : "UI Lab typed surface schema"}</dd></div>
                  <div><dt>身份</dt><dd>{UI_LAB_ROLE_LABELS[role]}</dd></div>
                  <div><dt>UI</dt><dd>{capability.uiStatus}</dd></div>
                  <div><dt>算法</dt><dd>{capability.algorithmStatus}</dd></div>
                </dl>
              </header>

              <section
                aria-live="polite"
                className={styles.stateNotice}
                data-tone={stateDetails.tone}
              >
                <div className={styles.stateNoticeHeader}>
                  <div>
                    <span>当前演示状态</span>
                    <strong>概览：{stateDetails.label}</strong>
                  </div>
                  <code className={styles.stateCode}>{state}</code>
                </div>
                <p>{stateDetails.description}</p>
              </section>

              <div
                className={styles.previewBody}
                data-full-page={rendersFullProductionPage}
                data-testid="ui-lab-preview-body"
              >
                <PreviewShell
                  capabilityId={capabilityId}
                  fixture={fixture}
                  key={`${fixture.id}-${state}-${role}-${capabilityId}`}
                  role={role}
                  state={state}
                />
              </div>
            </div>
          </div>

          <p className={styles.previewFooter}>
            画布使用精确 CSS 宽度与容器查询；截图前仍需在真实浏览器验证浏览器栏、缩放、键盘和系统字体。
          </p>
        </section>
      </div>
    </div>
  );
}
