export type AdminReconciliationItem = {
  id: string;
  kind: "payment" | "refund";
  reference: string;
  payment_id: string | null;
  refund_id: string | null;
  local_status: string | null;
  provider_status: string | null;
  local_amount_minor: number | null;
  provider_amount_minor: number | null;
  local_currency: string | null;
  provider_currency: string | null;
  discrepancy: string;
  created_at: string;
};

export type AdminReconciliationRun = {
  id: string;
  channel: string;
  run_at: string;
  status: string;
  item_count: number;
  matched_count: number;
  difference_count: number;
  created_at: string;
  items: readonly AdminReconciliationItem[];
};

export type AdminReconciliationResponse = {
  runs: readonly AdminReconciliationRun[];
};

export type AdminReconciliationPaymentDraft = {
  transaction_id: string;
  status: "pending" | "succeeded" | "failed" | "refunded";
  amount_minor: string;
  currency: string;
};

export type AdminReconciliationRefundDraft = {
  refund_id: string;
  payment_transaction_id: string;
  status: "pending" | "succeeded" | "failed";
  amount_minor: string;
  currency: string;
};
