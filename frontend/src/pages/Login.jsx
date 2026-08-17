import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

import {
  FiArrowRight,
  FiDatabase,
  FiFileText,
  FiFolder,
  FiSearch,
  FiShield,
} from "react-icons/fi";

import { FcGoogle } from "react-icons/fc";

const STORAGE_KEY = "gdrive_rag_session";

function Login({ user, checkingAuth }) {
  const navigate = useNavigate();

  // ==================================================
  // REDIRECT AFTER AUTHENTICATION
  // ==================================================

  useEffect(() => {
    if (checkingAuth || !user) {
      return;
    }

    try {
      const savedSession = localStorage.getItem(STORAGE_KEY);

      if (savedSession) {
        const parsedSession = JSON.parse(savedSession);

        /*
         * User has already analyzed a folder.
         *
         * Chat history does NOT matter.
         */

        if (parsedSession?.folderUrl && parsedSession?.analysis) {
          navigate("/chat", {
            replace: true,
          });

          return;
        }
      }
    } catch (error) {
      console.error("Failed to read saved session:", error);

      localStorage.removeItem(STORAGE_KEY);
    }

    // No analyzed folder
    navigate("/analyze", {
      replace: true,
    });
  }, [user, checkingAuth, navigate]);

  // ==================================================
  // GOOGLE LOGIN
  // ==================================================

  function login() {
    window.location.href = "/api/auth/google";
  }

  // ==================================================
  // LOADING
  // ==================================================

  if (checkingAuth) {
    return (
      <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[#080808] text-white">
        <Background />

        <div className="relative flex flex-col items-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-white/[0.09] bg-white/[0.035] shadow-2xl backdrop-blur-xl">
            <FiFolder className="text-lg text-neutral-300" />
          </div>

          <p className="mt-5 text-sm font-medium text-neutral-300">Zentra</p>

          <p className="mt-2 text-xs text-neutral-600">
            Checking authentication...
          </p>

          <div className="mt-5 h-1 w-1 animate-pulse rounded-full bg-neutral-400" />
        </div>
      </div>
    );
  }

  // ==================================================
  // ALREADY AUTHENTICATED
  // ==================================================

  if (user) {
    return (
      <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[#080808] text-white">
        <Background />

        <div className="relative flex flex-col items-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-white/[0.09] bg-white/[0.035] shadow-2xl backdrop-blur-xl">
            <FiFolder className="text-lg text-neutral-300" />
          </div>

          <p className="mt-5 text-sm font-medium text-neutral-300">Zentra</p>

          <p className="mt-2 text-xs text-neutral-600">
            Opening your workspace...
          </p>
        </div>
      </div>
    );
  }

  // ==================================================
  // LOGIN PAGE
  // ==================================================

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#080808] text-white">
      <Background />

      <main className="relative flex min-h-screen items-center justify-center px-5 py-12">
        <div className="w-full max-w-5xl">
          {/* BRAND */}

          <div className="mb-12 text-center">
            <div className="relative mx-auto mb-6 flex h-16 w-16 items-center justify-center">
              <div className="absolute inset-0 rounded-2xl bg-white/[0.03] blur-xl" />

              <div className="relative flex h-16 w-16 items-center justify-center rounded-2xl border border-white/[0.09] bg-white/[0.035] shadow-2xl backdrop-blur-xl">
                <FiFolder className="text-xl text-neutral-200" />
              </div>
            </div>

            <h1 className="text-4xl font-semibold tracking-[-0.03em] text-white sm:text-5xl">
              Zentra
            </h1>

            <p className="mt-4 text-sm font-medium tracking-wide text-neutral-400">
              Where Your Data Becomes Knowledge
            </p>

            <p className="mx-auto mt-3 max-w-md text-xs leading-6 text-neutral-600">
              Connect your Google Drive, search your documents, and get
              intelligent answers from your own data.
            </p>
          </div>

          {/* CONTENT */}

          <div className="grid gap-5 lg:grid-cols-[1fr_420px] lg:items-center">
            {/* FEATURES */}

            <div className="hidden lg:block">
              <div className="grid grid-cols-2 gap-3">
                <FeatureCard
                  icon={<FiFolder />}
                  title="Connect"
                  description="Connect a Google Drive folder and bring your documents into Zentra."
                />

                <FeatureCard
                  icon={<FiSearch />}
                  title="Search"
                  description="Find relevant information across your indexed documents."
                />

                <FeatureCard
                  icon={<FiDatabase />}
                  title="Understand"
                  description="Your documents become a searchable knowledge base."
                />

                <FeatureCard
                  icon={<FiFileText />}
                  title="Answer"
                  description="Ask natural questions and receive answers with document sources."
                />
              </div>

              <div className="mt-5 flex items-center gap-3 rounded-2xl border border-white/[0.06] bg-white/[0.02] px-5 py-4 backdrop-blur-xl">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-white/[0.06] bg-white/[0.03]">
                  <FiShield className="text-sm text-neutral-500" />
                </div>

                <div>
                  <p className="text-xs font-medium text-neutral-300">
                    Your data, your knowledge
                  </p>

                  <p className="mt-1 text-[11px] text-neutral-600">
                    Zentra works with the documents you choose to connect.
                  </p>
                </div>
              </div>
            </div>

            {/* LOGIN CARD */}

            <div className="relative">
              <div className="absolute -inset-8 rounded-[40px] bg-white/[0.015] blur-3xl" />

              <div className="relative rounded-3xl border border-white/[0.09] bg-white/[0.035] p-6 shadow-2xl backdrop-blur-2xl sm:p-8">
                <div className="text-center">
                  <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-xl border border-white/[0.08] bg-white/[0.04]">
                    <FiDatabase className="text-sm text-neutral-400" />
                  </div>

                  <h2 className="mt-5 text-lg font-medium text-neutral-200">
                    Welcome to Zentra
                  </h2>

                  <p className="mx-auto mt-2 max-w-xs text-xs leading-5 text-neutral-600">
                    Sign in with Google to connect and explore your documents.
                  </p>
                </div>

                <button
                  type="button"
                  onClick={login}
                  className="
                    group
                    mt-7
                    flex
                    w-full
                    items-center
                    justify-between
                    rounded-xl
                    border
                    border-white/[0.08]
                    bg-white
                    px-4
                    py-3.5
                    text-sm
                    font-medium
                    text-black
                    shadow-xl
                    transition-all
                    duration-200
                    hover:bg-neutral-200
                    active:scale-[0.99]
                  "
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-neutral-100">
                      <FcGoogle className="text-lg" />
                    </div>

                    <span>Continue with Google</span>
                  </div>

                  <FiArrowRight className="text-sm transition-transform duration-200 group-hover:translate-x-0.5" />
                </button>

                <div className="my-6 flex items-center gap-3">
                  <div className="h-px flex-1 bg-white/[0.06]" />

                  <span className="text-[10px] uppercase tracking-widest text-neutral-700">
                    Secure access
                  </span>

                  <div className="h-px flex-1 bg-white/[0.06]" />
                </div>

                <div className="flex items-start gap-3 rounded-xl border border-white/[0.05] bg-black/20 p-3.5">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-white/[0.06] bg-white/[0.025]">
                    <FiShield className="text-xs text-neutral-500" />
                  </div>

                  <div>
                    <p className="text-[11px] font-medium text-neutral-400">
                      Google authentication
                    </p>

                    <p className="mt-1 text-[10px] leading-4 text-neutral-700">
                      You will be redirected to Google to securely authenticate
                      your account.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <p className="mt-10 text-center text-[10px] tracking-wide text-neutral-700">
            Zentra · Google Drive Knowledge System
          </p>
        </div>
      </main>
    </div>
  );
}

// ==================================================
// FEATURE CARD
// ==================================================

function FeatureCard({ icon, title, description }) {
  return (
    <div
      className="
        group
        rounded-2xl
        border
        border-white/[0.06]
        bg-white/[0.02]
        p-5
        backdrop-blur-xl
        transition-all
        duration-300
        hover:border-white/[0.1]
        hover:bg-white/[0.035]
      "
    >
      <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/[0.07] bg-white/[0.03] text-sm text-neutral-500 transition group-hover:text-neutral-300">
        {icon}
      </div>

      <h3 className="mt-4 text-xs font-medium text-neutral-300">{title}</h3>

      <p className="mt-2 text-[11px] leading-5 text-neutral-700">
        {description}
      </p>
    </div>
  );
}

// ==================================================
// BACKGROUND
// ==================================================

function Background() {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      {/* Grid */}

      <div
        className="absolute inset-0 opacity-[0.035]"
        style={{
          backgroundImage: `
            linear-gradient(
              rgba(255,255,255,0.6) 1px,
              transparent 1px
            ),
            linear-gradient(
              90deg,
              rgba(255,255,255,0.6) 1px,
              transparent 1px
            )
          `,
          backgroundSize: "48px 48px",
        }}
      />

      {/* Top glow */}

      <div className="absolute left-1/2 top-[-400px] h-[750px] w-[750px] -translate-x-1/2 rounded-full bg-white/[0.025] blur-[140px]" />

      {/* Left glow */}

      <div className="absolute left-[-250px] top-[35%] h-[500px] w-[500px] rounded-full bg-white/[0.012] blur-[130px]" />

      {/* Right glow */}

      <div className="absolute bottom-[-300px] right-[-150px] h-[550px] w-[550px] rounded-full bg-white/[0.012] blur-[130px]" />

      {/* Floating document */}

      <div className="absolute left-[8%] top-[22%] hidden h-14 w-14 rotate-[-8deg] items-center justify-center rounded-2xl border border-white/[0.05] bg-white/[0.018] lg:flex">
        <FiFileText className="text-lg text-white/[0.15]" />
      </div>

      {/* Floating search */}

      <div className="absolute right-[8%] top-[24%] hidden h-16 w-16 rotate-[8deg] items-center justify-center rounded-2xl border border-white/[0.05] bg-white/[0.018] lg:flex">
        <FiSearch className="text-xl text-white/[0.15]" />
      </div>

      {/* Floating folder */}

      <div className="absolute bottom-[20%] left-[12%] hidden h-16 w-16 rotate-[5deg] items-center justify-center rounded-2xl border border-white/[0.05] bg-white/[0.018] lg:flex">
        <FiFolder className="text-xl text-white/[0.12]" />
      </div>
    </div>
  );
}

export default Login;
