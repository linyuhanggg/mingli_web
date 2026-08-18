"use client";

import { ReadingShell } from "@/components/reading/reading-shell";
import { BaziChart } from "@/components/readings/bazi-chart";
import { AccountSurface, AuthSurface, CommerceSurface, PublicContentSurface } from "@/components/surfaces";
import { ProductInputForm, type TaskFormValues } from "@/components/task/product-input-form";
import { Status } from "@/components/ui/status";
import { WorkbenchShell } from "@/components/workbench/workbench-shell";
import type { UiLabFixture, UiLabRelationshipFixture } from "@/fixtures/ui-lab";
import {
  UI_LAB_STATE_DETAILS,
  UI_LAB_STATUS_BY_STATE,
  uiLabCapabilityGate,
  uiLabRendersProductionSurface,
  type UiLabCapabilityId,
  type UiLabRole,
  type UiLabState,
} from "@/lib/ui-lab-contract";
import { getProductDefinition, type ProductId } from "@/products/catalog";
import { buildBaziChartViewFromViewModel } from "@/lib/reading-display";

import styles from "./ui-lab.module.css";

type PreviewShellProps = {
  readonly fixture: UiLabFixture;
  readonly state: UiLabState;
  readonly role: UiLabRole;
  readonly capabilityId: UiLabCapabilityId;
};

const filledTaskValuesBase: TaskFormValues = {
  subject: "演示受测人",
  calendar: "gregorian",
  birthDate: "1992-06-18",
  birthTime: "08:30",
  targetYear: "",
  targetMonth: "",
  targetDate: "",
  unknownTime: false,
  location: "江苏省常州市金坛区",
  timezone: "Asia/Shanghai",
  gender: "unspecified",
  timeStandard: "civil",
  longitude: "120.45",
  latitude: "31.73",
  coordinateSource: "fixture",
  issue: "这件事未来三个月应如何安排？",
  focus: "action",
  eventTime: "2026-08-14T09:00",
  timingStart: "",
  timingEnd: "",
  divinationMethod: "coins",
  meihuaCastingMethod: "time",
  meihuaNumber: "",
  meihuaCount: "",
  meihuaUpperTrigram: "乾",
  meihuaLowerTrigram: "坤",
  meihuaMovingLine: "1",
  meihuaSource: "演示资料",
  observationMode: "face",
  observationRegion: "forehead",
  observationDescriptor: "region_visible",
  observationVisibility: "full",
  observationUncertainty: "0",
  selectionEventProfile: "business_opening_transaction",
  selectionActions: "开市",
  selectionStart: "2026-09-01",
  selectionEnd: "2026-09-03",
  selectionConstraints: "演示约束",
  fengshuiPropertyScope: "residential",
  fengshuiSelectedSchool: "bazhai",
  fengshuiFacingDegrees: "180",
  fengshuiUncertaintyDegrees: "0",
  consent: true,
  photoSelected: false,
  observationNotes: "",
  saveToArchive: false,
  profile: "演示资料版本",
  arts: ["八字", "紫微"],
  preference: "direct",
  lines: ["young-yang", "young-yin", "old-yang", "young-yin", "young-yang", "old-yin"],
};

function filledTaskValues(productId: ProductId): TaskFormValues {
  const focus = productId === "liuyao"
    ? "coins"
    : productId === "daliuren"
      ? "progress"
      : "action";
  return { ...filledTaskValuesBase, focus };
}

function LabStatus({ state, title }: { readonly state: UiLabState; readonly title?: string }) {
  const details = UI_LAB_STATE_DETAILS[state];
  return (
    <Status
      description={details.description}
      state={UI_LAB_STATUS_BY_STATE[state]}
      title={title ?? details.label}
    />
  );
}

function RelationshipRegistryStatus({
  fixture,
}: {
  readonly fixture: UiLabRelationshipFixture;
}) {
  const product = getProductDefinition(fixture.productId);
  const ready = fixture.viewModel.state === "ready";
  return (
    <Status
      description={ready
        ? fixture.viewModel.description
        : "合盘核心已接入；UI Lab 不写入真实双人资料，当前不内置合盘结果 Fixture。"}
      state={ready ? "success" : "unavailable"}
      title={ready ? `${product.name}双人合盘已就绪` : `${product.name}合盘暂无结果 Fixture`}
    />
  );
}

function ProductionSurface({ fixture, state }: Pick<PreviewShellProps, "fixture" | "state">) {
  switch (fixture.previewKind) {
    case "product-input": {
      const product = getProductDefinition(fixture.productId);
      return (
        <ProductInputForm
          initialValues={state === "filled" ? filledTaskValues(fixture.productId) : undefined}
          onConfirm={() => undefined}
          product={product}
        />
      );
    }
    case "bazi-result":
      return (
        <BaziChart
          chart={buildBaziChartViewFromViewModel(fixture.viewModel)}
          evidence={fixture.evidence}
          title="八字结果页验收切片"
        />
      );
    case "workbench": {
      const product = getProductDefinition(fixture.productId);
      return <WorkbenchShell onBack={() => undefined} product={product} />;
    }
    case "reading": {
      const product = getProductDefinition(fixture.productId);
      return <ReadingShell product={product} />;
    }
    case "relationship-status": {
      return <RelationshipRegistryStatus fixture={fixture} />;
    }
    case "account":
      return <AccountSurface surface={fixture.surface} />;
    case "auth":
      return <AuthSurface surface={fixture.surface} />;
    case "commerce":
      return <CommerceSurface surface={fixture.surface} />;
    case "public-content":
      return <PublicContentSurface surface={fixture.surface} />;
  }
}

export function PreviewShell({ fixture, state, role, capabilityId }: PreviewShellProps) {
  const rendersProductionSurface = uiLabRendersProductionSurface(fixture.previewKind, state);
  const rendersRelationshipRegistry = fixture.previewKind === "relationship-status"
    && state === "pristine";
  const capabilityGate = (rendersProductionSurface || rendersRelationshipRegistry)
    ? uiLabCapabilityGate(fixture.previewKind, role, capabilityId)
    : null;

  return (
    <div className={styles.previewBodySurface} data-state={state}>
      {capabilityGate
        ? <Status
            description={capabilityGate.description}
            state={capabilityGate.state}
            title={capabilityGate.title}
          />
        : rendersRelationshipRegistry
        ? <RelationshipRegistryStatus fixture={fixture} />
        : rendersProductionSurface
        ? <ProductionSurface fixture={fixture} state={state} />
        : <LabStatus state={state} />}
    </div>
  );
}
