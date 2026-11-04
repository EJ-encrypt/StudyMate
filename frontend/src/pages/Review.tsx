import { ArrowLeft, Layers } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { AssessmentItem } from "../api/assessments";
import { getDueCards } from "../api/review";
import FlashcardDeck from "../components/FlashcardDeck";
import PageHeader from "../components/PageHeader";
import { Alert, EmptyState, ListSkeleton } from "../components/ui";

/** The flashcards due again today, from every set in the course. */
export default function Review() {
  const { courseId } = useParams<{ courseId: string }>();
  const [items, setItems] = useState<AssessmentItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDueCards(courseId)
      .then(setItems)
      .catch(() => setError("Could not load the cards due for review."));
  }, [courseId]);

  const back = (
    <Link to="/coach" className="btn-primary">
      <ArrowLeft className="h-4 w-4" aria-hidden /> Back to the Coach
    </Link>
  );

  return (
    <>
      <Link to="/coach" className="btn-ghost -ml-2 mb-2">
        <ArrowLeft className="h-4 w-4" aria-hidden /> Coach
      </Link>
      <PageHeader
        icon={Layers}
        title="Flashcard review"
        subtitle="Cards that are due again. Say whether you knew each one and the Coach spaces them out."
      />
      {error && <Alert>{error}</Alert>}
      {!items && !error && <ListSkeleton rows={1} />}
      {items && items.length === 0 && (
        <EmptyState icon={Layers} title="Nothing due right now" action={back}>
          Cards you have reviewed come back here when it is time to see them again.
        </EmptyState>
      )}
      {items && items.length > 0 && <FlashcardDeck items={items} finishedAction={back} />}
    </>
  );
}
