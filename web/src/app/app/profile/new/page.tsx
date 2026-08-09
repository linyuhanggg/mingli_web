"use client";

import { ProfileForm } from "@/components/profile-form";
import { privateShellStyles as styles } from "@/components/private-shell";

export default function NewProfilePage() {
  return (
    <section className={styles.panel}>
      <ProfileForm />
    </section>
  );
}
