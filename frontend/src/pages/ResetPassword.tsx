import { KeyRound } from "lucide-react";
import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

import AuthLayout from "../components/AuthLayout";
import { Alert, PasswordInput } from "../components/ui";
import { useAuth } from "../context/AuthContext";

/** Where the emailed reset link lands; Supabase has already signed the student in. */
export default function ResetPassword() {
  const { setNewPassword } = useAuth();
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (password.length < 8) {
      setError("Use at least 8 characters.");
      return;
    }
    setIsSaving(true);
    setError(null);
    try {
      await setNewPassword(password);
      navigate("/courses", { replace: true });
    } catch (err) {
      setError((err as Error).message || "Could not update your password. The link may have expired.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <AuthLayout title="Choose a new password">
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <label>
          <span className="label">New password</span>
          <PasswordInput
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
            className="mt-1"
          />
        </label>
        {error && <Alert>{error}</Alert>}
        <button type="submit" disabled={isSaving} className="btn-primary py-2.5">
          <KeyRound className="h-4 w-4" aria-hidden />
          {isSaving ? "Saving..." : "Save password"}
        </button>
      </form>
    </AuthLayout>
  );
}
