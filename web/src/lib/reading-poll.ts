const TERMINAL_WITHOUT_POLL = new Set([
  "accepted",
  "waiting_input",
  "terminal_stopped",
  "runtime_unknown",
  "delayed",
]);

export function shouldKeepPolling(summary: {
  status: string;
  poll_required?: boolean | null;
}): boolean {
  if (summary.poll_required === false) {
    return false;
  }
  return !TERMINAL_WITHOUT_POLL.has(summary.status);
}
