"use client";

import { ReactNode } from "react";
import { Sidebar } from "@/components/sidebar-new";
import { StatusPanel } from "@/components/status-panel";

interface ThreeColumnLayoutProps {
  children: ReactNode;
}

export function ThreeColumnLayout({ children }: ThreeColumnLayoutProps) {
  return (
    <div className="flex h-screen bg-background bg-grid overflow-hidden">
      {/* Left Sidebar - Navigation */}
      <Sidebar />

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        <div className="p-6 lg:p-8">
          {children}
        </div>
      </main>

      {/* Right Sidebar - Status Panel */}
      <StatusPanel />
    </div>
  );
}
