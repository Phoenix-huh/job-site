import { createClient } from "@supabase/supabase-js";

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || "";
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "";

const isConfigured = SUPABASE_URL && SUPABASE_ANON_KEY && SUPABASE_ANON_KEY.length > 40 && !SUPABASE_ANON_KEY.includes("placeholder");

const stubAuth = {
  getSession: async () => ({ data: { session: null } }),
  onAuthStateChange: () => ({ data: { subscription: { unsubscribe: () => { } } } }),
  signInWithPassword: async () => ({ error: new Error("Supabase not configured. Add NEXT_PUBLIC_SUPABASE_ANON_KEY to frontend/.env.local") }),
  signUp: async () => ({ error: new Error("Supabase not configured. Add NEXT_PUBLIC_SUPABASE_ANON_KEY to frontend/.env.local") }),
  verifyOtp: async () => ({ error: new Error("Supabase not configured. Add NEXT_PUBLIC_SUPABASE_ANON_KEY to frontend/.env.local") }),
  signOut: async () => { },
};

let supabaseInstance;

if (isConfigured) {
  try {
    supabaseInstance = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
  } catch (e) {
    console.error("Failed to create Supabase client:", e);
    supabaseInstance = { auth: stubAuth };
  }
} else {
  if (typeof window !== "undefined") {
    console.warn(
      "ShieldDB: Supabase Auth not configured. Set NEXT_PUBLIC_SUPABASE_ANON_KEY in frontend/.env.local.\n" +
      "Get your anon key from: https://supabase.com/dashboard/project/wehftvlajfmvbbmwtmzj/settings/api"
    );
  }
  supabaseInstance = { auth: stubAuth };
}

export const supabase = supabaseInstance;
