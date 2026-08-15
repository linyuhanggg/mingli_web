import type { Metadata } from "next";

import { EditorialPage, editorialStyles as styles } from "@/components/editorial-page";
import { PublicCmsProjection } from "@/components/public-cms-projection";
import { StatusPanel } from "@/components/status-panel";
import { getPublicCmsMetadata } from "@/lib/public-cms-metadata";


export async function generateMetadata(): Promise<Metadata> {
  return getPublicCmsMetadata("seo.about", {
    title: "关于与边界",
    description: "产品方法、能力状态与运营边界。",
  });
}

export default function AboutPage() {
  return (
    <EditorialPage
      eyebrow="关于与边界"
      title="先把能做什么、还不能做什么说清楚。"
      intro="正式品牌、运营主体与团队信息尚未冻结，当前只说明已经确认的产品原则。"
    >
      <section className={styles.prose}>
        <h2>当前原则</h2>
        <p>盘面事实由确定性能力生成，语言模型只负责受约束的表达；未接能力不展示模拟结果。</p>
      </section>
      <StatusPanel
        state="disabled"
        title="完整信息待确认"
        description="品牌与运营资料确认后再补充，不使用临时名称或虚构团队信息。"
      />
      <PublicCmsProjection
        heading="已发布页面内容"
        source={{ kind: "item", contentKey: "page.about" }}
      />
    </EditorialPage>
  );
}
