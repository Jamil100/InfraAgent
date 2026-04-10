// API base — in dev Next.js rewrites /api/* to the FastAPI backend
const BASE = "";

// ---- Types ---------------------------------------------------------------

export interface ChatRequest {
  message: string;
  session_id?: string;
  iac_language?: "bicep" | "terraform";
}

export interface ChatResponse {
  session_id: string;
  reply: string;
  stage: string;
  requirements_ready: boolean;
}

export interface PipelineStartResponse {
  session_id: string;
  status: string;
  message: string;
}

export interface PipelineStatusResponse {
  session_id: string;
  has_requirements: boolean;
  pipeline_running: boolean;
  h1_approved: boolean | null;
  h2_approved: boolean | null;
  pipeline_state: PipelineState | null;
}

export interface PipelineState {
  session_id: string;
  stage: string;
  loop1_iteration: number;
  loop2_iteration: number;
  pr_url: string;
  error: string;
  validation_findings: ValidationFinding[];
  codegen_output?: {
    files: { path: string; content: string }[];
    mermaid_diagram: string;
    explanation: string;
  };
  plan_result?: {
    success: boolean;
    output: string;
    error: string;
    resources_to_create: string[];
    resources_to_update: string[];
    resources_to_delete: string[];
  };
}

export interface ValidationFinding {
  checker: string;
  severity: "error" | "warning" | "info";
  resource?: string;
  file?: string;
  line?: number;
  message: string;
  remediation?: string;
}

export interface ApprovalRequest {
  session_id: string;
  approved: boolean;
  comment?: string;
}

// ---- Helpers -------------------------------------------------------------

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

// ---- API calls -----------------------------------------------------------

export const api = {
  chat: (req: ChatRequest) =>
    post<ChatResponse>("/api/chat", req),

  startPipeline: (sessionId: string) =>
    post<PipelineStartResponse>("/api/pipeline/start", { session_id: sessionId }),

  approveH1: (req: ApprovalRequest) =>
    post<{ session_id: string; gate: string; approved: boolean }>("/api/pipeline/approve/h1", req),

  approveH2: (req: ApprovalRequest) =>
    post<{ session_id: string; gate: string; approved: boolean }>("/api/pipeline/approve/h2", req),

  pipelineStatus: (sessionId: string) =>
    get<PipelineStatusResponse>(`/api/pipeline/status/${sessionId}`),
};
