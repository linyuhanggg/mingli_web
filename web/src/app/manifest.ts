import type { MetadataRoute } from "next";


export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "命理工具",
    short_name: "命理工具",
    description: "可核对的盘面、人生 K 线状态与一事一问。",
    start_url: "/",
    display: "standalone",
    background_color: "#ffffff",
    theme_color: "#ffffff",
    lang: "zh-CN",
  };
}
