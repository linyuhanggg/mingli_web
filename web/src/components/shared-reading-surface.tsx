"use client";

import { useEffect, useState } from "react";

import {
  ApiError,
  getReadingShare,
  type ReadingShareDocument,
} from "@/lib/api";

import { StatusPanel } from "./status-panel";
import { SecondarySurfaceFrame } from "./surfaces/secondary-surface-frame";
import styles from "./surfaces/secondary-surfaces.module.css";

type SharedReadingSurfaceProps = {
  readonly token: string;
};

function SharedReadingDocument({ document }: { document: ReadingShareDocument }) {
  return (
    <>
      <section aria-labelledby="shared-reading-summary" className={styles.section}>
        <h2 id="shared-reading-summary">接纳摘要</h2>
        <p>{document.answer_summary}</p>
      </section>

      {document.themes.length > 0 ? (
        <nav aria-label="分享主题" className={styles.section}>
          <h2>主题</h2>
          <ul className={styles.linkList}>
            {document.themes.map((theme) => (
              <li key={theme.theme_id}>{theme.label}</li>
            ))}
          </ul>
        </nav>
      ) : null}

      <section aria-labelledby="shared-reading-claims" className={styles.section}>
        <h2 id="shared-reading-claims">判断</h2>
        {document.claims.length > 0 ? (
          <ul>
            {document.claims.map((claim) => (
              <li key={claim.claim_id}>
                <p>{claim.text}</p>
              </li>
            ))}
          </ul>
        ) : (
          <p>当前分享没有可公开展示的判断。</p>
        )}
      </section>

      <section aria-labelledby="shared-reading-evidence" className={styles.section}>
        <h2 id="shared-reading-evidence">依据与边界</h2>
        {document.evidence.length > 0 ? (
          <ul>
            {document.evidence.map((evidence) => (
              <li key={evidence.evidence_ref}>{evidence.title}</li>
            ))}
          </ul>
        ) : null}
        {document.boundaries.length > 0 ? (
          <ul>
            {document.boundaries.map((boundary) => (
              <li key={boundary.limit_ref}>{boundary.text}</li>
            ))}
          </ul>
        ) : (
          <p>暂无额外边界说明。</p>
        )}
      </section>

      <p className={styles.policyPreview}>
        此页面只展示分享快照中的公开字段；分享链接过期或被撤销后，服务端不再返回正文。
      </p>
    </>
  );
}

export function SharedReadingSurface({ token }: SharedReadingSurfaceProps) {
  const [loading, setLoading] = useState(true);
  const [document, setDocument] = useState<ReadingShareDocument | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    getReadingShare(token)
      .then(({ document: next }) => {
        if (!cancelled) setDocument(next);
      })
      .catch((reason: unknown) => {
        if (cancelled) return;
        if (reason instanceof ApiError && [404, 410].includes(reason.status)) {
          setError("分享已过期、被撤销，或不存在。");
        } else if (reason instanceof Error && reason.message) {
          setError(reason.message);
        } else {
          setError("分享暂时无法读取，请稍后重试。");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [token]);

  return (
    <SecondarySurfaceFrame
      eyebrow="分享"
      intro="这是由服务端生成的短时分享快照；页面不会重新计算盘面，也不会读取分享者账户。"
      title="分享中的解读"
    >
      {loading ? (
        <StatusPanel
          state="loading"
          title="正在读取分享"
          description="服务端正在确认分享快照是否仍在有效期内。"
        />
      ) : error ? (
        <StatusPanel
          state="error"
          title="分享不可用"
          description={error}
          actionHref="/"
          actionLabel="返回首页"
        />
      ) : document ? (
        <SharedReadingDocument document={document} />
      ) : (
        <StatusPanel
          state="error"
          title="分享不可用"
          description="服务端没有返回分享内容。"
          actionHref="/"
          actionLabel="返回首页"
        />
      )}
    </SecondarySurfaceFrame>
  );
}
