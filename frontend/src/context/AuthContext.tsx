import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { User as AuthUser } from "@supabase/supabase-js";

import { deleteAccount as deleteAccountRequest, fetchCurrentUser, UserProfile } from "../api/auth";
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
  /** False for an account made with Google, until a password is added in Settings. */
  hasPassword: boolean;
  /** The captcha token is only needed once CAPTCHA protection is on (lib/captcha). */
  login: (email: string, password: string, captchaToken?: string) => Promise<void>;
  register: (email: string, password: string, fullName: string, captchaToken?: string) => Promise<SignUpResult>;
  /** Leaves the app for Google's sign-in page; Supabase brings the student back signed in. */
  signInWithGoogle: () => Promise<void>;
  sendPasswordReset: (email: string, captchaToken?: string) => Promise<void>;
  setNewPassword: (password: string) => Promise<void>;
  /** Check the current password, then set a new one. */
  changePassword: (currentPassword: string, newPassword: string, captchaToken?: string) => Promise<void>;
  /** First password for an account made with Google, so email sign-in works too. */
  addPassword: (password: string) => Promise<void>;
  /** Delete the account and everything in it, then sign out. */
  deleteAccount: () => Promise<void>;
  /** Re-read the profile, e.g. after onboarding changes it. */
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function notConfigured(): never {
  throw new Error("StudyMate is not connected to Supabase yet.");
}

/** A Google-only account has no password until one is added in Settings. */
function accountHasPassword(authUser: AuthUser | null | undefined): boolean {
  if (!authUser) return true;
  const providers = (authUser.app_metadata?.providers as string[] | undefined) ?? [authUser.app_metadata?.provider];
  return providers.includes("email") || !!authUser.user_metadata?.password_set;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRecoveringPassword, setIsRecoveringPassword] = useState(false);
  const [hasPassword, setHasPassword] = useState(true);

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
      setHasPassword(accountHasPassword(data.session?.user));
      if (data.session) await loadProfile();
      setIsLoading(false);
    });

    const { data: listener } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === "PASSWORD_RECOVERY") setIsRecoveringPassword(true);
      if (event === "SIGNED_OUT" || !session) {
        setUser(null);
        return;
      }
      setHasPassword(accountHasPassword(session.user));
      if (event === "SIGNED_IN" || event === "USER_UPDATED") {
        // Deferred: Supabase advises against awaiting other calls inside
        // this callback, which can deadlock its session lock.
        setTimeout(() => void loadProfile(), 0);
      }
    });
    return () => listener.subscription.unsubscribe();
  }, [loadProfile]);

  const login = useCallback(
    async (email: string, password: string, captchaToken?: string) => {
      if (!supabase) notConfigured();
      const { error } = await supabase.auth.signInWithPassword({ email, password, options: { captchaToken } });
      if (error) throw error;
      await loadProfile();
    },
    [loadProfile],
  );

  const register = useCallback(
    async (email: string, password: string, fullName: string, captchaToken?: string): Promise<SignUpResult> => {
      if (!supabase) notConfigured();
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: { full_name: fullName },
          emailRedirectTo: `${window.location.origin}/welcome`,
          captchaToken,
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

  const signInWithGoogle = useCallback(async () => {
    if (!supabase) notConfigured();
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      // A new student goes on to onboarding from here (App's RequireOnboarding).
      options: { redirectTo: `${window.location.origin}/courses` },
    });
    if (error) throw error;
  }, []);

  const sendPasswordReset = useCallback(async (email: string, captchaToken?: string) => {
    if (!supabase) notConfigured();
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/reset-password`,
      captchaToken,
    });
    if (error) throw error;
  }, []);

  const setNewPassword = useCallback(async (password: string) => {
    if (!supabase) notConfigured();
    const { error } = await supabase.auth.updateUser({ password });
    if (error) throw error;
    setIsRecoveringPassword(false);
  }, []);

  const changePassword = useCallback(
    async (currentPassword: string, newPassword: string, captchaToken?: string) => {
      if (!supabase) notConfigured();
      const email = user?.email;
      if (!email) throw new Error("Not signed in.");
      // Supabase lets a signed-in session set any password without the old
      // one, so a phone left unlocked could be locked out of its owner. Asking
      // for the current password first closes that.
      const { error: checkError } = await supabase.auth.signInWithPassword({
        email,
        password: currentPassword,
        options: { captchaToken },
      });
      if (checkError) throw new Error("Your current password is not right.");
      const { error } = await supabase.auth.updateUser({ password: newPassword });
      if (error) throw error;
    },
    [user?.email],
  );

  const addPassword = useCallback(async (password: string) => {
    if (!supabase) notConfigured();
    // password_set is only a hint for Settings: Supabase goes on listing such
    // an account under Google alone, though email sign-in now works for it.
    const { error } = await supabase.auth.updateUser({ password, data: { password_set: true } });
    if (error) throw error;
    setHasPassword(true);
  }, []);

  const deleteAccount = useCallback(async () => {
    await deleteAccountRequest();
    await supabase?.auth.signOut();
    setUser(null);
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
        hasPassword,
        login,
        register,
        signInWithGoogle,
        sendPasswordReset,
        setNewPassword,
        changePassword,
        addPassword,
        deleteAccount,
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
