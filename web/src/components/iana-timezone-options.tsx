import { IANA_TIME_ZONES } from "@/lib/iana-timezones";


export function IanaTimeZoneOptions({ id }: Readonly<{ id: string }>) {
  return (
    <datalist id={id}>
      {IANA_TIME_ZONES.map((timeZone) => (
        <option key={timeZone} value={timeZone} />
      ))}
    </datalist>
  );
}
