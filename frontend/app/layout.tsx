import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "InfraAgent",
  description: "AI-powered Infrastructure as Code generation on Azure AI Foundry",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-950 text-gray-100 antialiased">
        <header className="border-b border-gray-800 bg-gray-900 px-6 py-3 flex items-center gap-3">
          <div className="h-7 w-7 rounded bg-blue-600 flex items-center justify-center text-xs font-bold">IA</div>
          <span className="font-semibold tracking-tight text-white">InfraAgent</span>
          <span className="ml-auto text-xs text-gray-500">Powered by Azure AI Foundry</span>
        </header>
        <main>{children}</main>
      </body>
    </html>
  );
}
