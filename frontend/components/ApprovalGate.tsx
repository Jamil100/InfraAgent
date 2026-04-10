"use client";

import { useState } from "react";
import { api } from "@/lib/api";

interface Props {
  sessionId: string;
  gate: "h1" | "h2";
  label: string;
  approved: boolean | null;
}

export function ApprovalGate({ sessionId, gate, label, approved }: Props) {
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(approved !== null);

  if (done) {
    return (
      <div className="rounded-lg border border-gray-700 p-3 text-xs">
        <p className="font-medium text-gray-300">{label}</p>
        <p className={`mt-1 ${approved ? "text-green-400" : "text-red-400"}`}>
          {approved ? "✓ Approved" : "✗ Rejected"}
        </p>
      </div>
    );
  }

  async function submit(isApproved: boolean) {
    setSubmitting(true);
    try {
      const fn = gate === "h1" ? api.approveH1 : api.approveH2;
      await fn({ session_id: sessionId, approved: isApproved, comment });
      setDone(true);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="rounded-lg border border-yellow-700 bg-yellow-950/20 p-3">
      <p className="text-xs font-semibold text-yellow-300 mb-2">{label}</p>
      <p className="text-xs text-gray-400 mb-2">Review required before continuing.</p>
      <textarea
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        placeholder="Optional comment…"
        rows={2}
        className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1 text-xs text-gray-300 resize-none focus:outline-none focus:ring-1 focus:ring-blue-500 mb-2"
      />
      <div className="flex gap-2">
        <button
          onClick={() => submit(true)}
          disabled={submitting}
          className="flex-1 py-1.5 rounded bg-green-700 hover:bg-green-600 disabled:opacity-50 text-xs font-medium transition-colors"
        >
          Approve
        </button>
        <button
          onClick={() => submit(false)}
          disabled={submitting}
          className="flex-1 py-1.5 rounded bg-red-800 hover:bg-red-700 disabled:opacity-50 text-xs font-medium transition-colors"
        >
          Reject
        </button>
      </div>
    </div>
  );
}
