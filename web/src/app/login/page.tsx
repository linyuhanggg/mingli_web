import { redirect } from "next/navigation";

export default function LoginShortRoutePage() {
  redirect("/auth/login");
}
