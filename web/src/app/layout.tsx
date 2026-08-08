import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import "@fontsource-variable/noto-sans-sc";
import "@fontsource-variable/noto-serif-sc";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://fateradar.cn"),
  title: {
    default: "FateRadar｜个人命理档案与一事一问",
    template: "%s｜FateRadar",
  },
  description:
    "先做确定性计算，再给有依据、有边界、可核对的白话命理解读。",
  applicationName: "FateRadar",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  colorScheme: "light",
  themeColor: "#123a32",
};

const directionContract = `<!--
THESIS: FateRadar turns time into a private, checkable archive; it refuses the empty-chat homepage.
OWN-WORLD: Deep ink fields, warm paper, restrained gold rules, terracotta focus, serif reading hierarchy, and sans-serif controls.
STORY: A visitor understands the deterministic core, sees how evidence and limits are preserved, then starts one of three P0 tasks before login.
FIRST VIEWPORT: A dark editorial folio pairs a large promise and two actions with a calibrated time dial; the three trust facts remain visible without scrolling on desktop.
FORM: Eastern Editorial Archive, inherited authority, contract key FATERADAR-EASTERN-ARCHIVE-V1.
FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, and DESIGN.md
-->`;

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>
        <span
          aria-hidden="true"
          hidden
          dangerouslySetInnerHTML={{ __html: directionContract }}
        />
        {children}
      </body>
    </html>
  );
}
