import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, Outlet, RouterProvider } from "react-router";

import "./index.css";
import { LinkButton } from "./components/ui";
import { AuthProvider, RequireAuth } from "./lib/auth";
import { usePageTitle } from "./lib/format";
import { LogIn, SignUp } from "./pages/Auth";
import Feedback from "./pages/Feedback";
import History from "./pages/History";
import Interview from "./pages/Interview";
import Landing from "./pages/Landing";
import NewInterview from "./pages/NewInterview";

function Root() {
  return (
    <AuthProvider>
      <Outlet />
    </AuthProvider>
  );
}

function NotFound() {
  usePageTitle("Not Found");
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-6 px-4 text-center">
      <h1 className="headline text-[44px]">Page not found.</h1>
      <p className="text-[17px] text-muted">That link doesn’t go anywhere.</p>
      <LinkButton to="/">Go Home</LinkButton>
    </div>
  );
}

const protect = (element: React.ReactNode) => <RequireAuth>{element}</RequireAuth>;

const router = createBrowserRouter([
  {
    element: <Root />,
    children: [
      { path: "/", element: <Landing /> },
      { path: "/signup", element: <SignUp /> },
      { path: "/login", element: <LogIn /> },
      { path: "/interviews/new", element: protect(<NewInterview />) },
      { path: "/interviews/:interviewId", element: protect(<Interview />) },
      { path: "/interviews/:interviewId/feedback", element: protect(<Feedback />) },
      { path: "/history", element: protect(<History />) },
      { path: "*", element: <NotFound /> },
    ],
  },
]);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
);
