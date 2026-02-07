"use client";

import { createContext, useContext, useEffect, useState, useCallback, ReactNode } from "react";
import { User, Session, AuthChangeEvent } from "@supabase/supabase-js";
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

// Mock data for dev mode
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

  const fetchProfile = useCallback(async (userId: string): Promise<Profile | null> => {
    try {
      const { data, error } = await supabase
        .from("profiles")
        .select("*")
        .eq("id", userId)
        .single();

      if (error) {
        console.error("Error fetching profile:", error);
        return null;
      }
      return data;
    } catch (err) {
      console.error("Exception fetching profile:", err);
      return null;
    }
  }, []);

  const refreshProfile = useCallback(async () => {
    if (user) {
      const data = await fetchProfile(user.id);
      setProfile(data);
    }
  }, [user, fetchProfile]);

  // Initialize auth state - runs only once
  useEffect(() => {
    if (DEV_MODE) return;

    let mounted = true;

    // onAuthStateChange fires immediately with INITIAL_SESSION event
    // This handles both initial load and subsequent auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event: AuthChangeEvent, session: Session | null) => {
        console.log("Auth state change:", event, session?.user?.email || "no user");

        if (!mounted) return;

        if (session?.user) {
          setUser(session.user);
          setLoading(false);
          // Fetch profile in background
          fetchProfile(session.user.id).then(profileData => {
            if (mounted) setProfile(profileData);
          });
        } else {
          setUser(null);
          setProfile(null);
          setLoading(false);
        }

        console.log("Auth state change handled");
      }
    );

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, [fetchProfile]); // Include fetchProfile dependency

  const signOut = useCallback(async () => {
    await supabase.auth.signOut();
    setUser(null);
    setProfile(null);
    window.location.href = "/login";
  }, []);

  return (
    <AuthContext.Provider value={{ user, profile, loading, signOut, refreshProfile }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
