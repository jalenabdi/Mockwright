import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router";

import { Button, ErrorNote, Icon, LinkButton, Logo, Spinner } from "../components/ui";
import { LevelMeter } from "../components/Waveform";
import { api, ApiError, type FollowUp, type InterviewDetail, type Question } from "../lib/api";
import { FullPageSpinner } from "../lib/auth";
import { levelLabel, usePageTitle } from "../lib/format";
import { wakeAudio } from "../voice/audioMix";
import { useCamera, type CameraStatus, type Clip } from "../voice/useCamera";
import { formatClock, useCountdown } from "../voice/useCountdown";
import { useQuestionAudio, type SpokenLine } from "../voice/useQuestionAudio";
import { useVoiceAnswer } from "../voice/useVoiceAnswer";

const ANSWER_SECONDS = 180;
const FOLLOW_UP_SECONDS = 120;
const WARN_SECONDS = 30;

type Mode = "voice" | "text";
const MODE_KEY = "mockwright.answerMode";

/**
 * Each question is a short conversation. It moves through these steps:
 * waiting (only if the browser needs a click first) → reading (question read aloud)
 * → answering right away (up to 3 minutes; 2 for a follow-up) → finishing (last words)
 * → saving → then either a follow-up or the next question.
 * One video covers a whole question as a conversation: it starts when the question
 * is read aloud and runs through every follow-up. It records the interviewer's
 * voice as well as the candidate's.
 * An empty answer goes to "empty" instead of saving; a failed save to "save_failed".
 */
type Phase = "waiting" | "reading" | "answering" | "finishing" | "saving" | "empty" | "save_failed";

function readMode(): Mode {
  try {
    return localStorage.getItem(MODE_KEY) === "text" ? "text" : "voice";
  } catch {
    return "voice";
  }
}

/** Browsers block audio until the user has clicked something on the page. */
function needsClickFirst(): boolean {
  const activation = (navigator as Navigator & { userActivation?: { hasBeenActive: boolean } }).userActivation;
  return activation ? !activation.hasBeenActive : false;
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
          className={`h-10 rounded-full px-5 text-[15px] font-semibold transition-colors duration-150 disabled:opacity-60 ${
            mode === value ? "bg-[#f4f4f6] text-ink" : "text-muted hover:text-fg"
          }`}
        >
          {value === "voice" ? "Voice" : "Text"}
        </button>
      ))}
    </div>
  );
}

const CAMERA_MESSAGES: Partial<Record<CameraStatus, string>> = {
  blocked: "Camera access is blocked, so this interview won’t be recorded. Allow it in your browser’s site settings and reload to record.",
  missing: "No camera found, so this interview won’t be recorded.",
  unsupported: "This browser can’t record video. Your answers are still saved.",
  lost: "The camera stopped working, so the rest of this interview won’t be recorded. Reload the page to turn it back on.",
};

function CameraTile({ stream, status, recording }: { stream: MediaStream | null; status: CameraStatus; recording: boolean }) {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    video.srcObject = stream;
    if (stream) void video.play().catch(() => undefined);
  }, [stream]);

  const message = CAMERA_MESSAGES[status];
  return (
    <div className="relative aspect-[4/3] w-full overflow-hidden rounded-3xl border border-line bg-panel">
      {stream && (
        <video
          ref={videoRef}
          muted
          playsInline
          autoPlay
          aria-label="Your camera"
          className="size-full -scale-x-100 object-cover"
        />
      )}
      {!stream && (
        <div className="flex size-full flex-col items-center justify-center gap-3 px-6 text-center">
          {status === "starting" || status === "off" ? (
            <Spinner className="size-5" />
          ) : (
            <>
              <Icon.CameraOff className="size-7 text-muted" />
              <p className="text-[13px] leading-relaxed text-muted">{message}</p>
            </>
          )}
        </div>
      )}
      {recording && (
        <span className="absolute left-3 top-3 flex items-center gap-1.5 rounded-full bg-black/65 px-2.5 py-1 text-[12px] font-semibold text-fg">
          <span className="rec-dot size-2 rounded-full bg-danger" aria-hidden="true" />
          REC
        </span>
      )}
    </div>
  );
}

function Clock({ seconds, total, label, warn }: { seconds: number; total: number; label: string; warn?: boolean }) {
  return (
    <div className="w-full">
      <div className="flex items-baseline justify-between gap-4">
        <span className="text-[13px] font-semibold uppercase tracking-wide text-muted">{label}</span>
        <span
          className={`text-[28px] font-bold tabular-nums tracking-tight transition-colors ${warn ? "text-danger" : "text-fg"}`}
          role="timer"
          aria-live="off"
        >
          {formatClock(seconds)}
        </span>
      </div>
      <div className="mt-2 h-1 overflow-hidden rounded-full bg-line-strong" aria-hidden="true">
        <div
          className={`h-full rounded-full transition-[width] duration-300 ease-linear ${warn ? "bg-danger" : "bg-fg"}`}
          style={{ width: `${(seconds / total) * 100}%` }}
        />
      </div>
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
  const [question, setQuestion] = useState<Question | null>(
    interview && !interview.current_follow_up ? interview.current_question : null,
  );
  const [followUp, setFollowUp] = useState<FollowUp | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [mode, setModeState] = useState<Mode>(readMode);
  const [typed, setTyped] = useState("");
  const [phase, setPhase] = useState<Phase>("waiting");
  const [attempt, setAttempt] = useState(0);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [uploadWarning, setUploadWarning] = useState<string | null>(null);

  const audio = useQuestionAudio(interviewId);
  const voice = useVoiceAnswer(interviewId, { onSpeechStart: audio.stop });
  const camera = useCamera();

  const phaseRef = useRef<Phase>("waiting");
  phaseRef.current = phase;
  const runRef = useRef(0); // bumps per question so stale async steps are ignored
  const pendingRef = useRef<string | null>(null); // an answer whose save failed, to retry
  const uploadsRef = useRef<Promise<void>[]>([]);
  const startedRef = useRef<string | null>(null);
  const finishHandledRef = useRef(true); // false while an answer is waiting to be saved
  const followUpRef = useRef<FollowUp | null>(null);
  followUpRef.current = followUp;

  // What the candidate is answering right now: the question, or a follow-up on it.
  const turnKey = followUp ? `f${followUp.id}` : question ? `q${question.id}` : null;

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
          // Ask the server: it also settles a follow-up that was still being decided.
          const current = await api.currentQuestion(interviewId);
          if (cancelled) return;
          setFollowUp(current.follow_up);
          setQuestion(current.question);
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

  // The camera preview runs for the whole interview.
  const startCamera = camera.start;
  useEffect(() => {
    void startCamera();
  }, [startCamera]);

  const currentLine = useCallback((): SpokenLine | null => {
    if (!question) return null;
    const open = followUpRef.current;
    return open
      ? { questionId: question.id, followUpId: open.id, text: open.question_text }
      : { questionId: question.id, text: question.question_text };
  }, [question]);

  const startAnswering = useCallback(() => {
    if (!["reading", "empty"].includes(phaseRef.current)) return;
    audio.stop();
    setSaveError(null);
    setPhase("answering");
    setAttempt((a) => a + 1);
    camera.startClip(); // keeps going if this question's video is already recording
    if (mode === "voice") void voice.start();
  }, [audio, camera, mode, voice]);

  /** Read the current line aloud, then start answering right away. */
  const beginTurn = useCallback(async () => {
    const line = currentLine();
    if (!line) return;
    const run = ++runRef.current;
    setPhase("reading");
    await wakeAudio(); // lets the video record the interviewer's voice too
    if (run !== runRef.current) return;
    camera.startClip();
    await audio.play(line);
    if (run !== runRef.current || phaseRef.current !== "reading") return;
    startAnswering();
  }, [audio, camera, currentLine, startAnswering]);

  // Start each new question or follow-up once it's loaded (after a click if the browser needs one).
  useEffect(() => {
    if (!turnKey || startedRef.current === turnKey) return;
    startedRef.current = turnKey;
    if (needsClickFirst()) setPhase("waiting");
    else void beginTurn();
  }, [turnKey, beginTurn]);

  const finishAnswering = useCallback(() => {
    if (phaseRef.current !== "answering") return;
    setPhase("finishing");
    finishHandledRef.current = false;
    voice.stop();
  }, [voice]);

  const answerLeft = useCountdown(
    followUp ? FOLLOW_UP_SECONDS : ANSWER_SECONDS,
    phase === "answering",
    `${turnKey}-${attempt}`,
    finishAnswering,
  );

  /** The question is over: finish its video and upload it in the background. */
  const closeQuestionVideo = useCallback(
    async (interviewId: number, closed: Question) => {
      const clip: Clip | null = await camera.stopClip();
      if (!clip) return;
      uploadsRef.current.push(
        api.uploadRecording(interviewId, closed.id, clip.video, clip.durationSeconds).catch(() => {
          setUploadWarning(`The video for question ${closed.question_order} couldn’t be saved. Your answers were saved.`);
        }),
      );
    },
    [camera],
  );

  const save = useCallback(
    async (text: string) => {
      if (!interview || !question) return;
      const answering = followUpRef.current;
      pendingRef.current = text;
      setPhase("saving");
      setSaveError(null);
      try {
        const result = await api.submitAnswer(interview.id, question.id, text, answering?.id);
        pendingRef.current = null;
        setTyped("");
        voice.reset();
        if (result.follow_up) {
          setFollowUp(result.follow_up); // same question, same video
          return;
        }
        await closeQuestionVideo(interview.id, question);
        if (result.status === "completed" || !result.next_question) {
          // Score the interview while the last videos upload, so the Feedback page opens with the report ready.
          // If scoring fails here, the Feedback page tries again.
          await Promise.allSettled([...uploadsRef.current, api.createFeedback(interview.id)]);
          navigate(`/interviews/${interview.id}/feedback`, { replace: true });
          return;
        }
        setInterview({
          ...interview,
          answered_count: result.answered_count,
          current_question_position: result.next_question.question_order,
        });
        setFollowUp(null);
        setQuestion(result.next_question);
        window.scrollTo({ top: 0, behavior: "smooth" });
      } catch (caught) {
        if (caught instanceof ApiError && caught.status === 409) {
          // Already answered elsewhere (another tab): resync with the server.
          pendingRef.current = null;
          try {
            const current = await api.currentQuestion(interview.id);
            if (current.question.id !== question.id) await closeQuestionVideo(interview.id, question);
            startedRef.current = null;
            setTyped("");
            voice.reset();
            setFollowUp(current.follow_up);
            setQuestion(current.question);
            setPhase("waiting");
          } catch {
            navigate(`/interviews/${interview.id}/feedback`, { replace: true });
          }
        } else {
          setSaveError(caught instanceof Error ? caught.message : "Could not save your answer.");
          setPhase("save_failed");
        }
      }
    },
    [closeQuestionVideo, interview, navigate, question, voice],
  );

  // Once the last words are in (voice) or straight away (text), save the answer.
  useEffect(() => {
    if (phase !== "finishing" || voice.status !== "idle" || finishHandledRef.current) return;
    finishHandledRef.current = true;
    const text = (mode === "voice" ? voice.transcript : typed).trim();
    if (!text) {
      setPhase("empty"); // nothing heard: offer a retry instead of saving a blank answer
      return;
    }
    void save(text);
  }, [phase, voice.status, voice.transcript, mode, typed, save]);

  const setMode = useCallback(
    (next: Mode) => {
      if (next === mode) return;
      if (next === "text") {
        // Carry what was said so far into the text box.
        const spoken = [voice.transcript, voice.interim].filter(Boolean).join(" ").trim();
        if (spoken) setTyped((current) => (current ? `${current} ${spoken}` : spoken));
        voice.reset();
      } else if (phaseRef.current === "answering") {
        voice.setTranscript(typed.trim());
        setTyped("");
        void voice.start();
      }
      setModeState(next);
      try {
        localStorage.setItem(MODE_KEY, next);
      } catch {
        // Preference just won't persist.
      }
    },
    [mode, typed, voice],
  );

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
  const busy = phase === "finishing" || phase === "saving";
  const answering = phase === "answering";
  const warn = answering && answerLeft <= WARN_SECONDS;

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
              if ((answering || busy) && !window.confirm("Your saved answers are kept, but the answer you’re giving now will be lost. Leave anyway?")) {
                event.preventDefault();
              }
            }}
            className="justify-self-end text-[14px] text-muted transition-colors hover:text-fg"
          >
            Save &amp; Exit
          </Link>
        </div>
      </header>

      <main className="mx-auto grid w-full max-w-[1140px] gap-x-10 gap-y-8 px-4 pb-24 pt-10 [grid-template-areas:'q'_'c'_'a'] sm:px-6 sm:pt-14 lg:grid-cols-[minmax(0,1fr)_340px] lg:[grid-template-areas:'q_c'_'a_c']">
        <div className="[grid-area:q]">
          <Progress position={question.question_order} total={total} />
          <div key={turnKey} className="rise">
            {followUp ? (
              <>
                <p className="mt-8 text-[15px] leading-relaxed text-muted">{question.question_text}</p>
                <p className="mt-6 text-[13px] font-semibold uppercase tracking-wide text-accent">Follow-up</p>
                <h1 className="headline mt-2 text-[30px] sm:text-[40px]" aria-live="polite">
                  {followUp.question_text}
                </h1>
              </>
            ) : (
              <h1 className="headline mt-8 text-[30px] sm:text-[40px]" aria-live="polite">
                {question.question_text}
              </h1>
            )}
            <button
              type="button"
              onClick={() => {
                const line = currentLine();
                if (audio.playing) audio.stop();
                else if (line) void audio.play(line);
              }}
              disabled={answering || busy}
              className="mt-5 inline-flex h-11 items-center gap-2.5 rounded-full bg-panel-2 px-4 text-[15px] font-semibold transition-colors hover:bg-[#222226] disabled:opacity-50"
            >
              {audio.loading ? <Spinner className="size-4" /> : <Icon.Speaker className="size-4" />}
              {audio.playing ? "Stop Reading" : followUp ? "Hear Follow-up Again" : "Hear Question Again"}
            </button>
          </div>
        </div>

        <aside className="w-full max-w-[280px] justify-self-center sm:max-w-[400px] [grid-area:c] lg:sticky lg:top-8 lg:max-w-none lg:self-start" aria-label="Camera">
          <CameraTile stream={camera.stream} status={camera.status} recording={camera.recording} />
          {camera.stream && (
            <p className="mt-3 text-center text-[13px] text-faint">
              {camera.recording
                ? `Recording question ${question.question_order}.`
                : "Recording starts when the question is asked."}
            </p>
          )}
        </aside>

        <div className="[grid-area:a]">
          <ModeToggle mode={mode} onChange={setMode} disabled={busy} />

          <section className="card mt-6 px-6 pb-8 pt-8 sm:px-10" aria-label="Your answer">
            {phase === "waiting" && (
              <div className="flex flex-col items-center gap-5 py-6 text-center">
                <p className="text-[17px] text-fg/90">
                  {followUp
                    ? "Ready when you are. The follow-up will be read aloud, then you answer right away."
                    : "Ready when you are. The question will be read aloud, then you answer right away."}
                </p>
                <Button size="lg" onClick={() => void beginTurn()}>
                  {followUp ? "Hear the Follow-up" : `Start Question ${question.question_order}`}
                </Button>
              </div>
            )}

            {phase === "reading" && (
              <div className="flex flex-col items-center gap-5 py-6 text-center">
                <p className="flex items-center gap-2.5 text-[17px] text-fg/90" role="status">
                  <Icon.Speaker className="size-5 text-muted" /> {followUp ? "Listen to the follow-up…" : "Listen to the question…"}
                </p>
                <button type="button" onClick={startAnswering} className="text-[14px] font-semibold text-accent hover:underline">
                  Skip to answering
                </button>
              </div>
            )}

            {(answering || busy) && (
              <div className="flex flex-col gap-6">
                <Clock
                  seconds={answering ? answerLeft : 0}
                  total={followUp ? FOLLOW_UP_SECONDS : ANSWER_SECONDS}
                  label={answering ? "Time left" : "Time’s up"}
                  warn={warn}
                />

                {mode === "voice" ? (
                  <>
                    <div className="flex flex-col items-center gap-4">
                      <div className="w-full max-w-[260px]">
                        <LevelMeter levels={voice.levels} active={voice.status === "listening"} />
                      </div>
                      <p className="text-center text-[15px] text-fg/90" role="status">
                        {busy
                          ? phase === "finishing"
                            ? "Catching your last words…"
                            : "Thinking about your answer…"
                          : voice.status === "connecting"
                            ? "Connecting…"
                            : voice.status === "listening"
                              ? "Listening. Answer out loud."
                              : "Not listening."}
                      </p>
                    </div>
                    <div className="border-t border-line pt-5">
                      <p className="mb-2 text-[13px] font-semibold text-muted">Live Transcript</p>
                      <p className="min-h-[3.5em] text-[16px] leading-relaxed" aria-live="polite">
                        {voice.transcript}
                        {voice.interim && <span className="text-muted"> {voice.interim}</span>}
                        {!voice.transcript && !voice.interim && <span className="text-muted">Your words appear here as you speak.</span>}
                      </p>
                    </div>
                  </>
                ) : (
                  <div>
                    <label htmlFor="typed" className="sr-only">Your answer</label>
                    <textarea
                      id="typed"
                      className="input min-h-[220px] resize-y rounded-2xl p-5 text-[16px] leading-relaxed"
                      placeholder="Situation, task, action, result. Walk through what happened and what you did."
                      value={typed}
                      onChange={(e) => setTyped(e.target.value)}
                      maxLength={10000}
                      disabled={!answering}
                      autoFocus
                    />
                    <p className="mt-2 text-right text-[13px] tabular-nums text-faint">
                      {typed.trim() ? typed.trim().split(/\s+/).length : 0} words
                    </p>
                  </div>
                )}

                {voice.error && answering && mode === "voice" && (
                  <div className="flex flex-col items-center gap-3">
                    <ErrorNote>{voice.error.message}</ErrorNote>
                    {voice.error.code !== "session_expired" && (
                      <button type="button" onClick={() => setMode("text")} className="text-[14px] font-semibold text-accent hover:underline">
                        Switch to Text
                      </button>
                    )}
                  </div>
                )}

                <Button size="lg" className="w-full" onClick={finishAnswering} loading={busy} disabled={!answering}>
                  {busy ? "Saving…" : "Done Answering"}
                </Button>
              </div>
            )}

            {phase === "empty" && (
              <div className="flex flex-col items-center gap-5 py-4 text-center">
                <p className="text-[17px] font-semibold">We didn’t catch an answer.</p>
                <p className="max-w-[420px] text-[15px] text-muted">
                  {mode === "voice"
                    ? `Check that your microphone is on and not muted, then try again. You’ll get a fresh ${followUp ? 2 : 3} minutes.`
                    : `Type your answer when you try again. You’ll get a fresh ${followUp ? 2 : 3} minutes.`}
                </p>
                <Button size="lg" onClick={startAnswering}>Try Again</Button>
                {mode === "voice" && (
                  <button type="button" onClick={() => setMode("text")} className="text-[14px] font-semibold text-accent hover:underline">
                    Switch to Text
                  </button>
                )}
              </div>
            )}

            {phase === "save_failed" && (
              <div className="flex flex-col items-center gap-5 py-4 text-center">
                {saveError && <ErrorNote>{saveError}</ErrorNote>}
                <Button
                  size="lg"
                  onClick={() => {
                    const pending = pendingRef.current;
                    if (pending) void save(pending);
                  }}
                >
                  Try Saving Again
                </Button>
              </div>
            )}
          </section>

          {uploadWarning && (
            <p className="mt-4 text-center text-[13px] text-muted" role="status">{uploadWarning}</p>
          )}
        </div>
      </main>
    </div>
  );
}
