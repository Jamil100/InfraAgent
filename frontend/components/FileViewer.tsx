"use client";

import { useState } from "react";

interface File {
  path: string;
  content: string;
}

interface Props {
  files: File[];
}

export function FileViewer({ files }: Props) {
  const [selected, setSelected] = useState<string>(files[0]?.path ?? "");

  if (files.length === 0) {
    return <p className="text-sm text-gray-500">No files generated yet.</p>;
  }

  const current = files.find((f) => f.path === selected);

  return (
    <div className="flex h-full gap-4">
      {/* File tree */}
      <aside className="w-48 flex-shrink-0">
        <p className="text-xs text-gray-500 mb-2 font-semibold uppercase tracking-wide">Generated Files</p>
        <ul className="space-y-0.5">
          {files.map((f) => (
            <li key={f.path}>
              <button
                onClick={() => setSelected(f.path)}
                className={`w-full text-left text-xs font-mono px-2 py-1 rounded truncate transition-colors ${
                  selected === f.path
                    ? "bg-blue-600/20 text-blue-300"
                    : "text-gray-400 hover:bg-gray-800"
                }`}
              >
                {f.path}
              </button>
            </li>
          ))}
        </ul>
      </aside>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        <div className="flex items-center justify-between mb-2">
          <p className="text-xs font-mono text-gray-400">{selected}</p>
          <button
            onClick={() => navigator.clipboard.writeText(current?.content ?? "")}
            className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
          >
            Copy
          </button>
        </div>
        <pre className="bg-gray-900 border border-gray-800 rounded-xl p-4 text-xs text-gray-200 font-mono overflow-auto whitespace-pre-wrap">
          {current?.content ?? ""}
        </pre>
      </div>
    </div>
  );
}
