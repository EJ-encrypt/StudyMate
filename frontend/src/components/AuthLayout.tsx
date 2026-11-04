import { BellRing, Brain, Gamepad2, GraduationCap } from "lucide-react";
import { ReactNode } from "react";

import { useAuth } from "../context/AuthContext";
import { Alert } from "./ui";
import { CoachIcon } from "../lib/icons";

const FEATURES = [
  { icon: Brain, text: "Quizzes, flashcards and exam papers from your own slides and notes" },
  { icon: Gamepad2, text: "Revise with games: Beat the Clock and Concept Match" },
  { icon: BellRing, text: "Reminders before every lecture, and a nudge to capture what you learnt" },
  { icon: CoachIcon, text: "A coach that tracks every topic and tells you what to revise next" },
];

/** Split layout for the signed-out pages: product pitch beside the form. */
export default function AuthLayout({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  const { isConfigured } = useAuth();

  return (
    <div className="flex min-h-screen">
      <section className="relative hidden w-[44%] flex-col justify-between overflow-hidden bg-navy p-10 text-white lg:flex">
        <div className="pointer-events-none absolute -right-24 -top-24 h-80 w-80 rounded-full bg-gold/10" />
        <div className="pointer-events-none absolute -bottom-32 -left-16 h-96 w-96 rounded-full bg-white/5" />
        <span className="relative flex items-center gap-2 text-lg font-extrabold text-gold">
          <GraduationCap className="h-6 w-6" aria-hidden /> StudyMate
        </span>
        <div className="relative">
          <h2 className="text-3xl font-bold leading-tight">
            Study smarter with
            <br />
            <span className="text-gold">your own material.</span>
          </h2>
          <ul className="mt-8 space-y-4">
            {FEATURES.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-start gap-3 text-sm text-white/80">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white/10 text-gold">
                  <Icon className="h-4 w-4" aria-hidden />
                </span>
                <span className="pt-1.5">{text}</span>
              </li>
            ))}
          </ul>
        </div>
        <p className="relative text-xs text-white/40">University of Ghana · BSc IT final-year project</p>
      </section>

      <section className="flex flex-1 items-center justify-center px-5 py-10">
        <div className="w-full max-w-sm animate-fade-in">
          <span className="mb-8 flex items-center gap-2 text-lg font-extrabold text-ink lg:hidden">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-navy text-gold">
              <GraduationCap className="h-5 w-5" aria-hidden />
            </span>
            StudyMate
          </span>
          <h1 className="text-2xl font-bold tracking-tight text-ink">{title}</h1>
          {subtitle && <p className="mt-1 text-sm text-ink/60">{subtitle}</p>}
          {!isConfigured && (
            <div className="mt-4">
              <Alert>
                This build is not connected to Supabase. Set VITE_SUPABASE_URL and
                VITE_SUPABASE_ANON_KEY and rebuild.
              </Alert>
            </div>
          )}
          <div className="mt-6">{children}</div>
        </div>
      </section>
    </div>
  );
}
