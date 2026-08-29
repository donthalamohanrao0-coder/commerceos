"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, apiUpload } from "@/lib/api";
import type {
  ActivityDetail,
  ActivitySession,
  AgentApiKey,
  AuditEvent,
  ConsoleAnalytics,
  ConsoleApproval,
  ConsoleCampaign,
  ConsoleCustomer,
  ConsoleMetrics,
  ConsoleOrder,
  ConsolePayment,
  ConsoleProduct,
  ConsoleSettings,
  IssuedAgentKey,
  KnowledgeList,
  KnowledgePreview,
} from "@/lib/types";

export function useMetrics() {
  return useQuery({
    queryKey: ["console", "metrics"],
    queryFn: () => api<ConsoleMetrics>("/console/metrics"),
  });
}

export function useAnalytics(days = 45) {
  return useQuery({
    queryKey: ["console", "analytics", days],
    queryFn: () => api<ConsoleAnalytics>(`/console/analytics?days=${days}`),
  });
}

export function useActivity() {
  return useQuery({
    queryKey: ["console", "activity"],
    queryFn: () => api<{ sessions: ActivitySession[] }>("/console/activity?limit=50"),
    refetchInterval: 10_000,
  });
}

export function useActivityDetail(sessionId: string | null) {
  return useQuery({
    queryKey: ["console", "activity", sessionId],
    queryFn: () => api<ActivityDetail>(`/console/activity/${sessionId}`),
    enabled: !!sessionId,
  });
}

export function useApprovals() {
  return useQuery({
    queryKey: ["console", "approvals"],
    queryFn: () => api<{ approvals: ConsoleApproval[] }>("/console/approvals?status=pending"),
    refetchInterval: 8_000,
  });
}

export function useAudit() {
  return useQuery({
    queryKey: ["console", "audit"],
    queryFn: () => api<{ events: AuditEvent[] }>("/console/audit?limit=40"),
  });
}

export function useProducts() {
  return useQuery({
    queryKey: ["console", "products"],
    queryFn: () => api<{ products: ConsoleProduct[] }>("/console/products"),
  });
}

export function useCustomers() {
  return useQuery({
    queryKey: ["console", "customers"],
    queryFn: () => api<{ customers: ConsoleCustomer[] }>("/console/customers"),
  });
}

export function useOrders() {
  return useQuery({
    queryKey: ["console", "orders"],
    queryFn: () => api<{ orders: ConsoleOrder[] }>("/console/orders"),
  });
}

export function usePayments() {
  return useQuery({
    queryKey: ["console", "payments"],
    queryFn: () => api<{ payments: ConsolePayment[] }>("/console/payments"),
  });
}

export function useReconcilePayment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (paymentId: string) =>
      api<{ payment_id: string; status: string; action: string; provider_status?: string }>(
        `/console/payments/${paymentId}/reconcile`,
        { method: "POST" },
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["console", "payments"] }),
  });
}

export function useCampaigns() {
  return useQuery({
    queryKey: ["console", "campaigns"],
    queryFn: () => api<{ campaigns: ConsoleCampaign[] }>("/console/campaigns"),
  });
}

export function useSettings() {
  return useQuery({
    queryKey: ["console", "settings"],
    queryFn: () => api<ConsoleSettings>("/console/settings"),
  });
}

export function useKnowledge() {
  return useQuery({
    queryKey: ["console", "knowledge"],
    queryFn: () => api<KnowledgeList>("/console/knowledge"),
  });
}

export function useKnowledgePreview() {
  return useMutation({
    mutationFn: (body: { query: string; document_type?: string | null }) =>
      api<KnowledgePreview>("/console/knowledge/preview", { method: "POST", body }),
  });
}

export function useUploadKnowledge() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { file: File; title: string; documentType: string }) => {
      const fd = new FormData();
      fd.append("file", input.file);
      fd.append("title", input.title);
      fd.append("document_type", input.documentType);
      return apiUpload<{
        document_id: string;
        chunk_count: number;
        version_number: number;
      }>("/console/knowledge", fd);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["console", "knowledge"] }),
  });
}

// ---- catalog + campaign mutations ------------------------------------------

export interface ProductInput {
  name: string;
  category: string;
  brand?: string | null;
  description?: string | null;
  price_paise: number;
  compare_at_price_paise?: number | null;
  tags?: string[];
  stock?: number;
}

export function useCreateProduct() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ProductInput) =>
      api<ConsoleProduct>("/console/products", { method: "POST", body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["console", "products"] }),
  });
}

export function useUpdateProduct() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      patch,
    }: {
      id: string;
      patch: Partial<ProductInput> & { status?: string };
    }) => api<ConsoleProduct>(`/console/products/${id}`, { method: "PATCH", body: patch }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["console", "products"] }),
  });
}

export function useArchiveProduct() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api(`/console/products/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["console", "products"] }),
  });
}

export function useSetCampaignStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: "active" | "paused" | "archived" }) =>
      api(`/console/campaigns/${id}`, { method: "PATCH", body: { status } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["console", "campaigns"] }),
  });
}

export function useResolveApproval() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      sessionId,
      approvalId,
      approved,
    }: {
      sessionId: string;
      approvalId: string;
      approved: boolean;
    }) =>
      api(`/agent/sessions/${sessionId}/approvals/${approvalId}`, {
        method: "POST",
        body: { approved },
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["console", "approvals"] });
      void qc.invalidateQueries({ queryKey: ["console", "activity"] });
      void qc.invalidateQueries({ queryKey: ["console", "audit"] });
    },
  });
}

export function useAgentKeys() {
  return useQuery({
    queryKey: ["console", "agent-keys"],
    queryFn: () => api<{ keys: AgentApiKey[] }>("/agent-keys"),
  });
}

export function useIssueKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; scopes: string[]; rate_limit_per_minute: number }) =>
      api<IssuedAgentKey>("/agent-keys", { method: "POST", body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["console", "agent-keys"] }),
  });
}

export function useRevokeKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (keyId: string) => api(`/agent-keys/${keyId}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["console", "agent-keys"] }),
  });
}
