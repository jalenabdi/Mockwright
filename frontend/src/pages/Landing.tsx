import { useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router";

import { ScoreCard } from "../components/ScoreCard";
import { Icon, LinkButton, Logo } from "../components/ui";
import { AnimatedWaveform } from "../components/Waveform";
import type { FeedbackReport } from "../lib/api";
import { useAuth } from "../lib/auth";
import { usePageTitle } from "../lib/format";

const SAMPLE_REPORT: FeedbackReport = {
  relevance_score: 18,
  star_structure_score: 15,
  specificity_score: 14,
  individual_contribution_score: 17,
  communication_score: 18,
  total_score: 82,
  strengths: [],
  improvements: [],
  next_step: "",
  question_grades: [],
};

const DEMO_TRANSCRIPT =
  "On my last project, two of us wanted different approaches to the API, so I set up a quick call to walk through both";

function useTypewriter(text: string, speedMs = 45, pauseMs = 2600) {
  const [count, setCount] = useState(0);
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setCount(text.length);
      return;
    }
    const delay = count >= text.length ? pauseMs : speedMs;
    const timer = window.setTimeout(() => setCount((c) => (c >= text.length ? 0 : c + 1)), delay);
    return () => window.clearTimeout(timer);
  }, [count, text, speedMs, pauseMs]);
  return text.slice(0, count);
}

function Eyebrow({ children }: { children: ReactNode }) {
  return <p className="mb-3 text-[13px] font-semibold text-accent">{children}</p>;
}

function Section({ id, children, className = "" }: { id?: string; children: ReactNode; className?: string }) {
  return (
    <section id={id} className={`mx-auto max-w-[1040px] scroll-mt-20 px-4 sm:px-6 ${className}`}>
      {children}
    </section>
  );
}

function DemoCard() {
  const typed = useTypewriter(DEMO_TRANSCRIPT);
  return (
    <div className="card mx-auto w-full max-w-[640px] p-6 text-left shadow-[0_40px_120px_-40px_rgba(76,157,255,0.25)] sm:p-8">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 text-[12px] font-medium text-muted">
          Question 2 of 5
          <span className="flex gap-1" aria-hidden="true">
            {[0, 1, 2, 3, 4].map((i) => (
              <span key={i} className={`h-[3px] w-5 rounded-full ${i < 2 ? "bg-fg" : "bg-line-strong"}`} />
            ))}
          </span>
        </div>
        <span className="flex size-8 items-center justify-center rounded-full bg-panel-2 text-fg" aria-hidden="true">
          <Icon.Pause className="size-3.5" />
        </span>
      </div>
      <p className="mt-6 text-[22px] font-bold leading-snug tracking-tight sm:text-[26px]">
        “Describe a time you disagreed with a teammate. What did you do?”
      </p>
      <AnimatedWaveform className="my-7" />
      <div className="border-t border-line pt-4">
        <p className="mb-1.5 text-[12px] font-medium text-muted">Live transcript</p>
        <p className="min-h-[3em] text-[14px] leading-relaxed text-fg/90">
          {typed}
          <span className="caret ml-px inline-block h-[1em] w-px translate-y-[2px] bg-fg" aria-hidden="true" />
        </p>
      </div>
    </div>
  );
}

const STEPS = [
  {
    title: "Choose your target.",
    body: "Enter the role you’re going for and pick a level: Intern, Entry-level, Junior, or Senior. Add the job description if you have one.",
  },
  {
    title: "Have the conversation.",
    body: "5 behavioral questions, one at a time, each shaped by what you said before. Answer out loud with your microphone, or type if you’d rather.",
  },
  {
    title: "See your score.",
    body: "Get an overall score out of 100, broken down across 5 categories, with your strengths and what to improve.",
  },
  {
    title: "Come back sharper.",
    body: "Every interview is saved. Review past questions, answers, and feedback reports whenever you want.",
  },
];

const VOICE_FEATURES = [
  { icon: Icon.Speaker, title: "Hear every question.", body: "Your interviewer reads each question aloud, the way it happens in the room." },
  { icon: Icon.Transcript, title: "Watch your words appear.", body: "A live transcript follows along as you speak, so you can see exactly what you said." },
  { icon: Icon.Mic, title: "Interrupt naturally.", body: "Jump in whenever you’re ready. The interviewer stops and listens, just like a person would." },
  { icon: Icon.Keyboard, title: "Rather type?", body: "Switch to text on any question. Typed answers are saved through the same flow as voice." },
];

const HISTORY_SAMPLE = [
  { role: "Software Engineer", level: "Intern", score: 82 },
  { role: "Product Manager", level: "Entry-level", score: 74 },
  { role: "Data Analyst", level: "Junior", score: 68 },
];

const STACK = ["FastAPI", "PostgreSQL", "Gemini", "Deepgram", "WebSockets"];

export default function Landing() {
  usePageTitle("");
  const { token } = useAuth();
  const startHref = token ? "/interviews/new" : "/signup";

  return (
    <div className="overflow-x-clip">
      <header className="sticky top-0 z-20 border-b border-transparent bg-ink/80 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-[1140px] items-center justify-between px-4 sm:px-6">
          <Logo />
          <nav className="hidden items-center gap-8 text-[14px] text-muted md:flex" aria-label="Sections">
            <a href="#how-it-works" className="transition-colors hover:text-fg">How It Works</a>
            <a href="#voice" className="transition-colors hover:text-fg">Voice</a>
            <a href="#feedback" className="transition-colors hover:text-fg">Feedback</a>
            <a href="#history" className="transition-colors hover:text-fg">History</a>
          </nav>
          <div className="flex items-center gap-2 sm:gap-4">
            {token ? (
              <LinkButton to="/interviews/new" size="sm">Open App</LinkButton>
            ) : (
              <>
                <Link to="/login" className="px-2 text-[14px] text-muted transition-colors hover:text-fg">Log In</Link>
                <LinkButton to="/signup" size="sm">Get Started</LinkButton>
              </>
            )}
          </div>
        </div>
      </header>

      <main>
        <Section className="pb-24 pt-16 text-center sm:pt-24">
          <div className="rise">
            <Eyebrow>Voice-first interview practice</Eyebrow>
            <h1 className="headline text-[52px] sm:text-[84px]">Practice your story.</h1>
            <p className="mx-auto mt-5 max-w-[520px] text-[17px] leading-relaxed text-muted sm:text-[19px]">
              Strengthen your answers. Walk into the interview ready. Mockwright is a live mock interview for any role,
              with feedback on every answer you give.
            </p>
            <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
              <LinkButton to={startHref}>Start Practicing</LinkButton>
              <a href="#how-it-works" className="text-[15px] font-medium text-accent hover:underline">
                See How It Works ›
              </a>
            </div>
          </div>
          <div className="rise mt-14" style={{ animationDelay: "120ms" }}>
            <DemoCard />
          </div>
        </Section>

        <Section className="py-24 sm:py-32">
          <p className="headline max-w-[860px] text-[32px] sm:text-[46px]">
            Behavioral interviews aren’t won by knowing the answer.{" "}
            <span className="text-muted">
              They’re won by telling it well. Mockwright gives you a place to say it out loud, hear how it lands, and fix it
              before the real thing.
            </span>
          </p>
        </Section>

        <Section id="how-it-works" className="py-20">
          <Eyebrow>How It Works</Eyebrow>
          <h2 className="headline max-w-[460px] text-[38px] sm:text-[48px]">Four steps from nervous to ready.</h2>
          <ol className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {STEPS.map((step, i) => (
              <li key={step.title} className="card p-6">
                <span className="text-[13px] tabular-nums text-muted">0{i + 1}</span>
                <h3 className="mt-3 text-[18px] font-bold leading-tight tracking-tight">{step.title}</h3>
                <p className="mt-3 text-[14px] leading-relaxed text-muted">{step.body}</p>
              </li>
            ))}
          </ol>
        </Section>

        <Section id="voice" className="py-20">
          <Eyebrow>Live Voice</Eyebrow>
          <h2 className="headline text-[38px] sm:text-[48px]">
            It’s a conversation.
            <br />
            Not a quiz.
          </h2>
          <p className="mt-4 max-w-[520px] text-[17px] leading-relaxed text-muted">
            Real interviews happen out loud. So does practice. Mockwright talks with you through your browser’s microphone, in
            real time.
          </p>
          <div className="mt-10 grid gap-4 sm:grid-cols-2">
            {VOICE_FEATURES.map(({ icon: FeatureIcon, title, body }) => (
              <div key={title} className="card p-7">
                <span className="flex size-9 items-center justify-center rounded-full bg-panel-2" aria-hidden="true">
                  <FeatureIcon className="size-4" />
                </span>
                <h3 className="mt-6 text-[18px] font-bold tracking-tight">{title}</h3>
                <p className="mt-2 text-[14px] leading-relaxed text-muted">{body}</p>
              </div>
            ))}
          </div>
        </Section>

        <Section id="feedback" className="py-20">
          <Eyebrow>Feedback</Eyebrow>
          <h2 className="headline text-[38px] sm:text-[48px]">Feedback you can act on.</h2>
          <p className="mt-4 max-w-[560px] text-[17px] leading-relaxed text-muted">
            After your 5th answer, Mockwright scores the whole interview and tells you what worked, what didn’t, and what to do
            next.
          </p>
          <div className="mt-10">
            <ScoreCard report={SAMPLE_REPORT} badge="Sample report" />
          </div>
          <div className="mt-4 grid gap-4 sm:grid-cols-3">
            {[
              ["Strengths", "What you did well, called out so you know to keep doing it."],
              ["Areas for Improvement", "Where your answers lost points, so you know what to tighten."],
              ["One Next Step", "A single, clear recommendation to work on before your next interview."],
            ].map(([title, body]) => (
              <div key={title} className="card p-6">
                <h3 className="text-[17px] font-bold tracking-tight">{title}</h3>
                <p className="mt-2 text-[14px] leading-relaxed text-muted">{body}</p>
              </div>
            ))}
          </div>
        </Section>

        <Section id="history" className="py-20">
          <div className="grid items-center gap-10 md:grid-cols-2">
            <div>
              <Eyebrow>History</Eyebrow>
              <h2 className="headline text-[38px] sm:text-[48px]">
                Every interview,
                <br />
                saved.
              </h2>
              <p className="mt-4 max-w-[400px] text-[17px] leading-relaxed text-muted">
                Go back to any completed interview. Reread the questions, your answers, and the full feedback report.
              </p>
            </div>
            <ul className="card divide-y divide-line overflow-hidden">
              {HISTORY_SAMPLE.map((item) => (
                <li key={item.role} className="flex items-center justify-between px-6 py-5">
                  <div>
                    <p className="text-[15px] font-semibold">{item.role}</p>
                    <p className="text-[13px] text-muted">{item.level}</p>
                  </div>
                  <span className="text-[22px] font-bold tabular-nums">{item.score}</span>
                </li>
              ))}
            </ul>
          </div>
        </Section>

        <Section className="py-12">
          <div className="flex flex-col gap-4 border-y border-line py-6 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-[13px] text-muted">Under the Hood</p>
            <ul className="flex flex-wrap gap-2">
              {STACK.map((item) => (
                <li key={item} className="rounded-full border border-line px-3 py-1.5 text-[12px] text-muted">
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </Section>

        <Section className="py-28 text-center sm:py-36">
          <h2 className="headline text-[44px] text-muted sm:text-[64px]">
            Walk into the
            <br />
            interview ready.
          </h2>
          <LinkButton to={startHref} className="mt-8">
            {token ? "Start an Interview" : "Create Your Account"}
          </LinkButton>
        </Section>
      </main>

      <footer className="border-t border-line/70">
        <div className="mx-auto flex max-w-[1140px] flex-col gap-4 px-4 py-8 text-[13px] text-muted sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <p>Mockwright. Behavioral interview practice for any role.</p>
          <nav className="flex gap-6" aria-label="Footer">
            <Link to="/signup" className="hover:text-fg">Sign Up</Link>
            <Link to="/login" className="hover:text-fg">Log In</Link>
            <a href="https://github.com/jalenabdi/Mockwright" className="hover:text-fg" target="_blank" rel="noreferrer">
              GitHub
            </a>
          </nav>
        </div>
      </footer>
    </div>
  );
}
