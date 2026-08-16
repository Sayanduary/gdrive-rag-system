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
      {/* Background Grid */}
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.035]"
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
          backgroundSize: "50px 50px",
        }}
      />

      {/* Glow */}
      <div className="pointer-events-none absolute left-1/2 top-[-350px] h-[650px] w-[650px] -translate-x-1/2 rounded-full bg-white/[0.025] blur-3xl" />

      {/* Navbar with Chat button */}
      <Navbar user={user} showChat={true} onChat={handleGoToChat} />

      {/* Main */}
      <main className="relative mx-auto flex min-h-[calc(100vh-84px)] max-w-6xl items-center justify-center px-6 py-16">
        <div className="w-full max-w-2xl">
          {/* Intro */}
          <div className="mb-10 text-center">
            <div className="mx-auto mb-5 flex h-12 w-12 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.04]">
              <FiFolder className="text-lg text-neutral-300" />
            </div>

            <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
              Sync your Drive
            </h1>

            <p className="mx-auto mt-3 max-w-lg text-sm leading-6 text-neutral-500">
              Choose a Google Drive folder and turn its documents into a
              searchable AI knowledge base.
            </p>
          </div>

          {/* Card */}
          <div className="rounded-2xl border border-white/[0.08] bg-white/[0.035] p-5 shadow-2xl backdrop-blur-xl sm:p-6">
            <div className="mb-5">
              <label className="text-sm font-medium text-neutral-200">
                Google Drive folder
              </label>

              <p className="mt-1 text-xs text-neutral-600">
                Paste the URL of the folder you want to analyze.
              </p>
            </div>

            {/* Input */}
            <div
              className={`
                flex
                items-center
                rounded-xl
                border
                bg-black/20
                transition
                ${
                  error
                    ? "border-red-500/40"
                    : "border-white/[0.08] focus-within:border-white/20"
                }
              `}
            >
              <div className="pl-4 text-neutral-600">
                <FiFolder />
              </div>

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
                  px-3
                  py-4
                  text-sm
                  text-white
                  outline-none
                  placeholder:text-neutral-700
                "
              />

              <button
                onClick={analyzeFolder}
                disabled={analyzing}
                className="
                  mr-1.5
                  flex
                  h-10
                  items-center
                  gap-2
                  rounded-lg
                  bg-white
                  px-4
                  text-xs
                  font-medium
                  text-black
                  transition
                  hover:bg-neutral-200
                  disabled:cursor-not-allowed
                  disabled:opacity-50
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
                    <FiArrowRight />
                  </>
                )}
              </button>
            </div>

            {/* Error */}
            {error && (
              <div className="mt-3 rounded-lg border border-red-500/10 bg-red-500/[0.05] px-3 py-2.5 text-xs text-red-400">
                {error}
              </div>
            )}

            {/* Info */}
            <div className="mt-5 flex items-start gap-3 rounded-xl border border-white/[0.05] bg-white/[0.02] p-4">
              <FiShield className="mt-0.5 shrink-0 text-sm text-neutral-600" />
              <p className="text-[11px] leading-5 text-neutral-600">
                Make sure your Google account has access to the folder.
                Documents will be processed to build the RAG knowledge base.
              </p>
            </div>
          </div>

          {user?.email && (
            <p className="mt-6 text-center text-[11px] text-neutral-700">
              Signed in as {user.email}
            </p>
          )}
        </div>
      </main>
    </div>
  );
}

export default Analyze;
