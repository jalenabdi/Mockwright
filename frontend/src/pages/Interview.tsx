import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router";

import { Button, ErrorNote, Icon, LinkButton, Logo, Spinner } from "../components/ui";
import { LevelMeter } from "../components/Waveform";
import { api, ApiError, type InterviewDetail, type Question } from "../lib/api";
import { FullPageSpinner } from "../lib/auth";
import { levelLabel, usePageTitle } from "../lib/format";
import { useQuestionAudio } from "../voice/useQuestionAudio";
import { useVoiceAnswer } from "../voice/useVoiceAnswer";

type Mode = "voice" | "text";
const MODE_KEY = "mockwright.answerMode";

function readMode(): Mode {
  try {
    return localStorage.getItem(MODE_KEY) === "text" ? "text" : "voice";
  } catch {
    return "voice";
  }
}

function Progress({ position, total }: { position: number; total: number }) {
  return (
    <div className="flex items-center gap-4">
      <span className="text-[14px] font-semibold text-muted">
        Question {position} of {total}
      </span>
      <span className="flex gap-1.5" aria-hidden="true">
        {Array.from({ length: total }, (_, i) => (
          <span
            key={i}
            className={`h-[3px] w-10 rounded-full transition-colors duration-300 sm:w-[52px] ${
              i < position ? "bg-fg" : "bg-line-strong"
            }`}
          />
        ))}
      </span>
    </div>
  );
}

function ModeToggle({ mode, onChange, disabled }: { mode: Mode; onChange: (m: Mode) => void; disabled: boolean }) {
  return (
    <div className="inline-flex rounded-full bg-panel-2 p-1" role="tablist" aria-label="Answer with">
      {(["voice", "text"] as const).map((value) => (
        <button
          key={value}
          type="button"
          role="tab"
          aria-selected={mode === value}
          disabled={disabled}
          onClick={() => onChange(value)}
          className={`h-10 rounded-full px-5 text-[15px] font-semibold transition-colors duration-150 ${
            mode === value ? "bg-[#f4f4f6] text-ink" : "text-muted hover:text-fg"
          }`}
        >
          {value === "voice" ? "Voice" : "Text"}
        </button>
      ))}
    </div>
  );
}

export default function Interview() {
  const { interviewId: idParam } = useParams();
  const interviewId = Number(idParam);
  const navigate = useNavigate();
  const location = useLocation();
  const preloaded = (location.state as { interview?: InterviewDetail } | null)?.interview;

  const [interview, setInterview] = useState<InterviewDetail | null>(
    preloaded && preloaded.id === interviewId ? preloaded : null,
  );
  const [question, setQuestion] = useState<Question | null>(interview?.current_question ?? null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [mode, setModeState] = useState<Mode>(readMode);
  const [typed, setTyped] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const audio = useQuestionAudio(interviewId);
  const voice = useVoiceAnswer(interviewId, { onSpeechStart: audio.stop });
  const autoplayedRef = useRef<number | null>(null);

  usePageTitle(question ? `Question ${question.question_order}` : "Interview");

  // Load the interview (unless we arrived with it) and its current question.
  useEffect(() => {
    if (!Number.isInteger(interviewId) || interviewId <= 0) {
      setLoadError("That interview doesn’t exist.");
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const detail = interview ?? (await api.getInterview(interviewId));
        if (cancelled) return;
        if (detail.status === "completed") {
          navigate(`/interviews/${interviewId}/feedback`, { replace: true });
          return;
        }
        setInterview(detail);
        if (!question) {
          const current = detail.current_question ?? (await api.currentQuestion(interviewId)).question;
          if (!cancelled) setQuestion(current);
        }
      } catch (caught) {
        if (cancelled) return;
        setLoadError(
          caught instanceof ApiError && caught.status === 404
            ? "That interview doesn’t exist."
            : caught instanceof Error
              ? caught.message
              : "Could not load the interview.",
        );
      }
    })();
    return () => {
      cancelled = true;
    };
    // Load once per interview id.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [interviewId]);

  // Read each new question aloud in voice mode.
  useEffect(() => {
    if (!question || mode !== "voice" || autoplayedRef.current === question.id) return;
    autoplayedRef.current = question.id;
    void audio.play(question.id, question.question_text);
  }, [question, mode, audio]);

  const setMode = useCallback(
    (next: Mode) => {
      if (next === "text") {
        voice.stop();
        audio.stop();
        // Carry anything already spoken over to the text box.
        if (voice.transcript && !typed) setTyped(voice.transcript);
      }
      setModeState(next);
      try {
        localStorage.setItem(MODE_KEY, next);
      } catch {
        // Preference just won't persist.
      }
    },
    [audio, typed, voice],
  );

  const recording = voice.status !== "idle";
  const answerText = (mode === "voice" ? voice.transcript : typed).trim();

  async function save() {
    if (!interview || !question || !answerText || saving) return;
    setSaving(true);
    setSaveError(null);
    audio.stop();
    try {
      const result = await api.submitAnswer(interview.id, question.id, answerText);
      if (result.status === "completed" || !result.next_question) {
        navigate(`/interviews/${interview.id}/feedback`, { replace: true });
        return;
      }
      setInterview({ ...interview, answered_count: result.answered_count, current_question_position: result.next_question.question_order });
      setQuestion(result.next_question);
      setTyped("");
      voice.reset();
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 409) {
        // Already answered elsewhere (another tab): resync with the server.
        try {
          const current = await api.currentQuestion(interview.id);
          setQuestion(current.question);
          setTyped("");
          voice.reset();
        } catch {
          navigate(`/interviews/${interview.id}/feedback`, { replace: true });
        }
      } else {
        setSaveError(caught instanceof Error ? caught.message : "Could not save your answer.");
      }
    } finally {
      setSaving(false);
    }
  }

  if (loadError) {
    return (
      <div className="flex min-h-dvh flex-col items-center justify-center gap-6 px-4 text-center">
        <p className="text-[18px] text-muted">{loadError}</p>
        <LinkButton to="/history" variant="secondary">Back to History</LinkButton>
      </div>
    );
  }
  if (!interview || !question) return <FullPageSpinner label="Loading interview" />;

  const total = interview.total_questions;
  const isLast = question.question_order >= total;

  return (
    <div className="min-h-dvh">
      <header className="border-b border-line/70">
        <div className="mx-auto grid h-16 max-w-[1140px] grid-cols-[1fr_auto_1fr] items-center gap-4 px-4 sm:px-6">
          <Logo to="/interviews/new" />
          <p className="hidden truncate text-[14px] text-muted sm:block">
            {interview.target_role} · {levelLabel(interview.experience_level)}
          </p>
          <Link
            to="/history"
            onClick={(event) => {
              const unsaved = (mode === "voice" ? voice.transcript : typed).trim();
              if (unsaved && !window.confirm("Your saved answers are kept, but this unsaved answer will be lost. Leave anyway?")) {
                event.preventDefault();
              }
            }}
            className="justify-self-end text-[14px] text-muted transition-colors hover:text-fg"
          >
            Save &amp; Exit
          </Link>
        </div>
      </header>

      <main className="mx-auto w-full max-w-[780px] px-4 pb-24 pt-10 sm:pt-14">
        <Progress position={question.question_order} total={total} />

        <div
          key={question.id}
          className={`rise transition-opacity duration-300 ${saving && !isLast ? "opacity-40" : ""}`}
          aria-busy={saving}
        >
          {saving && !isLast && (
            <p className="mt-6 flex items-center gap-2 text-[14px] text-muted" role="status">
              <Spinner className="size-3.5" /> Reading your answer and writing the next question…
            </p>
          )}
          <h1 className="headline mt-8 text-[32px] sm:text-[44px]" aria-live="polite">
            {question.question_text}
          </h1>

          <button
            type="button"
            onClick={() => (audio.playing ? audio.stop() : void audio.play(question.id, question.question_text))}
            className="mt-5 inline-flex h-11 items-center gap-2.5 rounded-full bg-panel-2 px-4 text-[15px] font-semibold transition-colors hover:bg-[#222226]"
          >
            {audio.loading ? <Spinner className="size-4" /> : <Icon.Speaker className="size-4" />}
            {audio.playing ? "Stop Reading" : "Hear Question Again"}
          </button>
        </div>

        <div className="mt-8">
          <ModeToggle mode={mode} onChange={setMode} disabled={saving || voice.status === "finishing"} />
        </div>

        {mode === "voice" ? (
          <section className="card mt-7 px-6 pb-8 pt-10 sm:px-10" aria-label="Voice answer">
            <div className="flex flex-col items-center">
              <button
                type="button"
                onClick={() => {
                  if (recording) {
                    voice.stop();
                  } else {
                    audio.stop(); // speaking interrupts the interviewer
                    void voice.start();
                  }
                }}
                disabled={saving || voice.status === "finishing"}
                aria-pressed={voice.status === "listening"}
                aria-label={recording ? "Stop recording" : "Start recording"}
                className={`flex size-[88px] items-center justify-center rounded-full bg-[#f4f4f6] text-ink transition-transform duration-150 active:scale-95 ${
                  voice.status === "listening" ? "mic-live" : ""
                }`}
              >
                {voice.status === "connecting" || voice.status === "finishing" ? (
                  <Spinner className="size-6" />
                ) : recording ? (
                  <Icon.Stop className="size-7" />
                ) : (
                  <Icon.Mic className="size-8" />
                )}
              </button>

              <div className="mt-9 w-full max-w-[260px]">
                <LevelMeter levels={voice.levels} active={voice.status === "listening"} />
              </div>

              <p className="mt-6 text-center text-[16px] text-fg/90" role="status">
                {voice.status === "connecting"
                  ? "Connecting…"
                  : voice.status === "listening"
                    ? "Listening. Tap again when you’re done."
                    : voice.status === "finishing"
                      ? "Catching your last words…"
                      : voice.transcript
                        ? "Review your answer, tap the mic to add more, or save it."
                        : "Tap the microphone and answer out loud."}
              </p>
            </div>

            {voice.error && (
              <div className="mt-6 flex flex-col items-center gap-3">
                <ErrorNote>{voice.error.message}</ErrorNote>
                {voice.error.code !== "session_expired" && (
                  <button type="button" onClick={() => setMode("text")} className="text-[14px] font-semibold text-accent hover:underline">
                    Switch to Text
                  </button>
                )}
              </div>
            )}

            <div className="mt-8 border-t border-line pt-6">
              <label htmlFor="transcript" className="mb-2 block text-[13px] font-semibold text-muted">
                Live Transcript
              </label>
              {recording ? (
                <p className="min-h-[3.5em] text-[16px] leading-relaxed" aria-live="polite">
                  {voice.transcript}
                  {voice.interim && <span className="text-muted"> {voice.interim}</span>}
                  {!voice.transcript && !voice.interim && <span className="text-muted">Your words appear here as you speak.</span>}
                </p>
              ) : voice.transcript ? (
                <textarea
                  id="transcript"
                  className="min-h-[120px] w-full resize-y bg-transparent text-[16px] leading-relaxed text-fg focus:outline-none"
                  value={voice.transcript}
                  onChange={(e) => voice.setTranscript(e.target.value)}
                  maxLength={10000}
                />
              ) : (
                <p className="text-[16px] text-muted">Your words appear here as you speak.</p>
              )}
            </div>
          </section>
        ) : (
          <section className="mt-7" aria-label="Text answer">
            <label htmlFor="typed" className="sr-only">Your answer</label>
            <textarea
              id="typed"
              className="input min-h-[260px] resize-y rounded-3xl p-6 text-[16px] leading-relaxed"
              placeholder="Situation, task, action, result. Walk through what happened and what you did."
              value={typed}
              onChange={(e) => setTyped(e.target.value)}
              maxLength={10000}
              autoFocus
            />
            <p className="mt-2 text-right text-[13px] tabular-nums text-faint">
              {typed.trim() ? typed.trim().split(/\s+/).length : 0} words
            </p>
          </section>
        )}

        <div className="mt-7 flex flex-col gap-4">
          {saveError && <ErrorNote>{saveError}</ErrorNote>}
          <Button
            size="lg"
            className="w-full"
            onClick={save}
            loading={saving}
            disabled={!answerText || recording}
          >
            {saving
              ? isLast
                ? "Saving your last answer…"
                : "Writing your next question…"
              : isLast
                ? "Save Answer & Finish"
                : "Save Answer & Continue"}
          </Button>
          {recording && <p className="text-center text-[13px] text-muted">Stop recording to save your answer.</p>}
        </div>
      </main>
    </div>
  );
}
