"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { User, AuthChangeEvent, Session } from "@supabase/supabase-js";
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
  ai_risk_profile: "conservative" | "moderate" | "aggressive" | "maximize_profit";
  ai_custom_instructions: string;
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

// Dev mode check
const DEV_MODE = process.env.NEXT_PUBLIC_DEV_MODE === "true";

// Mock user for dev mode
const MOCK_USER: User = {
  id: "9f9b274c-958b-4432-a8d7-294c627b2101",
  email: "dev@polymind.local",
  app_metadata: {},
  user_metadata: {},
  aud: "authenticated",
  created_at: new Date().toISOString(),
} as User;

const MOCK_PROFILE: Profile = {
  id: "9f9b274c-958b-4432-a8d7-294c627b2101",
  display_name: null,
  starting_balance: 10000,
  copy_percentage: 0.10,
  max_daily_exposure: 500,
  max_trades_per_day: 500,
  min_account_balance: 5000,
  ai_enabled: true,
  confidence_threshold: 0.70,
  auto_trade: true,
  bot_status: "running",
  onboarding_completed: true,
  ai_risk_profile: "maximize_profit",
  ai_custom_instructions: "- Never sell within the first hour of buying\n- If a position is down but whale is still holding, prefer to hold\n- Take profits quickly on short-term (<7 day) markets",
};

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(DEV_MODE ? MOCK_USER : null);
  const [profile, setProfile] = useState<Profile | null>(DEV_MODE ? MOCK_PROFILE : null);
  const [loading, setLoading] = useState(!DEV_MODE);

  const fetchProfile = async (userId: string) => {
    try {
      const { data } = await supabase
        .from("profiles")
        .select("*")
        .eq("id", userId)
        .single();
      return data;
    } catch {
      return null;
    }
  };

  const refreshProfile = async () => {
    if (user) {
      const data = await fetchProfile(user.id);
      setProfile(data);
    }
  };

  // Initial load
  useEffect(() => {
    // Skip auth initialization in dev mode - we already have mock data
    if (DEV_MODE) return;

    let mounted = true;

    const init = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession();

        if (!mounted) return;

        if (session?.user) {
          setUser(session.user);
          const profileData = await fetchProfile(session.user.id);
          if (mounted) {
            setProfile(profileData);
          }
        }
      } catch (err) {
        console.error("Auth init error:", err);
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    init();

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (_event: AuthChangeEvent, session: Session | null) => {
        if (!mounted) return;

        if (session?.user) {
          setUser(session.user);
          const profileData = await fetchProfile(session.user.id);
          if (mounted) {
            setProfile(profileData);
          }
        } else {
          setUser(null);
          setProfile(null);
        }

        setLoading(false);
      }
    );

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, []);

  const signOut = async () => {
    await supabase.auth.signOut();
    setUser(null);
    setProfile(null);
    window.location.href = "/login";
  };

  return (
    <AuthContext.Provider value={{ user, profile, loading, signOut, refreshProfile }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
