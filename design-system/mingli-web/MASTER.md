# Design System Master File

> **LOGIC:** When building a specific page, first check `design-system/mingli-web/pages/[page-name].md`.
> If that file exists, its rules **override** this Master file.
> Otherwise follow the rules below.

---

**Project:** FateRadar / Mingli Web  
**Generated:** 2026-08-11  
**Category:** Eastern Editorial Archive / Premium Personal Archive  
**Design Dials:** Variance 5/10 | Motion 7/10 (Standard) | Density 5/10  
**Authority:** `DESIGN.md` (FATERADAR-EASTERN-ARCHIVE-V1)

---

## Global Rules

### Color Palette (Eastern Editorial Archive)

| Role | Hex / Value | CSS Variable |
|------|-------------|--------------|
| Deep archive ink | `#0a2823` | `--ink-950` |
| Working ink / primary action | `#123a32` | `--ink-900` |
| Active ink hover | `#1b4b41` | `--ink-800` |
| Reading secondary text | `#345f55` | `--ink-700` |
| Soft ink muted | `#6f8a82` | `--ink-500` |
| Warm paper canvas | `#fffdf7` | `--ivory-50` |
| Soft paper | `#f8f3e7` | `--ivory-100` |
| Divided paper | `#eee5d3` | `--ivory-200` |
| Archival gold | `#a9853f` | `--gold-500` |
| Soft gold | `#c1a263` | `--gold-400` |
| Terracotta focus | `#a85e46` | `--terracotta-500` |
| Deep terracotta error | `#884532` | `--terracotta-600` |
| Moss confirmation | `#dfe9df` | `--moss-100` |
| Moss boundary | `#2d6253` | `--moss-700` |
| Amber pending | `#f2e6c8` | `--amber-100` |
| Clean sheet | `#ffffff` | `--white` |

**Color Notes:** Deep ink green + warm ivory + muted gold + terracotta focus. Never introduce generic purple-blue AI gradients, neon astrology, or pink CTAs.

### Typography

- **Display / Headline / Title:** `Noto Serif SC Variable` (+ Songti fallbacks)
- **Body / UI / Forms:** `Noto Sans SC Variable` (+ system sans)
- **Mood:** calm, precise, private, archival, modern Chinese editorial
- **Do not** switch to Lora/Raleway or decorative calligraphy faces

### Spacing Variables

*Density: 5/10 — Standard*

| Token | Value | Usage |
|-------|-------|-------|
| `--space-xs` | `0.25rem` | Tight gaps |
| `--space-sm` | `0.5rem` | Icon gaps |
| `--space-md` | `1rem` | Standard padding |
| `--space-lg` | `1.5rem` | Section padding |
| `--space-xl` | `2rem` | Large gaps |
| `--space-2xl` | `3rem` | Section margins |
| `--space-3xl` | `4rem` | Hero padding |

### Motion Tokens

| Token | Value | Usage |
|-------|-------|-------|
| `--ease-out-expo` | `cubic-bezier(0.16, 1, 0.3, 1)` | Arrivals |
| `--duration-feedback` | `180ms` | Buttons, hover |
| `--duration-state` | `260ms` | Status / layer swaps |
| `--duration-entrance` | `450ms` | Section reveals |
| `--duration-focal` | `720ms` | Hero / TimeArchive |

### Stack Contract

- CSS Modules + semantic tokens in `web/src/app/globals.css`
- Interaction: `radix-ui`
- Motion: `motion/react` only (no GSAP/Lenis/Lottie)
- Icons: `lucide-react` for functional controls only
- Forms: React Hook Form + Zod
- Forbidden without DESIGN.md update: Tailwind, shadcn runtime, MUI, AntD, second motion library

### Key Effects

- Paper-and-ink hierarchy; flat by default
- Fine 1px rules, light corners (`radius-sm/md/lg`)
- Soft card lift only for real paper surfaces
- Ambient time-ring motion transform-only, 8–12s, reduced-motion off
- Focus ring: 3px terracotta, 3px offset
- Touch targets ≥ 44×44px

### Avoid (Anti-patterns)

- Neon astrology SaaS / fortune-teller kitsch
- Chat-box homepage
- Purple/pink AI gradients
- Layout-property animation (width/height/top/left/margin)
- Continuous blur/glow on large surfaces
- Motion that hides content without reduced-motion fallback

### Pre-Delivery Checklist

- [ ] No emojis as icons
- [ ] Hover / press feedback 150–300ms, transform/opacity only
- [ ] Focus visible for keyboard
- [ ] prefers-reduced-motion respected
- [ ] Responsive: 360, 768, 1024, 1440
- [ ] Loading / empty / error states honest
