"use client";

import { useEffect, useState, useRef } from "react";
import { use } from "react";
import { PipelineStatus } from "@/components/PipelineStatus";
import { FileViewer } from "@/components/FileViewer";
import { ApprovalGate } from "@/components/ApprovalGate";
import { api, type PipelineStatusResponse } from "@/lib/api";

export default function PipelinePage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = use(params);
  const [status, setStatus] = useState<PipelineStatusResponse | null>(null);
  const [activeTab, setActiveTab] = useState<"status" | "files" | "plan">("status");
  const intervalRef = useRef<number | null>(null);

  useEffect(() => {
    async function poll() {
      try {
        const s = await api.pipelineStatus(sessionId);
        setStatus(s);
        const stage = s.pipeline_state?.stage ?? "";
        // Stop polling only on true terminal stages
        // pr_created is NOT terminal when deploy is configured
        const isTerminal = ["deployed", "failed"].includes(stage) ||
          (stage === "pr_created" && !s.pipeline_running);
        if (isTerminal) {
          if (intervalRef.current) clearInterval(intervalRef.current);
        }
      } catch (e) {
        console.error(e);
      }
    }
    poll();
    intervalRef.current = setInterval(poll, 3000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [sessionId]);

  const state = status?.pipeline_state;
  const files = state?.codegen_output?.files ?? [];
  const planResult = state?.plan_result;

  return (
    <div className="flex h-[calc(100vh-49px)]">
      {/* Sidebar */}
      <aside className="w-64 border-r border-gray-800 bg-gray-900 flex flex-col">
        <div className="p-4 border-b border-gray-800">
          <p className="text-xs text-gray-500 font-mono truncate">{sessionId}</p>
        </div>
        <nav className="flex flex-col p-3 gap-1">
          {(["status", "files", "plan"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`text-left px-3 py-2 rounded-md text-sm capitalize transition-colors ${
                activeTab === tab
                  ? "bg-blue-600/20 text-blue-400"
                  : "text-gray-400 hover:bg-gray-800"
              }`}
            >
              {tab === "status" && "📊 "}
              {tab === "files" && "📁 "}
              {tab === "plan" && "📋 "}
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
              {tab === "files" && files.length > 0 && (
                <span className="ml-2 text-xs bg-gray-700 rounded px-1">{files.length}</span>
              )}
            </button>
          ))}
        </nav>

        {/* Human Gates */}
        {state && (
          <div className="mt-auto p-3 border-t border-gray-800 flex flex-col gap-2">
            {state.stage === "human_review_code" && (
              <ApprovalGate
                sessionId={sessionId}
                gate="h1"
                label="H1 — Code Review"
                approved={status?.h1_approved ?? null}
              />
            )}
            {state.stage === "human_review_plan" && (
              <ApprovalGate
                sessionId={sessionId}
                gate="h2"
                label="H2 — Plan Review"
                approved={status?.h2_approved ?? null}
              />
            )}
          </div>
        )}
      </aside>

      {/* Main content */}
      <div className="flex-1 overflow-auto p-6">
        {activeTab === "status" && (
          <PipelineStatus state={state} prUrl={state?.pr_url} />
        )}
        {activeTab === "files" && <FileViewer files={files} />}
        {activeTab === "plan" && planResult && (
          <div>
            <h2 className="text-lg font-semibold mb-4">
              Plan Result
              <span className={`ml-3 text-sm font-normal ${planResult.success ? "text-green-400" : "text-red-400"}`}>
                {planResult.success ? "✓ Success" : "✗ Failed"}
              </span>
            </h2>
            {planResult.resources_to_create.length > 0 && (
              <div className="mb-4">
                <p className="text-xs text-green-400 mb-1">+ Create ({planResult.resources_to_create.length})</p>
                <ul className="text-sm font-mono text-gray-300 space-y-0.5">
                  {planResult.resources_to_create.map((r) => <li key={r}>{r}</li>)}
                </ul>
              </div>
            )}
            {planResult.resources_to_update.length > 0 && (
              <div className="mb-4">
                <p className="text-xs text-yellow-400 mb-1">~ Update ({planResult.resources_to_update.length})</p>
                <ul className="text-sm font-mono text-gray-300 space-y-0.5">
                  {planResult.resources_to_update.map((r) => <li key={r}>{r}</li>)}
                </ul>
              </div>
            )}
            {planResult.resources_to_delete.length > 0 && (
              <div className="mb-4">
                <p className="text-xs text-red-400 mb-1">- Delete ({planResult.resources_to_delete.length})</p>
                <ul className="text-sm font-mono text-gray-300 space-y-0.5">
                  {planResult.resources_to_delete.map((r) => <li key={r}>{r}</li>)}
                </ul>
              </div>
            )}
            {planResult.error && (
              <pre className="mt-4 bg-red-950/50 border border-red-800 rounded p-3 text-xs text-red-300 overflow-auto max-h-64">
                {planResult.error}
              </pre>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
