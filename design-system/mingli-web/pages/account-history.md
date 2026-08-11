# Account / History / OTP — Surface Override

**Routes:** `/account`, `/app/readings`, `/app/profiles`  
**Mode:** Operate  
**World:** Eastern Editorial Archive

## Motion thesis

- Account paper + rail enter once; OTP shell and status messages enter on phase change.
- History and profile lists stagger lightly (cap ~0.3s) then stay still.
- Row hover is 2px translateX only; selected login method uses ink fill, locked method stays dashed.
- No fake payment motion; no continuous loaders beyond status-panel icon pulse.

## Rules

- Preserve honest signed-out / loading / error states from API.
- 48px inputs, 44px targets, reduced-motion off for all entrances.
