// Typed client for the Mockwright FastAPI backend.

export const API_URL = (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(/\/+$/, "");

/** ws:// or wss:// version of the API URL, for the voice socket. */
export const WS_URL = API_URL.replace(/^http/, "ws");

const TOKEN_KEY = "mockwright.token";
export const UNAUTHORIZED_EVENT = "mockwright:unauthorized";

export type ExperienceLevel = "intern" | "entry-level" | "junior" | "senior";

export interface User {
  id: number;
  email: string;
}

export interface Question {
  id: number;
  question_order: number;
  question_text: string;
}

export interface QuestionWithAnswer extends Question {
  answer_text: string | null;
}

export interface FeedbackReport {
  relevance_score: number;
  star_structure_score: number;
  specificity_score: number;
  individual_contribution_score: number;
  communication_score: number;
  total_score: number;
  strengths: string[];
  improvements: string[];
  next_step: string;
}

export interface InterviewSummary {
  id: number;
  target_role: string;
  experience_level: ExperienceLevel;
  status: "in_progress" | "completed";
  answered_count: number;
  total_questions: number;
  created_at: string;
  total_score: number | null;
}

export interface InterviewDetail extends InterviewSummary {
  job_description: string | null;
  current_question_position: number;
  current_question: Question | null;
  questions: QuestionWithAnswer[];
  feedback: FeedbackReport | null;
}

export interface SubmitAnswerResponse {
  answer: { id: number; question_id: number; answer_text: string };
  status: "in_progress" | "completed";
  answered_count: number;
  total_questions: number;
  next_question: Question | null;
}

export interface CurrentQuestionResponse {
  interview_id: number;
  current_position: number;
  total_questions: number;
  status: string;
  question: Question;
}

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    // Storage blocked (private mode): the session lasts until reload.
  }
}

function messageFrom(detail: unknown, fallback: string): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { msg?: string; loc?: unknown[] };
    const field = Array.isArray(first.loc) ? String(first.loc[first.loc.length - 1]) : "";
    if (field === "password") return "Use at least 8 characters for your password.";
    if (field === "email") return "Enter a valid email address.";
    return first.msg ?? fallback;
  }
  return fallback;
}

interface RequestOptions {
  method?: string;
  json?: unknown;
  form?: Record<string, string>;
  auth?: boolean;
  raw?: boolean;
}

async function request(path: string, options: RequestOptions = {}): Promise<Response> {
  const headers: Record<string, string> = {};
  let body: BodyInit | undefined;
  if (options.json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.json);
  } else if (options.form) {
    body = new URLSearchParams(options.form);
  }
  const token = getToken();
  if (options.auth !== false && token) headers.Authorization = `Bearer ${token}`;

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method: options.method ?? (body ? "POST" : "GET"),
      headers,
      body,
    });
  } catch {
    throw new ApiError(0, "Can't reach Mockwright right now. Check your connection and try again.");
  }

  if (response.status === 401 && options.auth !== false) {
    setToken(null);
    window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
  }
  if (!response.ok) {
    let detail: unknown;
    try {
      detail = (await response.json()).detail;
    } catch {
      detail = undefined;
    }
    throw new ApiError(response.status, messageFrom(detail, "Something went wrong. Please try again."));
  }
  return response;
}

async function requestJson<T>(path: string, options?: RequestOptions): Promise<T> {
  const response = await request(path, options);
  return (await response.json()) as T;
}

export const api = {
  register: (email: string, password: string) =>
    requestJson<User>("/auth/register", { json: { email, password }, auth: false }),

  login: (email: string, password: string) =>
    requestJson<{ access_token: string; token_type: string }>("/auth/token", {
      form: { username: email, password },
      auth: false,
    }),

  me: () => requestJson<User>("/auth/me"),

  startInterview: (payload: {
    target_role: string;
    experience_level: ExperienceLevel;
    job_description?: string;
  }) => requestJson<InterviewDetail>("/interviews/start", { json: payload }),

  listInterviews: () => requestJson<InterviewSummary[]>("/interviews"),

  getInterview: (id: number) => requestJson<InterviewDetail>(`/interviews/${id}`),

  currentQuestion: (id: number) =>
    requestJson<CurrentQuestionResponse>(`/interviews/${id}/current-question`),

  submitAnswer: (id: number, questionId: number, answerText: string) =>
    requestJson<SubmitAnswerResponse>(`/interviews/${id}/answers`, {
      json: { question_id: questionId, answer_text: answerText },
    }),

  createFeedback: (id: number) =>
    requestJson<FeedbackReport>(`/interviews/${id}/feedback`, { method: "POST" }),

  questionSpeech: async (interviewId: number, questionId: number): Promise<Blob> => {
    const response = await request(`/interviews/${interviewId}/questions/${questionId}/speech`, {
      method: "POST",
    });
    return response.blob();
  },
};
