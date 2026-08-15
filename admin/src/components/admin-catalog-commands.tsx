"use client";

import { useState, type FormEvent } from "react";

import { Button, Status } from "@/components/ui";
import { adminFetch, type StaffRole } from "@/lib/api";
import type {
  AdminCatalogApiFamily,
  AdminCatalogApiResponse,
  AdminCatalogApiVersion,
} from "@/lib/admin-catalog";

import styles from "./admin-catalog-surface.module.css";

type AdminCatalogCommandsProps = {
  payload: AdminCatalogApiResponse;
  pathname: string;
  role: StaffRole;
  onRefresh: () => Promise<boolean>;
};

type CommandKey =
  | "family"
  | "version"
  | "offer"
  | `publish:${string}`
  | `retire:${string}`
  | `offer:${string}`;

function requestedFamilyId(pathname: string): string | null {
  const parts = pathname.split("?", 1)[0].split("/").filter(Boolean);
  return parts[0] === "products" && parts[2] === "versions" ? parts[1] ?? null : null;
}

function visibleFamilies(
  payload: AdminCatalogApiResponse,
  pathname: string,
): readonly AdminCatalogApiFamily[] {
  const familyId = requestedFamilyId(pathname);
  return familyId
    ? payload.families.filter((family) => family.id === familyId)
    : payload.families;
}

function visibleVersions(
  families: readonly AdminCatalogApiFamily[],
): readonly AdminCatalogApiVersion[] {
  return families.flatMap((family) => family.versions);
}

export function AdminCatalogCommands({
  payload,
  pathname,
  role,
  onRefresh,
}: AdminCatalogCommandsProps) {
  const families = visibleFamilies(payload, pathname);
  const versions = visibleVersions(families);
  const defaultFamilyId = families[0]?.id ?? "";
  const defaultVersionId = versions[0]?.id ?? "";
  const [familyKey, setFamilyKey] = useState("");
  const [familyLabel, setFamilyLabel] = useState("");
  const [versionFamilyId, setVersionFamilyId] = useState(defaultFamilyId);
  const [versionName, setVersionName] = useState("");
  const [versionPrice, setVersionPrice] = useState("0");
  const [versionCurrency, setVersionCurrency] = useState("CNY");
  const [contractVersion, setContractVersion] = useState("reading-document-v1");
  const [followUpCount, setFollowUpCount] = useState("0");
  const [followUpWindow, setFollowUpWindow] = useState("0");
  const [offerVersionId, setOfferVersionId] = useState(defaultVersionId);
  const [offerChannel, setOfferChannel] = useState("");
  const [offerSku, setOfferSku] = useState("");
  const [offerPrice, setOfferPrice] = useState("0");
  const [offerCurrency, setOfferCurrency] = useState("CNY");
  const [offerEnabled, setOfferEnabled] = useState(false);
  const [reason, setReason] = useState("");
  const [reasonError, setReasonError] = useState<string | null>(null);
  const [pending, setPending] = useState<CommandKey | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function runCommand(
    key: CommandKey,
    path: string,
    body: Record<string, unknown>,
    successMessage: string,
  ) {
    const normalizedReason = reason.trim();
    if (normalizedReason.length < 4) {
      setReasonError("请填写至少 4 个字的 Catalog 操作原因。");
      return;
    }
    setReasonError(null);
    setError(null);
    setResult(null);
    setPending(key);
    const response = await adminFetch(path, {
      method: "POST",
      body: JSON.stringify({ ...body, reason: normalizedReason }),
    });
    if (!response.ok) {
      setError(response.title);
      setPending(null);
      return;
    }
    const refreshed = await onRefresh();
    setResult(refreshed ? successMessage : "命令已提交，但 Catalog 刷新失败；请重新读取。 ");
    setPending(null);
  }

  function submitFamily(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void runCommand(
      "family",
      "/api/v1/admin/catalog/families",
      { key: familyKey, label: familyLabel },
      "商品族已创建，Catalog 已刷新。",
    );
  }

  function submitVersion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void runCommand(
      "version",
      "/api/v1/admin/catalog/versions",
      {
        family_id: versionFamilyId || defaultFamilyId,
        version: versionName,
        price_minor: Number(versionPrice),
        currency: versionCurrency,
        contract_version: contractVersion,
        follow_up_count: Number(followUpCount),
        follow_up_window_seconds: Number(followUpWindow),
      },
      "商品版本已创建，Catalog 已刷新。",
    );
  }

  function submitOffer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void runCommand(
      "offer",
      "/api/v1/admin/catalog/offers",
      {
        product_version_id: offerVersionId || defaultVersionId,
        channel: offerChannel,
        channel_sku: offerSku,
        price_minor: Number(offerPrice),
        currency: offerCurrency,
        enabled: offerEnabled,
      },
      "报价已创建，Catalog 已刷新。",
    );
  }

  return (
    <section className={styles.commandSection} aria-labelledby="catalog-command-title">
      <div className={styles.sectionHeading}>
        <div>
          <h2 id="catalog-command-title">Catalog 管理命令</h2>
          <p>
            当前角色：{role}。所有变更都通过服务端权限、CSRF、状态校验和 AdminAuditEvent；页面不会直接改写数据库。
          </p>
        </div>
        <span className={styles.capability}>带审计</span>
      </div>

      <div className={styles.commandReason}>
        <label htmlFor="catalog-operation-reason">Catalog 操作原因</label>
        <textarea
          id="catalog-operation-reason"
          value={reason}
          onChange={(event) => setReason(event.target.value)}
          minLength={4}
          required
          aria-invalid={reasonError ? "true" : undefined}
          aria-describedby={reasonError ? "catalog-operation-reason-error" : undefined}
          placeholder="说明这次商品、版本或报价变更的业务原因…"
        />
        {reasonError ? (
          <p id="catalog-operation-reason-error" className={styles.inlineAlert} role="alert">
            {reasonError}
          </p>
        ) : null}
      </div>

      {result ? <Status state="success" title={result} description="服务端已返回成功结果，审计事实随命令写入。" /> : null}
      {error ? <Status state="error" title="Catalog 命令失败" description={error} /> : null}

      <div className={styles.commandGrid}>
        {pathname === "/products" ? (
          <form className={styles.commandCard} onSubmit={submitFamily}>
            <h3>创建商品族</h3>
            <label htmlFor="catalog-family-key">商品族 key</label>
            <input
              id="catalog-family-key"
              value={familyKey}
              onChange={(event) => setFamilyKey(event.target.value)}
              required
              minLength={1}
              maxLength={80}
            />
            <label htmlFor="catalog-family-label">商品族名称</label>
            <input
              id="catalog-family-label"
              value={familyLabel}
              onChange={(event) => setFamilyLabel(event.target.value)}
              required
              minLength={1}
              maxLength={160}
            />
            <Button type="submit" loading={pending === "family"}>
              创建商品族
            </Button>
          </form>
        ) : null}

        <form className={styles.commandCard} onSubmit={submitVersion}>
          <h3>创建商品版本</h3>
          <label htmlFor="catalog-version-family">所属商品族</label>
          <select
            id="catalog-version-family"
            value={versionFamilyId || defaultFamilyId}
            onChange={(event) => setVersionFamilyId(event.target.value)}
            required
            disabled={families.length === 0}
          >
            {families.length === 0 ? <option value="">暂无商品族</option> : null}
            {families.map((family) => (
              <option key={family.id} value={family.id}>
                {family.label} · {family.key}
              </option>
            ))}
          </select>
          <label htmlFor="catalog-version-name">商品版本</label>
          <input
            id="catalog-version-name"
            value={versionName}
            onChange={(event) => setVersionName(event.target.value)}
            required
            minLength={1}
            maxLength={40}
          />
          <div className={styles.fieldGrid}>
            <label htmlFor="catalog-version-price">
              价格（分）
              <input
                id="catalog-version-price"
                type="number"
                min={0}
                value={versionPrice}
                onChange={(event) => setVersionPrice(event.target.value)}
                required
              />
            </label>
            <label htmlFor="catalog-version-currency">
              币种
              <input
                id="catalog-version-currency"
                value={versionCurrency}
                onChange={(event) => setVersionCurrency(event.target.value)}
                minLength={3}
                maxLength={3}
                required
              />
            </label>
          </div>
          <label htmlFor="catalog-contract-version">交付合同版本</label>
          <input
            id="catalog-contract-version"
            value={contractVersion}
            onChange={(event) => setContractVersion(event.target.value)}
            required
            maxLength={80}
          />
          <div className={styles.fieldGrid}>
            <label htmlFor="catalog-follow-up-count">
              追问次数
              <input
                id="catalog-follow-up-count"
                type="number"
                min={0}
                value={followUpCount}
                onChange={(event) => setFollowUpCount(event.target.value)}
                required
              />
            </label>
            <label htmlFor="catalog-follow-up-window">
              窗口（秒）
              <input
                id="catalog-follow-up-window"
                type="number"
                min={0}
                value={followUpWindow}
                onChange={(event) => setFollowUpWindow(event.target.value)}
                required
              />
            </label>
          </div>
          <Button type="submit" loading={pending === "version"} disabled={families.length === 0}>
            创建商品版本
          </Button>
        </form>

        <form className={styles.commandCard} onSubmit={submitOffer}>
          <h3>创建报价</h3>
          <label htmlFor="catalog-offer-version">所属商品版本</label>
          <select
            id="catalog-offer-version"
            value={offerVersionId || defaultVersionId}
            onChange={(event) => setOfferVersionId(event.target.value)}
            required
            disabled={versions.length === 0}
          >
            {versions.length === 0 ? <option value="">暂无商品版本</option> : null}
            {families.map((family) =>
              family.versions.map((version) => (
                <option key={version.id} value={version.id}>
                  {family.label} · {version.version}
                </option>
              )),
            )}
          </select>
          <label htmlFor="catalog-offer-channel">渠道</label>
          <input
            id="catalog-offer-channel"
            value={offerChannel}
            onChange={(event) => setOfferChannel(event.target.value)}
            required
            maxLength={32}
          />
          <label htmlFor="catalog-offer-sku">渠道 SKU</label>
          <input
            id="catalog-offer-sku"
            value={offerSku}
            onChange={(event) => setOfferSku(event.target.value)}
            required
            maxLength={160}
          />
          <div className={styles.fieldGrid}>
            <label htmlFor="catalog-offer-price">
              报价（分）
              <input
                id="catalog-offer-price"
                type="number"
                min={0}
                value={offerPrice}
                onChange={(event) => setOfferPrice(event.target.value)}
                required
              />
            </label>
            <label htmlFor="catalog-offer-currency">
              币种
              <input
                id="catalog-offer-currency"
                value={offerCurrency}
                onChange={(event) => setOfferCurrency(event.target.value)}
                minLength={3}
                maxLength={3}
                required
              />
            </label>
          </div>
          <label className={styles.checkboxLabel} htmlFor="catalog-offer-enabled">
            <input
              id="catalog-offer-enabled"
              type="checkbox"
              checked={offerEnabled}
              onChange={(event) => setOfferEnabled(event.target.checked)}
            />
            创建后立即启用
          </label>
          <Button type="submit" loading={pending === "offer"} disabled={versions.length === 0}>
            创建报价
          </Button>
        </form>
      </div>

      <div className={styles.commandCard}>
        <h3>版本与报价状态</h3>
        {families.length === 0 ? <p>当前范围没有版本记录。</p> : null}
        {families.map((family) => (
          <div className={styles.versionGroup} key={family.id}>
            <strong>{family.label}</strong>
            {family.versions.map((version) => (
              <div className={styles.versionRow} key={version.id}>
                <div>
                  <strong>{version.version}</strong>
                  <span>{version.status} · {version.contract_version}</span>
                </div>
                <div className={styles.actionRow}>
                  {version.status === "draft" ? (
                    <Button
                      variant="secondary"
                      type="button"
                      loading={pending === `publish:${version.id}`}
                      disabled={!version.offers.some((offer) => offer.enabled)}
                      onClick={() =>
                        void runCommand(
                          `publish:${version.id}`,
                          `/api/v1/admin/catalog/versions/${version.id}/publish`,
                          {},
                          `${version.version} 已发布，Catalog 已刷新。`,
                        )
                      }
                    >
                      发布 {version.version}
                    </Button>
                  ) : null}
                  {version.status === "active" ? (
                    <Button
                      variant="destructive"
                      type="button"
                      loading={pending === `retire:${version.id}`}
                      onClick={() =>
                        void runCommand(
                          `retire:${version.id}`,
                          `/api/v1/admin/catalog/versions/${version.id}/retire`,
                          {},
                          `${version.version} 已退役，Catalog 已刷新。`,
                        )
                      }
                    >
                      退役 {version.version}
                    </Button>
                  ) : null}
                </div>
                {version.offers.map((offer) => (
                  <div className={styles.offerRow} key={offer.id}>
                    <span>{offer.channel} · {offer.channel_sku} · {offer.currency} {offer.price_minor}</span>
                    <Button
                      variant="ghost"
                      type="button"
                      loading={pending === `offer:${offer.id}`}
                      onClick={() =>
                        void runCommand(
                          `offer:${offer.id}`,
                          `/api/v1/admin/catalog/offers/${offer.id}/enabled`,
                          { enabled: !offer.enabled },
                          `报价已${offer.enabled ? "停用" : "启用"}，Catalog 已刷新。`,
                        )
                      }
                    >
                      {offer.enabled ? "停用报价" : "启用报价"}
                    </Button>
                  </div>
                ))}
              </div>
            ))}
          </div>
        ))}
      </div>
    </section>
  );
}
