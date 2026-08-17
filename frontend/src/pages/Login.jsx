import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { FiFolder, FiShield } from "react-icons/fi";
import { FcGoogle } from "react-icons/fc";

function Login({ user, checkingAuth }) {
  const navigate = useNavigate();

  useEffect(() => {
    if (!checkingAuth && user) {
      const savedSession = localStorage.getItem("gdrive_rag_session");
      if (savedSession) {
        navigate("/chat", { replace: true });
      } else {
        navigate("/analyze", { replace: true });
      }
    }
  }, [user, checkingAuth, navigate]);

  function login() {
    const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");
    window.location.href = `${apiBaseUrl}/api/auth/google`;
  }



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
      <div className="pointer-events-none absolute left-1/2 top-[-300px] h-[600px] w-[600px] -translate-x-1/2 rounded-full bg-white/[0.025] blur-3xl" />

      <main className="relative flex min-h-screen items-center justify-center px-6">
        <div className="w-full max-w-md text-center">
          <div className="mx-auto mb-7 flex h-14 w-14 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.05]">
            <FiFolder className="text-xl text-neutral-200" />
          </div>

          <h1 className="text-3xl font-semibold tracking-tight">
            Google Drive RAG
          </h1>

          <p className="mx-auto mt-3 max-w-sm text-sm leading-6 text-neutral-500">
            Connect your Google Drive and chat with your documents using
            AI-powered search.
          </p>

          <div className="mt-8 rounded-2xl border border-white/[0.08] bg-white/[0.035] p-6 text-left shadow-2xl backdrop-blur-xl">
            <p className="flex items-center justify-center text-sm font-medium text-neutral-200">
              Welcome back
            </p>

            <p className="mt-1 flex items-center justify-center text-xs text-neutral-600">
              Sign in with Google to access your documents.
            </p>

            <button
              onClick={login}
              className="
                mt-6
                flex
                w-full
                items-center
                justify-center
                gap-3
                rounded-xl
                bg-white
                px-4
                py-3
                text-sm
                font-medium
                text-black
                transition
                hover:bg-neutral-200
                active:scale-[0.99]
              "
            >
              <FcGoogle className="text-xl" />
              <span>Continue with Google</span>
            </button>

            <div className="mt-6 flex items-center justify-center gap-2 text-[11px] text-neutral-600">
              <FiShield />
              <span>Your documents remain private.</span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default Login;
