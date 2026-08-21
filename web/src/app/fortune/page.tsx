import type { Metadata } from "next";

import {
  FORTUNE_PUBLIC_SUMMARY,
  FORTUNE_PUBLIC_TITLE,
  FortunePublicPage,
} from "@/components/fortune-public-page";

export const metadata: Metadata = {
  title: FORTUNE_PUBLIC_TITLE,
  description: FORTUNE_PUBLIC_SUMMARY,
};

export default function FortunePage() {
  return <FortunePublicPage />;
}
