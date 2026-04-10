"use client";

import React, { useState, useRef, useEffect, KeyboardEvent } from "react";
import { api, type ChatResponse } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  text: string;
}

interface Props {
  sessionId: string;
  onUpdate: (resp: ChatResponse) => void;
}

export function ChatWindow({ sessionId, onUpdate }: Props) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      text: "Hi! I'm InfraAgent. Describe the Azure infrastructure you'd like to provision and I'll help you generate production-ready Bicep or Terraform code.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [iacLanguage, setIacLanguage] = useState<"bicep" | "terraform">("bicep");
  const [localSession, setLocalSession] = useState(sessionId);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send() {
    const text = input.trim();
    if (!text || loading) return;

    setMessages((m: Message[]) => [...m, { role: "user", text }]);
    setInput("");
    setLoading(true);

    try {
      const resp = await api.chat({
        message: text,
        session_id: localSession || undefined,
        iac_language: iacLanguage,
      });
      if (!localSession) setLocalSession(resp.session_id);
      setMessages((m: Message[]) => [...m, { role: "assistant", text: resp.reply }]);
      onUpdate(resp);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setMessages((m: Message[]) => [...m, { role: "assistant", text: `⚠️ Error: ${msg}` }]);
    } finally {
      setLoading(false);
    }
  }

  function handleKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.map((m: Message, i: number) => (
          <div
            key={i}
            className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-2xl rounded-2xl px-4 py-3 text-sm whitespace-pre-wrap ${
                m.role === "user"
                  ? "bg-blue-600 text-white rounded-br-sm"
                  : "bg-gray-800 text-gray-100 rounded-bl-sm"
              }`}
            >
              {m.text}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-800 rounded-2xl rounded-bl-sm px-4 py-3 text-sm text-gray-400 animate-pulse">
              InfraAgent is thinking…
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-800 bg-gray-900 p-4 flex gap-3 items-end">
        <select
          aria-label="IaC language"
          value={iacLanguage}
          onChange={(e: React.ChangeEvent<HTMLSelectElement>) =>
            setIacLanguage(e.target.value as "bicep" | "terraform")
          }
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="bicep">Bicep</option>
          <option value="terraform">Terraform</option>
        </select>

        <textarea
          value={input}
          onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setInput(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Describe the infrastructure you need…"
          rows={1}
          className="flex-1 bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-sm text-gray-100 placeholder-gray-500 resize-none focus:outline-none focus:ring-1 focus:ring-blue-500"
        />

        <button
          onClick={send}
          disabled={!input.trim() || loading}
          className="px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-sm font-medium transition-colors"
        >
          Send
        </button>
      </div>
    </div>
  );
}

