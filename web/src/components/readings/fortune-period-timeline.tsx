import type { FortunePeriodMarker } from "@/lib/fortune-period-markers";

import styles from "./fortune-period-timeline.module.css";


export function FortunePeriodTimeline({
  markers,
}: Readonly<{ markers: FortunePeriodMarker[] }>) {
  if (markers.length === 0) return null;

  return (
    <div className={styles.frame}>
      <p className={styles.note}>
        按服务端返回顺序展示；缺少的日期或关系字段会直接省略，浏览器不补算。
      </p>
      <ol className={styles.timeline}>
        {markers.map((marker) => (
          <li className={styles.item} key={marker.key}>
            {marker.date && marker.rawDate ? (
              <time className={styles.date} dateTime={marker.rawDate}>
                {marker.date}
              </time>
            ) : null}
            <dl className={styles.details}>
              {marker.dayPillar ? (
                <div>
                  <dt>日柱</dt>
                  <dd>{marker.dayPillar}</dd>
                </div>
              ) : null}
              {marker.dayRole ? (
                <div>
                  <dt>日主关系</dt>
                  <dd>{marker.dayRole}</dd>
                </div>
              ) : null}
              {marker.activeLuckCycle ? (
                <div>
                  <dt>当前大运</dt>
                  <dd>{marker.activeLuckCycle}</dd>
                </div>
              ) : null}
            </dl>
          </li>
        ))}
      </ol>
    </div>
  );
}
