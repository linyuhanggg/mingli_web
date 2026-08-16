import { redirect } from "next/navigation";


export default function LegacyReadingsPage() {
  redirect("/account/history");
}
