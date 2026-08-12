import type { ReadingFact } from "@/lib/api";
import {
  buildBaziFactDisplay,
  type BaziPillarPosition,
  type BaziStemTenGod,
} from "@/lib/bazi-fact-display";

import styles from "./bazi-fact-matrix.module.css";

const PILLAR_LABELS: Record<BaziPillarPosition, string> = {
  year: "年柱",
  month: "月柱",
  day: "日柱",
  hour: "时柱",
};

function stemTenGodText(value: BaziStemTenGod): string {
  return `${value.stem} · ${value.tenGod}`;
}

function positionList(positions: BaziPillarPosition[]): string {
  return positions.map((position) => PILLAR_LABELS[position]).join("、");
}

export function BaziFactMatrix({
  facts,
}: Readonly<{ facts: ReadingFact[] }>) {
  const view = buildBaziFactDisplay(facts);

  return (
    <section className={styles.matrix} aria-label="八字细盘明细">
      <header className={styles.header}>
        <p className={styles.eyebrow}>Runtime 5.1 公开事实</p>
        <h3>八字细盘明细</h3>
        <p>仅展示服务端已投影的盘面事实，不在浏览器内补算。</p>
      </header>

      <div
        className={styles.tableScroll}
        role="region"
        aria-label="四柱藏干、十神与纳音横向滚动区"
        tabIndex={0}
      >
        <table className={styles.table}>
          <caption>四柱藏干、十神与纳音</caption>
          <thead>
            <tr>
              <th scope="col">明细</th>
              {view.pillars.map((pillar) => (
                <th key={pillar.position} scope="col">
                  <span className={styles.columnLabel}>{pillar.label}</span>
                  <strong className={styles.pillarValue}>
                    {pillar.pillar ?? "暂无"}
                  </strong>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              <th scope="row">天干十神</th>
              {view.pillars.map((pillar) => (
                <td key={pillar.position}>
                  {pillar.heavenlyStemTenGod
                    ? stemTenGodText(pillar.heavenlyStemTenGod)
                    : "暂无"}
                </td>
              ))}
            </tr>
            <tr>
              <th scope="row">藏干</th>
              {view.pillars.map((pillar) => (
                <td key={pillar.position}>
                  {pillar.hiddenStems.length > 0
                    ? pillar.hiddenStems.join(" · ")
                    : "暂无"}
                </td>
              ))}
            </tr>
            <tr>
              <th scope="row">藏干十神</th>
              {view.pillars.map((pillar) => (
                <td key={pillar.position}>
                  {pillar.hiddenStemTenGods.length > 0 ? (
                    <span className={styles.cellStack}>
                      {pillar.hiddenStemTenGods.map((item, index) => (
                        <span key={`${item.stem}-${item.tenGod}-${index}`}>
                          {stemTenGodText(item)}
                        </span>
                      ))}
                    </span>
                  ) : (
                    "暂无"
                  )}
                </td>
              ))}
            </tr>
            <tr>
              <th scope="row">纳音</th>
              {view.pillars.map((pillar) => (
                <td key={pillar.position}>{pillar.nayin ?? "暂无"}</td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>

      <div className={styles.block}>
        {view.elements ? (
          <div
            className={styles.tableScroll}
            role="region"
            aria-label="五行盘面计数横向滚动区"
            tabIndex={0}
          >
            <table className={`${styles.table} ${styles.elementTable}`}>
              <caption>五行盘面计数</caption>
              <thead>
                <tr>
                  <th scope="col">口径</th>
                  {view.elements.map((item) => (
                    <th key={item.element} scope="col">
                      {item.element}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <tr>
                  <th scope="row">显干支</th>
                  {view.elements.map((item) => (
                    <td key={item.element}>{item.visibleCount}</td>
                  ))}
                </tr>
                <tr>
                  <th scope="row">藏干出现</th>
                  {view.elements.map((item) => (
                    <td key={item.element}>{item.hiddenCount}</td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>
        ) : (
          <p className={styles.empty}>五行盘面计数暂缺。</p>
        )}
        <p className={styles.scopeNote}>盘面计数，不代表旺衰或用神。</p>
      </div>

      <div className={styles.block}>
        <h4>神煞辅助</h4>
        <p className={styles.scopeNote}>仅展示 Runtime 已计算并命中的辅助项。</p>
        {view.shenshaAuxiliary ? (
          view.shenshaAuxiliary.items.length > 0 ? (
            <ul className={styles.shenshaList}>
              {view.shenshaAuxiliary.items.map((item, index) => (
                <li key={`${item.name}-${item.targetBranch ?? "none"}-${index}`}>
                  <strong>{item.name}</strong>
                  {item.matchedPositions.length > 0 ? (
                    <span>命中：{positionList(item.matchedPositions)}</span>
                  ) : null}
                  {item.targetBranch ? (
                    <span>目标地支：{item.targetBranch}</span>
                  ) : null}
                  {item.anchorPositions.length > 0 ? (
                    <span>依据柱位：{positionList(item.anchorPositions)}</span>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : (
            <p className={styles.empty}>本盘暂无已计算的神煞辅助项。</p>
          )
        ) : (
          <p className={styles.empty}>神煞辅助事实暂缺。</p>
        )}
      </div>

      <div className={styles.block}>
        <h4>待 Runtime 投影</h4>
        <ul className={styles.unprojectedList}>
          {view.unprojected.map((item) => (
            <li key={item.id}>
              <strong>{item.label}</strong>
              <span>{item.status}</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
