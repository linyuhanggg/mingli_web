// Design-sync only: pulls the repo-root global style layer (ui/tokens.css +
// ui/base.css) into the exported bundle's CSS.
//
// The app itself loads these through web/src/app/globals.css. cfg.cssEntry
// can't reach them (it is bounded to the package dir, and ui/ lives at the
// repo root), so this module rides in through cfg.extraEntries and lets
// esbuild inline both files into _ds_bundle.css. Exports nothing on purpose.
import "../ui/tokens.css";
import "../ui/base.css";

export {};
