"use client";

import { createContext, useContext, useEffect, useState, useRef, ReactNode } from "react";
import { User, Session } from "@supabase/supabase-js";
import { createClient } from "./client";

interface Profile {
  id: string;
  display_name: string | null;
  starting_balance: number;
  copy_percentage: number;
  max_daily_exposure: number;
  max_trades_per_day: number;
  min_account_balance: number;
  ai_enabled: boolean;
  confidence_threshold: number;
  auto_trade: boolean;
  bot_status: "running" | "paused" | "stopped";
  onboarding_completed: boolean;
}

interface AuthContextType {
  user: User | null;
  profile: Profile | null;
  loading: boolean;
  signOut: () => Promise<void>;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  profile: null,
  loading: true,
  signOut: async () => {},
  refreshProfile: async () => {},
});

// Get singleton client outside component
const supabase = createClient();

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const initRef = useRef(false);

  const refreshProfile = async () => {
    const { data: { user } } = await supabase.auth.getUser();
    if (user) {
      const { data } = await supabase
        .from("profiles")
        .select("*")
        .eq("id", user.id)
        .single();
      setProfile(data);
    }
  };

  useEffect(() => {
    // Prevent double init in React strict mode
    if (initRef.current) return;
    initRef.current = true;

    let cancelled = false;

    // Safety timeout - if loading takes more than 8 seconds, force completion
    const safetyTimeout = setTimeout(() => {
      if (!cancelled) {
        console.warn("Auth loading timeout - forcing completion");
        setLoading(false);
      }
    }, 8000);

    const init = async () => {
      console.log("Auth init starting...");
      try {
        const { data: { user }, error: authError } = await supabase.auth.getUser();

        console.log("Auth getUser result:", user?.email, authError?.message);

        if (cancelled) return;

        setUser(user ?? null);

        if (user) {
          const { data, error: profileError } = await supabase
            .from("profiles")
            .select("*")
            .eq("id", user.id)
            .single();

          console.log("Profile fetch result:", data?.id, profileError?.message);

          if (!cancelled) {
            setProfile(data ?? null);
          }
        }
      } catch (err) {
        console.error("Auth init error:", err);
      } finally {
        if (!cancelled) {
          console.log("Auth init complete");
          clearTimeout(safetyTimeout);
          setLoading(false);
        }
      }
    };

    init();

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event: string, session: Session | null) => {
        if (cancelled) return;

        console.log("Auth state change:", event, session?.user?.email);

        setUser(session?.user ?? null);

        if (session?.user) {
          const { data } = await supabase
            .from("profiles")
            .select("*")
            .eq("id", session.user.id)
            .single();

          if (!cancelled) {
            setProfile(data ?? null);
          }
        } else {
          setProfile(null);
        }

        if (!cancelled) {
          setLoading(false);
        }
      }
    );

    return () => {
      cancelled = true;
      clearTimeout(safetyTimeout);
      subscription.unsubscribe();
    };
  }, []);

  const signOut = async () => {
    await supabase.auth.signOut();
    window.location.href = "/login";
  };

  return (
    <AuthContext.Provider value={{ user, profile, loading, signOut, refreshProfile }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
