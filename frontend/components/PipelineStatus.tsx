"use client";

import type { PipelineState } from "@/lib/api";

const STAGE_ORDER = [
  "consulting",
  "codegen",
  "validation",
  "standards",
  "security",
  "human_review_code",
  "pr_created",
  "plan",
  "human_review_plan",
  "deploying",
  "deployed",
];

const STAGE_LABELS: Record<string, string> = {
  consulting: "Consulting",
  codegen: "Code Generation",
  validation: "IaC Validation",
  standards: "Standards Review",
  security: "Security Scan",
  human_review_code: "H1 — Code Review",
  pr_created: "PR Created",
  plan: "Plan",
  human_review_plan: "H2 — Plan Review",
  deploying: "Deploying",
  deployed: "Deployed ✓",
  failed: "Failed ✗",
};

interface Props {
  state: PipelineState | null | undefined;
  prUrl?: string;
}

export function PipelineStatus({ state, prUrl }: Props) {
  const currentStage = state?.stage ?? "";
  const isFailed = currentStage === "failed";
  const currentIdx = STAGE_ORDER.indexOf(currentStage);

  return (
    <div>
      <h2 className="text-lg font-semibold mb-6">Pipeline Progress</h2>

      <ol className="relative border-l border-gray-700 ml-4 space-y-6">
        {STAGE_ORDER.map((stage, idx) => {
          const done = idx < currentIdx || (currentIdx === idx && !isFailed && currentStage === "deployed");
          const active = idx === currentIdx && !isFailed;

          return (
            <li key={stage} className="ml-6">
              <span
                className={`absolute -left-3 flex h-6 w-6 items-center justify-center rounded-full ring-2 ring-gray-950 text-xs font-bold
                  ${done ? "bg-green-500 text-white" : active ? "bg-blue-500 text-white animate-pulse" : "bg-gray-700 text-gray-500"}`}
              >
                {done ? "✓" : idx + 1}
              </span>
              <p
                className={`text-sm font-medium ${
                  done ? "text-green-400" : active ? "text-blue-300" : "text-gray-500"
                }`}
              >
                {STAGE_LABELS[stage] ?? stage}
              </p>
              {active && stage === "codegen" && state?.loop1_iteration && state.loop1_iteration > 1 && (
                <p className="text-xs text-yellow-400 mt-0.5">Iteration {state.loop1_iteration} / 3</p>
              )}
              {active && stage === "plan" && state?.loop2_iteration && state.loop2_iteration > 1 && (
                <p className="text-xs text-yellow-400 mt-0.5">Rework iteration {state.loop2_iteration} / 2</p>
              )}
            </li>
          );
        })}

        {isFailed && (
          <li className="ml-6">
            <span className="absolute -left-3 flex h-6 w-6 items-center justify-center rounded-full ring-2 ring-gray-950 bg-red-600 text-white text-xs">✗</span>
            <p className="text-sm font-medium text-red-400">Failed</p>
            {state?.error && <p className="text-xs text-red-300 mt-1">{state.error}</p>}
          </li>
        )}
      </ol>

      {/* Findings summary */}
      {(state?.validation_findings?.length ?? 0) > 0 && (
        <div className="mt-8">
          <h3 className="text-sm font-semibold mb-3 text-gray-300">Review Findings</h3>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {state!.validation_findings.map((f, i) => (
              <div
                key={i}
                className={`rounded-lg p-3 text-xs border ${
                  f.severity === "error"
                    ? "bg-red-950/50 border-red-800 text-red-200"
                    : f.severity === "warning"
                    ? "bg-yellow-950/50 border-yellow-800 text-yellow-200"
                    : "bg-gray-800 border-gray-700 text-gray-300"
                }`}
              >
                <span className="font-mono font-bold">[{f.checker}]</span>
                {f.file && <span className="ml-2 text-gray-400">{f.file}{f.line ? `:${f.line}` : ""}</span>}
                <p className="mt-0.5">{f.message}</p>
                {f.remediation && <p className="mt-0.5 opacity-70">{f.remediation}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* PR link */}
      {prUrl && (
        <div className="mt-8 p-4 rounded-xl border border-blue-800 bg-blue-950/30">
          <p className="text-sm font-medium text-blue-300 mb-1">Pull Request Created</p>
          <a href={prUrl} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-400 hover:underline break-all">
            {prUrl}
          </a>
        </div>
      )}
    </div>
  );
}
