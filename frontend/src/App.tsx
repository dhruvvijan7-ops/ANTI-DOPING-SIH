import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { RequireAuth } from "@/components/auth/RequireAuth";
import { ErrorBoundary } from "@/components/ui/error-boundary";
import { PageLoading } from "@/components/ui/spinner";
import { ToastViewport } from "@/components/ui/toasts";

const Landing = lazy(() => import("@/pages/Landing"));
const Login = lazy(() => import("@/pages/Login"));
const Signup = lazy(() => import("@/pages/Signup"));
const ForgotPassword = lazy(() => import("@/pages/ForgotPassword"));
const ResetPassword = lazy(() => import("@/pages/ResetPassword"));
const Dashboard = lazy(() => import("@/pages/Dashboard"));
const Intelligence = lazy(() => import("@/pages/Intelligence"));
const Alerts = lazy(() => import("@/pages/Alerts"));
const AlertDetail = lazy(() => import("@/pages/AlertDetail"));
const Athletes = lazy(() => import("@/pages/Athletes"));
const AthleteDetail = lazy(() => import("@/pages/AthleteDetail"));
const Investigations = lazy(() => import("@/pages/Investigations"));
const InvestigationWorkspace = lazy(() => import("@/pages/InvestigationWorkspace"));
const Relationships = lazy(() => import("@/pages/Relationships"));
const Reports = lazy(() => import("@/pages/Reports"));
const ReportEditorPage = lazy(() => import("@/pages/ReportEditorPage"));
const Imports = lazy(() => import("@/pages/Imports"));
const Osint = lazy(() => import("@/pages/Osint"));
const Audit = lazy(() => import("@/pages/Audit"));
const AiAssistant = lazy(() => import("@/pages/AiAssistant"));
const Users = lazy(() => import("@/pages/Users"));
const NotFound = lazy(() => import("@/pages/NotFound"));

function Lazy({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<PageLoading />}>{children}</Suspense>;
}

export function App() {
  return (
    <ErrorBoundary>
      <ToastViewport />
      <Routes>
        <Route path="/" element={<Lazy><Landing /></Lazy>} />
        <Route path="/login" element={<Lazy><Login /></Lazy>} />
        <Route path="/signup" element={<Lazy><Signup /></Lazy>} />
        <Route path="/forgot-password" element={<Lazy><ForgotPassword /></Lazy>} />
        <Route path="/reset-password" element={<Lazy><ResetPassword /></Lazy>} />
        <Route element={<RequireAuth><AppShell /></RequireAuth>}>
          <Route path="/dashboard" element={<Lazy><Dashboard /></Lazy>} />
          <Route path="/intelligence" element={<Lazy><Intelligence /></Lazy>} />
          <Route path="/alerts" element={<Lazy><Alerts /></Lazy>} />
          <Route path="/alerts/:alertId" element={<Lazy><AlertDetail /></Lazy>} />
          <Route path="/athletes" element={<Lazy><Athletes /></Lazy>} />
          <Route path="/athletes/:athleteId" element={<Lazy><AthleteDetail /></Lazy>} />
          <Route path="/investigations" element={<Lazy><Investigations /></Lazy>} />
          <Route path="/investigations/:investigationId/reports/:reportId/edit" element={<Lazy><ReportEditorPage /></Lazy>} />
          <Route path="/investigations/:investigationId/*" element={<Lazy><InvestigationWorkspace /></Lazy>} />
          <Route path="/relationships" element={<Lazy><Relationships /></Lazy>} />
          <Route path="/reports" element={<Lazy><Reports /></Lazy>} />
          <Route path="/imports" element={<Lazy><Imports /></Lazy>} />
          <Route path="/osint" element={<Lazy><Osint /></Lazy>} />
          <Route path="/audit" element={<Lazy><Audit /></Lazy>} />
          <Route path="/ai" element={<Lazy><AiAssistant /></Lazy>} />
          <Route path="/users" element={<Lazy><Users /></Lazy>} />
        </Route>
        <Route path="/404" element={<Lazy><NotFound /></Lazy>} />
        <Route path="*" element={<Navigate to="/404" replace />} />
      </Routes>
    </ErrorBoundary>
  );
}