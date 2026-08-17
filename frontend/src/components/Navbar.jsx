import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  FiBarChart2,
  FiFolder,
  FiLogOut,
  FiMessageSquare,
  FiRefreshCw,
  FiMenu,
} from "react-icons/fi";

import api from "../services/api";

function Navbar({
  user,
  onLogout,
  onHistory,
  showDashboard = false,
  showChat = false,
  showSync = false,
  showHistory = false,
  activeTab = "",
}) {
  const navigate = useNavigate();

  const [open, setOpen] = useState(false);

  const menuRef = useRef(null);

  const displayName = user?.name || "Google User";

  const email = user?.email || "";

  const avatar = user?.picture || "";

  const initial = displayName.charAt(0).toUpperCase();

  // ==================================================
  // CLOSE DROPDOWN
  // ==================================================

  useEffect(() => {
    function handleClickOutside(event) {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  // ==================================================
  // NAVIGATION
  // ==================================================

  function goDashboard() {
    setOpen(false);
    navigate("/dashboard");
  }

  function goChat() {
    setOpen(false);
    navigate("/chat");
  }

  function goAnalyze() {
    setOpen(false);
    navigate("/analyze");
  }

  // ==================================================
  // MOBILE HISTORY
  // ==================================================

  function handleHistory() {
    setOpen(false);

    if (typeof onHistory === "function") {
      onHistory();
    }
  }

  // ==================================================
  // LOGOUT
  // ==================================================
  async function logout() {
    setOpen(false);

    if (typeof onLogout === "function") {
      await onLogout();
      return;
    }

    try {
      await api.post("/api/auth/logout");
    } catch (error) {
      console.error("Logout failed:", error);
    }
  }
  const dashboardActive = activeTab === "dashboard";

  const chatActive = activeTab === "chat";

  return (
    <header className="relative z-50 border-b border-white/[0.06] bg-[#0d0d0d]/90 backdrop-blur-xl">
      <div className="mx-auto flex h-[84px] max-w-[1440px] items-center justify-between px-4 sm:px-10 lg:px-12">
        {/* ==================================================
            LEFT
        ================================================== */}

        <div className="flex items-center gap-3">
          {/* MOBILE HISTORY */}

          {showHistory && (
            <button
              type="button"
              onClick={handleHistory}
              aria-label="Open chat history"
              className="
                flex
                h-11
                w-11
                items-center
                justify-center
                rounded-xl
                border
                border-white/[0.08]
                bg-white/[0.035]
                text-neutral-400
                transition
                hover:border-white/[0.14]
                hover:bg-white/[0.07]
                hover:text-white
                lg:hidden
              "
            >
              <FiMenu className="text-lg" />
            </button>
          )}

          {/* BRAND */}

          <button
            type="button"
            onClick={
              showDashboard ? goDashboard : showChat ? goChat : undefined
            }
            className="
              flex
              items-center
              gap-4
            "
          >
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-white/[0.12] bg-white/[0.04]">
              <FiFolder className="text-[20px] text-neutral-300" />
            </div>

            <span className="text-[18px] font-medium tracking-tight text-neutral-200">
              Zentra
            </span>
          </button>
        </div>

        {/* ==================================================
            RIGHT
        ================================================== */}

        <div className="flex items-center gap-2 sm:gap-3">
          {/* DASHBOARD */}

          {showDashboard && (
            <button
              type="button"
              onClick={goDashboard}
              className={`
                flex
                items-center
                gap-2
                rounded-xl
                border
                px-3
                py-2.5
                text-xs
                font-medium
                transition-all
                ${
                  dashboardActive
                    ? `
                      border-white/[0.14]
                      bg-white/[0.09]
                      text-white
                    `
                    : `
                      border-white/[0.08]
                      bg-white/[0.035]
                      text-neutral-400
                      hover:border-white/[0.14]
                      hover:bg-white/[0.07]
                      hover:text-white
                    `
                }
              `}
            >
              <FiBarChart2 />

              <span>Dashboard</span>
            </button>
          )}

          {/* CHAT */}

          {showChat && (
            <button
              type="button"
              onClick={goChat}
              className={`
                flex
                items-center
                gap-2
                rounded-xl
                border
                px-3
                py-2.5
                text-xs
                font-medium
                transition-all
                ${
                  chatActive
                    ? `
                      border-white/[0.14]
                      bg-white/[0.09]
                      text-white
                    `
                    : `
                      border-white/[0.08]
                      bg-white/[0.035]
                      text-neutral-400
                      hover:border-white/[0.14]
                      hover:bg-white/[0.07]
                      hover:text-white
                    `
                }
              `}
            >
              <FiMessageSquare />

              <span>Chat</span>
            </button>
          )}

          {/* SYNC */}

          {showSync && (
            <button
              type="button"
              onClick={goAnalyze}
              className="
                flex
                items-center
                gap-2
                rounded-xl
                border
                border-white/[0.08]
                bg-white/[0.035]
                px-3
                py-2.5
                text-xs
                font-medium
                text-neutral-400
                transition
                hover:border-white/[0.14]
                hover:bg-white/[0.07]
                hover:text-white
              "
            >
              <FiRefreshCw />

              <span className="hidden sm:inline">Sync another folder</span>

              <span className="sm:hidden">Sync</span>
            </button>
          )}

          {/* USER */}

          <div ref={menuRef} className="relative ml-1">
            <button
              type="button"
              onClick={() => setOpen((previous) => !previous)}
              className="
                flex
                h-11
                w-11
                items-center
                justify-center
                overflow-hidden
                rounded-full
                border
                border-white/[0.12]
                bg-white/[0.04]
                text-sm
                font-medium
                text-neutral-300
                transition
                hover:border-white/[0.2]
                hover:bg-white/[0.08]
              "
            >
              {avatar ? (
                <img
                  src={avatar}
                  alt={displayName}
                  className="h-full w-full object-cover"
                />
              ) : (
                initial
              )}
            </button>

            {open && (
              <div
                className="
                  absolute
                  right-0
                  top-[54px]
                  w-64
                  overflow-hidden
                  rounded-xl
                  border
                  border-white/[0.09]
                  bg-[#151515]
                  shadow-2xl
                "
              >
                <div className="border-b border-white/[0.06] px-4 py-3">
                  <p className="truncate text-sm font-medium text-neutral-200">
                    {displayName}
                  </p>

                  <p className="mt-0.5 truncate text-xs text-neutral-600">
                    {email}
                  </p>
                </div>

                {showDashboard && (
                  <button
                    type="button"
                    onClick={goDashboard}
                    className="
                      flex
                      w-full
                      items-center
                      gap-3
                      px-4
                      py-3
                      text-left
                      text-sm
                      text-neutral-400
                      transition
                      hover:bg-white/[0.05]
                      hover:text-white
                    "
                  >
                    <FiBarChart2 />
                    <span>Dashboard</span>
                  </button>
                )}

                {showChat && (
                  <button
                    type="button"
                    onClick={goChat}
                    className="
                      flex
                      w-full
                      items-center
                      gap-3
                      px-4
                      py-3
                      text-left
                      text-sm
                      text-neutral-400
                      transition
                      hover:bg-white/[0.05]
                      hover:text-white
                    "
                  >
                    <FiMessageSquare />
                    <span>Chat</span>
                  </button>
                )}

                {showSync && (
                  <button
                    type="button"
                    onClick={goAnalyze}
                    className="
                      flex
                      w-full
                      items-center
                      gap-3
                      px-4
                      py-3
                      text-left
                      text-sm
                      text-neutral-400
                      transition
                      hover:bg-white/[0.05]
                      hover:text-white
                    "
                  >
                    <FiRefreshCw />
                    <span>Sync another folder</span>
                  </button>
                )}

                <button
                  type="button"
                  onClick={logout}
                  className="
                    flex
                    w-full
                    items-center
                    gap-3
                    border-t
                    border-white/[0.06]
                    px-4
                    py-3
                    text-left
                    text-sm
                    text-neutral-400
                    transition
                    hover:bg-white/[0.05]
                    hover:text-red-400
                  "
                >
                  <FiLogOut />
                  <span>Logout</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}

export default Navbar;
