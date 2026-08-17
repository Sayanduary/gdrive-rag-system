import { useEffect, useState } from "react";
import { Routes, Route, Navigate } from "react-router-dom";

import api from "./services/api";

import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Analyze from "./pages/Analyze";
import Chat from "./pages/Chat";

// ==================================================
// STORAGE KEYS
// ==================================================

const STORAGE_KEY = "gdrive_rag_session";

const ACTIVE_CHAT_KEY = "gdrive_rag_active_conversation";

// ==================================================
// LOADING SCREEN
// ==================================================

function LoadingScreen() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0d0d0d] text-white">
      <div className="flex flex-col items-center gap-4">
        <div
          className="
            h-8
            w-8
            animate-spin
            rounded-full
            border-2
            border-white/10
            border-t-white
          "
        />

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

        const response = await api.get(`/api/auth/me?_=${Date.now()}`);

        if (ignore) {
          return;
        }



        // ============================================
        // NOT AUTHENTICATED
        // ============================================

        if (!response.data?.authenticated) {
          setUser(null);

          setAnalysis(null);

          localStorage.removeItem(STORAGE_KEY);

          localStorage.removeItem(ACTIVE_CHAT_KEY);

          return;
        }

        // ============================================
        // AUTHENTICATED
        // ============================================

        const authenticatedUser = response.data?.user || null;



        setUser(authenticatedUser);

        // IMPORTANT:
        // Do NOT restore an old user's
        // analysis from localStorage.
        //
        // Dashboard data comes from
        // PostgreSQL using the authenticated
        // user's Google sub.

        setAnalysis(null);
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

    if (newAnalysis && folderUrl) {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          folderUrl,
          analysis: newAnalysis,

          // Store the owner too.
          userId: user?.sub || null,
        }),
      );
    }
  }

  // ==================================================
  // CLEAR LOCAL SESSION
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

    window.location.href = "/analyze";
  }

  // ==================================================
  // LOGOUT
  // ==================================================

  async function handleLogout() {
    console.log("LOGOUT STARTED");

    try {
      const response = await api.post("/api/auth/logout");

      console.log("LOGOUT RESPONSE:", response.data);
    } catch (error) {
      console.error("Logout request failed:", error);
    } finally {
      // ==========================================
      // ALWAYS CLEAR FRONTEND STATE
      // ==========================================

      setUser(null);

      setAnalysis(null);

      localStorage.removeItem(STORAGE_KEY);

      localStorage.removeItem(ACTIVE_CHAT_KEY);

      // ==========================================
      // GO TO LOGIN
      // ==========================================

      window.location.href = "/login";
    }
  }

  // ==================================================
  // ROOT ROUTE
  // ==================================================

  function RootRoute() {
    if (checkingAuth) {
      return <LoadingScreen />;
    }

    if (!user) {
      return <Navigate to="/login" replace />;
    }

    return <Navigate to="/dashboard" replace />;
  }

  // ==================================================
  // USER KEY
  // ==================================================

  const userKey = user?.sub || user?.email || "anonymous";

  // ==================================================
  // ROUTES
  // ==================================================

  return (
    <Routes>
      {/* ============================================
          LOGIN
      ============================================ */}

      <Route
        path="/login"
        element={<Login user={user} checkingAuth={checkingAuth} />}
      />

      {/* ============================================
          DASHBOARD
      ============================================ */}

      <Route
        path="/dashboard"
        element={
          <ProtectedRoute user={user} checkingAuth={checkingAuth}>
            <Dashboard
              key={`dashboard-${userKey}`}
              user={user}
              onLogout={handleLogout}
            />
          </ProtectedRoute>
        }
      />

      {/* ============================================
          ANALYZE
      ============================================ */}

      <Route
        path="/analyze"
        element={
          <ProtectedRoute user={user} checkingAuth={checkingAuth}>
            <Analyze
              key={`analyze-${userKey}`}
              user={user}
              onAnalysisComplete={handleAnalysisComplete}
              onLogout={handleLogout}
            />
          </ProtectedRoute>
        }
      />

      {/* ============================================
          CHAT
      ============================================ */}

      <Route
        path="/chat"
        element={
          <ProtectedRoute user={user} checkingAuth={checkingAuth}>
            <Chat
              key={`chat-${userKey}`}
              user={user}
              analysis={analysis}
              onSyncAnotherFolder={handleSyncAnotherFolder}
              onLogout={handleLogout}
            />
          </ProtectedRoute>
        }
      />

      {/* ============================================
          ROOT
      ============================================ */}

      <Route path="/" element={<RootRoute />} />

      {/* ============================================
          UNKNOWN
      ============================================ */}

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
