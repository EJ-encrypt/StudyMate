import { FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  AssessmentDetail,
  AttemptResult,
  getAssessment,
  KIND_LABELS,
  submitAttempt,
} from "../api/assessments";

export default function Quiz() {
  const { assessmentId } = useParams<{ assessmentId: string }>();
  const [assessment, setAssessment] = useState<AssessmentDetail | null>(null);
  const [responses, setResponses] = useState<Record<string, string>>({});
  const [revealed, setRevealed] = useState<Record<string, boolean>>({});
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
    } catch {
      setError("Could not submit your answers. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (error && !assessment) {
    return <p className="mx-auto max-w-3xl px-4 py-8 text-red-600">{error}</p>;
  }
  if (!assessment) {
    return <p className="mx-auto max-w-3xl px-4 py-8 text-navy/70">Loading...</p>;
  }

  const graded = result ? Object.fromEntries(result.answers.map((a) => [a.item_id, a])) : {};
  const isFlashcards = assessment.kind === "flashcard";

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <Link to="/materials" className="text-sm font-semibold text-gold-dark">
        &larr; Back to Materials
      </Link>
      <h1 className="mt-2 text-2xl font-bold text-navy">{assessment.title}</h1>
      <p className="mt-1 text-sm text-navy/60">
        {KIND_LABELS[assessment.kind]} &middot; {assessment.items.length} items
      </p>

      {result && (
        <div className="mt-6 rounded border border-gold bg-gold/10 p-4">
          <p className="font-semibold text-navy">
            Score: {result.correct_count} / {result.total_count}
          </p>
          {result.new_badges.length > 0 && (
            <div className="mt-3">
              <p className="text-sm font-semibold text-navy">Badge earned</p>
              <ul className="mt-1 flex flex-col gap-1">
                {result.new_badges.map((badge) => (
                  <li key={badge.code} className="text-sm text-navy/80">
                    <span className="font-semibold">{badge.name}</span> - {badge.description}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {isFlashcards ? (
        <ul className="mt-6 flex flex-col gap-3">
          {assessment.items.map((item) => (
            <li key={item.id} className="rounded border border-navy/10 p-4">
              <p className="font-semibold text-navy">
                {item.position}. {item.question}
              </p>
              <button
                type="button"
                onClick={() => setRevealed((prev) => ({ ...prev, [item.id]: !prev[item.id] }))}
                className="mt-2 text-sm font-semibold text-gold-dark hover:underline"
              >
                {revealed[item.id] ? "Hide answer" : "Show answer"}
              </button>
              {revealed[item.id] && <p className="mt-2 text-navy/80">{item.answer}</p>}
            </li>
          ))}
        </ul>
      ) : (
        <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-5">
          {assessment.items.map((item) => {
            const answer = graded[item.id];
            return (
              <fieldset key={item.id} className="rounded border border-navy/10 p-4">
                <legend className="px-1 text-sm font-semibold text-navy/60">{item.position}</legend>
                <p className="font-semibold text-navy">{item.question}</p>

                {item.kind === "mcq" && (
                  <div className="mt-3 flex flex-col gap-2">
                    {item.options.map((option) => (
                      <label key={option} className="flex items-center gap-2 text-navy">
                        <input
                          type="radio"
                          name={item.id}
                          value={option}
                          checked={responses[item.id] === option}
                          disabled={!!result}
                          onChange={() => setResponses((prev) => ({ ...prev, [item.id]: option }))}
                        />
                        {option}
                      </label>
                    ))}
                  </div>
                )}

                {item.kind === "short_answer" && (
                  <textarea
                    placeholder="Answer in one to three sentences"
                    value={responses[item.id] ?? ""}
                    disabled={!!result}
                    rows={4}
                    onChange={(e) => setResponses((prev) => ({ ...prev, [item.id]: e.target.value }))}
                    className="mt-3 w-full rounded border border-navy/20 px-3 py-2"
                  />
                )}

                {item.kind === "fill_blank" && (
                  <input
                    type="text"
                    placeholder="Your answer"
                    value={responses[item.id] ?? ""}
                    disabled={!!result}
                    onChange={(e) => setResponses((prev) => ({ ...prev, [item.id]: e.target.value }))}
                    className="mt-3 w-full rounded border border-navy/20 px-3 py-2"
                  />
                )}

                {answer && (
                  <div className="mt-3 text-sm">
                    <p className={answer.is_correct ? "font-semibold text-green-700" : "font-semibold text-red-600"}>
                      {answer.is_correct ? "Correct" : "Incorrect"}
                    </p>
                    {!answer.is_correct && (
                      <p className="mt-1 text-navy">
                        <span className="font-semibold">Model answer:</span> {answer.correct_answer}
                      </p>
                    )}
                    {answer.explanation && <p className="mt-1 text-navy/70">{answer.explanation}</p>}
                  </div>
                )}
              </fieldset>
            );
          })}

          {error && <p className="text-sm text-red-600">{error}</p>}

          {!result && (
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-fit rounded bg-navy px-4 py-2 font-semibold text-gold hover:bg-navy-light disabled:opacity-50"
            >
              {isSubmitting ? "Submitting..." : "Submit answers"}
            </button>
          )}
        </form>
      )}
    </div>
  );
}
