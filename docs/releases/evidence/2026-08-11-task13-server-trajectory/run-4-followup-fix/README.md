# Task13 run-4 follow-up fix evidence

Date: 2026-08-11 (Asia/Shanghai)

Deploy: `6ec1578` on fateradar-prod (`/opt/fateradar/releases/6ec15786ac8ce110bbf698b1c8578518123b1a2a`)

## Result

| track | status |
|---|---|
| guest/login/profile | ok |
| preview | accepted |
| today | accepted |
| week | accepted |
| liuyao | accepted |
| followup | accepted |
| list_scan | ok |

Totals: 5 product accepted / 9 tracks.

## What changed from previous partial runs

- `b104245` closed missing candidate fact/evidence refs before Guard → preview/today/week/liuyao accepted
- `6ec1578` fixed follow-up prepare: use latest Accepted `state_token`, `transition=null`

## Files

- `summary.json`
- `console.log` (status poll only)
- `*-safe.json` (length/prefix only; no cookies/secrets)

Still: production blocked / real traffic disabled.
