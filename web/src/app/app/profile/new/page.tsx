import { redirect } from "next/navigation";


export default function LegacyNewProfilePage() {
  redirect("/account/profiles");
}
