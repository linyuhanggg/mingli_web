import { Field } from "mingli-web";

const stack: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "20px",
  maxWidth: "360px",
};

export function TextInput() {
  return (
    <div style={stack}>
      <Field label="姓名" description="仅用于生成档案标题，可随时修改。">
        <input type="text" name="name" defaultValue="林某" autoComplete="off" />
      </Field>
    </div>
  );
}

export function Required() {
  return (
    <div style={stack}>
      <Field
        label="出生日期"
        description="请填写公历日期；农历可在下一步切换。"
        required
      >
        <input type="date" name="birth-date" defaultValue="1993-04-18" />
      </Field>
    </div>
  );
}

export function WithError() {
  return (
    <div style={stack}>
      <Field
        label="出生时刻"
        description="精确到分钟可提升定盘精度。"
        error="时刻格式不正确，请使用 24 小时制。"
        required
      >
        <input type="text" name="birth-time" defaultValue="25:70" />
      </Field>
    </div>
  );
}

export function DisabledWithReason() {
  return (
    <div style={stack}>
      <Field
        label="出生地时区"
        description="用于真太阳时换算。"
        disabledReason="先填写出生地，才能确定时区。"
      >
        <input type="text" name="timezone" defaultValue="Asia/Shanghai" disabled />
      </Field>
    </div>
  );
}
