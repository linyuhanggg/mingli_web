import type { ReadingFact } from "./api";
import { formatDateTimeLike } from "./reading-display";


export type FortunePeriodMarker = {
  key: string;
  rawDate: string | null;
  date: string | null;
  dayPillar: string | null;
  dayRole: string | null;
  activeLuckCycle: string | null;
};

const PERIOD_MARKER_DISPLAY =
  /^\s*(?:period_markers|周期确定性标记)\s*(?::|：|$)/i;

function stringField(
  value: Record<string, unknown>,
  key: string,
): string | null {
  const field = value[key];
  if (typeof field !== "string") return null;
  const trimmed = field.trim();
  return trimmed || null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function isFortunePeriodMarkerFact(fact: ReadingFact): boolean {
  const kind = fact.kind_id.trim().replace(/^fact:/i, "");
  return (
    kind === "period_markers" ||
    kind === "周期确定性标记" ||
    PERIOD_MARKER_DISPLAY.test(fact.display_text ?? "")
  );
}

/**
 * Extract only public marker fields already returned by the service.
 * Invalid items and absent fields are omitted; this helper never derives a
 * date, pillar, relationship, or luck cycle in the browser.
 */
export function extractFortunePeriodMarkers(
  facts: ReadingFact[],
): FortunePeriodMarker[] {
  return facts.flatMap((fact, factIndex) => {
    if (!isFortunePeriodMarkerFact(fact) || !Array.isArray(fact.value)) {
      return [];
    }

    return fact.value.flatMap((value, markerIndex) => {
      if (!isRecord(value)) return [];

      const rawDate = stringField(value, "date");
      const dayPillar = stringField(value, "day_pillar");
      const dayRole = stringField(value, "day_role");
      const activeLuckCycle = stringField(value, "active_luck_cycle");

      if (!rawDate && !dayPillar && !dayRole && !activeLuckCycle) {
        return [];
      }

      return [
        {
          key: `period-marker-${factIndex}-${markerIndex}`,
          rawDate,
          date: rawDate ? formatDateTimeLike(rawDate) : null,
          dayPillar,
          dayRole,
          activeLuckCycle,
        },
      ];
    });
  });
}
