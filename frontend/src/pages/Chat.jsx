import { useEffect, useRef, useState } from "react";
import {
  FiArrowUp,
  FiEdit2,
  FiFileText,
  FiMessageSquare,
  FiPlus,
  FiShield,
  FiTrash2,
  FiUser,
} from "react-icons/fi";

import api from "../services/api";
import Navbar from "../components/Navbar";

const ACTIVE_CHAT_KEY = "gdrive_rag_active_conversation";

function Chat({ user, onSyncAnotherFolder }) {
  // ==================================================
  // CHAT STATE
  // ==================================================

  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);

  // ==================================================
  // CONVERSATION STATE
  // ==================================================

  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);

  // ==================================================
  // UI STATE
  // ==================================================

  const [loading, setLoading] = useState(false);
  const [loadingConversations, setLoadingConversations] = useState(true);
  const [error, setError] = useState("");

  // ==================================================
  // REFS
  // ==================================================

  const requestInFlightRef = useRef(false);

  const pendingSourcesRef = useRef([]);

  // IMPORTANT:
  // This is the actual scrollable chat container.
  const messagesContainerRef = useRef(null);

  // Invisible element at the very bottom of messages.
  const messagesEndRef = useRef(null);

  // ==================================================
  // AUTO SCROLL
  // ==================================================

  useEffect(() => {
    if (!messagesContainerRef.current) {
      return;
    }

    const container = messagesContainerRef.current;

    // Smoothly move to the latest message.
    requestAnimationFrame(() => {
      container.scrollTo({
        top: container.scrollHeight,
        behavior: "smooth",
      });
    });
  }, [messages, loading]);

  // ==================================================
  // INITIAL LOAD
  // ==================================================

  useEffect(() => {
    loadConversations();
  }, []);

  // ==================================================
  // LOAD CONVERSATIONS
  // ==================================================

  async function loadConversations() {
    try {
      setLoadingConversations(true);
      setError("");

      const response = await api.get("/api/conversations");

      const items = response.data.conversations || [];

      setConversations(items);

      if (items.length === 0) {
        setActiveConversationId(null);
        setMessages([]);

        localStorage.removeItem(ACTIVE_CHAT_KEY);

        return;
      }

      const savedId = localStorage.getItem(ACTIVE_CHAT_KEY);

      const savedConversation = items.find(
        (item) => String(item.id) === savedId,
      );

      const conversationToOpen = savedConversation || items[0];

      await loadConversation(conversationToOpen.id);
    } catch (error) {
      setError(error.response?.data?.detail || "Failed to load conversations.");
    } finally {
      setLoadingConversations(false);
    }
  }

  // ==================================================
  // LOAD ONE CONVERSATION
  // ==================================================

  async function loadConversation(conversationId) {
    if (requestInFlightRef.current) {
      return;
    }

    try {
      setError("");

      const response = await api.get(`/api/conversations/${conversationId}`);

      setMessages(response.data.messages || []);

      setActiveConversationId(conversationId);

      localStorage.setItem(ACTIVE_CHAT_KEY, String(conversationId));
    } catch (error) {
      setError(error.response?.data?.detail || "Failed to load conversation.");
    }
  }

  // ==================================================
  // CREATE NEW CHAT
  // ==================================================

  async function createNewChat() {
    if (requestInFlightRef.current) {
      return;
    }

    try {
      setError("");

      const response = await api.post("/api/conversations");

      const conversationId = response.data.conversation_id;

      const folderId = response.data.folder_id || null;

      const now = new Date().toISOString();

      const newConversation = {
        id: conversationId,
        folder_id: folderId,
        title: "New Chat",
        created_at: now,
        updated_at: now,
      };

      setConversations((previous) => [newConversation, ...previous]);

      setActiveConversationId(conversationId);

      localStorage.setItem(ACTIVE_CHAT_KEY, String(conversationId));

      setMessages([]);
      setQuestion("");
      setError("");
    } catch (error) {
      setError(
        error.response?.data?.detail || "Failed to create conversation.",
      );
    }
  }

  // ==================================================
  // DELETE CONVERSATION
  // ==================================================

  async function deleteConversation(conversationId) {
    if (requestInFlightRef.current) {
      return;
    }

    try {
      setError("");

      await api.delete(`/api/conversations/${conversationId}`);

      const remaining = conversations.filter(
        (conversation) => conversation.id !== conversationId,
      );

      setConversations(remaining);

      if (activeConversationId === conversationId) {
        localStorage.removeItem(ACTIVE_CHAT_KEY);

        if (remaining.length > 0) {
          await loadConversation(remaining[0].id);
        } else {
          setActiveConversationId(null);
          setMessages([]);
        }
      }
    } catch (error) {
      setError(
        error.response?.data?.detail || "Failed to delete conversation.",
      );
    }
  }

  // ==================================================
  // RENAME CONVERSATION
  // ==================================================

  async function renameConversation(conversation) {
    if (requestInFlightRef.current) {
      return;
    }

    const title = window.prompt("Conversation title:", conversation.title);

    if (title === null || !title.trim()) {
      return;
    }

    try {
      const newTitle = title.trim();

      await api.patch(`/api/conversations/${conversation.id}`, {
        title: newTitle,
      });

      setConversations((previous) =>
        previous.map((item) =>
          item.id === conversation.id
            ? {
                ...item,
                title: newTitle,
              }
            : item,
        ),
      );
    } catch (error) {
      setError(
        error.response?.data?.detail || "Failed to rename conversation.",
      );
    }
  }

  // ==================================================
  // REFRESH SIDEBAR
  // ==================================================

  async function refreshConversationList() {
    try {
      const response = await api.get("/api/conversations");

      setConversations(response.data.conversations || []);
    } catch {
      // Don't interrupt active chat.
    }
  }

  // ==================================================
  // SSE EVENT PARSER
  // ==================================================

  function parseSSEBlock(block) {
    const lines = block.split(/\r?\n/);

    let eventName = "message";
    let dataText = "";

    for (const line of lines) {
      if (line.startsWith("event:")) {
        eventName = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        dataText += line.slice(5).trim();
      }
    }

    if (!dataText) {
      return null;
    }

    let data;

    try {
      data = JSON.parse(dataText);
    } catch {
      return null;
    }

    return {
      eventName,
      data,
    };
  }

  // ==================================================
  // ASK QUESTION - STREAMING
  // ==================================================

  async function askQuestion() {
    const currentQuestion = question.trim();

    if (!currentQuestion || requestInFlightRef.current) {
      return;
    }

    requestInFlightRef.current = true;

    setLoading(true);
    setError("");

    pendingSourcesRef.current = [];

    // Add user message immediately.
    setMessages((previous) => [
      ...previous,

      {
        role: "user",
        content: currentQuestion,
        sources: [],
      },

      {
        role: "assistant",
        content: "",
        sources: [],
      },
    ]);

    // Clear composer immediately.
    setQuestion("");

    try {
      const response = await fetch("http://localhost:8000/api/query/stream", {
        method: "POST",

        credentials: "include",

        headers: {
          "Content-Type": "application/json",
        },

        body: JSON.stringify({
          question: currentQuestion,
          conversation_id: activeConversationId,
        }),
      });

      if (!response.ok) {
        let detail = "Failed to generate an answer.";

        try {
          const data = await response.json();

          detail = data.detail || detail;
        } catch {
          // Ignore parsing failure.
        }

        throw new Error(detail);
      }

      if (!response.body) {
        throw new Error("Streaming response is unavailable.");
      }

      const reader = response.body.getReader();

      const decoder = new TextDecoder();

      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();

        if (done) {
          break;
        }

        buffer += decoder.decode(value, {
          stream: true,
        });

        const blocks = buffer.split(/\r?\n\r?\n/);

        buffer = blocks.pop() || "";

        for (const block of blocks) {
          const parsed = parseSSEBlock(block);

          if (!parsed) {
            continue;
          }

          const { eventName, data } = parsed;

          // ==========================================
          // METADATA
          // ==========================================

          if (eventName === "metadata") {
            const conversationId = data.conversation_id;

            if (conversationId) {
              setActiveConversationId(conversationId);

              localStorage.setItem(ACTIVE_CHAT_KEY, String(conversationId));
            }

            pendingSourcesRef.current = data.sources || [];

            continue;
          }

          // ==========================================
          // TOKEN
          // ==========================================

          if (eventName === "token") {
            const token = data.content || "";

            if (!token) {
              continue;
            }

            setMessages((previous) => {
              if (previous.length === 0) {
                return previous;
              }

              const updated = [...previous];

              const lastIndex = updated.length - 1;

              updated[lastIndex] = {
                ...updated[lastIndex],

                content: (updated[lastIndex].content || "") + token,
              };

              return updated;
            });

            continue;
          }

          // ==========================================
          // ERROR
          // ==========================================

          if (eventName === "error") {
            throw new Error(data.message || "Generation failed.");
          }

          // ==========================================
          // DONE
          // ==========================================

          if (eventName === "done") {
            const finalSources = pendingSourcesRef.current || [];

            setMessages((previous) => {
              if (previous.length === 0) {
                return previous;
              }

              const updated = [...previous];

              const lastIndex = updated.length - 1;

              updated[lastIndex] = {
                ...updated[lastIndex],
                sources: finalSources,
              };

              return updated;
            });

            pendingSourcesRef.current = [];

            await refreshConversationList();
          }
        }
      }
    } catch (error) {
      // Remove optimistic messages.
      setMessages((previous) => previous.slice(0, -2));

      pendingSourcesRef.current = [];

      setError(error.message || "Failed to generate an answer.");
    } finally {
      requestInFlightRef.current = false;

      setLoading(false);
    }
  }

  // ==================================================
  // KEYBOARD
  // ==================================================

  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();

      askQuestion();
    }
  }

  // ==================================================
  // LOGOUT
  // ==================================================

  async function logout() {
    try {
      await api.post("/api/auth/logout");
    } finally {
      localStorage.removeItem(ACTIVE_CHAT_KEY);

      window.location.href = "/";
    }
  }

  // ==================================================
  // RENDER
  // ==================================================

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#050505] text-white">
      {/* ==================================================
          SCOPED STYLES (scrollbar + ambient motion)
      ================================================== */}

      <style>{`
        .aurora-drift {
          animation: aurora-drift 14s ease-in-out infinite;
        }
        @keyframes aurora-drift {
          0%, 100% { transform: translate(0px, 0px) scale(1); opacity: 0.55; }
          50% { transform: translate(20px, -15px) scale(1.08); opacity: 0.85; }
        }
        @media (prefers-reduced-motion: reduce) {
          .aurora-drift { animation: none; }
        }
        .thin-scroll::-webkit-scrollbar { width: 6px; height: 6px; }
        .thin-scroll::-webkit-scrollbar-track { background: transparent; }
        .thin-scroll::-webkit-scrollbar-thumb {
          background: linear-gradient(180deg, rgba(139,92,246,0.35), rgba(34,211,238,0.35));
          border-radius: 999px;
        }
        .thin-scroll::-webkit-scrollbar-thumb:hover {
          background: linear-gradient(180deg, rgba(139,92,246,0.55), rgba(34,211,238,0.55));
        }
        .focus-glow:focus-visible {
          outline: none;
          box-shadow: 0 0 0 2px #050505, 0 0 0 4px rgba(139,92,246,0.6);
        }
      `}</style>

      {/* ==================================================
          BACKGROUND
      ================================================== */}

      <div
        className="pointer-events-none fixed inset-0 opacity-[0.03]"
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

      {/* Twin aurora glow — signature ambient element, very low intensity */}
      <div
        aria-hidden="true"
        className="aurora-drift pointer-events-none fixed left-[10%] top-[-320px] h-[600px] w-[600px] rounded-full blur-[120px]"
        style={{
          background:
            "radial-gradient(circle, rgba(139,92,246,0.16), transparent 70%)",
        }}
      />
      <div
        aria-hidden="true"
        className="aurora-drift pointer-events-none fixed right-[8%] top-[-260px] h-[520px] w-[520px] rounded-full blur-[120px]"
        style={{
          background:
            "radial-gradient(circle, rgba(34,211,238,0.12), transparent 70%)",
          animationDelay: "3s",
        }}
      />

      {/* ==================================================
          NAVBAR
      ================================================== */}

      <Navbar user={user} onSyncAnotherFolder={onSyncAnotherFolder} />

      {/* ==================================================
          APP LAYOUT
      ================================================== */}

      <div className="relative flex h-[calc(100vh-84px)]">
        {/* ==================================================
            SIDEBAR
        ================================================== */}

        <aside className="hidden w-72 shrink-0 border-r border-white/[0.06] bg-white/[0.02] backdrop-blur-2xl lg:flex lg:flex-col">
          {/* Sidebar Header */}
          <div className="flex items-center justify-between border-b border-white/[0.06] p-4">
            <p className="text-sm font-medium tracking-wide text-neutral-300">
              Conversations
            </p>

            <button
              onClick={createNewChat}
              disabled={loading || requestInFlightRef.current}
              className="
                focus-glow
                flex
                h-8
                w-8
                items-center
                justify-center
                rounded-lg
                border
                border-white/[0.08]
                bg-white/[0.04]
                text-neutral-400
                transition
                hover:border-violet-400/30
                hover:bg-white/[0.08]
                hover:text-white
                disabled:cursor-not-allowed
                disabled:opacity-50
              "
              title="New chat"
            >
              <FiPlus />
            </button>
          </div>

          {/* Conversations */}
          <div className="thin-scroll flex-1 overflow-y-auto p-3">
            {loadingConversations ? (
              <div className="px-2 py-4 text-xs text-neutral-600">
                Loading conversations...
              </div>
            ) : conversations.length === 0 ? (
              <div className="px-2 py-4 text-xs leading-5 text-neutral-600">
                No conversations yet. Start your first chat.
              </div>
            ) : (
              <div className="space-y-1">
                {conversations.map((conversation) => {
                  const active = activeConversationId === conversation.id;

                  return (
                    <div
                      key={conversation.id}
                      className={`
                          group
                          relative
                          flex
                          items-center
                          gap-1
                          overflow-hidden
                          rounded-xl
                          border
                          transition
                          ${
                            active
                              ? "border-white/[0.09] bg-gradient-to-r from-violet-500/[0.08] via-white/[0.03] to-transparent"
                              : "border-transparent hover:bg-white/[0.035]"
                          }
                        `}
                    >
                      {active && (
                        <span
                          aria-hidden="true"
                          className="absolute inset-y-1.5 left-0 w-[3px] rounded-full bg-gradient-to-b from-violet-400 to-cyan-400"
                        />
                      )}

                      <button
                        onClick={() => loadConversation(conversation.id)}
                        disabled={loading}
                        className="
                            focus-glow
                            min-w-0
                            flex-1
                            px-3.5
                            py-2.5
                            text-left
                            disabled:opacity-50
                          "
                      >
                        <div className="flex items-center gap-2">
                          <FiMessageSquare
                            className={`shrink-0 text-xs ${active ? "text-violet-300" : "text-neutral-600"}`}
                          />

                          <span
                            className={`truncate text-xs ${active ? "text-neutral-100" : "text-neutral-300"}`}
                          >
                            {conversation.title}
                          </span>
                        </div>
                      </button>

                      <button
                        onClick={() => renameConversation(conversation)}
                        disabled={loading}
                        className="
                            focus-glow
                            hidden
                            h-7
                            w-7
                            items-center
                            justify-center
                            rounded-lg
                            text-neutral-700
                            transition
                            hover:bg-white/[0.06]
                            hover:text-neutral-300
                            group-hover:flex
                            disabled:opacity-50
                          "
                        title="Rename"
                      >
                        <FiEdit2 className="text-xs" />
                      </button>

                      <button
                        onClick={() => deleteConversation(conversation.id)}
                        disabled={loading}
                        className="
                            focus-glow
                            mr-1
                            hidden
                            h-7
                            w-7
                            items-center
                            justify-center
                            rounded-lg
                            text-neutral-700
                            transition
                            hover:bg-red-500/[0.08]
                            hover:text-red-400
                            group-hover:flex
                            disabled:opacity-50
                          "
                        title="Delete"
                      >
                        <FiTrash2 className="text-xs" />
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* New Conversation */}
          <div className="border-t border-white/[0.06] p-3">
            <button
              onClick={createNewChat}
              disabled={loading}
              className="
                focus-glow
                flex
                w-full
                items-center
                justify-center
                gap-2
                rounded-xl
                border
                border-white/[0.07]
                bg-white/[0.03]
                px-3
                py-2.5
                text-xs
                text-neutral-400
                transition
                hover:border-violet-400/20
                hover:bg-white/[0.06]
                hover:text-white
                disabled:opacity-50
              "
            >
              <FiPlus />
              New conversation
            </button>
          </div>
        </aside>

        {/* ==================================================
            MAIN CHAT
        ================================================== */}

        <main className="relative min-w-0 flex-1">
          {/* ==================================================
              MESSAGE SCROLL CONTAINER
          ================================================== */}

          <div
            ref={messagesContainerRef}
            className="
              thin-scroll
              absolute
              inset-0
              overflow-y-auto
              px-4
              pb-48
              pt-10
              sm:px-6
            "
          >
            {/* Content wrapper */}
            <div className="mx-auto w-full max-w-3xl">
              {/* ==================================================
                  EMPTY STATE
              ================================================== */}

              {messages.length === 0 && !loading && !error ? (
                <div className="flex min-h-[calc(100vh-260px)] items-center justify-center">
                  <div className="w-full max-w-2xl text-center">
                    <div className="relative mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-2xl border border-white/[0.09] bg-white/[0.04]">
                      <div
                        aria-hidden="true"
                        className="absolute inset-0 rounded-2xl bg-gradient-to-br from-violet-500/20 to-cyan-400/10 blur-md"
                      />
                      <FiFileText className="relative text-xl text-neutral-200" />
                    </div>

                    <h1 className="bg-gradient-to-r from-white via-white to-neutral-400 bg-clip-text text-3xl font-semibold tracking-tight text-transparent">
                      Ask your documents
                    </h1>

                    <p className="mx-auto mt-3 max-w-md text-sm leading-6 text-neutral-500">
                      Ask questions about the documents in your Google Drive
                      knowledge base.
                    </p>

                    <div className="mt-8 grid grid-cols-1 gap-3 sm:grid-cols-2">
                      <button
                        onClick={() =>
                          setQuestion("How many documents are available?")
                        }
                        disabled={loading}
                        className="
                          focus-glow
                          group
                          rounded-xl
                          border
                          border-white/[0.07]
                          bg-white/[0.025]
                          p-4
                          text-left
                          transition
                          hover:border-violet-400/25
                          hover:bg-white/[0.045]
                          disabled:opacity-50
                        "
                      >
                        <p className="text-xs font-medium text-neutral-300 group-hover:text-white">
                          Document overview
                        </p>

                        <p className="mt-1 text-[11px] text-neutral-600">
                          How many documents are available?
                        </p>
                      </button>

                      <button
                        onClick={() =>
                          setQuestion("Summarize the important information.")
                        }
                        disabled={loading}
                        className="
                          focus-glow
                          group
                          rounded-xl
                          border
                          border-white/[0.07]
                          bg-white/[0.025]
                          p-4
                          text-left
                          transition
                          hover:border-cyan-400/25
                          hover:bg-white/[0.045]
                          disabled:opacity-50
                        "
                      >
                        <p className="text-xs font-medium text-neutral-300 group-hover:text-white">
                          Summarize documents
                        </p>

                        <p className="mt-1 text-[11px] text-neutral-600">
                          Summarize the important information.
                        </p>
                      </button>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="space-y-8">
                  {/* ==================================================
                      MESSAGES
                  ================================================== */}

                  {messages.map((message, index) => {
                    const isLastMessage = index === messages.length - 1;

                    const isGenerating =
                      loading && isLastMessage && message.role === "assistant";

                    return (
                      <div
                        key={index}
                        className={
                          message.role === "user"
                            ? "flex justify-end"
                            : "flex justify-start"
                        }
                      >
                        {/* ==================================================
                              USER MESSAGE
                          ================================================== */}

                        {message.role === "user" ? (
                          <div className="flex w-full justify-end">
                            <div className="flex max-w-[85%] items-start gap-3 sm:max-w-[75%]">
                              <div
                                className="
                                    rounded-2xl
                                    rounded-tr-md
                                    border
                                    border-white/[0.09]
                                    bg-white/[0.07]
                                    px-4
                                    py-3
                                    shadow-[0_1px_0_0_rgba(255,255,255,0.04)_inset]
                                    backdrop-blur-sm
                                  "
                              >
                                <p className="whitespace-pre-wrap text-sm leading-6 text-neutral-200">
                                  {message.content}
                                </p>
                              </div>

                              <div
                                className="
                                    mt-1
                                    flex
                                    h-8
                                    w-8
                                    shrink-0
                                    items-center
                                    justify-center
                                    rounded-full
                                    border
                                    border-white/[0.08]
                                    bg-white/[0.04]
                                  "
                              >
                                <FiUser className="text-xs text-neutral-500" />
                              </div>
                            </div>
                          </div>
                        ) : (
                          /* ==================================================
                               ASSISTANT MESSAGE
                            ================================================== */

                          <div className="w-full">
                            <div className="flex items-start gap-3 sm:gap-4">
                              {/* AI Icon */}
                              <div
                                className="
                                    relative
                                    flex
                                    h-8
                                    w-8
                                    shrink-0
                                    items-center
                                    justify-center
                                    overflow-hidden
                                    rounded-xl
                                    border
                                    border-white/[0.08]
                                    bg-white/[0.04]
                                  "
                              >
                                <div
                                  aria-hidden="true"
                                  className="absolute inset-0 bg-gradient-to-br from-violet-500/25 to-cyan-400/15"
                                />
                                <span className="relative text-[10px] font-semibold text-neutral-100">
                                  AI
                                </span>
                              </div>

                              {/* Assistant Content */}
                              <div className="min-w-0 flex-1 border-l border-white/[0.06] pl-4 sm:pl-5">
                                <p className="mb-2 text-xs font-medium text-neutral-500">
                                  Google Drive RAG
                                </p>

                                {/* Answer */}
                                {message.content ? (
                                  <div className="whitespace-pre-wrap text-sm leading-7 text-neutral-300">
                                    {message.content}
                                  </div>
                                ) : isGenerating ? (
                                  <div className="flex items-center gap-2 py-2">
                                    <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-violet-400" />

                                    <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-fuchsia-400 [animation-delay:150ms]" />

                                    <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-cyan-400 [animation-delay:300ms]" />

                                    <span className="ml-2 text-xs text-neutral-600">
                                      Searching your documents...
                                    </span>
                                  </div>
                                ) : null}

                                {/* Sources */}
                                {!isGenerating &&
                                  message.sources?.length > 0 && (
                                    <div className="mt-6">
                                      <div className="mb-3 flex items-center gap-2">
                                        <FiFileText className="text-xs text-neutral-600" />

                                        <span className="text-[11px] font-medium uppercase tracking-wider text-neutral-600">
                                          Sources
                                        </span>
                                      </div>

                                      <div className="space-y-2">
                                        {message.sources.map(
                                          (source, sourceIndex) => (
                                            <div
                                              key={sourceIndex}
                                              className="
                                                  group
                                                  rounded-xl
                                                  border
                                                  border-white/[0.06]
                                                  bg-white/[0.02]
                                                  px-4
                                                  py-3
                                                  transition
                                                  hover:border-violet-400/20
                                                  hover:bg-white/[0.035]
                                                "
                                            >
                                              <div className="flex items-start gap-3">
                                                <div
                                                  className="
                                                      flex
                                                      h-8
                                                      w-8
                                                      shrink-0
                                                      items-center
                                                      justify-center
                                                      rounded-lg
                                                      bg-white/[0.04]
                                                      transition
                                                      group-hover:bg-gradient-to-br
                                                      group-hover:from-violet-500/20
                                                      group-hover:to-cyan-400/10
                                                    "
                                                >
                                                  <FiFileText className="text-xs text-neutral-500 group-hover:text-neutral-200" />
                                                </div>

                                                <div className="min-w-0">
                                                  <p className="truncate text-xs font-medium text-neutral-300">
                                                    {source.file_name}
                                                  </p>

                                                  <p className="mt-0.5 text-[10px] text-neutral-600">
                                                    Chunk {source.chunk_id}
                                                    {source.path && (
                                                      <>
                                                        {" · "}
                                                        {source.path}
                                                      </>
                                                    )}
                                                  </p>
                                                </div>
                                              </div>
                                            </div>
                                          ),
                                        )}
                                      </div>
                                    </div>
                                  )}
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}

                  {/* Invisible bottom anchor */}
                  <div ref={messagesEndRef} className="h-1" />
                </div>
              )}

              {/* Error */}
              {error && (
                <div className="mt-8 rounded-xl border border-red-500/15 bg-red-500/[0.05] px-4 py-3 text-xs text-red-400">
                  {error}
                </div>
              )}
            </div>
          </div>

          {/* ==================================================
              COMPOSER
          ================================================== */}

          <div className="pointer-events-none absolute bottom-0 left-0 right-0 z-40">
            {/* Fade */}
            <div className="pointer-events-none absolute inset-x-0 bottom-0 h-48 bg-gradient-to-t from-[#050505] via-[#050505]/95 to-transparent" />

            <div className="relative mx-auto w-full max-w-3xl px-4 pb-5 sm:px-6">
              {/* Composer */}
              <div className="pointer-events-auto relative rounded-2xl border border-white/[0.09] bg-[#0c0c0c]/90 p-2 shadow-2xl backdrop-blur-2xl focus-within:border-violet-400/30">
                <div
                  aria-hidden="true"
                  className="pointer-events-none absolute -inset-px -z-10 rounded-2xl bg-gradient-to-r from-violet-500/[0.06] via-transparent to-cyan-400/[0.06]"
                />

                <textarea
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask anything about your documents..."
                  rows={1}
                  disabled={loading}
                  className="
                    focus-glow
                    max-h-40
                    min-h-[52px]
                    w-full
                    resize-none
                    rounded-xl
                    bg-transparent
                    px-4
                    py-3
                    text-sm
                    leading-6
                    text-neutral-200
                    outline-none
                    placeholder:text-neutral-600
                    disabled:opacity-50
                  "
                />

                <div className="flex items-center justify-between px-2 pb-1">
                  <div className="flex items-center gap-2">
                    <div className="hidden items-center gap-1.5 text-[10px] text-neutral-700 sm:flex">
                      <FiShield />
                      Drive documents
                    </div>
                  </div>

                  <button
                    onClick={askQuestion}
                    disabled={loading || !question.trim()}
                    className="
                      focus-glow
                      flex
                      h-9
                      w-9
                      items-center
                      justify-center
                      rounded-xl
                      bg-gradient-to-br
                      from-violet-500
                      to-cyan-400
                      text-black
                      shadow-[0_0_16px_rgba(139,92,246,0.35)]
                      transition
                      hover:shadow-[0_0_20px_rgba(139,92,246,0.5)]
                      disabled:cursor-not-allowed
                      disabled:bg-white/[0.08]
                      disabled:bg-none
                      disabled:text-neutral-600
                      disabled:shadow-none
                    "
                  >
                    <FiArrowUp className="text-sm" />
                  </button>
                </div>
              </div>

              <p className="pointer-events-auto mt-2 text-center text-[10px] text-neutral-700">
                AI-generated answers are based on your indexed Google Drive
                documents.
              </p>
            </div>
          </div>
        </main>
      </div>

      {/* ==================================================
          MOBILE NEW CHAT
      ================================================== */}

      <button
        onClick={createNewChat}
        disabled={loading}
        className="
          focus-glow
          fixed
          bottom-24
          right-5
          z-50
          flex
          h-11
          w-11
          items-center
          justify-center
          rounded-full
          border
          border-white/[0.08]
          bg-[#0c0c0c]
          text-neutral-300
          shadow-[0_0_18px_rgba(139,92,246,0.25)]
          lg:hidden
        "
        title="New chat"
      >
        <FiPlus />
      </button>
    </div>
  );
}

export default Chat;
