"use client";

import Link from "next/link";
import { useEffect, useId, useState, type FormEvent } from "react";

import { Container } from "./container";
import { PublicPageShell } from "./public-page-shell";
import { Status, type CoreStatusState } from "./ui/status";
import {
  ApiError,
  formatProfileOption,
  listProfiles,
  type ProfileSummary,
} from "@/lib/api";
import { loginContinueHref } from "@/lib/login-continue";
import styles from "./life-kline-page.module.css";

export type LifeKlineViewState =
  | "need-input"
  | "select-profile"
  | "loading"
  | "unsupported"
  | "error";

export type LifeKlineProfileOption = Readonly<{
  id: string;
  label: string;
  versionLabel: string;
}>;

type LifeKlinePageProps = Readonly<{
  initialState?: LifeKlineViewState;
  profileOptions?: readonly LifeKlineProfileOption[];
}>;

type ProfileLoadState = "idle" | "loading" | "unauthorized" | "error" | "success";

const profileLoginHref = loginContinueHref(
  "/life-kline",
  "?state=select-profile",
);

const breadcrumbState: Readonly<Record<LifeKlineViewState, CoreStatusState>> = {
  "need-input": "need-input",
  "select-profile": "need-input",
  loading: "loading",
  unsupported: "empty",
  error: "error",
};

function toProfileOption(profile: ProfileSummary): LifeKlineProfileOption {
  return {
    id: profile.profile_version_id,
    label: formatProfileOption(profile),
    versionLabel: `版本 ${profile.version}`,
  };
}

export function LifeKlinePage({
  initialState = "need-input",
  profileOptions,
}: LifeKlinePageProps) {
  const [viewState, setViewState] = useState<LifeKlineViewState>(initialState);
  const [selectedProfileId, setSelectedProfileId] = useState("");
  const [loadedProfileOptions, setLoadedProfileOptions] = useState<
    readonly LifeKlineProfileOption[]
  >([]);
  const [profileLoadState, setProfileLoadState] = useState<ProfileLoadState>(
    profileOptions === undefined ? "idle" : "success",
  );
  const [profileLoadAttempt, setProfileLoadAttempt] = useState(0);
  const [showLoadingPlaceholder, setShowLoadingPlaceholder] = useState(false);
  const [canCancel, setCanCancel] = useState(false);
  const [timedOut, setTimedOut] = useState(false);
  const profileGroupId = useId();
  const availableProfiles = profileOptions ?? loadedProfileOptions;
  const selectedProfile =
    availableProfiles.find(({ id }) => id === selectedProfileId) ?? null;

  useEffect(() => {
    if (viewState !== "select-profile" || profileOptions !== undefined) return;

    let active = true;

    listProfiles()
      .then(({ profiles }) => {
        if (!active) return;
        const nextProfiles = profiles.map(toProfileOption);
        setLoadedProfileOptions(nextProfiles);
        setSelectedProfileId((currentId) =>
          nextProfiles.some(({ id }) => id === currentId) ? currentId : "",
        );
        setProfileLoadState("success");
      })
      .catch((reason: unknown) => {
        if (!active) return;
        setLoadedProfileOptions([]);
        setSelectedProfileId("");
        setProfileLoadState(
          reason instanceof ApiError && reason.status === 401
            ? "unauthorized"
            : "error",
        );
      });

    return () => {
      active = false;
    };
  }, [profileLoadAttempt, profileOptions, viewState]);

  useEffect(() => {
    if (viewState !== "loading") return;

    const placeholderTimer = window.setTimeout(() => setShowLoadingPlaceholder(true), 300);
    const cancelTimer = window.setTimeout(() => setCanCancel(true), 15_000);
    const timeoutTimer = window.setTimeout(() => {
      setTimedOut(true);
      setViewState("error");
    }, 60_000);

    return () => {
      window.clearTimeout(placeholderTimer);
      window.clearTimeout(cancelTimer);
      window.clearTimeout(timeoutTimer);
    };
  }, [viewState]);

  function showUnsupported() {
    setTimedOut(false);
    setShowLoadingPlaceholder(false);
    setCanCancel(false);
    setViewState("unsupported");
  }

  function cancelLoading() {
    setShowLoadingPlaceholder(false);
    setCanCancel(false);
    setViewState("need-input");
  }

  function submitProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedProfileId) return;
    showUnsupported();
  }

  function retryProfileLoad() {
    setProfileLoadState("loading");
    setProfileLoadAttempt((attempt) => attempt + 1);
  }

  function openProfilePicker() {
    if (profileOptions === undefined) {
      setProfileLoadState("loading");
    }
    setViewState("select-profile");
  }

  const identity = selectedProfile ? (
    <div className={styles.identity} aria-label="当前档案">
      <span>
        <small>当前档案</small>
        <strong>{selectedProfile.label}</strong>
      </span>
      <span className={styles.version}>{selectedProfile.versionLabel}</span>
      <button className={styles.textButton} type="button" onClick={openProfilePicker}>
        切换档案
      </button>
    </div>
  ) : null;

  let stateContent;

  if (viewState === "need-input") {
    stateContent = (
      <Status
        actions={
          <>
            <Link href="/account/profiles/new">去建档</Link>
            <button data-variant="secondary" type="button" onClick={openProfilePicker}>
              选择已有档案
            </button>
          </>
        }
        description="人生 K 线需要先绑定一个受测人档案。登录只用于档案归属、保存与同步，不是付费门槛。"
        state="need-input"
        title="需要档案"
      />
    );
  } else if (viewState === "select-profile") {
    stateContent = (
      <div className={styles.stateStack}>
        {profileLoadState === "idle" || profileLoadState === "loading" ? (
          <Status
            description="正在读取当前账号可用的确认档案；等待期间不会使用默认档案或演示数据。"
            state="loading"
            title="正在加载档案"
          />
        ) : null}
        {profileLoadState === "error" ? (
          <Status
            actions={
              <>
                <button type="button" onClick={retryProfileLoad}>
                  重新加载档案
                </button>
                <button
                  data-variant="secondary"
                  type="button"
                  onClick={() => setViewState("need-input")}
                >
                  返回
                </button>
              </>
            }
            description="这次没有读到可确认的档案列表。页面不会把失败当成空列表，也不会选择默认档案。"
            state="error"
            title="档案读取失败"
          />
        ) : null}
        {profileLoadState === "unauthorized" ? (
          <Status
            actions={
              <>
                <Link href={profileLoginHref}>登录后继续</Link>
                <button
                  data-variant="secondary"
                  type="button"
                  onClick={() => setViewState("need-input")}
                >
                  返回
                </button>
              </>
            }
            description="登录后才能读取已保存的档案；登录完成后会回到本页继续选择。"
            state="unauthorized"
            title="登录后选择档案"
          />
        ) : null}
        {profileLoadState === "success" ? (
          <Status
            description="只选择档案版本；本页不会显示姓名以外的个人资料，也不会在浏览器中推算走势。"
            state={availableProfiles.length > 0 ? "need-input" : "empty"}
            title="选择档案"
          />
        ) : null}
        {profileLoadState === "success" && availableProfiles.length > 0 ? (
          <form className={styles.profileForm} onSubmit={submitProfile}>
            <fieldset aria-describedby={`${profileGroupId}-hint`}>
              <legend>可用档案</legend>
              <p className={styles.formHint} id={`${profileGroupId}-hint`}>
                请选择一个不透明档案版本，再读取当前能力状态。
              </p>
              <div className={styles.profileOptions}>
                {availableProfiles.map((profile) => (
                  <label className={styles.profileOption} key={profile.id}>
                    <input
                      checked={selectedProfileId === profile.id}
                      name={profileGroupId}
                      type="radio"
                      value={profile.id}
                      onChange={() => setSelectedProfileId(profile.id)}
                    />
                    <span>
                      <strong>{profile.label}</strong>
                      <small>{profile.versionLabel}</small>
                    </span>
                  </label>
                ))}
              </div>
            </fieldset>
            <div className={styles.formActions}>
              <button className={styles.primaryButton} disabled={!selectedProfileId} type="submit">
                读取人生 K 线状态
              </button>
              <button className={styles.secondaryButton} type="button" onClick={() => setViewState("need-input")}>
                取消
              </button>
            </div>
          </form>
        ) : null}
        {profileLoadState === "success" && availableProfiles.length === 0 ? (
          <div className={styles.emptyProfiles} role="status">
            <p>当前没有可在此页读取的档案。</p>
            <div className={styles.inlineActions}>
              <Link className={styles.primaryLink} href="/account/profiles">
                管理受测人档案
              </Link>
              <button className={styles.secondaryButton} type="button" onClick={() => setViewState("need-input")}>
                返回
              </button>
            </div>
          </div>
        ) : null}
      </div>
    );
  } else if (viewState === "loading") {
    stateContent = (
      <div className={styles.stateStack}>
        <Status
          actions={
            <>
              {canCancel ? (
                <button type="button" onClick={cancelLoading}>
                  取消读取
                </button>
              ) : null}
              <Link data-variant="secondary" href="/">
                返回首页
              </Link>
            </>
          }
          description="正在确认是否存在版本化、可核对的时间层事实；等待期间不会补算分数或绘制走势。"
          state="loading"
          title="正在读取时间层事实"
        />
        {showLoadingPlaceholder ? (
          <div
            aria-label="时间层事实读取占位"
            className={styles.loadingPlaceholder}
            data-testid="life-kline-loading-placeholder"
            role="status"
          >
            <span>正在确认可用时间层</span>
            <div aria-hidden="true" className={styles.placeholderRows}>
              {Array.from({ length: 6 }, (_, index) => (
                <i key={index} />
              ))}
            </div>
          </div>
        ) : null}
      </div>
    );
  } else if (viewState === "unsupported") {
    stateContent = (
      <div className={styles.stateStack}>
        <Status
          actions={
            <>
              <button type="button" onClick={showUnsupported}>
                刷新状态
              </button>
              <button data-variant="secondary" type="button" onClick={openProfilePicker}>
                切换档案
              </button>
              <Link data-variant="secondary" href="/">
                返回首页
              </Link>
            </>
          }
          description="当前权威事实服务尚未提供可跨时间比较的版本化人生序列，因此不会显示默认分数、方向或残缺走势。"
          state="unavailable"
          title="数据不足，暂不支持绘制"
        />
        <section aria-labelledby="life-kline-missing-title" className={styles.boundaryPanel}>
          <h2 id="life-kline-missing-title">当前保留的边界</h2>
          <ul>
            <li>只有权威事实合同完整返回后，才会进入可视化结果。</li>
            <li>时间层事实与解释分开，不把数量、关系或标签换算成人生分数。</li>
            <li>未知能力保持关闭，不使用演示数据补齐。</li>
          </ul>
        </section>
      </div>
    );
  } else {
    stateContent = (
      <Status
        actions={
          <>
            <button type="button" onClick={showUnsupported}>
              重试
            </button>
            <Link data-variant="secondary" href="/">
              返回首页
            </Link>
          </>
        }
        description={
          timedOut
            ? "等待已停止。可以重试或返回；不会继续转圈，也不会保留未确认的半成品。"
            : "这次没有读到可确认的时间层状态。可以重试或返回；页面不会展示猜测结果。"
        }
        state="error"
        title={timedOut ? "读取超时" : "读取失败"}
      />
    );
  }

  return (
    <PublicPageShell breadcrumbStatus={breadcrumbState[viewState]}>
      <main className={styles.main} data-view-state={viewState} id="main-content" tabIndex={-1}>
        <Container className={styles.container}>
          <header className={styles.header}>
            <p className={styles.eyebrow}>可核对的时间层</p>
            <h1>人生 K 线</h1>
            <p>
              按档案查看可核对的人生时间序列。只有权威事实完整返回时才会绘制；当前先诚实呈现输入、等待与不可用状态。
            </p>
          </header>
          {identity}
          <section aria-label="人生 K 线当前状态" className={styles.stateRegion}>
            {stateContent}
          </section>
        </Container>
      </main>
    </PublicPageShell>
  );
}
