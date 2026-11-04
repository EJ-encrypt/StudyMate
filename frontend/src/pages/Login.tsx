import { LogIn } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import AuthLayout from "../components/AuthLayout";
import { Alert } from "../components/ui";
import { useAuth } from "../context/AuthContext";

function friendly(message: string): string {
  if (/email not confirmed/i.test(message)) {
    return "Please confirm your email first - check your inbox for the link we sent.";
  }
  if (/invalid login credentials/i.test(message)) return "Incorrect email or password.";
  return message || "Could not log in. Please try again.";
}

export default function Login() {
  const { user, login, sendPasswordReset } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? "/courses";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (user) navigate(from, { replace: true });
  }, [user, from, navigate]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setNotice(null);
    setIsSubmitting(true);
    try {
      await login(email, password);
    } catch (err) {
      setError(friendly((err as Error).message));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleForgot() {
    setError(null);
    if (!email) {
      setError("Type your email above first, then choose Forgot password.");
      return;
    }
    try {
      await sendPasswordReset(email);
      setNotice(`If ${email} has an account, a reset link is on its way.`);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <AuthLayout title="Log in" subtitle="Welcome back. Pick up where you left off.">
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <label>
          <span className="label">Email</span>
          <input
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="input mt-1"
          />
        </label>
        <label>
          <span className="label">Password</span>
          <input
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="input mt-1"
          />
        </label>
        <button
          type="button"
          onClick={handleForgot}
          className="-mt-1 w-fit text-xs font-semibold text-gold-dark hover:underline"
        >
          Forgot password?
        </button>
        {error && <Alert>{error}</Alert>}
        {notice && <Alert kind="success">{notice}</Alert>}
        <button type="submit" disabled={isSubmitting} className="btn-primary mt-1 py-2.5">
          <LogIn className="h-4 w-4" aria-hidden />
          {isSubmitting ? "Logging in..." : "Log in"}
        </button>
      </form>
      <p className="mt-6 text-sm text-ink/70">
        New to StudyMate?{" "}
        <Link to="/register" className="font-semibold text-gold-dark hover:underline">
          Create an account
        </Link>
      </p>
    </AuthLayout>
  );
}
