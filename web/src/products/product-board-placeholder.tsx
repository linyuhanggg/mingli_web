import type { ProductId } from "./catalog";
import styles from "./product-board-placeholder.module.css";

function BaziBoard() {
  return <div className={styles.pillars} aria-label="八字四柱结构槽位">{["年柱", "月柱", "日柱", "时柱"].map((item) => <div key={item}><strong>{item}</strong><span>待计算</span><small>十神 · 藏干 · 纳音</small></div>)}</div>;
}

function ZiweiBoard() {
  const palaces = ["命宫", "兄弟", "夫妻", "子女", "财帛", "疾厄", "迁移", "交友", "官禄", "田宅", "福德", "父母"];
  return <div className={styles.palaces} aria-label="紫微十二宫结构槽位">{palaces.map((item) => <span key={item}>{item}<small>待计算</small></span>)}</div>;
}

function QizhengBoard() {
  return <div className={styles.orbit} aria-label="七政星盘结构槽位"><div><strong>星盘</strong><span>十一曜宿度待计算</span></div></div>;
}

function LiuyaoBoard() {
  return <div className={styles.hexagram} aria-label="六爻卦盘结构槽位">{["上爻", "五爻", "四爻", "三爻", "二爻", "初爻"].map((item) => <div key={item}><span>{item}</span><i /><small>六亲 · 世应 · 动静</small></div>)}</div>;
}

function QimenBoard() {
  return <div className={styles.nineGrid} aria-label="奇门九宫结构槽位">{["巽四", "离九", "坤二", "震三", "中五", "兑七", "艮八", "坎一", "乾六"].map((item) => <span key={item}>{item}<small>星 · 门 · 神</small></span>)}</div>;
}

function DaliurenBoard() {
  return <div className={styles.liuren} aria-label="大六壬四课三传结构槽位"><div>{["一课", "二课", "三课", "四课"].map((item) => <span key={item}>{item}</span>)}</div><div>{["初传", "中传", "末传"].map((item) => <strong key={item}>{item}</strong>)}</div></div>;
}

function LumingNayinBoard() {
  return <div className={styles.pillars} aria-label="禄命纳音四柱结构槽位">{["年柱", "月柱", "日柱", "时柱"].map((item) => <div key={item}><strong>{item}</strong><span>纳音待计算</span><small>三元 · 关系</small></div>)}</div>;
}

function TaiyiBoard() {
  return <div className={styles.orbit} aria-label="太乙年计盘结构槽位"><div><strong>年度太乙盘</strong><span>周期 · 主客 · 四将待计算</span></div></div>;
}

function SelectionBoard() {
  return <div className={styles.comparison} aria-label="择日候选结构槽位"><div>候选日期</div><div>淘汰原因</div><div>可解释排序</div></div>;
}

function FengshuiBoard() {
  return <div className={styles.observation} aria-label="风水空间结构槽位"><div>罗盘方向<small>真北 · 度数 · 误差</small></div><div>布局图<small>节点 · 关系</small></div><div>形势与理气<small>来源 · 缺失</small></div></div>;
}

function ObservationBoard() {
  return <div className={styles.observation} aria-label="见相观察结构槽位"><div>采集质量<small>角度 · 光线 · 遮挡</small></div><div>区域观察<small>部位 · 置信度</small></div><div>证据充足度<small>用户补充 · 边界</small></div></div>;
}

function CrossBoard({ label }: { label: string }) {
  return <div className={styles.comparison} aria-label={`${label}结构槽位`}><div>独立信号</div><div>共同印证</div><div>分歧与缺失</div></div>;
}

export function ProductBoardPlaceholder({ productId }: { productId: ProductId }) {
  if (productId === "bazi") return <BaziBoard />;
  if (productId === "ziwei") return <ZiweiBoard />;
  if (productId === "qizheng") return <QizhengBoard />;
  if (productId === "liuyao") return <LiuyaoBoard />;
  if (productId === "qimen") return <QimenBoard />;
  if (productId === "daliuren") return <DaliurenBoard />;
  if (productId === "luming-nayin") return <LumingNayinBoard />;
  if (productId === "taiyi") return <TaiyiBoard />;
  if (productId === "selection") return <SelectionBoard />;
  if (productId === "jianxiang") return <ObservationBoard />;
  if (productId === "fengshui") return <FengshuiBoard />;
  if (productId === "hecan") return <CrossBoard label="命盘合参" />;
  if (productId === "wenshi") return <CrossBoard label="问事合参" />;
  return <CrossBoard label="多盘问答" />;
}
