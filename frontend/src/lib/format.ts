import { useEffect } from "react";

import type { ExperienceLevel } from "./api";

export const LEVELS: { value: ExperienceLevel; label: string }[] = [
  { value: "intern", label: "Intern" },
  { value: "entry-level", label: "Entry-level" },
  { value: "junior", label: "Junior" },
  { value: "senior", label: "Senior" },
];

export function levelLabel(level: string): string {
  return LEVELS.find((l) => l.value === level)?.label ?? level;
}

export function formatDate(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export const CATEGORIES = [
  { key: "relevance_score", label: "Relevance" },
  { key: "star_structure_score", label: "STAR Structure" },
  { key: "specificity_score", label: "Specificity" },
  { key: "individual_contribution_score", label: "Individual Contribution" },
  { key: "communication_score", label: "Communication" },
] as const;

export function usePageTitle(title: string) {
  useEffect(() => {
    document.title = title ? `${title} · Mockwright` : "Mockwright";
  }, [title]);
}
