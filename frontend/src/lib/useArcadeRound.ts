import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";

import { errorMessage } from "../api/client";
import {
  GameResult,
  GameSlug,
  RoundBase,
  RoundSubmission,
  startChallengeRound,
  startRound,
  submitChallenge,
  submitRound,
} from "../api/games";

/**
 * Loading and submitting one round of any Arcade game: your own, or a
 * friend's challenge when the URL carries ?challenge=<id>. The game pages
 * only deal with play; where the round comes from and goes to is here.
 */
export function useArcadeRound<T extends RoundBase>(slug: GameSlug) {
  const { courseId = "" } = useParams<{ courseId: string }>();
  const [params] = useSearchParams();
  const challengeId = params.get("challenge");
  const documentId = params.get("document");

  const [round, setRound] = useState<T | null>(null);
  const [result, setResult] = useState<GameResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  // A game timer that fires after the student has left the page must not
  // submit the abandoned round.
  const active = useRef(true);
  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
    };
  }, []);

  const load = useCallback(() => {
    setRound(null);
    setResult(null);
    setError(null);
    const request = challengeId ? startChallengeRound<T>(challengeId) : startRound<T>(courseId, slug, documentId);
    request.then(setRound).catch((err) => setError(errorMessage(err, "Could not start a round.")));
  }, [challengeId, courseId, documentId, slug]);

  useEffect(load, [load]);

  const submit = useCallback(
    async (submission: RoundSubmission) => {
      if (!round || !active.current) return;
      setIsSubmitting(true);
      try {
        setResult(
          challengeId ? await submitChallenge(challengeId, submission) : await submitRound(round.round_id, submission),
        );
      } catch (err) {
        setError(errorMessage(err, "Could not save your score."));
      } finally {
        setIsSubmitting(false);
      }
    },
    [challengeId, round],
  );

  return {
    round,
    result,
    error,
    isSubmitting,
    load,
    submit,
    challengeId,
    /** Where "back" goes: the course's Arcade, or the challenges list. */
    backTo: challengeId ? "/friends?tab=challenges" : `/play?course=${courseId}`,
  };
}
