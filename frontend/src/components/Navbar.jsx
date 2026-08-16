import { useEffect, useRef, useState } from "react";
import { FiChevronDown, FiFolder, FiLogOut, FiRefreshCw } from "react-icons/fi";

import api from "../services/api";

function Navbar({ user, onSyncAnotherFolder }) {
  const [open, setOpen] = useState(false);

  const menuRef = useRef(null);

  const displayName = user?.name || "Google User";
  const email = user?.email || "";
  const avatar = user?.picture || "";
  const initial = displayName.charAt(0).toUpperCase();

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

  async function logout() {
    try {
      await api.post("/api/auth/logout");
    } catch (error) {
      console.error("Logout failed:", error);
    } finally {
      localStorage.removeItem("gdrive_rag_session");
      window.location.href = "/";
    }
  }

  function handleSyncAnotherFolder() {
    setOpen(false);

    if (onSyncAnotherFolder) {
      onSyncAnotherFolder();
    }
  }

  return (
    <header className="relative z-50 border-b border-white/[0.06] bg-[#0d0d0d]/90 backdrop-blur-xl">
      <div className="mx-auto flex h-[84px] max-w-[1440px] items-center justify-between px-6 sm:px-10 lg:px-12">
        {/* Brand */}
        <div className="flex items-center gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-white/[0.12] bg-white/[0.04]">
            <FiFolder className="text-[20px] text-neutral-300" />
          </div>

          <span className="text-[18px] font-medium tracking-tight text-neutral-200">
            Google Drive RAG
          </span>
        </div>

        {/* User */}
        <div ref={menuRef} className="relative flex items-center gap-4">
          {/* User information */}
          <div className="hidden text-right sm:block">
            <p className="text-[15px] font-medium leading-5 text-neutral-300">
              {displayName}
            </p>

            <p className="text-[13px] leading-5 text-neutral-600">{email}</p>
          </div>

          {/* Avatar */}
          <button
            type="button"
            onClick={() => setOpen((prev) => !prev)}
            className="
              flex
              h-12
              w-12
              items-center
              justify-center
              overflow-hidden
              rounded-full
              border
              border-white/[0.12]
              bg-white/[0.04]
              text-[15px]
              font-medium
              text-neutral-300
              transition
              hover:border-white/[0.2]
              hover:bg-white/[0.08]
            "
          >
            {initial}
          </button>

          {/* Dropdown */}
          {open && (
            <div className="absolute right-0 top-[60px] w-64 overflow-hidden rounded-xl border border-white/[0.09] bg-[#151515] shadow-2xl">
              {/* User information */}
              <div className="border-b border-white/[0.06] px-4 py-3">
                <p className="truncate text-sm font-medium text-neutral-200">
                  {displayName}
                </p>

                <p className="mt-0.5 truncate text-xs text-neutral-600">
                  {email}
                </p>
              </div>

              {/* Sync another folder */}
              <button
                type="button"
                onClick={handleSyncAnotherFolder}
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
                <FiRefreshCw className="text-[16px]" />

                <span>Sync another folder</span>
              </button>

              {/* Logout */}
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
                <FiLogOut className="text-[16px]" />

                <span>Logout</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

export default Navbar;
