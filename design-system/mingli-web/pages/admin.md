# Admin Console — Surface Override

**Routes:** `/admin/*` (or dedicated `admin` app under same brand tokens)  
**Mode:** Operate + Audit  
**World:** Eastern Editorial Archive (inherits Master + `DESIGN.md`)  
**Authority order:** `DESIGN.md` > Master > this override > generic dashboard kits  

---

## Design dials (admin only)

| Dial | Value | Why |
|------|-------|-----|
| Variance | 4/10 | Keep brand calm; no experimental admin chrome |
| Motion | 3/10 | Status feedback only; no hero theatrics |
| Density | 7/10 | Tables/filters need tighter spacing, still paper-and-ink |

## Thesis

Admin is still FateRadar paper archive, not a blue SaaS console.  
It is a **ledger desk**: list, filter, inspect, approve, audit.  
C-end sells calm privacy. Admin sells **clear facts + safe action**.

Same tokens, same type voices, same anti-patterns.  
Different shell: denser rails, tabular data, audit-first copy.

## Keep from C-end

- Tokens only from `web/src/app/globals.css` / `DESIGN.md`
- Canvas: `--ivory-50`; paper cards: `--white`; soft surfaces: `--ivory-100`
- Primary action: `--ink-900` → hover `--ink-800`
- Status tags: amber pending / moss success / ivory+terracotta error
- Fonts: Serif for page titles & ledger headings; Sans for UI, filters, tables
- Icons: `lucide-react` outline only; never emoji icons
- Focus: 3px terracotta ring + offset
- Touch targets ≥ 44×44 even when density rises
- Stack: CSS Modules + radix-ui + motion/react light feedback + RHF/Zod

## Override from C-end

| C-end habit | Admin habit |
|-------------|-------------|
| Large scene cards / TimeArchive hero | Small KPI chips + work queue |
| Generous section breathing | Compact toolbars, sticky filter bar |
| Marketing serif display | Serif only for H1/section titles; tables all sans |
| Soft storytelling | Explicit state text + timestamps + actor |
| Mobile-first consumer flows | Desktop-first ops (≥1024 preferred); mobile still usable as card lists |

## Shell

```
┌──────────────────────────────────────────────────────────┐
│ Top bar: brand mark · env badge · staff · sign-out       │
├──────────────┬───────────────────────────────────────────┤
│ Side nav     │ Page header (title + short duty)          │
│ 总览         │ Filter bar (search / date / status)       │
│ 用户档案     │ Main ledger (table desktop / cards mobile)│
│ 订单支付     │ Detail drawer or full page inspect        │
│ 退款审批     │                                           │
│ 解读任务     │                                           │
│ 对账         │                                           │
│ 审计日志     │                                           │
└──────────────┴───────────────────────────────────────────┘
```

- Left rail: paper edge, 1px `--border-subtle`, active item ink fill or gold rule
- Top bar: translucent ivory like public header, no marketing CTAs
- Env badge required: `local` / `test` / `prod` (terracotta on prod)
- Skip link to main content on every page

## Components (admin vocabulary)

1. **LedgerTable** — desktop table; sticky header; tabular numerals; row hover ivory-100
2. **LedgerCards** — mobile fallback of same columns as stacked cards
3. **FilterBar** — labeled fields only (no placeholder-only); apply/reset explicit
4. **StatusTag** — color + text always; never color alone
5. **KpiChip** — short number + label; no decorative sparklines in P0
6. **InspectPanel** — right drawer or second column; identity fields masked by default
7. **AuditLine** — who / when / action / target id
8. **DangerAction** — secondary by default; confirm dialog for refund/reverse/retry-pay

## Status mapping (must reuse tokens)

| State | Surface | Text |
|-------|---------|------|
| Pending / processing | `--amber-100` | ink-950 + word “处理中/待审” |
| Success / paid / accepted | `--moss-100` | ink-950 + word |
| Error / rejected / failed | `--ivory-100` + terracotta text | explicit reason |
| Neutral / draft | ivory-100 | ink-700 |

## Data viz (P0/P1)

- Prefer **tables first**
- KPI counts as chips, not big charts
- If chart later: simple horizontal bar / line only; always table alternative
- No candlestick, sunburst, treemap in admin v1

## Motion

- Feedback 150–180ms opacity/transform only
- Row expand / drawer enter ≤ 260ms
- No stagger grids on dense tables
- `prefers-reduced-motion`: instant state, no entrance

## Accessibility non-negotiables

- Keyboard path for filter → table → row actions → confirm
- Visible focus everywhere
- Icon-only controls need `aria-label`
- Errors via `role="alert"` near field
- Contrast ≥ 4.5:1 on ivory
- Tables: proper `<th scope>`; sortable headers announce state

## Privacy / safety UI rules

- Mask phone / email / birth by default; reveal is deliberate click + audit
- Never show `state_token`, raw secrets, full payment channel payloads
- Destructive ops need typed confirm or secondary confirm step
- Empty / loading / error honest; no fake “今日收入 ¥0” if API not ready

## Forbidden in admin (even if “dashboard kits” suggest)

- Purple/pink AI accents, neon, glassmorphism dark OLED default
- Tailwind/shadcn/MUI/AntD as new system
- Fira / Inter / generic gray SaaS palette replacing brand tokens
- Emoji status, chat-style ops UI
- Full-page dark mode as default admin look

## Page overrides (P0)

### `/admin` 总览
- 4 KPI chips: 待审退款 / 失败解读 / 今日支付异常 / 对账差异
- Work queue list (not marketing hero)

### `/admin/orders`
- Filter: order id, user id, status, date range
- Columns: order, product, amount, pay state, created, actions

### `/admin/refunds`
- Queue-first; approve/reject with reason required
- Show entitlement impact preview before submit

### `/admin/readings`
- Failed / stuck jobs; retry only when backend allows
- Show reading type, profile version, last error code (not stack dump)

### `/admin/users`
- Search by user uuid / masked phone / email
- Read-only profiles + entitlement ledger summary

### `/admin/audit`
- Append-only list; filter by actor/action/day

## Pre-delivery checklist (admin)

- [ ] Same token set as C-end; no new brand colors
- [ ] Density higher but spacing still uses space tokens
- [ ] Desktop table + mobile card path both work
- [ ] Status text + color
- [ ] Masked PII default
- [ ] Confirm path for destructive action
- [ ] Focus, labels, skip-link
- [ ] Reduced-motion respected
