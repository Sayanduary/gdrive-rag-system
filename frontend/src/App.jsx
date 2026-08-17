import { useEffect, useState } from "react";
import { Routes, Route, Navigate } from "react-router-dom";

import api from "./services/api";
import Login from "./pages/Login";
import Analyze from "./pages/Analyze";
import Chat from "./pages/Chat";

const STORAGE_KEY = "gdrive_rag_session";

function ProtectedRoute({ user, checkingAuth, children }) {
  if (checkingAuth) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#0d0d0d] text-white">
        <div className="flex flex-col items-center gap-4">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-white/10 border-t-white" />
          <p className="text-sm text-neutral-500">Checking authentication...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

function App() {
  const [user, setUser] = useState(null);
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [analysis, setAnalysis] = useState(null);

  useEffect(() => {
    let ignore = false;

    async function checkAuthentication() {
      try {
        const response = await api.get("/api/auth/me");

        if (ignore) return;

        if (response.data.authenticated) {
          setUser(response.data.user || null);
          try {
            const savedSession = localStorage.getItem(STORAGE_KEY);
            if (savedSession) {
              const parsedSession = JSON.parse(savedSession);
              if (parsedSession?.analysis) {
                setAnalysis(parsedSession.analysis);
              }
            }
          } catch (err) {
            console.error("Failed to restore session:", err);
            localStorage.removeItem(STORAGE_KEY);
            setAnalysis(null);
          }
        } else {
          setUser(null);
          localStorage.removeItem(STORAGE_KEY);
          setAnalysis(null);
        }
      } catch {
        if (!ignore) {
          setUser(null);
          localStorage.removeItem(STORAGE_KEY);
          setAnalysis(null);
        }
      } finally {
        if (!ignore) {
          setCheckingAuth(false);
        }
      }
    }

    checkAuthentication();

    return () => {
      ignore = true;
    };
  }, []);

  function clearSession() {
    localStorage.removeItem(STORAGE_KEY);
    setAnalysis(null);
  }

  function handleAnalysisComplete(newAnalysis) {
    setAnalysis(newAnalysis);
  }

  function handleSyncAnotherFolder() {
    clearSession();
  }

  const hasSession = Boolean(analysis || localStorage.getItem(STORAGE_KEY));

  return (
    <Routes>
      <Route
        path="/login"
        element={<Login user={user} checkingAuth={checkingAuth} />}
      />

      <Route
        path="/analyze"
        element={
          <ProtectedRoute user={user} checkingAuth={checkingAuth}>
            <Analyze user={user} onAnalysisComplete={handleAnalysisComplete} />
          </ProtectedRoute>
        }
      />

      <Route
        path="/chat"
        element={
          <ProtectedRoute user={user} checkingAuth={checkingAuth}>
            <Chat
              user={user}
              analysis={analysis}
              onSyncAnotherFolder={handleSyncAnotherFolder}
            />
          </ProtectedRoute>
        }
      />

      <Route
        path="/"
        element={
          checkingAuth ? (
            <div className="flex min-h-screen items-center justify-center bg-[#0d0d0d] text-white">
              <div className="flex flex-col items-center gap-4">
                <div className="h-8 w-8 animate-spin rounded-full border-2 border-white/10 border-t-white" />
                <p className="text-sm text-neutral-500">
                  Checking authentication...
                </p>
              </div>
            </div>
          ) : !user ? (
            <Navigate to="/login" replace />
          ) : hasSession ? (
            <Navigate to="/chat" replace />
          ) : (
            <Navigate to="/analyze" replace />
          )
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
