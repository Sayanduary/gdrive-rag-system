import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { FiArrowRight, FiFolder, FiShield } from "react-icons/fi";

import api from "../services/api";
import Navbar from "../components/Navbar";

const STORAGE_KEY = "gdrive_rag_session";

function Analyze({ user, onAnalysisComplete }) {
  const navigate = useNavigate();
  const [folderUrl, setFolderUrl] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState("");

  async function analyzeFolder() {
    const trimmedUrl = folderUrl.trim();

    if (!trimmedUrl) {
      setError("Please enter a Google Drive folder link.");
      return;
    }

    setError("");
    setAnalyzing(true);

    try {
      const response = await api.post("/api/drive/analyze", {
        folder_url: trimmedUrl,
      });

      const newAnalysis = response.data;

      // Persist session
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          folderUrl: trimmedUrl,
          analysis: newAnalysis,
        }),
      );

      if (typeof onAnalysisComplete === "function") {
        onAnalysisComplete(newAnalysis, trimmedUrl);
      }

      // Navigate to chat after successful analysis
      navigate("/chat");
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to analyze folder.");
    } finally {
      setAnalyzing(false);
    }
  }

  function handleGoToChat() {
    navigate("/chat");
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#0d0d0d] text-white">
      {/* Background grid */}
      <div
        className="pointer-events-none fixed inset-0 opacity-[0.035]"
        style={{
          backgroundImage: `
          linear-gradient(
            rgba(255,255,255,0.5) 1px,
            transparent 1px
          ),
          linear-gradient(
            90deg,
            rgba(255,255,255,0.5) 1px,
            transparent 1px
          )
        `,
          backgroundSize: "48px 48px",
        }}
      />

      {/* Soft background glow */}
      <div className="pointer-events-none fixed left-1/2 top-[-350px] h-[700px] w-[700px] -translate-x-1/2 rounded-full bg-white/[0.025] blur-[130px]" />

      {/* Secondary glow */}
      <div className="pointer-events-none fixed bottom-[-300px] left-[10%] h-[500px] w-[500px] rounded-full bg-white/[0.012] blur-[120px]" />

      {/* Existing Navbar */}
      <Navbar user={user} showChat={true} onChat={handleGoToChat} />

      {/* Main */}
      <main className="relative mx-auto flex min-h-[calc(100vh-84px)] max-w-6xl items-center justify-center px-5 py-12 sm:px-8 lg:px-10">
        <div className="w-full max-w-2xl">

          {/* ==================================================
            INTRO
        ================================================== */}

          <div className="mb-9 text-center">
            {/* Icon */}
            <div className="relative mx-auto mb-6 flex h-16 w-16 items-center justify-center">
              <div className="absolute inset-0 rounded-2xl bg-white/[0.025] blur-xl" />

              <div className="relative flex h-16 w-16 items-center justify-center rounded-2xl border border-white/[0.09] bg-white/[0.035] shadow-2xl backdrop-blur-xl">
                <FiFolder className="text-xl text-neutral-300" />
              </div>
            </div>

            <p className="mb-3 text-[10px] font-medium uppercase tracking-[0.25em] text-neutral-600">
              Google Drive Knowledge Base
            </p>

            <h1 className="text-3xl font-semibold tracking-[-0.02em] text-neutral-100 sm:text-4xl">
              Sync your Drive
            </h1>

            <p className="mx-auto mt-4 max-w-lg text-sm leading-6 text-neutral-500">
              Choose a Google Drive folder and turn its documents
              into a searchable AI knowledge base.
            </p>
          </div>

          {/* ==================================================
            MAIN BOX
        ================================================== */}

          <div className="relative overflow-hidden rounded-3xl border border-white/[0.08] bg-white/[0.025] shadow-2xl backdrop-blur-2xl">

            {/* Top highlight */}
            <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/[0.12] to-transparent" />

            <div className="p-5 sm:p-7">

              {/* Card heading */}
              <div className="mb-6">
                <div className="flex items-center gap-3">

                  <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-white/[0.07] bg-white/[0.03]">
                    <FiFolder className="text-sm text-neutral-500" />
                  </div>

                  <div>
                    <label className="text-sm font-medium text-neutral-200">
                      Google Drive folder
                    </label>

                    <p className="mt-1 text-[11px] text-neutral-600">
                      Paste the URL of the folder you want to analyze.
                    </p>
                  </div>

                </div>
              </div>

              {/* ==================================================
                INPUT
            ================================================== */}

              <div
                className={`
                group
                flex
                items-center
                rounded-2xl
                border
                bg-black/20
                p-1.5
                transition-all
                duration-200
                ${error
                    ? "border-red-500/40"
                    : "border-white/[0.08] focus-within:border-white/[0.18] focus-within:bg-black/30"
                  }
              `}
              >
                {/* Input icon */}
                <div className="flex h-11 w-11 shrink-0 items-center justify-center text-neutral-600">
                  <FiFolder className="text-sm transition-colors group-focus-within:text-neutral-400" />
                </div>

                {/* Input */}
                <input
                  type="text"
                  value={folderUrl}
                  onChange={(event) => {
                    setFolderUrl(event.target.value);

                    if (error) {
                      setError("");
                    }
                  }}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && !analyzing) {
                      analyzeFolder();
                    }
                  }}
                  placeholder="https://drive.google.com/drive/folders/..."
                  className="
                  min-w-0
                  flex-1
                  bg-transparent
                  px-2
                  py-3
                  text-sm
                  text-neutral-200
                  outline-none
                  placeholder:text-neutral-700
                "
                />

                {/* Analyze button */}
                <button
                  onClick={analyzeFolder}
                  disabled={analyzing}
                  className="
                  flex
                  h-11
                  shrink-0
                  items-center
                  gap-2
                  rounded-xl
                  bg-white
                  px-4
                  text-xs
                  font-medium
                  text-black
                  shadow-lg
                  transition-all
                  duration-200
                  hover:bg-neutral-200
                  active:scale-[0.98]
                  disabled:cursor-not-allowed
                  disabled:opacity-40
                  sm:px-5
                "
                >
                  {analyzing ? (
                    <>
                      <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-black/20 border-t-black" />

                      <span>Analyzing</span>
                    </>
                  ) : (
                    <>
                      <span>Analyze</span>
                      <FiArrowRight className="text-sm" />
                    </>
                  )}
                </button>
              </div>

              {/* ==================================================
                ERROR
            ================================================== */}

              {error && (
                <div className="mt-3 rounded-xl border border-red-500/[0.15] bg-red-500/[0.04] px-4 py-3 text-xs leading-5 text-red-400">
                  {error}
                </div>
              )}

              {/* ==================================================
                INFO BOX
            ================================================== */}

              <div className="mt-5 rounded-2xl border border-white/[0.06] bg-black/20 p-4">
                <div className="flex items-start gap-3">

                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-white/[0.06] bg-white/[0.025]">
                    <FiShield className="text-sm text-neutral-500" />
                  </div>

                  <div>
                    <p className="text-xs font-medium text-neutral-400">
                      Before you continue
                    </p>

                    <p className="mt-1.5 text-[11px] leading-5 text-neutral-600">
                      Make sure your Google account has access to
                      the folder. Documents will be processed to
                      build the RAG knowledge base.
                    </p>
                  </div>

                </div>
              </div>

            </div>

            {/* ==================================================
              BOTTOM STATUS BOXES
          ================================================== */}

            <div className="grid grid-cols-3 border-t border-white/[0.06]">

              <div className="border-r border-white/[0.06] px-3 py-4 text-center">
                <div className="text-[10px] font-medium uppercase tracking-wider text-neutral-700">
                  Step
                </div>

                <div className="mt-1 text-xs text-neutral-400">
                  Connect
                </div>
              </div>

              <div className="border-r border-white/[0.06] px-3 py-4 text-center">
                <div className="text-[10px] font-medium uppercase tracking-wider text-neutral-700">
                  Step
                </div>

                <div className="mt-1 text-xs text-neutral-400">
                  Analyze
                </div>
              </div>

              <div className="px-3 py-4 text-center">
                <div className="text-[10px] font-medium uppercase tracking-wider text-neutral-700">
                  Step
                </div>

                <div className="mt-1 text-xs text-neutral-400">
                  Chat
                </div>
              </div>

            </div>
          </div>

          {/* Signed-in information */}
          {user?.email && (
            <p className="mt-6 text-center text-[10px] tracking-wide text-neutral-700">
              Signed in as{" "}
              <span className="text-neutral-600">
                {user.email}
              </span>
            </p>
          )}

        </div>
      </main>
    </div>
  );
}

export default Analyze;
