import type { FeedbackReport } from "../lib/api";
import { CATEGORIES } from "../lib/format";

export function ScoreRing({ score, size = 190 }: { score: number; size?: number }) {
  const stroke = 7;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const filled = Math.max(0, Math.min(100, score)) / 100;

  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90" aria-hidden="true">
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="var(--color-line-strong)" strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--color-fg)"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - filled)}
          style={{ transition: "stroke-dashoffset 900ms var(--ease-out-quint)" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-[56px] font-bold leading-none tracking-tight tabular-nums" style={{ fontSize: size * 0.3 }}>
          {score}
        </span>
        <span className="mt-1 text-[13px] text-muted">out of 100</span>
      </div>
    </div>
  );
}

export function CategoryBars({ report }: { report: FeedbackReport }) {
  return (
    <dl className="flex w-full flex-col gap-5">
      {CATEGORIES.map(({ key, label }) => {
        const value = report[key];
        return (
          <div key={key}>
            <div className="mb-2 flex items-baseline justify-between text-[15px]">
              <dt className="font-semibold">{label}</dt>
              <dd className="tabular-nums text-muted">{value} / 20</dd>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-line-strong" aria-hidden="true">
              <div
                className="h-full rounded-full bg-fg"
                style={{ width: `${(value / 20) * 100}%`, transition: "width 900ms var(--ease-out-quint)" }}
              />
            </div>
          </div>
        );
      })}
    </dl>
  );
}

export function ScoreCard({ report, badge }: { report: FeedbackReport; badge?: string }) {
  return (
    <section className="card flex flex-col items-center gap-10 p-8 sm:p-12 md:flex-row md:gap-16" aria-label="Scores">
      <div className="flex flex-col items-center gap-4 md:w-[38%]">
        <ScoreRing score={report.total_score} />
        {badge && <span className="rounded-full bg-panel-2 px-3 py-1 text-[12px] font-medium text-muted">{badge}</span>}
      </div>
      <CategoryBars report={report} />
    </section>
  );
}
