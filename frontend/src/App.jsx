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

function LoadingScreen({ text = "Loading..." }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0d0d0d] text-white">
      <div className="flex flex-col items-center gap-4">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-white/10 border-t-white" />

        <p className="text-sm text-neutral-500">{text}</p>
      </div>
    </div>
  );
}

// ==================================================
// PROTECTED ROUTE
// ==================================================

function ProtectedRoute({ user, checkingAuth, children }) {
  if (checkingAuth) {
    return <LoadingScreen text="Checking authentication..." />;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

// ==================================================
// APP
// ==================================================

function App() {
  const [user, setUser] = useState(null);

  const [checkingAuth, setCheckingAuth] = useState(true);

  const [analysis, setAnalysis] = useState(null);

  // ==================================================
  // CHECK AUTHENTICATION
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

        if (!response.data.authenticated) {
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
        // RESTORE ANALYZED FOLDER SESSION
        // --------------------------------------------

        try {
          const savedSession = localStorage.getItem(STORAGE_KEY);

          if (savedSession) {
            const parsedSession = JSON.parse(savedSession);

            if (parsedSession?.analysis) {
              setAnalysis(parsedSession.analysis);
            } else {
              setAnalysis(null);
            }
          } else {
            setAnalysis(null);
          }
        } catch (error) {
          console.error("Failed to restore Drive session:", error);

          localStorage.removeItem(STORAGE_KEY);

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

  function handleAnalysisComplete(newAnalysis) {
    /*
     * Only update the analyzed-folder
     * state here.
     *
     * Chat history is NOT checked because
     * it does not affect routing.
     */

    setAnalysis(newAnalysis);
  }

  // ==================================================
  // SYNC ANOTHER FOLDER
  // ==================================================

  function handleSyncAnotherFolder() {
    /*
     * Clear the current analyzed folder.
     *
     * Chat history is NOT deleted.
     */

    localStorage.removeItem(STORAGE_KEY);

    localStorage.removeItem(ACTIVE_CHAT_KEY);

    setAnalysis(null);
  }

  // ==================================================
  // ROOT ROUTE
  // ==================================================

  function RootRoute() {
    // --------------------------------------------
    // CHECKING AUTH
    // --------------------------------------------

    if (checkingAuth) {
      return <LoadingScreen text="Checking authentication..." />;
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

    const hasAnalyzedFolder = Boolean(
      analysis || localStorage.getItem(STORAGE_KEY),
    );

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
      {/* ==================================================
          LOGIN
      ================================================== */}

      <Route
        path="/login"
        element={<Login user={user} checkingAuth={checkingAuth} />}
      />

      {/* ==================================================
          ANALYZE
      ================================================== */}

      <Route
        path="/analyze"
        element={
          <ProtectedRoute user={user} checkingAuth={checkingAuth}>
            <Analyze user={user} onAnalysisComplete={handleAnalysisComplete} />
          </ProtectedRoute>
        }
      />

      {/* ==================================================
          CHAT
      ================================================== */}

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

      {/* ==================================================
          ROOT
      ================================================== */}

      <Route path="/" element={<RootRoute />} />

      {/* ==================================================
          UNKNOWN ROUTES
      ================================================== */}

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
