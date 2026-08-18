/**
 * 省 / 市 / 区县三级行政区划，数据来自 `china-division`（民政部行政区划）。
 *
 * 只在用户真正展开出生地点时按需加载：pca.json 约 47KB，直接静态引入会进首屏包。
 * 中国大陆全境使用 Asia/Shanghai，所以选中国内地点后时区可以直接推导，
 * 不需要用户再单独选一次；海外走「直接输入」逃生口，由用户自己确认时区。
 */

export type ProvinceCityAreas = Record<string, Record<string, string[]>>;

let cache: ProvinceCityAreas | null = null;
let pending: Promise<ProvinceCityAreas> | null = null;

export async function loadDivisions(): Promise<ProvinceCityAreas> {
  if (cache) return cache;
  pending ??= import("china-division/dist/pca.json").then((module) => {
    cache = (module.default ?? module) as ProvinceCityAreas;
    return cache;
  });
  return pending;
}

/** 中国大陆、港澳台在行政上都只用一个法定时间，统一映射到 Asia/Shanghai。 */
export const CHINA_TIME_ZONE = "Asia/Shanghai";

export function joinLocation(province: string, city: string, area: string): string {
  return [province, city, area].filter(Boolean).join(" / ");
}
