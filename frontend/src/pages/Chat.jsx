import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  FiArrowUp,
  FiEdit2,
  FiFileText,
  FiMessageSquare,
  FiPlus,
  FiShield,
  FiTrash2,
  FiUser,
  FiX,
} from "react-icons/fi";

import api from "../services/api";
import Navbar from "../components/Navbar";

// ==================================================
// USER-SCOPED LOCAL STORAGE KEY
// ==================================================

function getActiveChatKey(user) {
  const userId = user?.sub || user?.email || "anonymous";

  return `gdrive_rag_active_conversation_${userId}`;
}

// ==================================================
// CHAT COMPONENT
// ==================================================

function Chat({ user, onSyncAnotherFolder, onLogout }) {
  const navigate = useNavigate();

  // IMPORTANT:
  // Every Google account gets its own
  // active conversation localStorage key.

  const activeChatKey = getActiveChatKey(user);

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

  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  // ==================================================
  // REFS
  // ==================================================

  const requestInFlightRef = useRef(false);

  const pendingSourcesRef = useRef([]);

  const messagesContainerRef = useRef(null);

  const messagesEndRef = useRef(null);

  // ==================================================
  // AUTO SCROLL
  // ==================================================

  useEffect(() => {
    const container = messagesContainerRef.current;

    if (!container) {
      return;
    }

    requestAnimationFrame(() => {
      container.scrollTo({
        top: container.scrollHeight,
        behavior: "smooth",
      });
    });
  }, [messages, loading]);

  // ==================================================
  // CLOSE MOBILE SIDEBAR WITH ESC
  // ==================================================

  useEffect(() => {
    function handleEscape(event) {
      if (event.key === "Escape") {
        setMobileSidebarOpen(false);
      }
    }

    document.addEventListener("keydown", handleEscape);

    return () => {
      document.removeEventListener("keydown", handleEscape);
    };
  }, []);

  // ==================================================
  // PREVENT BODY SCROLL
  // ==================================================

  useEffect(() => {
    if (!mobileSidebarOpen) {
      document.body.style.overflow = "";
      return;
    }

    document.body.style.overflow = "hidden";

    return () => {
      document.body.style.overflow = "";
    };
  }, [mobileSidebarOpen]);

  // ==================================================
  // INITIAL LOAD
  // ==================================================

  useEffect(() => {
    let ignore = false;

    async function initialLoad() {
      try {
        setLoadingConversations(true);
        setError("");

        const response = await api.get("/api/conversations");

        if (ignore) {
          return;
        }

        const items = response.data.conversations || [];

        setConversations(items);

        // No conversations
        if (items.length === 0) {
          setActiveConversationId(null);

          setMessages([]);

          localStorage.removeItem(activeChatKey);

          return;
        }

        // Restore this specific user's
        // last active conversation.

        const savedId = localStorage.getItem(activeChatKey);

        const savedConversation = items.find(
          (item) => String(item.id) === savedId,
        );

        const conversationToOpen = savedConversation || items[0];

        await loadConversation(conversationToOpen.id);
      } catch (error) {
        if (!ignore) {
          setError(
            error.response?.data?.detail || "Failed to load conversations.",
          );
        }
      } finally {
        if (!ignore) {
          setLoadingConversations(false);
        }
      }
    }

    initialLoad();

    return () => {
      ignore = true;
    };
  }, [activeChatKey]);

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

      localStorage.setItem(activeChatKey, String(conversationId));
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

      localStorage.setItem(activeChatKey, String(conversationId));

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
  // GENERATE TITLE
  // ==================================================

  function generateChatTitle(text) {
    const cleaned = text.replace(/\s+/g, " ").trim();

    if (!cleaned) {
      return "New Chat";
    }

    const maxLength = 45;

    if (cleaned.length <= maxLength) {
      return cleaned;
    }

    return `${cleaned.slice(0, maxLength).trim()}...`;
  }

  // ==================================================
  // UPDATE CHAT TITLE
  // ==================================================

  async function updateChatTitle(conversationId, title) {
    try {
      await api.patch(`/api/conversations/${conversationId}`, {
        title,
      });
    } catch (error) {
      console.error("Failed to update conversation title:", error);
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
        localStorage.removeItem(activeChatKey);

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

      const items = response.data.conversations || [];

      setConversations(items);
    } catch {
      // Don't interrupt active chat.
    }
  }

  // ==================================================
  // SSE PARSER
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

    const isFirstMessage = messages.length === 0;

    const generatedTitle = generateChatTitle(currentQuestion);

    // ----------------------------------------------
    // Optimistically update title
    // ----------------------------------------------

    if (isFirstMessage && activeConversationId) {
      setConversations((previous) =>
        previous.map((conversation) =>
          conversation.id === activeConversationId
            ? {
                ...conversation,
                title: generatedTitle,
              }
            : conversation,
        ),
      );

      updateChatTitle(activeConversationId, generatedTitle);
    }

    // ----------------------------------------------
    // Add optimistic messages
    // ----------------------------------------------

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

    setQuestion("");

    try {
      // IMPORTANT:
      // Use Vercel same-origin proxy.
      // Do not use VITE_API_BASE_URL here.

      const response = await fetch("/api/query/stream", {
        method: "POST",

        credentials: "include",

        headers: {
          "Content-Type": "application/json",

          Accept: "text/event-stream",
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
          // Ignore parsing errors.
        }

        throw new Error(detail);
      }

      if (!response.body) {
        throw new Error("Streaming response is unavailable.");
      }

      const reader = response.body.getReader();

      const decoder = new TextDecoder();

      let buffer = "";

      // ----------------------------------------------
      // Read SSE stream
      // ----------------------------------------------

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

              localStorage.setItem(activeChatKey, String(conversationId));

              // New conversation created by
              // the backend during the query.

              if (isFirstMessage && conversationId) {
                setConversations((previous) =>
                  previous.map((conversation) =>
                    conversation.id === conversationId
                      ? {
                          ...conversation,
                          id: conversationId,
                          title: generatedTitle,
                        }
                      : conversation,
                  ),
                );

                updateChatTitle(conversationId, generatedTitle);
              }
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
            throw new Error(
              data.message || data.content || "Generation failed.",
            );
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
      // Remove optimistic user +
      // assistant messages.

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
  // SYNC ANOTHER FOLDER
  // ==================================================

  function handleSyncAnotherFolder() {
    if (typeof onSyncAnotherFolder === "function") {
      onSyncAnotherFolder();
    } else {
      localStorage.removeItem("gdrive_rag_session");
    }

    navigate("/analyze");
  }

  // ==================================================
  // MOBILE: OPEN CONVERSATION
  // ==================================================

  async function handleMobileConversation(conversationId) {
    await loadConversation(conversationId);

    setMobileSidebarOpen(false);
  }

  // ==================================================
  // MOBILE: NEW CHAT
  // ==================================================

  async function handleMobileNewChat() {
    await createNewChat();

    setMobileSidebarOpen(false);
  }

  // ==================================================
  // RENDER
  // ==================================================

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#090909] text-white selection:bg-white/10 selection:text-white">
      {/* ==================================================
          BACKGROUND
      ================================================== */}

      <div
        className="pointer-events-none fixed inset-0 opacity-[0.028]"
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

      <div className="pointer-events-none fixed left-1/2 top-[-420px] h-[760px] w-[760px] -translate-x-1/2 rounded-full bg-white/[0.025] blur-[130px]" />

      <div className="pointer-events-none fixed bottom-[-350px] left-[15%] h-[550px] w-[550px] rounded-full bg-white/[0.012] blur-[130px]" />

      {/* ==================================================
          NAVBAR
      ================================================== */}

      <Navbar
        user={user}
        onLogout={onLogout}
        showDashboard={true}
        showChat={true}
        showHistory={true}
        onHistory={() => setMobileSidebarOpen(true)}
        activeTab="chat"
      />

      {/* ==================================================
          APP LAYOUT
      ================================================== */}

      <div className="relative flex h-[calc(100dvh-84px)] overflow-hidden bg-[#090909]">
        {/* ==================================================
            DESKTOP SIDEBAR
        ================================================== */}

        <aside className="hidden w-[280px] shrink-0 border-r border-white/[0.06] bg-[#0d0d0d]/90 backdrop-blur-2xl lg:flex lg:flex-col">
          <div className="border-b border-white/[0.06] p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-neutral-200">
                  Conversations
                </p>

                <p className="mt-1 text-[10px] text-neutral-600">
                  Your chat history
                </p>
              </div>

              <button
                type="button"
                onClick={createNewChat}
                disabled={loading}
                className="
                  flex
                  h-9
                  w-9
                  items-center
                  justify-center
                  rounded-xl
                  border
                  border-white/[0.08]
                  bg-white/[0.035]
                  text-neutral-500
                  transition-all
                  duration-200
                  hover:border-white/[0.14]
                  hover:bg-white/[0.07]
                  hover:text-white
                  disabled:cursor-not-allowed
                  disabled:opacity-50
                "
                title="New chat"
              >
                <FiPlus className="text-sm" />
              </button>
            </div>
          </div>

          <div className="chat-sidebar-scrollbar flex-1 overflow-y-auto p-3">
            {loadingConversations ? (
              <div className="rounded-xl border border-white/[0.05] bg-white/[0.015] px-3 py-4 text-xs text-neutral-600">
                Loading conversations...
              </div>
            ) : conversations.length === 0 ? (
              <div className="rounded-xl border border-dashed border-white/[0.06] bg-white/[0.012] px-3 py-5 text-xs leading-5 text-neutral-600">
                No conversations yet. Start your first chat.
              </div>
            ) : (
              <div className="space-y-1.5">
                {conversations.map((conversation) => {
                  const active =
                    String(activeConversationId) === String(conversation.id);

                  return (
                    <div
                      key={conversation.id}
                      className={`
                          group
                          flex
                          items-center
                          gap-1
                          rounded-xl
                          border
                          transition-all
                          duration-200
                          ${
                            active
                              ? "border-white/[0.11] bg-white/[0.065] shadow-lg shadow-black/20"
                              : "border-transparent hover:border-white/[0.06] hover:bg-white/[0.035]"
                          }
                        `}
                    >
                      <button
                        type="button"
                        onClick={() => loadConversation(conversation.id)}
                        disabled={loading}
                        className="
                            min-w-0
                            flex-1
                            px-3
                            py-3
                            text-left
                            disabled:opacity-50
                          "
                      >
                        <div className="flex items-center gap-2.5">
                          <div
                            className={`
                                flex
                                h-7
                                w-7
                                shrink-0
                                items-center
                                justify-center
                                rounded-lg
                                border
                                ${
                                  active
                                    ? "border-white/[0.10] bg-white/[0.07]"
                                    : "border-white/[0.05] bg-white/[0.025]"
                                }
                              `}
                          >
                            <FiMessageSquare
                              className={`
                                  text-[11px]
                                  ${
                                    active
                                      ? "text-neutral-300"
                                      : "text-neutral-600"
                                  }
                                `}
                            />
                          </div>

                          <span className="truncate text-xs text-neutral-300">
                            {conversation.title || "New Chat"}
                          </span>
                        </div>
                      </button>

                      <button
                        type="button"
                        onClick={() => renameConversation(conversation)}
                        disabled={loading}
                        className="
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
                        type="button"
                        onClick={() => deleteConversation(conversation.id)}
                        disabled={loading}
                        className="
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

          <div className="border-t border-white/[0.06] p-3">
            <button
              type="button"
              onClick={createNewChat}
              disabled={loading}
              className="
                flex
                w-full
                items-center
                justify-center
                gap-2
                rounded-xl
                border
                border-white/[0.07]
                bg-white/[0.025]
                px-3
                py-2.5
                text-xs
                font-medium
                text-neutral-400
                transition-all
                duration-200
                hover:border-white/[0.12]
                hover:bg-white/[0.05]
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
            MOBILE CHAT HISTORY
        ================================================== */}

        {mobileSidebarOpen && (
          <div className="fixed inset-x-0 bottom-0 top-[84px] z-[60] lg:hidden">
            <button
              type="button"
              aria-label="Close chat history"
              onClick={() => setMobileSidebarOpen(false)}
              className="
                absolute
                inset-0
                cursor-default
                bg-black/65
                backdrop-blur-[3px]
              "
            />

            <aside
              className="
                relative
                flex
                h-full
                w-[min(86vw,320px)]
                flex-col
                border-r
                border-white/[0.08]
                bg-[#0d0d0d]
                shadow-2xl
              "
            >
              <div className="flex items-center justify-between border-b border-white/[0.06] bg-white/[0.015] p-4">
                <div>
                  <p className="text-sm font-medium text-neutral-200">
                    Conversations
                  </p>

                  <p className="mt-1 text-[10px] text-neutral-600">
                    Chat history
                  </p>
                </div>

                <button
                  type="button"
                  onClick={() => setMobileSidebarOpen(false)}
                  className="
                    flex
                    h-8
                    w-8
                    items-center
                    justify-center
                    rounded-xl
                    border
                    border-white/[0.08]
                    bg-white/[0.035]
                    text-neutral-500
                    transition
                    hover:bg-white/[0.08]
                    hover:text-white
                  "
                  aria-label="Close chat history"
                >
                  <FiX className="text-sm" />
                </button>
              </div>

              <div className="border-b border-white/[0.06] p-3">
                <button
                  type="button"
                  onClick={handleMobileNewChat}
                  disabled={loading}
                  className="
                    flex
                    w-full
                    items-center
                    justify-center
                    gap-2
                    rounded-xl
                    border
                    border-white/[0.08]
                    bg-white/[0.04]
                    px-3
                    py-2.5
                    text-xs
                    font-medium
                    text-neutral-300
                    transition
                    hover:bg-white/[0.08]
                    hover:text-white
                    disabled:cursor-not-allowed
                    disabled:opacity-50
                  "
                >
                  <FiPlus />
                  New conversation
                </button>
              </div>

              <div className="chat-sidebar-scrollbar flex-1 overflow-y-auto p-3">
                {loadingConversations ? (
                  <div className="px-2 py-4 text-xs text-neutral-600">
                    Loading conversations...
                  </div>
                ) : conversations.length === 0 ? (
                  <div className="rounded-xl border border-dashed border-white/[0.06] bg-white/[0.012] px-3 py-5 text-xs leading-5 text-neutral-600">
                    No conversations yet. Start your first chat.
                  </div>
                ) : (
                  <div className="space-y-1.5">
                    {conversations.map((conversation) => {
                      const active =
                        String(activeConversationId) ===
                        String(conversation.id);

                      return (
                        <div
                          key={conversation.id}
                          className={`
                              group
                              flex
                              items-center
                              gap-1
                              rounded-xl
                              border
                              transition-all
                              duration-200
                              ${
                                active
                                  ? "border-white/[0.11] bg-white/[0.065]"
                                  : "border-transparent hover:border-white/[0.06] hover:bg-white/[0.035]"
                              }
                            `}
                        >
                          <button
                            type="button"
                            onClick={() =>
                              handleMobileConversation(conversation.id)
                            }
                            disabled={loading}
                            className="
                                min-w-0
                                flex-1
                                px-3
                                py-3
                                text-left
                                disabled:opacity-50
                              "
                          >
                            <div className="flex items-center gap-2.5">
                              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-white/[0.06] bg-white/[0.025]">
                                <FiMessageSquare className="text-[11px] text-neutral-600" />
                              </div>

                              <span className="truncate text-xs text-neutral-300">
                                {conversation.title || "New Chat"}
                              </span>
                            </div>
                          </button>

                          <button
                            type="button"
                            onClick={() => renameConversation(conversation)}
                            disabled={loading}
                            className="
                                flex
                                h-8
                                w-8
                                shrink-0
                                items-center
                                justify-center
                                rounded-lg
                                text-neutral-700
                                transition
                                hover:bg-white/[0.06]
                                hover:text-neutral-300
                                disabled:opacity-50
                              "
                            title="Rename"
                          >
                            <FiEdit2 className="text-xs" />
                          </button>

                          <button
                            type="button"
                            onClick={() => deleteConversation(conversation.id)}
                            disabled={loading}
                            className="
                                mr-1
                                flex
                                h-8
                                w-8
                                shrink-0
                                items-center
                                justify-center
                                rounded-lg
                                text-neutral-700
                                transition
                                hover:bg-red-500/[0.08]
                                hover:text-red-400
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
            </aside>
          </div>
        )}

        {/* ==================================================
            MAIN CHAT
        ================================================== */}

        <main className="relative flex h-full min-w-0 flex-1 flex-col overflow-hidden bg-[#090909]">
          <div className="min-h-0 flex-1 overflow-hidden px-4 sm:px-6">
            <div
              ref={messagesContainerRef}
              className="
                chat-scrollbar
                mx-auto
                h-full
                w-full
                max-w-3xl
                overflow-y-auto
                py-6
                sm:py-8
              "
            >
              {/* ==================================================
                  EMPTY STATE
              ================================================== */}

              {messages.length === 0 && !loading && !error ? (
                <div className="flex min-h-[calc(100vh-260px)] items-center justify-center px-2">
                  <div className="w-full max-w-2xl text-center">
                    <div className="relative mx-auto mb-7 flex h-16 w-16 items-center justify-center">
                      <div className="absolute inset-0 rounded-2xl bg-white/[0.025] blur-xl" />

                      <div className="relative flex h-16 w-16 items-center justify-center rounded-2xl border border-white/[0.09] bg-white/[0.035] shadow-2xl">
                        <FiFileText className="text-xl text-neutral-300" />
                      </div>
                    </div>

                    <p className="mb-3 text-[10px] font-medium uppercase tracking-[0.22em] text-neutral-700">
                      Zentra Knowledge Base
                    </p>

                    <h1 className="text-3xl font-semibold tracking-[-0.025em] text-neutral-100 sm:text-4xl">
                      Ask your documents
                    </h1>

                    <p className="mx-auto mt-4 max-w-md text-sm leading-6 text-neutral-500">
                      Ask questions about the documents in your Google Drive
                      knowledge base.
                    </p>

                    <div className="mt-9 grid grid-cols-1 gap-3 sm:grid-cols-2">
                      <button
                        type="button"
                        onClick={() =>
                          setQuestion("How many documents are available?")
                        }
                        className="
                          group
                          relative
                          overflow-hidden
                          rounded-2xl
                          border
                          border-white/[0.07]
                          bg-white/[0.02]
                          p-4
                          text-left
                          transition-all
                          duration-300
                          hover:-translate-y-0.5
                          hover:border-white/[0.14]
                          hover:bg-white/[0.04]
                          hover:shadow-xl
                        "
                      >
                        <div className="flex items-start gap-3">
                          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-white/[0.07] bg-white/[0.03] transition group-hover:border-white/[0.12] group-hover:bg-white/[0.055]">
                            <FiFileText className="text-sm text-neutral-500" />
                          </div>

                          <div className="min-w-0">
                            <p className="text-xs font-medium text-neutral-300">
                              Document overview
                            </p>

                            <p className="mt-1.5 text-[11px] leading-5 text-neutral-600">
                              How many documents are available?
                            </p>
                          </div>
                        </div>
                      </button>

                      <button
                        type="button"
                        onClick={() =>
                          setQuestion("Summarize the important information.")
                        }
                        className="
                          group
                          relative
                          overflow-hidden
                          rounded-2xl
                          border
                          border-white/[0.07]
                          bg-white/[0.02]
                          p-4
                          text-left
                          transition-all
                          duration-300
                          hover:-translate-y-0.5
                          hover:border-white/[0.14]
                          hover:bg-white/[0.04]
                          hover:shadow-xl
                        "
                      >
                        <div className="flex items-start gap-3">
                          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-white/[0.07] bg-white/[0.03] transition group-hover:border-white/[0.12] group-hover:bg-white/[0.055]">
                            <FiMessageSquare className="text-sm text-neutral-500" />
                          </div>

                          <div className="min-w-0">
                            <p className="text-xs font-medium text-neutral-300">
                              Summarize documents
                            </p>

                            <p className="mt-1.5 text-[11px] leading-5 text-neutral-600">
                              Summarize the important information.
                            </p>
                          </div>
                        </div>
                      </button>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="space-y-8 pb-4">
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
                        {/* USER */}

                        {message.role === "user" ? (
                          <div className="flex w-full justify-end">
                            <div className="flex max-w-[88%] items-end gap-3 sm:max-w-[78%]">
                              <div className="rounded-2xl rounded-tr-md border border-white/[0.09] bg-white/[0.075] px-4 py-3 shadow-[0_8px_30px_rgba(0,0,0,0.18)] transition hover:bg-white/[0.09]">
                                <p className="whitespace-pre-wrap text-sm leading-6 text-neutral-200">
                                  {message.content}
                                </p>
                              </div>

                              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-white/[0.08] bg-white/[0.04]">
                                <FiUser className="text-xs text-neutral-500" />
                              </div>
                            </div>
                          </div>
                        ) : (
                          // ASSISTANT

                          <div className="w-full">
                            <div className="flex items-start gap-3 sm:gap-4">
                              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border border-white/[0.08] bg-white/[0.035] shadow-sm">
                                <span className="text-[9px] font-semibold tracking-wide text-neutral-300">
                                  AI
                                </span>
                              </div>

                              <div className="min-w-0 flex-1">
                                <div className="mb-2 flex items-center gap-2">
                                  <p className="text-xs font-medium text-neutral-400">
                                    Zentra
                                  </p>

                                  <span className="h-1 w-1 rounded-full bg-neutral-700" />

                                  <span className="text-[10px] text-neutral-700">
                                    AI response
                                  </span>
                                </div>

                                {message.content ? (
                                  <div className="rounded-2xl border border-white/[0.055] bg-white/[0.018] px-4 py-4 whitespace-pre-wrap text-sm leading-7 text-neutral-300 shadow-sm sm:px-5 sm:py-5">
                                    {message.content}
                                  </div>
                                ) : isGenerating ? (
                                  <div className="rounded-2xl border border-white/[0.045] bg-white/[0.012] px-4 py-4">
                                    <div className="flex items-center gap-2">
                                      <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-neutral-500" />

                                      <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-neutral-500 [animation-delay:150ms]" />

                                      <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-neutral-500 [animation-delay:300ms]" />

                                      <span className="ml-2 text-xs text-neutral-600">
                                        Searching your documents...
                                      </span>
                                    </div>
                                  </div>
                                ) : null}

                                {/* SOURCES */}

                                {!isGenerating &&
                                  message.sources?.length > 0 && (
                                    <div className="mt-6">
                                      <div className="mb-3 flex items-center gap-2">
                                        <div className="flex h-6 w-6 items-center justify-center rounded-lg border border-white/[0.05] bg-white/[0.025]">
                                          <FiFileText className="text-[10px] text-neutral-600" />
                                        </div>

                                        <span className="text-[10px] font-medium uppercase tracking-[0.18em] text-neutral-600">
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
                                                  bg-white/[0.018]
                                                  px-4
                                                  py-3
                                                  transition-all
                                                  duration-200
                                                  hover:border-white/[0.11]
                                                  hover:bg-white/[0.03]
                                                "
                                            >
                                              <div className="flex items-start gap-3">
                                                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-white/[0.05] bg-white/[0.025]">
                                                  <FiFileText className="text-xs text-neutral-500" />
                                                </div>

                                                <div className="min-w-0">
                                                  <p className="truncate text-xs font-medium text-neutral-300">
                                                    {source.file_name}
                                                  </p>

                                                  <p className="mt-1 text-[10px] text-neutral-600">
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

                  <div ref={messagesEndRef} className="h-1" />
                </div>
              )}

              {/* ERROR */}

              {error && (
                <div className="mt-8 rounded-xl border border-red-500/[0.15] bg-red-500/[0.04] px-4 py-3 text-xs leading-5 text-red-400">
                  {error}
                </div>
              )}
            </div>
          </div>

          {/* ==================================================
              COMPOSER
          ================================================== */}

          <div className="sticky bottom-0 z-40 w-full shrink-0 border-t border-white/[0.06] bg-[#090909]/95 px-4 py-3 backdrop-blur-2xl sm:px-6 sm:py-4">
            <div className="mx-auto w-full max-w-3xl">
              <div className="rounded-2xl border border-white/[0.09] bg-[#131313]/95 p-2 shadow-[0_-10px_40px_rgba(0,0,0,0.18)] backdrop-blur-2xl transition-all duration-200 focus-within:border-white/[0.16] focus-within:bg-[#151515] focus-within:shadow-[0_-10px_50px_rgba(0,0,0,0.25)]">
                <textarea
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask anything about your documents..."
                  rows={1}
                  disabled={loading}
                  className="
                    max-h-36
                    min-h-[48px]
                    w-full
                    resize-none
                    bg-transparent
                    px-3
                    py-2.5
                    text-sm
                    leading-6
                    text-neutral-200
                    outline-none
                    placeholder:text-neutral-600
                    disabled:opacity-50
                  "
                />

                <div className="flex items-center justify-between px-2 pb-1 pt-1">
                  <div className="hidden items-center gap-1.5 text-[10px] text-neutral-700 sm:flex">
                    <FiShield className="text-[10px]" />

                    <span>Drive documents</span>
                  </div>

                  <button
                    type="button"
                    onClick={askQuestion}
                    disabled={loading || !question.trim()}
                    className="
                      ml-auto
                      flex
                      h-9
                      w-9
                      items-center
                      justify-center
                      rounded-xl
                      bg-white
                      text-black
                      shadow-lg
                      transition-all
                      duration-200
                      hover:-translate-y-0.5
                      hover:bg-neutral-200
                      hover:shadow-xl
                      active:translate-y-0
                      disabled:cursor-not-allowed
                      disabled:bg-white/[0.08]
                      disabled:text-neutral-600
                      disabled:shadow-none
                    "
                  >
                    <FiArrowUp className="text-sm" />
                  </button>
                </div>
              </div>

              <p className="mt-2 text-center text-[10px] text-neutral-700">
                AI-generated answers are based on your indexed Google Drive
                documents.
              </p>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

export default Chat;
