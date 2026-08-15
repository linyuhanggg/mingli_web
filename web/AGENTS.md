# Web UI working rules

These rules apply to everything under `web/`.

## Binding context

- Read `../DESIGN.md` before UI work.
- Product scope, route/state inventory, dependencies, progress, and evidence are governed only by `../docs/CHECKLIST.md`.
- Shared terminology is governed by `../CONTEXT.md`; Runtime, Provider, Orchestrator, and ReadingDocument boundaries are governed by `../docs/MINGLI_V51_WEB_INTEGRATION.md`.
- Qingnang is a product-mode and information-architecture reference. METIS is the neutral component, task-shell, and workbench reference. MIT-licensed presentation code may be adapted with its license preserved; do not import either site's brand assets, proprietary production code, business data, client-side algorithms, or private behavior.

## Skill routing

- New page, component family, token change, or major redesign: invoke `ui-ux-pro-max` first.
- Shape, critique, visual refinement, typography, or final polish: invoke `impeccable`.
- Any JavaScript or CSS motion: invoke `fixing-motion-performance` before completion.
- Forms, dialogs, menus, tabs, controls, and pre-release review: invoke `fixing-accessibility`.
- Final UI code review: invoke `web-design-guidelines`.

Do not invoke design Skills for backend-only or non-visual changes.

## Implementation rules

- Import the shared semantic-token source from `../ui/tokens.css` in `src/app/globals.css`; keep only Web-specific global rules there and use CSS Modules for component styling.
- Use `radix-ui` for complex keyboard/focus interactions and do not mix primitive systems in one surface.
- Use only `motion/react` for JavaScript animation. Prefer CSS for simple transform/opacity transitions.
- Use Lucide only for functional icons; use reviewed custom marks for domain-specific命理 imagery.
- Use React Hook Form + Zod for multi-step input and validation.
- Do not add Tailwind, MUI, Ant Design, GSAP, Lenis, Lottie, or another motion/primitive library without updating `../DESIGN.md` and recording the reason.
- Preserve 44px targets, visible focus, reduced motion, semantic HTML, and complete loading/empty/error states.

## Completion checks

- Run `npm test`, `npm run typecheck`, `npm run lint`, and `npm run build` as applicable.
- Verify 360, 768, 1024, and 1440px layouts.
- Test keyboard navigation and `prefers-reduced-motion` for interactive or animated work.
- Record real-browser evidence for every affected route/state. DOM presence, CSS regexes, unit tests, or a checked checklist item cannot by themselves establish UI completion; user acceptance is required by `../docs/CHECKLIST.md`.

<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
