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

/** A short follow-up the interviewer asked about a question's answer. */
export interface FollowUp {
  id: number;
  question_id: number;
  position: number;
  question_text: string;
  answer_text: string | null;
}

export interface QuestionWithAnswer extends Question {
  answer_text: string | null;
  has_recording: boolean;
  follow_ups: FollowUp[];
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
  /** One per answer, in question order. Empty for reports saved before grades existed. */
  question_grades: QuestionGrade[];
}

export interface QuestionGrade {
  question_number: number;
  score: number;
  comment: string;
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
  /** The questions were based on the resume saved to the account. */
  used_resume: boolean;
  current_question_position: number;
  current_question: Question | null;
  /** The follow-up waiting for an answer on the current question, if any. */
  current_follow_up: FollowUp | null;
  questions: QuestionWithAnswer[];
  feedback: FeedbackReport | null;
}

/** The resume saved to the account. Only its text is kept. */
export interface SavedResume {
  file_name: string;
  updated_at: string;
  word_count: number;
  /** The start of the text read from the file, to check it parsed correctly. */
  preview: string;
}

export interface SubmitAnswerResponse {
  answer: { id: number; question_id: number; answer_text: string };
  status: "in_progress" | "completed";
  answered_count: number;
  total_questions: number;
  /** At most one is set: a follow-up on the same question, or the next question. Neither once completed. */
  follow_up: FollowUp | null;
  next_question: Question | null;
}

export interface CurrentQuestionResponse {
  interview_id: number;
  current_position: number;
  total_questions: number;
  status: string;
  question: Question;
  /** Set when the candidate should answer this follow-up on `question` next. */
  follow_up: FollowUp | null;
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
  /** Raw body (e.g. a video Blob) sent with its own Content-Type. */
  body?: Blob;
  contentType?: string;
}

async function request(path: string, options: RequestOptions = {}): Promise<Response> {
  const headers: Record<string, string> = {};
  let body: BodyInit | undefined;
  if (options.json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.json);
  } else if (options.form) {
    body = new URLSearchParams(options.form);
  } else if (options.body) {
    headers["Content-Type"] = options.contentType ?? options.body.type;
    body = options.body;
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
    use_resume?: boolean;
  }) => requestJson<InterviewDetail>("/interviews/start", { json: payload }),

  /** The saved resume, or null if there isn't one. */
  resume: async (): Promise<SavedResume | null> => {
    try {
      return await requestJson<SavedResume>("/resume");
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 404) return null;
      throw caught;
    }
  },

  /** Save a resume to the account, replacing any earlier one. */
  uploadResume: (file: File) =>
    requestJson<SavedResume>(`/resume?file_name=${encodeURIComponent(file.name)}`, {
      method: "PUT",
      body: file,
      contentType: file.type || "application/octet-stream",
    }),

  deleteResume: async (): Promise<void> => {
    await request("/resume", { method: "DELETE" });
  },

  listInterviews: () => requestJson<InterviewSummary[]>("/interviews"),

  getInterview: (id: number) => requestJson<InterviewDetail>(`/interviews/${id}`),

  currentQuestion: (id: number) =>
    requestJson<CurrentQuestionResponse>(`/interviews/${id}/current-question`),

  /** Answer the current question, or the open follow-up on it when `followUpId` is given. */
  submitAnswer: (id: number, questionId: number, answerText: string, followUpId?: number) =>
    requestJson<SubmitAnswerResponse>(`/interviews/${id}/answers`, {
      json: { question_id: questionId, follow_up_id: followUpId ?? null, answer_text: answerText },
    }),

  createFeedback: (id: number) =>
    requestJson<FeedbackReport>(`/interviews/${id}/feedback`, { method: "POST" }),

  deleteInterview: async (id: number): Promise<void> => {
    await request(`/interviews/${id}`, { method: "DELETE" });
  },

  uploadRecording: async (
    interviewId: number,
    questionId: number,
    video: Blob,
    durationSeconds: number,
  ): Promise<void> => {
    const seconds = Math.max(0, Math.round(durationSeconds * 10) / 10);
    await request(`/interviews/${interviewId}/questions/${questionId}/recording?duration_seconds=${seconds}`, {
      method: "PUT",
      body: video,
      contentType: video.type || "video/webm",
    });
  },

  recording: async (interviewId: number, questionId: number): Promise<Blob> => {
    const response = await request(`/interviews/${interviewId}/questions/${questionId}/recording`);
    return response.blob();
  },

  /**
   * Start reading a line aloud: a question, or a follow-up when `followUpId` is given.
   * Resolves as soon as the MP3 starts arriving, so it can play while it streams.
   */
  speech: (interviewId: number, line: { questionId: number; followUpId?: number }): Promise<Response> =>
    request(
      line.followUpId
        ? `/interviews/${interviewId}/follow-ups/${line.followUpId}/speech`
        : `/interviews/${interviewId}/questions/${line.questionId}/speech`,
      { method: "POST" },
    ),
};
