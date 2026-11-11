import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "react-router";

import { AppHeader } from "../components/AppHeader";
import { ScoreCard } from "../components/ScoreCard";
import { Button, Icon, LinkButton, Spinner } from "../components/ui";
import { api, ApiError, type FeedbackReport, type InterviewDetail, type QuestionGrade } from "../lib/api";
import { FullPageSpinner } from "../lib/auth";
import { formatDate, levelLabel, usePageTitle } from "../lib/format";

function ListCard({ title, items }: { title: string; items: string[] }) {
  return (
    <section className="card p-7 sm:p-8">
      <h2 className="text-[20px] font-bold tracking-tight">{title}</h2>
      <ul className="mt-5 flex list-disc flex-col gap-4 pl-5 text-[15px] leading-relaxed text-fg/90 marker:text-muted">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}

/** Loads an answer's video only when its row is opened. */
function AnswerVideo({ interviewId, questionId }: { interviewId: number; questionId: number }) {
  const [url, setUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let objectUrl: string | null = null;
    let cancelled = false;
    api
      .recording(interviewId, questionId)
      .then((video) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(video);
        setUrl(objectUrl);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [interviewId, questionId]);

  if (failed) return <p className="mb-5 text-[14px] text-muted">Couldn’t load the video for this answer.</p>;
  return (
    <div className="mb-5 aspect-[4/3] w-full max-w-[480px] overflow-hidden rounded-2xl border border-line bg-panel">
      {url ? (
        <video src={url} controls playsInline preload="metadata" className="size-full object-cover" aria-label="Your recorded answer" />
      ) : (
        <div className="flex size-full items-center justify-center">
          <Spinner className="size-5" />
        </div>
      )}
    </div>
  );
}

function AnswerRow({
  interviewId,
  questionId,
  order,
  question,
  answer,
  hasRecording,
  grade,
}: {
  interviewId: number;
  questionId: number;
  order: number;
  question: string;
  answer: string | null;
  hasRecording: boolean;
  grade: QuestionGrade | undefined;
}) {
  const [open, setOpen] = useState(false);
  const id = `answer-${order}`;
  return (
    <li className="border-t border-line">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-controls={id}
        className="flex w-full items-center gap-4 py-6 text-left"
      >
        <span className="w-4 shrink-0 text-[15px] tabular-nums text-muted">{order}</span>
        <span className="flex-1 text-[16px] font-semibold leading-snug">{question}</span>
        {hasRecording && (
          <span className="hidden shrink-0 rounded-full bg-panel-2 px-2.5 py-1 text-[12px] font-semibold text-muted sm:inline">Video</span>
        )}
        {grade && (
          <span className="shrink-0 text-[15px] font-bold tabular-nums" aria-label={`Score ${grade.score} out of 100`}>
            {grade.score}
            <span className="text-[12px] font-medium text-muted">/100</span>
          </span>
        )}
        <Icon.Chevron
          className={`size-4 shrink-0 text-muted transition-transform duration-200 ${open ? "rotate-90" : ""}`}
          aria-hidden="true"
        />
      </button>
      {open && (
        <div id={id} className="rise pb-6 pl-8 pr-8">
          {hasRecording && <AnswerVideo interviewId={interviewId} questionId={questionId} />}
          {grade && (
            <div className="mb-5">
              <p className="mb-1.5 text-[12px] font-semibold uppercase tracking-wide text-faint">Why {grade.score}</p>
              <p className="text-[15px] leading-relaxed text-fg/90">{grade.comment}</p>
            </div>
          )}
          <p className="mb-1.5 text-[12px] font-semibold uppercase tracking-wide text-faint">Your answer</p>
          <p className="whitespace-pre-wrap text-[15px] leading-relaxed text-fg/85">{answer ?? "No answer saved."}</p>
        </div>
      )}
    </li>
  );
}

type GenerationState = { kind: "idle" } | { kind: "generating" } | { kind: "error"; message: string; retryable: boolean };

export default function Feedback() {
  usePageTitle("Your Feedback");
  const interviewId = Number(useParams().interviewId);
  const [interview, setInterview] = useState<InterviewDetail | null>(null);
  const [report, setReport] = useState<FeedbackReport | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [generation, setGeneration] = useState<GenerationState>({ kind: "idle" });

  const inFlightRef = useRef(false);

  const generate = useCallback(async () => {
    if (inFlightRef.current) return; // one Gemini call at a time
    inFlightRef.current = true;
    setGeneration({ kind: "generating" });
    try {
      setReport(await api.createFeedback(interviewId));
      setGeneration({ kind: "idle" });
    } catch (caught) {
      const status = caught instanceof ApiError ? caught.status : 0;
      setGeneration({
        kind: "error",
        retryable: status !== 503,
        message:
          status === 503
            ? "Feedback isn’t available yet because the AI service isn’t set up on this server. Your answers are saved, so come back once it is."
            : caught instanceof Error
              ? caught.message
              : "Could not generate feedback right now.",
      });
    } finally {
      inFlightRef.current = false;
    }
  }, [interviewId]);

  useEffect(() => {
    let cancelled = false;
    api
      .getInterview(interviewId)
      .then((detail) => {
        if (cancelled) return;
        setInterview(detail);
        if (detail.feedback) setReport(detail.feedback);
        else if (detail.status === "completed") void generate();
      })
      .catch((caught) => {
        if (!cancelled) {
          setLoadError(caught instanceof ApiError && caught.status === 404 ? "That interview doesn’t exist." : "Could not load this interview.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [interviewId, generate]);

  if (loadError) {
    return (
      <div className="min-h-dvh">
        <AppHeader />
        <div className="flex flex-col items-center gap-6 px-4 pt-32 text-center">
          <p className="text-[18px] text-muted">{loadError}</p>
          <LinkButton to="/history" variant="secondary">Back to History</LinkButton>
        </div>
      </div>
    );
  }
  if (!interview) return <FullPageSpinner label="Loading feedback" />;

  const meta = `${interview.target_role} · ${levelLabel(interview.experience_level)} · ${formatDate(interview.created_at)}`;

  return (
    <div className="min-h-dvh">
      <AppHeader />
      <main className="mx-auto w-full max-w-[960px] px-4 pb-24 pt-12 sm:px-6 sm:pt-16">
        <header className="rise">
          <h1 className="headline text-[44px] sm:text-[56px]">Your feedback.</h1>
          <p className="mt-3 text-[17px] text-muted">{meta}</p>
        </header>

        {interview.status !== "completed" ? (
          <section className="card mt-10 flex flex-col items-start gap-5 p-8">
            <p className="text-[17px] text-fg/90">
              You’ve answered {interview.answered_count} of {interview.total_questions} questions. Finish the interview to get your
              score.
            </p>
            <LinkButton to={`/interviews/${interview.id}`}>Continue Interview</LinkButton>
          </section>
        ) : report ? (
          <div className="rise mt-10 flex flex-col gap-5">
            <ScoreCard report={report} />
            <div className="grid gap-5 md:grid-cols-2">
              <ListCard title="Strengths" items={report.strengths} />
              <ListCard title="Areas for Improvement" items={report.improvements} />
            </div>
            <section className="rounded-3xl bg-[#f4f4f6] p-7 text-ink sm:p-8">
              <p className="text-[14px] font-medium text-[#55555c]">Your Next Step</p>
              <p className="mt-2 text-[22px] font-semibold leading-snug tracking-tight sm:text-[26px]">{report.next_step}</p>
            </section>
          </div>
        ) : generation.kind === "error" ? (
          <section className="card mt-10 flex flex-col items-start gap-5 p-8" role="alert">
            <p className="text-[17px] leading-relaxed text-fg/90">{generation.message}</p>
            {generation.retryable && <Button onClick={generate}>Try Again</Button>}
          </section>
        ) : (
          <section className="card mt-10 flex flex-col items-center gap-4 px-8 py-16 text-center" role="status">
            <Spinner className="size-7" />
            <p className="text-[18px] font-semibold">Scoring your interview…</p>
            <p className="max-w-[380px] text-[15px] text-muted">
              Reading all five answers for relevance, structure, specifics, your own contribution and delivery.
            </p>
          </section>
        )}

        <section className="mt-16" aria-labelledby="answers-heading">
          <h2 id="answers-heading" className="headline mb-4 text-[28px] sm:text-[32px]">Your answers.</h2>
          <ol className="border-b border-line">
            {interview.questions.map((q) => (
              <AnswerRow
                key={q.id}
                interviewId={interview.id}
                questionId={q.id}
                order={q.question_order}
                question={q.question_text}
                answer={q.answer_text}
                hasRecording={q.has_recording}
                grade={report?.question_grades?.find((g) => g.question_number === q.question_order)}
              />
            ))}
          </ol>
        </section>

        <div className="mt-12 flex flex-wrap gap-3">
          <LinkButton to="/interviews/new" size="lg">Practice Again</LinkButton>
          <LinkButton to="/history" variant="secondary" size="lg">View History</LinkButton>
        </div>
      </main>
    </div>
  );
}
