import { useEffect, useRef, useState, type ChangeEvent, type FormEvent } from "react";
import { useNavigate } from "react-router";

import { AppHeader } from "../components/AppHeader";
import { Button, ErrorNote, Spinner } from "../components/ui";
import { api, type ExperienceLevel, type SavedResume } from "../lib/api";
import { formatDate, LEVELS, usePageTitle } from "../lib/format";

const MAX_RESUME_BYTES = 5 * 1024 * 1024;
const RESUME_TYPES = ".pdf,.docx,.txt,.md";

/**
 * The resume saved to the account. Uploading reads its text on the server and
 * keeps it for every future interview; `use` says whether this one is based on it.
 */
function ResumeField({
  resume,
  onChange,
  use,
  onUseChange,
}: {
  resume: SavedResume | null | undefined;
  onChange: (resume: SavedResume | null) => void;
  use: boolean;
  onUseChange: (use: boolean) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState<"uploading" | "removing" | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = ""; // picking the same file again should still upload it
    if (!file) return;
    if (file.size > MAX_RESUME_BYTES) {
      setError("Resumes can be up to 5 MB.");
      return;
    }
    setError(null);
    setBusy("uploading");
    try {
      onChange(await api.uploadResume(file));
      onUseChange(true);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Couldn’t read that resume.");
    } finally {
      setBusy(null);
    }
  }

  async function remove() {
    setError(null);
    setBusy("removing");
    try {
      await api.deleteResume();
      onChange(null);
      onUseChange(false);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Couldn’t remove the resume.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div>
      <p className="label">
        Resume <span className="font-normal text-muted">(Optional)</span>
      </p>
      <input ref={inputRef} type="file" accept={RESUME_TYPES} className="sr-only" tabIndex={-1} onChange={onFile} aria-label="Upload your resume" />

      {resume === undefined ? (
        <div className="flex h-[88px] items-center justify-center rounded-2xl border border-line-strong bg-panel">
          <Spinner className="size-5" />
        </div>
      ) : resume === null ? (
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={busy !== null}
          className="flex w-full flex-col items-center gap-1.5 rounded-2xl border border-dashed border-line-strong bg-panel px-6 py-6 text-center transition-colors hover:border-faint disabled:opacity-60"
        >
          <span className="flex items-center gap-2 text-[16px] font-semibold">
            {busy === "uploading" && <Spinner className="size-4" />}
            {busy === "uploading" ? "Reading your resume…" : "Upload Your Resume"}
          </span>
          <span className="text-[14px] text-muted">
            PDF, Word or text, up to 5 MB. Questions will be about your real experience, and it’s saved for next time.
          </span>
        </button>
      ) : (
        <div className="rounded-2xl border border-line-strong bg-panel p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="truncate text-[16px] font-semibold">{resume.file_name}</p>
              <p className="mt-0.5 text-[13px] text-muted">
                {resume.word_count.toLocaleString()} words read · Saved {formatDate(resume.updated_at)}
              </p>
            </div>
            <div className="flex gap-4 text-[14px] font-semibold">
              <button type="button" onClick={() => inputRef.current?.click()} disabled={busy !== null} className="text-accent hover:underline disabled:opacity-60">
                {busy === "uploading" ? "Reading…" : "Replace"}
              </button>
              <button type="button" onClick={remove} disabled={busy !== null} className="text-muted hover:text-fg disabled:opacity-60">
                {busy === "removing" ? "Removing…" : "Remove"}
              </button>
            </div>
          </div>
          <p className="mt-3 line-clamp-3 whitespace-pre-line text-[13px] leading-relaxed text-faint">{resume.preview}</p>
          <label className="mt-4 flex cursor-pointer items-center gap-3 border-t border-line pt-4 text-[15px]">
            <input type="checkbox" checked={use} onChange={(e) => onUseChange(e.target.checked)} className="size-[18px] accent-[#f4f4f6]" />
            Ask questions based on my resume
          </label>
        </div>
      )}
      {error && (
        <div className="mt-3">
          <ErrorNote>{error}</ErrorNote>
        </div>
      )}
    </div>
  );
}

export default function NewInterview() {
  usePageTitle("New Interview");
  const navigate = useNavigate();
  const [role, setRole] = useState("");
  const [level, setLevel] = useState<ExperienceLevel>("intern");
  const [jobDescription, setJobDescription] = useState("");
  const [resume, setResume] = useState<SavedResume | null | undefined>(undefined); // undefined while loading
  const [useResume, setUseResume] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api
      .resume()
      .then((saved) => !cancelled && setResume(saved))
      .catch(() => !cancelled && setResume(null)); // still lets them upload one
    return () => {
      cancelled = true;
    };
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const targetRole = role.trim();
    if (!targetRole) {
      setError("Enter the role you’re interviewing for.");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      const interview = await api.startInterview({
        target_role: targetRole,
        experience_level: level,
        job_description: jobDescription.trim() || undefined,
        use_resume: Boolean(resume) && useResume,
      });
      navigate(`/interviews/${interview.id}`, { state: { interview } });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not start the interview.");
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-dvh">
      <AppHeader />
      <main className="mx-auto w-full max-w-[640px] px-4 pb-24 pt-14 sm:pt-20">
        <div className="rise">
          <h1 className="headline text-[40px] sm:text-[52px]">Set up your interview.</h1>
          <p className="mt-4 text-[17px] leading-relaxed text-muted sm:text-[19px]">
            Tell Mockwright what you’re interviewing for. You’ll get 5 behavioral questions to answer by voice or text, each
            one shaped by your last answer.
          </p>
        </div>

        <form onSubmit={onSubmit} className="rise mt-12 flex flex-col gap-10" style={{ animationDelay: "60ms" }} noValidate>
          <div>
            <label htmlFor="role" className="label">Target Role</label>
            <input
              id="role"
              className="input"
              placeholder="e.g. Software Engineer..."
              maxLength={100}
              autoComplete="organization-title"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              autoFocus
            />
          </div>

          <fieldset>
            <legend className="label">Experience Level</legend>
            <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4" role="radiogroup">
              {LEVELS.map(({ value, label }) => {
                const selected = value === level;
                return (
                  <button
                    key={value}
                    type="button"
                    role="radio"
                    aria-checked={selected}
                    onClick={() => setLevel(value)}
                    className={`h-[52px] rounded-2xl border text-[16px] font-semibold transition-colors duration-150 ${
                      selected ? "border-fg bg-[#f4f4f6] text-ink" : "border-line-strong bg-panel text-fg hover:border-faint"
                    }`}
                  >
                    {label}
                  </button>
                );
              })}
            </div>
          </fieldset>

          <div>
            <label htmlFor="jd" className="label">
              Job Description <span className="font-normal text-muted">(Optional)</span>
            </label>
            <textarea
              id="jd"
              className="input min-h-[180px] resize-y leading-relaxed"
              placeholder="Paste the job description..."
              maxLength={5000}
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
            />
          </div>

          <ResumeField resume={resume} onChange={setResume} use={useResume} onUseChange={setUseResume} />

          <div className="flex flex-col gap-4">
            {error && <ErrorNote>{error}</ErrorNote>}
            <Button type="submit" size="lg" loading={submitting} className="w-full">
              {submitting ? "Writing your first question…" : "Start Interview"}
            </Button>
            <p className="flex justify-center gap-6 text-[14px] text-muted">
              <span>5 questions</span>
              <span>Voice or text</span>
              <span>Feedback at the end</span>
            </p>
          </div>
        </form>
      </main>
    </div>
  );
}
