import { ArrowLeft } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import {
  AssessmentKind,
  KIND_LABELS,
  createAssessment,
  createCumulativeAssessment,
} from "../api/assessments";
import { ConceptDetail as ConceptDetailData, STATUS_LABELS, STATUS_STYLES, getConceptDetail } from "../api/coach";
import PageHeader from "../components/PageHeader";
import { Alert, Spinner, StatTile } from "../components/ui";

const PRACTICE_KINDS: AssessmentKind[] = ["flashcard", "mcq", "short_answer"];

export default function ConceptDetail() {
  const { conceptId } = useParams<{ conceptId: string }>();
  const navigate = useNavigate();
  const [concept, setConcept] = useState<ConceptDetailData | null>(null);
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    if (!conceptId) return;
    getConceptDetail(conceptId)
      .then(setConcept)
      .catch(() => setError("Could not load this topic."));
  }, [conceptId]);

  async function practise(kind: AssessmentKind) {
    if (!concept) return;
    setIsBusy(true);
    setError(null);
    try {
      // Practice is drawn from the document this topic came from where there
      // is exactly one, so the questions stay close to it. Otherwise it falls
      // back to the whole course.
      const created =
        concept.sources.length === 1
          ? await createAssessment(concept.sources[0].document_id, kind)
          : await createCumulativeAssessment(concept.course_id, kind);
      setNotice(`Generating ${KIND_LABELS[kind].toLowerCase()}. It will appear in Study Engine.`);
      setTimeout(() => navigate(`/study/${concept.course_id}`), 1200);
      return created;
    } catch {
      setError("Could not start that just now. Please try again.");
    } finally {
      setIsBusy(false);
    }
  }

  if (error && !concept) {
    return <Alert>{error}</Alert>;
  }
  if (!concept) {
    return <Spinner />;
  }

  const percent = concept.score === null ? null : Math.round(concept.score * 100);

  return (
    <>
      <Link to="/coach" className="btn-ghost -ml-2 mb-2">
        <ArrowLeft className="h-4 w-4" aria-hidden /> Back to Coach
      </Link>
      <PageHeader
        title={concept.name}
        subtitle={
          <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${STATUS_STYLES[concept.status]}`}>
            {STATUS_LABELS[concept.status]}
          </span>
        }
      />

      <section className="mb-4 card p-4">
        <h2 className="text-xs font-bold uppercase tracking-wide text-navy/50">What this is</h2>
        <p className="mt-1 text-sm text-navy/80">{concept.summary}</p>
      </section>

      <section className="mb-4 grid grid-cols-3 gap-3">
        <StatTile label="Mastery" value={percent === null ? "—" : `${percent}%`} />
        <StatTile label="Correct" value={`${concept.correct}/${concept.attempts}`} />
        <StatTile label={`Source ${concept.sources.length === 1 ? "file" : "files"}`} value={concept.sources.length} />
      </section>

      {concept.mentions.length > 0 && (
        <section className="mb-4 card p-4">
          <h2 className="text-xs font-bold uppercase tracking-wide text-navy/50">
            How your material puts it
          </h2>
          <ul className="mt-1 flex flex-col gap-2">
            {concept.mentions.map((mention, index) => (
              <li key={index} className="text-sm text-navy/80">
                <span className="text-navy/50">
                  {concept.sources[index]?.filename ?? "Source"}:
                </span>{" "}
                {mention}
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="rounded-xl border border-gold bg-gold/10 p-4">
        <h2 className="text-xs font-bold uppercase tracking-wide text-navy/60">
          Practise this
        </h2>
        <p className="mt-1 text-sm text-navy/75">
          {concept.sources.length === 1
            ? `Generated from ${concept.sources[0].filename}.`
            : "Generated from the whole course, since this topic appears in several files."}
        </p>
        <div className="mt-2 flex flex-wrap gap-2">
          {PRACTICE_KINDS.map((kind) => (
            <button
              key={kind}
              type="button"
              disabled={isBusy}
              onClick={() => practise(kind)}
              className="btn-secondary"
            >
              {KIND_LABELS[kind]}
            </button>
          ))}
        </div>
        {notice && <p className="mt-2 text-sm text-green-700">{notice}</p>}
        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      </section>
    </>
  );
}
