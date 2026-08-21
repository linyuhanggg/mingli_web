#!/usr/bin/env node
// stop: if the board still lists actionable work from an active session,
// tell the PM to dispatch the next step instead of waiting for the user.
'use strict';

const fs = require('fs');
const path = require('path');

const BOARD = path.join(process.cwd(), '.cursor', 'team', 'BOARD.md');
const TERMINAL = ['已完成', '阻塞', '已取消'];
const PLACEHOLDER = '—';
// Only nudge while a run is genuinely in flight. Without this, an unrelated
// question hours later would resurrect stale board rows.
const ACTIVE_WINDOW_MS = 30 * 60 * 1000;

function activeRows(board) {
  const section = board.split('## 在办')[1];
  if (!section) return [];
  const table = section.split('## 交接日志')[0];

  return table
    .split('\n')
    .filter((line) => line.trim().startsWith('|'))
    .map((line) => line.split('|').slice(1, -1).map((c) => c.trim()))
    .filter((cells) => cells.length >= 4)
    .filter((cells) => !/^-+$/.test(cells[0]) && cells[0] !== '编号')
    .filter((cells) => cells[0] && cells[0] !== PLACEHOLDER)
    .filter((cells) => !TERMINAL.includes(cells[3]));
}

function main() {
  if (!fs.existsSync(BOARD)) return {};
  if (Date.now() - fs.statSync(BOARD).mtimeMs > ACTIVE_WINDOW_MS) return {};

  const rows = activeRows(fs.readFileSync(BOARD, 'utf8'));
  if (!rows.length) return {};

  const pending = rows
    .slice(0, 5)
    .map((c) => `${c[0]} ${c[1]}（Owner ${c[2]}，状态 ${c[3]}）`)
    .join('；');

  return {
    followup_message:
      `白板「在办」还有未收尾的刀：${pending}。` +
      '读 `.cursor/team/BOARD.md` 的交接日志末尾，按协议派下一跳或把已完成的行改成「已完成」。' +
      '确实没有可执行的刀了，就把原因写进白板然后停下，不要空转。',
  };
}

let out = {};
try {
  out = main() || {};
} catch {
  out = {};
}
process.stdout.write(JSON.stringify(out));
