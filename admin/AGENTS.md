# Admin UI working rules

These rules apply to everything under `admin/`.

## Binding context

- Read `../DESIGN.md` before Admin UI work.
- Product scope, route/state inventory, dependencies, progress, and evidence are governed only by `../docs/CHECKLIST.md`.
- Shared terminology is governed by `../CONTEXT.md`; Runtime, Provider, Orchestrator, Guard, and ReadingDocument boundaries are governed by `../docs/MINGLI_V51_WEB_INTEGRATION.md`.
- Qingnang is an information-architecture reference and METIS is a neutral presentation reference. Preserve licenses for adapted MIT presentation code; do not import brand assets, proprietary production code, client-side algorithms, private behavior, or business data.

## Skill routing

- New page, component family, token change, or major redesign: invoke `ui-ux-pro-max` first.
- Shape, critique, typography, or visual polish: invoke `impeccable`.
- JavaScript or CSS motion: invoke `fixing-motion-performance` before completion.
- Forms, dialogs, menus, tabs, controls, and pre-release review: invoke `fixing-accessibility`.
- Final UI review: invoke `web-design-guidelines`.

## Implementation rules

- Import shared semantic tokens from `../ui/tokens.css` in `src/app/globals.css`; keep only Admin-specific global rules there and use CSS Modules for component styling.
- Use the same approved primitive, form, icon, and motion systems as Web; do not introduce a second UI stack.
- Staff RBAC is enforced by the server. Hidden controls never substitute for an explicit forbidden/read-only state.
- Authorized staff see complete business information without masking; passwords, hashes, OTPs, cookies, tokens, keys, prompts, and system secrets never render.
- Preserve 44px targets, visible focus, reduced motion, semantic HTML, and every loading/empty/error/forbidden/conflict/audit state in `DESIGN.md`.

## Completion checks

- Run Admin test, typecheck, lint, and build commands that exist for the affected scope; P3-012 must add any missing test gate before integration.
- Verify 360, 768, 1024, and 1440 layouts, keyboard navigation, and `prefers-reduced-motion`.
- Record real-browser evidence for every affected route/state. DOM presence, CSS regexes, unit tests, or a checked checklist item cannot establish UI completion; user acceptance is required by `../docs/CHECKLIST.md`.

<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
