"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Users,
  Brain,
  BarChart3,
  GitCompare,
  TrendingUp,
  Settings,
  Zap,
} from "lucide-react";

const navItems = [
  {
    label: "Overview",
    items: [
      { name: "Dashboard", href: "/", icon: LayoutDashboard },
      { name: "Copy Trading", href: "/wallets", icon: Users },
      { name: "Algo", href: "/algo", icon: Brain },
      { name: "Analyze", href: "/analyze", icon: BarChart3 },
      { name: "Arbitrage", href: "/arbitrage", icon: GitCompare },
    ]
  },
  {
    label: "Activity",
    items: [
      { name: "Live Activity", href: "/activity", icon: Zap },
      { name: "Markets", href: "/markets", icon: TrendingUp },
    ]
  },
];

const bottomItems = [
  { name: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-60 h-screen bg-card/50 border-r border-border flex flex-col">
      {/* Logo & Welcome */}
      <div className="p-6 border-b border-border">
        <h1 className="text-xl font-display font-bold tracking-tight bg-gradient-to-r from-violet-400 to-fuchsia-400 bg-clip-text text-transparent">
          POLYMIND
        </h1>
        <div className="mt-4">
          <p className="text-foreground font-medium">Welcome Back</p>
          <p className="text-xs text-muted-foreground mt-1">
            Last Login: {new Date().toLocaleDateString()}
          </p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-6 overflow-auto">
        {navItems.map((section) => (
          <div key={section.label}>
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3 px-3">
              {section.label}
            </p>
            <ul className="space-y-1">
              {section.items.map((item) => {
                const isActive = pathname === item.href ||
                  (item.href !== "/" && pathname.startsWith(item.href));
                return (
                  <li key={item.name}>
                    <Link
                      href={item.href}
                      className={cn(
                        "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200",
                        isActive
                          ? "bg-violet-500/10 text-violet-400 border-l-2 border-violet-500"
                          : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
                      )}
                    >
                      <item.icon className="h-4 w-4" />
                      {item.name}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      {/* Bottom Items */}
      <div className="p-4 border-t border-border">
        <ul className="space-y-1">
          {bottomItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <li key={item.name}>
                <Link
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200",
                    isActive
                      ? "bg-violet-500/10 text-violet-400"
                      : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
                  )}
                >
                  <item.icon className="h-4 w-4" />
                  {item.name}
                </Link>
              </li>
            );
          })}
        </ul>
      </div>
    </aside>
  );
}
