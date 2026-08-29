// Shapes returned by the FastAPI backend (unwrapped from the { data, request_id } envelope).

export interface Identity {
  user: { id: string; email: string; role: string };
  merchant: { id: string; merchant_code: string; business_name: string };
}

export interface ToolTraceRow {
  tool: string;
  status: "succeeded" | "failed" | string;
  output: Record<string, unknown> | null;
}

export interface PendingApproval {
  approval_id: string;
  action: string;
  order_id?: string;
}

export interface AgentTurn {
  session_id: string;
  session_status: string;
  assistant: string;
  pending_approval: PendingApproval | null;
  tool_trace: ToolTraceRow[];
}

export interface StartSessionResponse {
  session_id: string;
  workflow: string;
  status: string;
}

// ---- catalog / commerce sub-shapes carried inside tool_trace outputs ----

export interface CatalogProduct {
  product_id: string;
  name: string;
  brand: string | null;
  category: string | null;
  price_paise: number;
  rating: number | null;
  tags: string[];
}

export interface OrderSummary {
  order_id: string;
  order_number: string;
  status: string;
  subtotal_paise: number;
  discount_paise: number;
  shipping_paise: number;
  tax_paise: number;
  total_paise: number;
}

export interface SessionCart {
  cart_id: string | null;
  items: {
    name: string;
    category: string | null;
    image_key: string | null;
    quantity: number;
    unit_price_paise: number;
    line_total_paise: number;
  }[];
  item_count: number;
  subtotal_paise: number;
}

export interface KnowledgeResult {
  document_id: string;
  document_type: string;
  heading: string | null;
  text: string;
  score: number;
}

// ---- merchant console ----

export interface ConsoleMetrics {
  revenue_paise: number;
  order_count: number;
  paid_order_count: number;
  aov_paise: number;
  top_products: {
    product_id: string;
    name: string;
    category: string;
    units_sold: number;
    revenue_paise: number;
  }[];
  cross_sell_pairs: {
    a_name: string;
    b_name: string;
    co_occurrence: number;
    attach_rate: number;
  }[];
  category_revenue: { category: string; revenue_paise: number }[];
}

export interface ConsoleAnalytics {
  window_days: number;
  summary: {
    revenue_paise: number;
    order_count: number;
    paid_order_count: number;
    aov_paise: number;
  };
  timeseries: { date: string; orders: number; revenue_paise: number }[];
  sources: { source: string; orders: number; revenue_paise: number }[];
  statuses: { status: string; count: number }[];
  category_revenue: { category: string; revenue_paise: number }[];
  top_products: { name: string; units: number; revenue_paise: number }[];
}

export interface ActivitySession {
  session_id: string;
  workflow: string;
  status: string;
  channel: string;
  started_at: string;
  ended_at: string | null;
  message_count: number;
  action_count: number;
}

export interface ActivityAction {
  node_name: string;
  tool_name: string | null;
  status: string;
  input: Record<string, unknown>;
  output: Record<string, unknown> | null;
  policy_decision: Record<string, unknown> | null;
  duration_ms: number | null;
  created_at: string;
}

export interface ActivityMessage {
  role: string;
  content_type: string;
  content: Record<string, unknown>;
  created_at: string;
}

export interface ActivityDetail {
  session: {
    session_id: string;
    workflow: string;
    status: string;
    channel: string;
    started_at: string;
  } | null;
  messages: ActivityMessage[];
  actions: ActivityAction[];
}

export interface ConsoleApproval {
  approval_id: string;
  session_id: string | null;
  workflow: string | null;
  requested_action: string;
  requested_by: string;
  status: string;
  payload: Record<string, unknown>;
  created_at: string;
  expires_at: string | null;
  order: {
    order_id: string;
    order_number: string;
    total_paise: number;
    discount_paise: number;
    status: string;
  } | null;
}

export interface AuditEvent {
  id: string;
  actor_type: string;
  actor_id: string | null;
  action: string;
  session_id: string | null;
  order_id: string | null;
  policy_decision: Record<string, unknown> | null;
  created_at: string;
}

export interface ConsoleProduct {
  id: string;
  sku: string;
  name: string;
  category: string;
  brand: string | null;
  description: string | null;
  price_paise: number;
  compare_at_price_paise: number | null;
  rating: number | null;
  review_count: number;
  image_key: string | null;
  tags: string[];
  status: string;
}

export interface ConsoleCustomer {
  id: string;
  name: string;
  email: string | null;
  city: string | null;
  segment: string | null;
  lifetime_value_paise: number;
  orders_count: number;
  preferred_categories: string[];
}

export interface ConsoleOrder {
  id: string;
  order_number: string;
  status: string;
  source: string;
  subtotal_paise: number;
  discount_paise: number;
  shipping_paise: number;
  tax_paise: number;
  total_paise: number;
  item_count: number;
  created_at: string;
}

export interface ConsolePayment {
  id: string;
  order_number: string | null;
  status: string;
  amount_paise: number;
  currency: string;
  provider: string;
  provider_order_id: string | null;
  provider_payment_id: string | null;
  signature_verified: boolean;
  failure_reason: string | null;
  payment_link_url: string | null;
  created_at: string;
}

export interface ConsoleCampaign {
  id: string;
  name: string;
  external_campaign_code: string;
  status: string;
  discount_type: string;
  discount_percent: number | null;
  discount_fixed_paise: number | null;
  max_discount_paise: number | null;
  requires_merchant_approval: boolean;
  created_at: string;
}

export interface ConsoleSettings {
  merchant: {
    id: string;
    merchant_code: string;
    business_name: string;
    legal_name: string | null;
    currency: string;
    country: string;
    timezone: string;
    gst_percent: number;
    prices_tax_inclusive: boolean;
    status: string;
  } | null;
  policies: { key: string; value: unknown }[];
}

export interface AgentApiKey {
  key_id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  status: string;
  rate_limit_per_minute: number;
  last_used_at: string | null;
}

export interface IssuedAgentKey {
  key_id: string;
  api_key: string;
  key_prefix: string;
  scopes: string[];
  rate_limit_per_minute: number;
  grantable_scopes: string[];
}

export interface KnowledgeDocument {
  id: string;
  title: string;
  document_type: string;
  status: string;
  source_path: string;
  version_number: number | null;
  chunk_count: number;
  namespace: string | null;
  indexed_at: string | null;
}

export interface KnowledgeList {
  documents: KnowledgeDocument[];
  summary: {
    document_count: number;
    indexed_count: number;
    chunk_count: number;
    retrieval_calls: number;
  };
}

export interface KnowledgeChunk {
  document_id: string;
  document_type: string;
  heading: string;
  text: string;
  score: number;
  source_path: string;
}

export interface KnowledgePreview {
  query: string;
  results: KnowledgeChunk[];
}
