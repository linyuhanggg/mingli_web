# FateRadar Design System

> Status: Accepted
> Updated: 2026-08-09
> Scope: responsive website first; future native iOS should preserve the same brand language

## 1. Design thesis

The visual direction is **Eastern Editorial Archive**: a contemporary personal archive shaped by time, evidence, traditional calculation, and restrained Chinese editorial design.

The product should feel calm, precise, private, and premium. It must not look like an enterprise dashboard, a neon astrology SaaS, a fortune-teller stall, or a chat interface with a decorative skin.

The existing brand image and website tokens are the starting point:

- deep ink green carries trust, depth, and privacy;
- warm ivory provides a paper-like reading surface;
- muted gold marks hierarchy and important evidence;
- terracotta is reserved for focus, warning, and small warm accents;
- generous negative space and clear typography create the premium feeling.

## 2. What we take from Metis

Metis is a structural and interaction reference, not a brand template.

Adopt:

- an editorial landing page rather than an empty chat box;
- a large typographic hero with one clear promise;
- large scene cards for real user tasks;
- numbered modules only when order or sequence is meaningful;
- trial before forced login;
- clear Free versus paid-result comparison;
- restrained fixed navigation and direct payment-status feedback.

Do not copy:

- the Metis wordmark, imagery, copy, exact composition, or private APIs;
- its black-and-white identity as our default palette;
- permanent-unlimited AI promises or browser-local sensitive history;
- any layout whose only purpose is to imitate the reference site.

## 3. Visual language

### Color

Use the semantic tokens already defined in `web/src/app/globals.css`.

| Role | Token | Value |
| --- | --- | --- |
| Primary text / deepest surface | `--ink-950` | `#0a2823` |
| Brand surface / primary action | `--ink-900` | `#123a32` |
| Interactive brand hover | `--ink-800` | `#1b4b41` |
| Secondary text | `--ink-700` | `#345f55` |
| Canvas | `--ivory-50` | `#fffdf7` |
| Soft surface | `--ivory-100` | `#f8f3e7` |
| Divided section | `--ivory-200` | `#eee5d3` |
| Primary accent | `--gold-500` | `#a9853f` |
| Soft accent | `--gold-400` | `#c1a263` |
| Focus / warning accent | `--terracotta-500` | `#a85e46` |

Gold is an accent, not a fill for every component. A view should normally have one dominant accent. Never introduce generic purple-blue AI gradients.

### Typography

- Display and reading headings: `Noto Serif SC Variable`, then the existing Song-style fallbacks.
- UI, forms, navigation, and body copy: `Noto Sans SC Variable`, then system sans fallbacks.
- Use the serif face for hierarchy, conclusions, and report reading—not every label.
- Use tabular numerals for dates, prices, time, order state, and chart data.
- Avoid fake calligraphy, excessive letter spacing in Chinese, and tiny low-contrast captions.

### Layout

- Mobile first from 360px; all purchase and reading flows must remain complete on mobile.
- Public pages may use asymmetry, large type, full-bleed dark sections, and spacious scene cards.
- Private application pages prioritize the task and result; decoration must not compete with inputs or evidence.
- Desktop reading pages may use navigation / main reading / evidence columns, but must collapse explicitly on mobile.
- Cards exist only when they express a real grouping or hierarchy. Prefer whitespace, dividers, and section contrast over nested cards.

### Imagery and symbols

- Domain imagery may draw from celestial cycles, time rings, ink lines, paper, seals, trigrams, and archival notation.
- Use abstract, original compositions rather than literal dragons, temples, flames, fortune tellers, or wallpaper made from repeated bagua symbols.
- Lucide is for functional controls only. Important命理 concepts use custom, reviewed symbols or typography.
- Emoji must not be used as interface icons.

## 4. Component and library contract

- Styling owner: semantic CSS variables plus CSS Modules.
- Accessible interaction primitives: `radix-ui`.
- JavaScript motion: `motion`, imported from `motion/react`.
- Functional icons: `lucide-react`.
- Conditional class composition: `clsx`.
- Forms: `react-hook-form` plus `zod` and `@hookform/resolvers`.
- Chinese type: `@fontsource-variable/noto-sans-sc` and `@fontsource-variable/noto-serif-sc`.

Do not introduce Tailwind, shadcn runtime, MUI, Ant Design, another primitive system, GSAP, Lenis, Lottie, or a second motion library without an explicit design/architecture decision. shadcn/ui may be used as a component-structure reference, but copied components must be restyled through this system and use only one primitive owner per interaction.

## 5. Motion language

Motion should suggest **time becoming legible**, not spectacle.

### Approved patterns

- Page/section entrance: opacity plus `translateY(8px–12px)`, 400–550ms, ease-out.
- Related-item stagger: 60–90ms, capped at 5 visible items.
- Button and card feedback: 160–200ms; at most 2px lift or a very small press scale.
- Result reveal: 240–360ms per meaningful block, conclusion first, then evidence and boundaries.
- Dialog and mobile sheet: spring motion with low bounce; focus behavior remains owned by Radix.
- Optional ambient time/astrolabe ring: 8–12s, transform/opacity only, non-blocking, paused off-screen.

### Forbidden patterns

- scroll hijacking, mandatory parallax, cursor followers, autoplay sound, or motion that delays reading;
- continuous blur, glow, gradient, or large-image animation;
- bouncing payment, privacy, destructive, or error controls;
- animating width, height, top, left, margin, or padding when transform/opacity can express the same change;
- adding animation to every section merely because the library is available.

Every non-essential animation must honor `prefers-reduced-motion`. With reduced motion enabled, content appears immediately and no information may be lost.

## 6. Accessibility and trust floor

- Interactive targets are at least 44×44px.
- Body text contrast targets WCAG AA; focus indicators remain clearly visible.
- Do not communicate certainty, payment state, error state, or verification state using color alone.
- Forms always have visible labels, nearby helper/error text, and keyboard-complete interaction.
- Dialogs, popovers, select controls, and tabs use tested primitives rather than hand-built focus management.
- Loading, empty, error, pending-payment, generation, and reduced-motion states are part of the component definition.

## 7. Required design workflow

1. Read this file and the relevant product contract before changing UI.
2. For a new surface or major redesign, invoke `ui-ux-pro-max`, then use `impeccable` to shape or critique the direction.
3. Implement with the existing tokens and approved component owners.
4. For any motion work, invoke `fixing-motion-performance` before considering the work complete.
5. Before handoff, invoke `web-design-guidelines` and `fixing-accessibility`; use `impeccable` for the final audit/polish pass on major surfaces.
6. Verify at 360, 768, 1024, and 1440px, including reduced motion and keyboard navigation.

Change tokens and shared primitives before adding page-local exceptions. If a new visual rule cannot be expressed through this contract, update this document deliberately instead of silently creating a second design system.
