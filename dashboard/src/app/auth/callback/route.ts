import { NextResponse } from "next/server";
import { headers } from "next/headers";
import { createClient } from "@/lib/supabase/server";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const code = searchParams.get("code");

  // Get the correct origin from headers (handles proxy/docker)
  const headersList = await headers();
  const host = headersList.get("x-forwarded-host") || headersList.get("host") || "polymind-dashboard.fly.dev";
  const protocol = headersList.get("x-forwarded-proto") || "https";
  const origin = `${protocol}://${host}`;

  if (code) {
    const supabase = await createClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);

    if (!error) {
      // Check if user has completed onboarding
      const { data: { user } } = await supabase.auth.getUser();
      if (user) {
        const { data: profile } = await supabase
          .from("profiles")
          .select("onboarding_completed")
          .eq("id", user.id)
          .single();

        const redirectTo = profile?.onboarding_completed ? "/" : "/onboarding";
        return NextResponse.redirect(`${origin}${redirectTo}`);
      }
    }
  }

  // Return to login on error
  return NextResponse.redirect(`${origin}/login?error=auth_error`);
}
