"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ChatWindow } from "@/components/ChatWindow";
import { api, type ChatResponse } from "@/lib/api";

export default function HomePage() {
  const router = useRouter();
  const [sessionId, setSessionId] = useState("");
  const [requirementsReady, setRequirementsReady] = useState(false);
  const [launching, setLaunching] = useState(false);

  function handleChatUpdate(resp: ChatResponse) {
    if (!sessionId) setSessionId(resp.session_id);
    if (resp.requirements_ready) setRequirementsReady(true);
  }

  async function launchPipeline() {
    if (!sessionId) return;
    setLaunching(true);
    try {
      await api.startPipeline(sessionId);
      router.push(`/pipeline/${sessionId}`);
    } finally {
      setLaunching(false);
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-49px)]">
      <div className="flex-1 overflow-hidden">
        <ChatWindow
          sessionId={sessionId}
          onUpdate={handleChatUpdate}
        />
      </div>

      {requirementsReady && (
        <div className="border-t border-gray-800 bg-gray-900 p-4 flex items-center gap-4">
          <p className="text-sm text-green-400 flex-1">
            ✓ Requirements captured — ready to generate infrastructure
          </p>
          <button
            onClick={launchPipeline}
            disabled={launching}
            className="px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-sm font-medium transition-colors"
          >
            {launching ? "Launching…" : "Generate Infrastructure →"}
          </button>
        </div>
      )}
    </div>
  );
}
