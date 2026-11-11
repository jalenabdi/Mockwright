import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router";

import { AppHeader } from "../components/AppHeader";
import { Button, ErrorNote } from "../components/ui";
import { api, type ExperienceLevel } from "../lib/api";
import { LEVELS, usePageTitle } from "../lib/format";

export default function NewInterview() {
  usePageTitle("New Interview");
  const navigate = useNavigate();
  const [role, setRole] = useState("");
  const [level, setLevel] = useState<ExperienceLevel>("intern");
  const [jobDescription, setJobDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

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
