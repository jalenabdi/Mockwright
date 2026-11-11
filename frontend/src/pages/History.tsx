import { useEffect, useState } from "react";
import { Link } from "react-router";

import { AppHeader } from "../components/AppHeader";
import { ErrorNote, Icon, LinkButton, Spinner } from "../components/ui";
import { api, type InterviewSummary } from "../lib/api";
import { formatDate, levelLabel, usePageTitle } from "../lib/format";

function Row({ item }: { item: InterviewSummary }) {
  const completed = item.status === "completed";
  const href = completed ? `/interviews/${item.id}/feedback` : `/interviews/${item.id}`;
  return (
    <li>
      <Link to={href} className="group flex items-center gap-4 px-6 py-5 transition-colors hover:bg-panel-2 sm:px-8">
        <div className="min-w-0 flex-1">
          <p className="truncate text-[17px] font-bold tracking-tight">{item.target_role}</p>
          <p className="mt-0.5 text-[14px] text-muted">
            {levelLabel(item.experience_level)} · {formatDate(item.created_at)}
          </p>
        </div>
        {item.total_score !== null ? (
          <p className="shrink-0">
            <span className="text-[30px] font-bold tabular-nums tracking-tight">{item.total_score}</span>
            <span className="text-[14px] text-muted"> / 100</span>
          </p>
        ) : completed ? (
          <span className="shrink-0 text-[14px] font-semibold text-accent">Get feedback</span>
        ) : (
          <span className="flex shrink-0 items-center gap-3">
            <span className="hidden text-[14px] text-muted sm:inline">
              {item.answered_count} of {item.total_questions} answered
            </span>
            <span className="rounded-full bg-pill px-4 py-2 text-[13px] font-semibold text-ink">Resume</span>
          </span>
        )}
        <Icon.Chevron className="size-4 shrink-0 text-muted transition-transform duration-150 group-hover:translate-x-0.5" aria-hidden="true" />
      </Link>
    </li>
  );
}

export default function History() {
  usePageTitle("History");
  const [items, setItems] = useState<InterviewSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listInterviews()
      .then(setItems)
      .catch((caught) => setError(caught instanceof Error ? caught.message : "Could not load your history."));
  }, []);

  const completedCount = items?.filter((i) => i.status === "completed").length ?? 0;

  return (
    <div className="min-h-dvh">
      <AppHeader />
      <main className="mx-auto w-full max-w-[880px] px-4 pb-24 pt-12 sm:px-6 sm:pt-16">
        <div className="rise flex flex-wrap items-end justify-between gap-6">
          <div>
            <h1 className="headline text-[44px] sm:text-[56px]">History.</h1>
            {items && (
              <p className="mt-2 text-[17px] text-muted">
                {completedCount} completed interview{completedCount === 1 ? "" : "s"}
              </p>
            )}
          </div>
          <LinkButton to="/interviews/new">New Interview</LinkButton>
        </div>

        <div className="mt-10">
          {error ? (
            <ErrorNote>{error}</ErrorNote>
          ) : items === null ? (
            <div className="flex justify-center py-20" role="status">
              <Spinner className="size-6" />
            </div>
          ) : items.length === 0 ? (
            <div className="card flex flex-col items-center gap-5 px-8 py-16 text-center">
              <p className="text-[20px] font-bold tracking-tight">No interviews yet.</p>
              <p className="max-w-[340px] text-[15px] text-muted">
                Your first practice interview takes about ten minutes. Every one you finish is saved here with its feedback.
              </p>
              <LinkButton to="/interviews/new">Start Your First Interview</LinkButton>
            </div>
          ) : (
            <ul className="card rise divide-y divide-line overflow-hidden">
              {items.map((item) => (
                <Row key={item.id} item={item} />
              ))}
            </ul>
          )}
        </div>
      </main>
    </div>
  );
}
