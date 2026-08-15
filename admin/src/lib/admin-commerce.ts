export type AdminCommerceKind = "orders" | "payments" | "refunds";

export type AdminOrder = {
  id: string;
  owner_user_id: string;
  product_version_id: string;
  purchase_target_ref: string;
  amount_minor: number;
  currency: string;
  status: string;
  fulfillment_status: string | null;
  created_at: string;
  paid_at: string | null;
};

export type AdminPayment = {
  id: string;
  order_id: string;
  channel: string;
  channel_transaction_id: string;
  amount_minor: number;
  currency: string;
  status: string;
  confirmed_at: string;
};

export type AdminRefund = {
  id: string;
  payment_id: string;
  order_id: string;
  channel: string;
  channel_refund_id: string | null;
  amount_minor: number;
  currency: string;
  reason: string;
  status: string;
  created_at: string;
  confirmed_at: string | null;
  referral_confirmation_id: string | null;
  referral_confirmation_policy_version: string | null;
  referral_confirmation_at: string | null;
};

export type AdminOrdersResponse = { orders: readonly AdminOrder[] };
export type AdminPaymentsResponse = { payments: readonly AdminPayment[] };
export type AdminRefundsResponse = { refunds: readonly AdminRefund[] };
export type AdminCommerceResponse =
  | AdminOrdersResponse
  | AdminPaymentsResponse
  | AdminRefundsResponse;
