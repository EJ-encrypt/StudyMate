import { ChevronDown, FileText, Link2, RotateCcw } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { errorMessage } from "../api/client";
import {
  ConceptProgress,
  ConceptStatus,
  explainTopic,
  RevisionTopic,
  STATUS_LABELS,
  STATUS_STYLES,
  TopicExplanation,
} from "../api/coach";
import MathText from "./MathText";
import { Skeleton } from "./ui";

export function StatusBadge({ status }: { status: ConceptStatus }) {
  return (
    <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold ${STATUS_STYLES[status]}`}>
      {STATUS_LABELS[status]}
    </span>
  );
}

function SourceLine({ concept }: { concept: ConceptProgress }) {
  const sources = concept.sources ?? [];
  if (sources.length === 0) return null;
  return (
    <p className="mt-1 flex items-start gap-1 text-[11px] leading-snug text-ink/45">
      <FileText className="mt-px h-3 w-3 shrink-0" aria-hidden />
      <span>
        {sources.map((source, index) => (
          <span key={source.document_id}>
            {index > 0 && "; "}
            {source.filename}
            {source.location && ` · ${source.location}`}
          </span>
        ))}
      </span>
    </p>
  );
}

/**
 * One topic in "Revise these next". Tapping it opens the concepts in it, where
 * each is explained in the student's own material, and, written by the AI the
 * first time, how the ones that need work tie in with the rest.
 */
export default function RevisionTopicCard({
  courseId,
  topic,
  number,
}: {
  courseId: string;
  topic: RevisionTopic;
  number: number;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [explanation, setExplanation] = useState<TopicExplanation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function load() {
    setIsLoading(true);
    setError(null);
    try {
      setExplanation(await explainTopic(courseId, topic.concepts.map((c) => c.concept_id)));
    } catch (err) {
      setError(errorMessage(err, "Could not explain this topic right now."));
    } finally {
      setIsLoading(false);
    }
  }

  function toggle() {
    const opening = !isOpen;
    setIsOpen(opening);
    if (opening && !explanation && !isLoading) void load();
  }

  const panelId = `topic-${number}`;

  return (
    <li className="rounded-lg border border-ink/10 bg-surface/80">
      <button
        type="button"
        onClick={toggle}
        aria-expanded={isOpen}
        aria-controls={panelId}
        className="flex w-full items-start gap-2 p-3 text-left"
      >
        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-navy text-xs font-bold text-gold">
          {number}
        </span>
        <span className="min-w-0 flex-1">
          <span className="flex flex-wrap items-center gap-2">
            <span className="font-semibold text-ink">
              {topic.title}
              {topic.concepts.length > 1 && (
                <span className="font-normal text-ink/55"> and {topic.concepts.length - 1} related</span>
              )}
            </span>
            <StatusBadge status={topic.status} />
          </span>
          {!isOpen && (
            <span className="mt-1 line-clamp-2 block text-sm text-ink/70">
              <MathText text={topic.summary} />
            </span>
          )}
        </span>
        <ChevronDown
          className={`mt-0.5 h-5 w-5 shrink-0 text-ink/50 transition-transform ${isOpen ? "rotate-180" : ""}`}
          aria-hidden
        />
      </button>

      {isOpen && (
        <div id={panelId} className="animate-fade-in border-t border-ink/10 px-3 pb-3 pt-3">
          {isLoading && (
            <div className="mb-3 space-y-2" aria-label="Working out how these fit together">
              <Skeleton className="h-3 w-full" />
              <Skeleton className="h-3 w-4/5" />
            </div>
          )}
          {error && (
            <p className="mb-3 flex flex-wrap items-center gap-2 text-sm text-ink/60">
              {error}
              <button type="button" onClick={() => void load()} className="btn-ghost px-1 py-0.5 text-xs">
                <RotateCcw className="h-3.5 w-3.5" aria-hidden /> Try again
              </button>
            </p>
          )}
          {explanation && (
            <p className="mb-3 rounded-lg bg-gold/10 px-3 py-2 text-sm text-ink/80">
              <MathText text={explanation.overview} />
            </p>
          )}

          <ul className="divide-y divide-ink/5">
            {topic.concepts.map((concept) => {
              const link = explanation?.links[concept.concept_id];
              return (
                <li key={concept.concept_id} className="py-2.5 first:pt-0 last:pb-0">
                  <div className="flex items-start justify-between gap-2">
                    <Link to={`/coach/concept/${concept.concept_id}`} className="font-semibold text-ink hover:underline">
                      {concept.name}
                    </Link>
                    <StatusBadge status={concept.status} />
                  </div>
                  <div className="mt-0.5 text-sm text-ink/75">
                    <MathText text={concept.summary} />
                  </div>
                  <SourceLine concept={concept} />
                  {link && (
                    <p className="mt-1.5 flex items-start gap-1.5 border-l-2 border-gold pl-2 text-xs text-ink/70">
                      <Link2 className="mt-0.5 h-3 w-3 shrink-0 text-gold-dark" aria-hidden />
                      <span>
                        <MathText text={link} />
                      </span>
                    </p>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </li>
  );
}
