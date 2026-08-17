import { useEffect, useState } from "react";
import { Routes, Route, Navigate } from "react-router-dom";

import api from "./services/api";

import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Analyze from "./pages/Analyze";
import Chat from "./pages/Chat";

// ==================================================
// STORAGE HELPERS
// ==================================================

const LEGACY_STORAGE_KEY = "gdrive_rag_session";

function getActiveChatKey(user) {
  const userId = user?.sub || user?.email || "anonymous";

  return `gdrive_rag_active_conversation_${userId}`;
}

function clearUserStorage(user) {
  localStorage.removeItem(LEGACY_STORAGE_KEY);

  if (user) {
    localStorage.removeItem(getActiveChatKey(user));
  }

  // Remove old global key too.
  localStorage.removeItem("gdrive_rag_active_conversation");
}

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

        const response = await api.get("/api/auth/me", {
          // Always ask the browser for the
          // current session-backed response.
          params: {
            _: Date.now(),
          },
        });

        if (ignore) {
          return;
        }

        console.log("CURRENT AUTH USER:", response.data?.user);

        // ==========================================
        // NOT AUTHENTICATED
        // ==========================================

        if (!response.data?.authenticated) {
          setUser(null);
          setAnalysis(null);

          clearUserStorage(user);

          return;
        }

        // ==========================================
        // AUTHENTICATED
        // ==========================================

        const authenticatedUser = response.data?.user || null;

        setUser(authenticatedUser);

        // Do not restore old analysis state
        // across users.
        setAnalysis(null);
      } catch (error) {
        if (!ignore) {
          console.error("Authentication check failed:", error);

          setUser(null);
          setAnalysis(null);

          clearUserStorage(user);
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
        LEGACY_STORAGE_KEY,
        JSON.stringify({
          folderUrl,
          analysis: newAnalysis,
          userId: user?.sub || null,
        }),
      );
    }
  }

  // ==================================================
  // CLEAR SESSION
  // ==================================================

  function clearSession() {
    localStorage.removeItem(LEGACY_STORAGE_KEY);

    if (user) {
      localStorage.removeItem(getActiveChatKey(user));
    }

    localStorage.removeItem("gdrive_rag_active_conversation");

    setAnalysis(null);
  }

  // ==================================================
  // SYNC ANOTHER FOLDER
  // ==================================================

  function handleSyncAnotherFolder() {
    clearSession();
  }

  // ==================================================
  // LOGOUT
  // ==================================================

  async function handleLogout() {
    try {
      await api.post("/api/auth/logout");
    } catch (error) {
      console.error("Logout failed:", error);
    } finally {
      clearUserStorage(user);

      setAnalysis(null);

      setUser(null);
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
  // USER-SPECIFIC COMPONENT KEY
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
