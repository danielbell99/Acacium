export type DocumentScope = {
  title: string;
  first_physical_page: number;
  last_physical_page: number;
  page_count: number;
  reporting_period: string;
  layout: string;
};

export type SourceDocument = {
  id: string;
  organisation: string;
  meeting_date: string;
  filename: string;
  source_url: string;
  page_count: number;
  scope: DocumentScope;
};

export type Evidence = {
  document_id: string;
  filename: string;
  physical_page: number;
  excerpt: string;
  scope_title: string;
};

export type Signal = {
  id: string;
  organisation: string;
  category: string;
  service: string;
  source_fact: string;
  interpretation: string;
  reporting_period: string | null;
  score: number;
  score_reasons: string[];
  proposed_next_action: string;
  evidence: Evidence;
  review_status: "pending" | "approved" | "rejected";
  review_reason: string | null;
  caveats: string[];
};

export type Run = {
  id: string;
  status:
    "queued" | "running" | "completed" | "completed_with_errors" | "failed";
  created_at: string;
  completed_at: string | null;
  document_ids: string[];
  progress: {
    selected_pages: number;
    processed_pages: number;
    candidates_found: number;
  };
  as_of_date: string;
  rubric_version: string;
  source_manifest_version: string;
  service_catalogue_version: string;
  error: string | null;
};

type DocumentResponse = {
  documents: SourceDocument[];
  selected_report_page_count: number;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  documents: () => request<DocumentResponse>("/api/documents"),
  signals: () => request<Signal[]>("/api/signals"),
  jobs: () => request<Run[]>("/api/jobs"),
  startRun: (documentIds: string[]) =>
    request<Run>("/api/jobs", {
      method: "POST",
      body: JSON.stringify({ document_ids: documentIds }),
    }),
  reviewSignal: (
    signalId: string,
    decision: "approved" | "rejected",
    reason: string,
  ) =>
    request<Signal>(`/api/signals/${signalId}/review`, {
      method: "POST",
      body: JSON.stringify({
        decision,
        reason,
      }),
    }),
};
