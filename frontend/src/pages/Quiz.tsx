import { AlertCircle, ArrowLeft, CheckCircle2, Gamepad2, Send, Trophy, XCircle } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  AssessmentDetail,
  AttemptResult,
  getAssessment,
  KIND_LABELS,
  submitAttempt,
} from "../api/assessments";
import FlashcardDeck from "../components/FlashcardDeck";
import MathText from "../components/MathText";
import { Alert, ListSkeleton, NewBadges } from "../components/ui";

export default function Quiz() {
  const { assessmentId } = useParams<{ assessmentId: string }>();
  const [assessment, setAssessment] = useState<AssessmentDetail | null>(null);
  const [responses, setResponses] = useState<Record<string, string>>({});
  const [result, setResult] = useState<AttemptResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (!assessmentId) return;
    getAssessment(assessmentId)
      .then(setAssessment)
      .catch(() => setError("Could not load this assessment."));
  }, [assessmentId]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!assessmentId || !assessment) return;

    setIsSubmitting(true);
    setError(null);
    try {
      const answers = assessment.items.map((item) => ({
        item_id: item.id,
        response: responses[item.id] ?? "",
      }));
      setResult(await submitAttempt(assessmentId, answers));
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch {
      setError("Could not submit your answers. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (error && !assessment) {
    return <Alert>{error}</Alert>;
  }
  if (!assessment) {
    return <ListSkeleton rows={3} />;
  }

  const graded = result ? Object.fromEntries(result.answers.map((a) => [a.item_id, a])) : {};
  const isFlashcards = assessment.kind === "flashcard";
  const answered = assessment.items.filter((item) => (responses[item.id] ?? "").trim()).length;
  const playable = assessment.kind === "mcq" || assessment.kind === "fill_blank";
  const percent = result && result.total_count ? Math.round((result.correct_count / result.total_count) * 100) : 0;
  const unmarked = result ? result.answers.filter((a) => !a.marked).length : 0;

  return (
    <div className="mx-auto max-w-3xl">
      <Link to={`/study/${assessment.course_id}`} className="btn-ghost -ml-2 mb-2">
        <ArrowLeft className="h-4 w-4" aria-hidden /> Back to course
      </Link>
      <h1 className="text-xl font-bold tracking-tight text-ink sm:text-2xl">{assessment.title}</h1>
      <p className="mt-1 text-sm text-ink/60">
        {KIND_LABELS[assessment.kind]} · {assessment.items.length} items
        {isFlashcards && " · tap the card to flip it"}
      </p>

      {result && (
        <div className="card mt-5 animate-pop overflow-hidden">
          <div className="flex items-center gap-4 bg-navy p-4 text-white">
            <span className="flex h-14 w-14 items-center justify-center rounded-full bg-gold/20 text-gold">
              <Trophy className="h-7 w-7" aria-hidden />
            </span>
            <div>
              <p className="text-2xl font-bold">
                {result.total_count ? `${result.correct_count} / ${result.total_count}` : "Not marked"}
              </p>
              {result.total_count > 0 && <p className="text-sm text-white/70">{percent}% correct</p>}
              {unmarked > 0 && (
                <p className="text-sm text-white/70">
                  {unmarked} written answer{unmarked === 1 ? "" : "s"} could not be marked and {unmarked === 1 ? "is" : "are"} not counted.
                </p>
              )}
            </div>
          </div>
          <div className="space-y-3 p-4">
            <NewBadges badges={result.new_badges} />
            {playable && (
              <Link to={`/play/${assessment.course_id}/clock`} className="btn-gold">
                <Gamepad2 className="h-4 w-4" aria-hidden /> Race these questions in Beat the Clock
              </Link>
            )}
          </div>
        </div>
      )}

      {isFlashcards ? (
        <FlashcardDeck items={assessment.items} />
      ) : (
        <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
          {assessment.items.map((item, index) => {
            const answer = graded[item.id];
            return (
              <fieldset
                key={item.id}
                className={[
                  "card p-4",
                  !answer ? "" : !answer.marked ? "border-amber-300" : answer.is_correct ? "border-green-300" : "border-red-300",
                ].join(" ")}
              >
                <legend className="sr-only">Question {index + 1}</legend>
                <p className="flex gap-2 font-semibold text-ink">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-ink/5 text-xs">
                    {index + 1}
                  </span>
                  <MathText text={item.question} />
                </p>

                {item.kind === "mcq" && (
                  <div className="mt-3 grid gap-2">
                    {item.options.map((option) => {
                      const chosen = responses[item.id] === option;
                      const isAnswer = answer && option === answer.correct_answer;
                      return (
                        <label
                          key={option}
                          className={[
                            "flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-sm transition",
                            isAnswer
                              ? "border-green-400 bg-green-50"
                              : chosen && answer
                                ? "border-red-300 bg-red-50"
                                : chosen
                                  ? "border-gold bg-gold/10"
                                  : "border-ink/15 hover:border-ink/30",
                          ].join(" ")}
                        >
                          <input
                            type="radio"
                            name={item.id}
                            value={option}
                            checked={chosen}
                            disabled={!!result}
                            onChange={() => setResponses((prev) => ({ ...prev, [item.id]: option }))}
                            className="accent-ink"
                          />
                          <MathText text={option} />
                        </label>
                      );
                    })}
                  </div>
                )}

                {item.kind === "short_answer" && (
                  <textarea
                    placeholder="Answer in one to three sentences"
                    value={responses[item.id] ?? ""}
                    disabled={!!result}
                    rows={4}
                    onChange={(e) => setResponses((prev) => ({ ...prev, [item.id]: e.target.value }))}
                    className="input mt-3"
                  />
                )}

                {item.kind === "fill_blank" && (
                  <input
                    type="text"
                    placeholder="Your answer"
                    value={responses[item.id] ?? ""}
                    disabled={!!result}
                    onChange={(e) => setResponses((prev) => ({ ...prev, [item.id]: e.target.value }))}
                    className="input mt-3"
                  />
                )}

                {answer && (
                  <div className="mt-3 text-sm">
                    <p
                      className={[
                        "flex items-center gap-1.5 font-semibold",
                        !answer.marked ? "text-amber-700" : answer.is_correct ? "text-green-700" : "text-red-600",
                      ].join(" ")}
                    >
                      {!answer.marked ? (
                        <AlertCircle className="h-4 w-4" aria-hidden />
                      ) : answer.is_correct ? (
                        <CheckCircle2 className="h-4 w-4" aria-hidden />
                      ) : (
                        <XCircle className="h-4 w-4" aria-hidden />
                      )}
                      {!answer.marked ? "Not marked" : answer.is_correct ? "Correct" : "Incorrect"}
                    </p>
                    {!answer.is_correct && (
                      <p className="mt-1 text-ink">
                        <span className="font-semibold">Model answer:</span> <MathText text={answer.correct_answer} />
                      </p>
                    )}
                    {answer.explanation && (
                      <p className="mt-1 text-ink/70">
                        <MathText text={answer.explanation} />
                      </p>
                    )}
                  </div>
                )}
              </fieldset>
            );
          })}

          {error && <Alert>{error}</Alert>}

          {!result && (
            <div className="sticky bottom-20 z-10 flex items-center justify-between gap-3 rounded-xl border border-ink/10 bg-surface/95 p-3 shadow-lift backdrop-blur md:bottom-4">
              <span className="text-sm text-ink/60">
                {answered} of {assessment.items.length} answered
              </span>
              <button type="submit" disabled={isSubmitting} className="btn-primary">
                <Send className="h-4 w-4" aria-hidden />
                {isSubmitting ? "Marking..." : "Submit answers"}
              </button>
            </div>
          )}
        </form>
      )}
    </div>
  );
}
