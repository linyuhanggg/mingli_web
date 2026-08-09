const LOCAL_DATE_TIME =
  /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?$/;

function offsetMinutesAt(date: Date, timeZone: string): number {
  const formatter = new Intl.DateTimeFormat("en-US", {
    timeZone,
    timeZoneName: "longOffset",
  });
  const offsetName = formatter
    .formatToParts(date)
    .find((part) => part.type === "timeZoneName")?.value;
  if (!offsetName || offsetName === "GMT" || offsetName === "UTC") {
    return 0;
  }
  const match = /^(?:GMT|UTC)([+-])(\d{1,2})(?::?(\d{2}))?$/.exec(offsetName);
  if (!match) {
    throw new Error("无法确认所选时区的 UTC 偏移");
  }
  const minutes = Number(match[2]) * 60 + Number(match[3] ?? "0");
  return match[1] === "-" ? -minutes : minutes;
}

function formatOffset(minutes: number): string {
  if (minutes === 0) {
    return "Z";
  }
  const sign = minutes < 0 ? "-" : "+";
  const absolute = Math.abs(minutes);
  const hours = Math.floor(absolute / 60).toString().padStart(2, "0");
  const remainder = (absolute % 60).toString().padStart(2, "0");
  return `${sign}${hours}:${remainder}`;
}

export function localDateTimeWithOffset(
  value: string,
  timeZone: string,
): string {
  const match = LOCAL_DATE_TIME.exec(value);
  if (!match) {
    throw new Error("日期时间格式无效，请重新确认");
  }
  const [, year, month, day, hour, minute, second = "00"] = match;
  const localAsUtc = new Date(
    Date.UTC(
      Number(year),
      Number(month) - 1,
      Number(day),
      Number(hour),
      Number(minute),
      Number(second),
    ),
  );
  const firstOffset = offsetMinutesAt(localAsUtc, timeZone);
  const resolvedInstant = new Date(localAsUtc.getTime() - firstOffset * 60_000);
  const resolvedOffset = offsetMinutesAt(resolvedInstant, timeZone);
  return `${year}-${month}-${day}T${hour}:${minute}:${second}${formatOffset(resolvedOffset)}`;
}
