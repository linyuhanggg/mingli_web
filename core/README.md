# Mingli Core workspace

`core/mingli-master/` is the visible, NAS-syncable source checkout for the
independent `mingli-master` module. It owns its own Git history and remote; the
parent `mingli_web` repository intentionally ignores that directory.

The two directories have different jobs:

- `core/mingli-master/`: edit, review, test, and commit core source here.
- `.runtime/v53-time-check-release/`: signed local Runtime Release consumed by
  the one-shot Adapter. Treat it as generated installation output, not source.

Run `make mingli-core-status` from the website root to confirm that the source
checkout exists and that the installed Runtime has not drifted from its managed
source files. Runtime publication still uses the core repository's release gate;
copying files into `.runtime` by hand is not a release.
