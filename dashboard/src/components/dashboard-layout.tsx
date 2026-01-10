"use client";

import { Sidebar } from "./sidebar";

export function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      <main className="ml-64 min-h-screen">
        <div className="grid-pattern fixed inset-0 ml-64 pointer-events-none opacity-30" />
        <div className="relative">
          {children}
        </div>
      </main>
    </div>
  );
}
