import type { MetadataRoute } from "next";


export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "FateRadar 命理档案",
    short_name: "FateRadar",
    description: "个人命理档案、今日与近七日，以及一事一问。",
    start_url: "/",
    display: "standalone",
    background_color: "#fffdf7",
    theme_color: "#123a32",
    lang: "zh-CN",
  };
}
