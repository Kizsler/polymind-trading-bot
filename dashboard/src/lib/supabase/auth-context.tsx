"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
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
    let cancelled = false;

    const init = async () => {
      try {
        const { data: { user }, error: authError } = await supabase.auth.getUser();

        if (authError) {
          console.error("Auth getUser error:", authError);
        }

        if (cancelled) return;

        setUser(user);

        if (user) {
          try {
            const { data, error: profileError } = await supabase
              .from("profiles")
              .select("*")
              .eq("id", user.id)
              .single();

            if (profileError) {
              console.error("Profile fetch error:", profileError);
            }

            if (!cancelled) {
              setProfile(data);
            }
          } catch (err) {
            console.error("Profile fetch exception:", err);
            if (!cancelled) {
              setProfile(null);
            }
          }
        }
      } catch (err) {
        console.error("Auth init error:", err);
      } finally {
        // Always set loading to false, even if there were errors
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    init();

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event: string, session: Session | null) => {
        if (cancelled) return;

        // Set loading when auth state changes to prevent race conditions
        setLoading(true);
        setUser(session?.user ?? null);

        if (session?.user) {
          try {
            const { data } = await supabase
              .from("profiles")
              .select("*")
              .eq("id", session.user.id)
              .single();

            if (!cancelled) {
              setProfile(data);
            }
          } catch (err) {
            console.error("Profile fetch error on auth change:", err);
            if (!cancelled) {
              setProfile(null);
            }
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
