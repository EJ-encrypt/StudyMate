import { MailCheck, UserPlus } from "lucide-react";
import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import AuthLayout from "../components/AuthLayout";
import GoogleSignIn from "../components/GoogleSignIn";
import { Alert, PasswordInput } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { Captcha, captchaEnabled } from "../lib/captcha";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [awaitingConfirmation, setAwaitingConfirmation] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [captchaToken, setCaptchaToken] = useState<string | null>(null);
  // A captcha token works once, so the check is redone after every attempt.
  const [captchaRound, setCaptchaRound] = useState(0);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError("Use at least 8 characters for your password.");
      return;
    }
    setIsSubmitting(true);
    try {
      const { needsConfirmation } = await register(email, password, fullName.trim(), captchaToken ?? undefined);
      if (needsConfirmation) setAwaitingConfirmation(true);
      else navigate("/welcome");
    } catch (err) {
      const message = (err as Error).message;
      setError(
        /already registered/i.test(message) ? "That email already has an account. Try logging in." : message,
      );
      setCaptchaRound((round) => round + 1);
    } finally {
      setIsSubmitting(false);
    }
  }

  if (awaitingConfirmation) {
    return (
      <AuthLayout title="Check your email">
        <div className="card flex flex-col items-center p-6 text-center">
          <span className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-gold/15 text-gold-dark">
            <MailCheck className="h-6 w-6" aria-hidden />
          </span>
          <p className="text-sm text-ink/75">
            We sent a confirmation link to <span className="font-semibold text-ink">{email}</span>.
            Open it on this device to finish creating your account.
          </p>
          <p className="mt-3 text-xs text-ink/50">Nothing after a few minutes? Check your spam folder.</p>
        </div>
        <p className="mt-6 text-sm text-ink/70">
          Already confirmed?{" "}
          <Link to="/login" className="font-semibold text-gold-dark hover:underline">
            Log in
          </Link>
        </p>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout title="Create your account" subtitle="Free for students. Takes under a minute.">
      <GoogleSignIn />
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <label>
          <span className="label">Full name</span>
          <input
            type="text"
            autoComplete="name"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            required
            className="input mt-1"
          />
        </label>
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
          <PasswordInput
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
            className="mt-1"
          />
          <span className="mt-1 block text-xs text-ink/50">At least 8 characters.</span>
        </label>
        <Captcha key={captchaRound} onToken={setCaptchaToken} />
        {error && <Alert>{error}</Alert>}
        <button type="submit" disabled={isSubmitting || (captchaEnabled && !captchaToken)} className="btn-primary mt-1 py-2.5">
          <UserPlus className="h-4 w-4" aria-hidden />
          {isSubmitting ? "Creating account..." : "Create account"}
        </button>
      </form>
      <p className="mt-6 text-sm text-ink/70">
        Already have an account?{" "}
        <Link to="/login" className="font-semibold text-gold-dark hover:underline">
          Log in
        </Link>
      </p>
    </AuthLayout>
  );
}
