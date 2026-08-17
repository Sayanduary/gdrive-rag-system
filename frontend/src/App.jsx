import { useEffect, useState } from "react";
import { Routes, Route, Navigate } from "react-router-dom";

import api from "./services/api";
import Login from "./pages/Login";
import Analyze from "./pages/Analyze";
import Chat from "./pages/Chat";

const STORAGE_KEY = "gdrive_rag_session";
const ACTIVE_CHAT_KEY = "gdrive_rag_active_conversation";

// ==================================================
// LOADING SCREEN
// ==================================================

function LoadingScreen() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0d0d0d] text-white">
      <div className="flex flex-col items-center gap-4">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-white/10 border-t-white" />

        <p className="text-sm text-neutral-500">Checking authentication...</p>
      </div>
    </div>
  );
}

// ==================================================
// PROTECTED ROUTE
// ==================================================

function ProtectedRoute({ user, checkingAuth, children }) {
  if (checkingAuth) {
    return <LoadingScreen />;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

// ==================================================
// CHECK SAVED DRIVE SESSION
// ==================================================

function getSavedAnalysis() {
  try {
    const savedSession = localStorage.getItem(STORAGE_KEY);

    if (!savedSession) {
      return null;
    }

    const parsedSession = JSON.parse(savedSession);

    if (parsedSession?.folderUrl && parsedSession?.analysis) {
      return parsedSession;
    }

    return null;
  } catch (error) {
    console.error("Failed to read saved Drive session:", error);

    localStorage.removeItem(STORAGE_KEY);

    return null;
  }
}

// ==================================================
// APP
// ==================================================

function App() {
  const [user, setUser] = useState(null);
  const [checkingAuth, setCheckingAuth] = useState(true);

  const [analysis, setAnalysis] = useState(null);

  // ==================================================
  // AUTHENTICATION
  // ==================================================

  useEffect(() => {
    let ignore = false;

    async function checkAuthentication() {
      try {
        setCheckingAuth(true);

        const response = await api.get("/api/auth/me");

        if (ignore) {
          return;
        }

        // --------------------------------------------
        // NOT AUTHENTICATED
        // --------------------------------------------

        if (!response.data?.authenticated) {
          setUser(null);
          setAnalysis(null);

          localStorage.removeItem(STORAGE_KEY);

          localStorage.removeItem(ACTIVE_CHAT_KEY);

          return;
        }

        // --------------------------------------------
        // AUTHENTICATED
        // --------------------------------------------

        setUser(response.data.user || null);

        // --------------------------------------------
        // RESTORE ANALYZED FOLDER
        // --------------------------------------------

        const savedSession = getSavedAnalysis();

        if (savedSession) {
          setAnalysis(savedSession.analysis);
        } else {
          setAnalysis(null);
        }
      } catch (error) {
        if (!ignore) {
          console.error("Authentication check failed:", error);

          setUser(null);
          setAnalysis(null);

          localStorage.removeItem(STORAGE_KEY);

          localStorage.removeItem(ACTIVE_CHAT_KEY);
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

  // ==================================================
  // ANALYSIS COMPLETE
  // ==================================================

  function handleAnalysisComplete(newAnalysis, folderUrl) {
    setAnalysis(newAnalysis);

    /*
     * Analyze.jsx normally saves this already.
     * We save it here as well so App state and
     * localStorage stay synchronized.
     */

    if (newAnalysis && folderUrl) {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          folderUrl,
          analysis: newAnalysis,
        }),
      );
    }
  }

  // ==================================================
  // CLEAR CURRENT DRIVE SESSION
  // ==================================================

  function clearSession() {
    localStorage.removeItem(STORAGE_KEY);

    localStorage.removeItem(ACTIVE_CHAT_KEY);

    setAnalysis(null);
  }

  // ==================================================
  // SYNC ANOTHER FOLDER
  // ==================================================

  function handleSyncAnotherFolder() {
    clearSession();
  }

  // ==================================================
  // ROOT REDIRECT
  // ==================================================

  function RootRoute() {
    if (checkingAuth) {
      return <LoadingScreen />;
    }

    // --------------------------------------------
    // NOT LOGGED IN
    // --------------------------------------------

    if (!user) {
      return <Navigate to="/login" replace />;
    }

    // --------------------------------------------
    // CHECK ANALYZED FOLDER
    // --------------------------------------------

    const savedSession = getSavedAnalysis();

    const hasAnalyzedFolder = Boolean(analysis || savedSession);

    // --------------------------------------------
    // ANALYZED FOLDER EXISTS
    // --------------------------------------------

    if (hasAnalyzedFolder) {
      return <Navigate to="/chat" replace />;
    }

    // --------------------------------------------
    // NO ANALYZED FOLDER
    // --------------------------------------------

    return <Navigate to="/analyze" replace />;
  }

  // ==================================================
  // ROUTES
  // ==================================================

  return (
    <Routes>
      {/* LOGIN */}

      <Route
        path="/login"
        element={<Login user={user} checkingAuth={checkingAuth} />}
      />

      {/* ANALYZE */}

      <Route
        path="/analyze"
        element={
          <ProtectedRoute user={user} checkingAuth={checkingAuth}>
            <Analyze user={user} onAnalysisComplete={handleAnalysisComplete} />
          </ProtectedRoute>
        }
      />

      {/* CHAT */}

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

      {/* ROOT */}

      <Route path="/" element={<RootRoute />} />

      {/* UNKNOWN */}

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
