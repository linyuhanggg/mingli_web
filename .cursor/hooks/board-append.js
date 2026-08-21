#!/usr/bin/env node
// subagentStop: append a compact audit line to the board so the trail stays
// accurate even when a role forgets to write its own handoff record.
'use strict';

const fs = require('fs');
const path = require('path');

const BOARD = path.join(process.cwd(), '.cursor', 'team', 'BOARD.md');
const LOG_HEADING = '## 交接日志';

function readStdin() {
  try {
    return fs.readFileSync(0, 'utf8');
  } catch {
    return '';
  }
}

function stamp() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

function main() {
  const raw = readStdin();
  let input = {};
  try {
    input = JSON.parse(raw || '{}');
  } catch {
    return;
  }

  const role = input.subagent_type || input.subagentType || 'unknown';
  const status = input.status || 'unknown';
  const files = Array.isArray(input.modified_files) ? input.modified_files : [];

  if (!fs.existsSync(BOARD)) return;

  let board = fs.readFileSync(BOARD, 'utf8');
  if (!board.includes(LOG_HEADING)) return;

  const shown = files.slice(0, 6).map((f) => path.relative(process.cwd(), f) || f);
  const more = files.length > shown.length ? ` +${files.length - shown.length}` : '';
  const changed = files.length ? `改动 ${shown.join(', ')}${more}` : '无文件改动';

  board = `${board.replace(/\s*$/, '')}\n\n- \`auto\` ${stamp()} · ${role} · ${status} · ${changed}\n`;
  fs.writeFileSync(BOARD, board);
}

try {
  main();
} catch {
  // Hooks fail open by design; never block a run because logging broke.
}
process.stdout.write('{}');
