import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router";

import { Button, ErrorNote, Logo } from "../components/ui";
import { ApiError } from "../lib/api";
import { useAuth } from "../lib/auth";
import { usePageTitle } from "../lib/format";

type Mode = "signup" | "login";

const COPY: Record<Mode, { title: string; lede: string; submit: string; switchText: string; switchLink: string; switchTo: string }> = {
  signup: {
    title: "Create your account.",
    lede: "Your interviews and feedback reports are saved to your account, so you can come back to them anytime.",
    submit: "Create Account",
    switchText: "Already have an account?",
    switchLink: "Log In",
    switchTo: "/login",
  },
  login: {
    title: "Welcome back.",
    lede: "Log in to start a new interview or review your past feedback.",
    submit: "Log In",
    switchText: "New to Mockwright?",
    switchLink: "Create an account",
    switchTo: "/signup",
  },
};

function safeNext(next: string | null): string {
  // Only follow same-site paths, never an absolute URL.
  return next && next.startsWith("/") && !next.startsWith("//") ? next : "/interviews/new";
}

function AuthPage({ mode }: { mode: Mode }) {
  const copy = COPY[mode];
  usePageTitle(mode === "signup" ? "Sign Up" : "Log In");
  const { token, login, register } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const next = safeNext(params.get("next"));

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (token && !submitting) return <Navigate to={next} replace />;

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (mode === "signup" && password.length < 8) {
      setError("Use at least 8 characters for your password.");
      return;
    }
    setSubmitting(true);
    try {
      if (mode === "signup") await register(email, password);
      else await login(email, password);
      navigate(next, { replace: true });
    } catch (caught) {
      setError(
        caught instanceof ApiError && caught.status === 401
          ? "That email and password don’t match an account."
          : caught instanceof Error
            ? caught.message
            : "Something went wrong. Please try again.",
      );
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-dvh">
      <header className="mx-auto flex h-16 max-w-[1140px] items-center px-4 sm:px-6">
        <Logo />
      </header>
      <main className="mx-auto w-full max-w-[420px] px-4 pb-20 pt-12 sm:pt-20">
        <div className="rise text-center">
          <h1 className="headline text-[40px] sm:text-[44px]">{copy.title}</h1>
          <p className="mt-4 text-[16px] leading-relaxed text-muted">{copy.lede}</p>
        </div>

        <form onSubmit={onSubmit} className="rise mt-10 flex flex-col gap-6" style={{ animationDelay: "60ms" }} noValidate>
          <div>
            <label htmlFor="email" className="label">Email</label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              inputMode="email"
              required
              className="input"
              placeholder="name@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>

          <div>
            <label htmlFor="password" className="label">Password</label>
            <div className="relative">
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                autoComplete={mode === "signup" ? "new-password" : "current-password"}
                required
                minLength={mode === "signup" ? 8 : undefined}
                className="input pr-20"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                aria-describedby={mode === "signup" ? "password-hint" : undefined}
              />
              <button
                type="button"
                onClick={() => setShowPassword((s) => !s)}
                className="absolute inset-y-0 right-0 px-4 text-[14px] font-semibold text-accent hover:underline"
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
            {mode === "signup" && (
              <p id="password-hint" className="mt-2 text-[13px] text-muted">Use at least 8 characters.</p>
            )}
          </div>

          {error && <ErrorNote>{error}</ErrorNote>}

          <Button type="submit" size="lg" loading={submitting} className="w-full">
            {copy.submit}
          </Button>
        </form>

        <p className="mt-10 text-center text-[15px] text-muted">
          {copy.switchText}{" "}
          <Link
            to={`${copy.switchTo}${params.get("next") ? `?next=${encodeURIComponent(next)}` : ""}`}
            className="ml-1 font-semibold text-accent hover:underline"
          >
            {copy.switchLink}
          </Link>
        </p>
      </main>
    </div>
  );
}

export function SignUp() {
  return <AuthPage mode="signup" />;
}

export function LogIn() {
  return <AuthPage mode="login" />;
}
