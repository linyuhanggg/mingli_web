import styles from "./hexagram-glyphs.module.css";

/** DESIGN.md §13 / 六爻规格共享卦象族：只画卦。纳甲、六亲、体用标注不进此层。 */

export const TRIGRAM_NAMES = ["乾", "兑", "离", "震", "巽", "坎", "艮", "坤"] as const;
export type TrigramName = (typeof TRIGRAM_NAMES)[number];

/** 自下而上三爻：true=阳。 */
export const TRIGRAM_LINES: Record<TrigramName, readonly [boolean, boolean, boolean]> = {
  乾: [true, true, true],
  兑: [true, true, false],
  离: [true, false, true],
  震: [true, false, false],
  巽: [false, true, true],
  坎: [false, true, false],
  艮: [false, false, true],
  坤: [false, false, false],
};

export type LineGlyphSize = "s" | "m" | "l";

export function isTrigramName(value: string): value is TrigramName {
  return (TRIGRAM_NAMES as readonly string[]).includes(value);
}

export function LineGlyph({
  yang,
  moving,
  size = "m",
}: Readonly<{
  yang: boolean;
  moving: boolean;
  size?: LineGlyphSize;
}>) {
  return (
    <span
      className={styles.lineGlyph}
      data-kind={yang ? "yang" : "yin"}
      data-moving={moving ? "true" : "false"}
      data-size={size}
      aria-label={moving ? (yang ? "阳动爻" : "阴动爻") : yang ? "阳爻" : "阴爻"}
    >
      {yang ? (
        <span className={styles.bar} aria-hidden="true" />
      ) : (
        <>
          <span className={styles.bar} aria-hidden="true" />
          <span className={styles.gap} aria-hidden="true" />
          <span className={styles.bar} aria-hidden="true" />
        </>
      )}
      {moving ? (
        <span className={styles.movingMark} aria-hidden="true">
          <i className={styles.cinnabar} />
          {yang ? "○" : "×"}
        </span>
      ) : null}
    </span>
  );
}

export function TrigramGlyph({
  name,
  size = "s",
}: Readonly<{
  name: string;
  size?: LineGlyphSize;
}>) {
  const lines = isTrigramName(name) ? TRIGRAM_LINES[name] : null;
  return (
    <span className={styles.trigram} data-size={size}>
      <span className={styles.trigramFigure} aria-hidden="true">
        {lines
          ? [...lines].reverse().map((lineYang, index) => (
              <LineGlyph key={`${name}-${index}`} yang={lineYang} moving={false} size={size} />
            ))
          : null}
      </span>
      <span className={styles.trigramName}>{name}</span>
    </span>
  );
}

export function HexagramFigure({
  lines,
  size = "m",
  silhouette = false,
}: Readonly<{
  lines: ReadonlyArray<{ yang: boolean; moving: boolean }>;
  size?: LineGlyphSize;
  silhouette?: boolean;
}>) {
  const ordered = [...lines].reverse();
  return (
    <ol
      className={styles.figure}
      data-size={size}
      data-silhouette={silhouette ? "true" : "false"}
      aria-hidden={silhouette || undefined}
    >
      {ordered.map((line, index) => (
        <li key={`line-${ordered.length - index}`}>
          <LineGlyph yang={line.yang} moving={line.moving} size={size} />
        </li>
      ))}
    </ol>
  );
}

export function HexagramHeader({
  name,
  upper,
  lower,
  upper_trigram,
  lower_trigram,
}: Readonly<{
  name: string;
  upper?: string;
  lower?: string;
  upper_trigram?: string;
  lower_trigram?: string;
}>) {
  const upperName = upper_trigram ?? upper ?? "";
  const lowerName = lower_trigram ?? lower ?? "";
  return (
    <header className={styles.header}>
      <strong className={styles.hexName}>{name}</strong>
      <span className={styles.compose}>
        <TrigramGlyph name={upperName} />
        <span aria-hidden="true">/</span>
        <TrigramGlyph name={lowerName} />
      </span>
    </header>
  );
}

export function hexagramLinesFromTrigrams(
  upper: string,
  lower: string,
  movingLines: ReadonlyArray<number>,
): Array<{ yang: boolean; moving: boolean }> {
  const lowerLines = isTrigramName(lower) ? TRIGRAM_LINES[lower] : [false, false, false];
  const upperLines = isTrigramName(upper) ? TRIGRAM_LINES[upper] : [false, false, false];
  const moving = new Set(movingLines);
  return [...lowerLines, ...upperLines].map((lineYang, index) => ({
    yang: lineYang,
    moving: moving.has(index + 1),
  }));
}
