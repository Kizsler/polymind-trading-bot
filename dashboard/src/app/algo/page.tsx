"use client";

import { ThreeColumnLayout } from "@/components/layouts/three-column-layout";
import { Card, CardContent } from "@/components/ui/card";
import {
  Home,
  ChevronRight,
  Brain,
} from "lucide-react";

export default function AlgoPage() {
  return (
    <ThreeColumnLayout>
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-muted-foreground mb-8 animate-fade-in">
        <Home className="h-4 w-4" />
        <ChevronRight className="h-4 w-4" />
        <span className="text-foreground">Algo</span>
      </div>

      {/* Title */}
      <div className="mb-8 animate-fade-in stagger-1">
        <h1 className="text-2xl font-display font-bold flex items-center gap-3">
          <Brain className="h-6 w-6 text-violet-400" />
          AI Decision Engine
        </h1>
        <p className="text-muted-foreground mt-1">
          Claude-powered trade analysis and execution decisions
        </p>
      </div>

      {/* Coming Soon */}
      <Card className="glass border-border animate-fade-in stagger-2">
        <CardContent className="py-16">
          <div className="text-center">
            <Brain className="h-16 w-16 mx-auto mb-6 text-violet-400 opacity-50" />
            <h2 className="text-2xl font-display font-bold text-muted-foreground mb-2">
              Coming Soon
            </h2>
            <p className="text-muted-foreground">
              Contact <span className="text-violet-400 font-medium">@Kizsler</span> for testing
            </p>
          </div>
        </CardContent>
      </Card>
    </ThreeColumnLayout>
  );
}
