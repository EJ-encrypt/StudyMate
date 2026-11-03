import React, { createContext, useCallback, useContext, useEffect, useState } from "react";

import { fetchCurrentUser, UserProfile } from "../api/auth";
import { supabase } from "../lib/supabase";

interface SignUpResult {
  /** True when Supabase wants the address confirmed before the first sign-in. */
  needsConfirmation: boolean;
}

interface AuthContextValue {
  user: UserProfile | null;
  isLoading: boolean;
  /** False when the build is missing its Supabase settings. */
  isConfigured: boolean;
  /** Set while the student is following a password-reset link. */
  isRecoveringPassword: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<SignUpResult>;
  sendPasswordReset: (email: string) => Promise<void>;
  setNewPassword: (password: string) => Promise<void>;
  /** Re-read the profile, e.g. after onboarding changes it. */
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function notConfigured(): never {
  throw new Error("StudyMate is not connected to Supabase yet.");
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRecoveringPassword, setIsRecoveringPassword] = useState(false);

  const loadProfile = useCallback(async () => {
    try {
      setUser(await fetchCurrentUser());
    } catch {
      setUser(null);
    }
  }, []);

  useEffect(() => {
    if (!supabase) {
      setIsLoading(false);
      return;
    }

    supabase.auth.getSession().then(async ({ data }) => {
      if (data.session) await loadProfile();
      setIsLoading(false);
    });

    const { data: listener } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === "PASSWORD_RECOVERY") setIsRecoveringPassword(true);
      if (event === "SIGNED_OUT" || !session) {
        setUser(null);
        return;
      }
      if (event === "SIGNED_IN" || event === "USER_UPDATED") {
        // Deferred: Supabase advises against awaiting other calls inside
        // this callback, which can deadlock its session lock.
        setTimeout(() => void loadProfile(), 0);
      }
    });
    return () => listener.subscription.unsubscribe();
  }, [loadProfile]);

  const login = useCallback(
    async (email: string, password: string) => {
      if (!supabase) notConfigured();
      const { error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) throw error;
      await loadProfile();
    },
    [loadProfile],
  );

  const register = useCallback(
    async (email: string, password: string, fullName: string): Promise<SignUpResult> => {
      if (!supabase) notConfigured();
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: { full_name: fullName },
          emailRedirectTo: `${window.location.origin}/welcome`,
        },
      });
      if (error) throw error;
      if (data.session) {
        await loadProfile();
        return { needsConfirmation: false };
      }
      return { needsConfirmation: true };
    },
    [loadProfile],
  );

  const sendPasswordReset = useCallback(async (email: string) => {
    if (!supabase) notConfigured();
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/reset-password`,
    });
    if (error) throw error;
  }, []);

  const setNewPassword = useCallback(async (password: string) => {
    if (!supabase) notConfigured();
    const { error } = await supabase.auth.updateUser({ password });
    if (error) throw error;
    setIsRecoveringPassword(false);
  }, []);

  const refresh = useCallback(async () => {
    setUser(await fetchCurrentUser());
  }, []);

  const logout = useCallback(async () => {
    await supabase?.auth.signOut();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isConfigured: !!supabase,
        isRecoveringPassword,
        login,
        register,
        sendPasswordReset,
        setNewPassword,
        refresh,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
