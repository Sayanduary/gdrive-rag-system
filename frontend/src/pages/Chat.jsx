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
    <div className="relative min-h-screen overflow-hidden bg-[#0d0d0d] text-white">
      {/* ==================================================
          BACKGROUND
      ================================================== */}

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

          backgroundSize: "50px 50px",
        }}
      />

      <div className="pointer-events-none fixed left-1/2 top-[-400px] h-[700px] w-[700px] -translate-x-1/2 rounded-full bg-white/[0.025] blur-3xl" />

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

        <aside className="hidden w-72 shrink-0 border-r border-white/[0.06] bg-[#101010]/80 backdrop-blur-xl lg:flex lg:flex-col">
          {/* Sidebar Header */}
          <div className="flex items-center justify-between border-b border-white/[0.06] p-4">
            <p className="text-sm font-medium text-neutral-300">
              Conversations
            </p>

            <button
              onClick={createNewChat}
              disabled={loading || requestInFlightRef.current}
              className="
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
          <div className="flex-1 overflow-y-auto p-3">
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
                          flex
                          items-center
                          gap-1
                          rounded-xl
                          border
                          transition
                          ${
                            active
                              ? "border-white/[0.09] bg-white/[0.06]"
                              : "border-transparent hover:bg-white/[0.035]"
                          }
                        `}
                    >
                      <button
                        onClick={() => loadConversation(conversation.id)}
                        disabled={loading}
                        className="
                            min-w-0
                            flex-1
                            px-3
                            py-2.5
                            text-left
                            disabled:opacity-50
                          "
                      >
                        <div className="flex items-center gap-2">
                          <FiMessageSquare className="shrink-0 text-xs text-neutral-600" />

                          <span className="truncate text-xs text-neutral-300">
                            {conversation.title}
                          </span>
                        </div>
                      </button>

                      <button
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

          {/* New Conversation */}
          <div className="border-t border-white/[0.06] p-3">
            <button
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
                bg-white/[0.03]
                px-3
                py-2.5
                text-xs
                text-neutral-400
                transition
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
                    <div className="mx-auto mb-6 flex h-14 w-14 items-center justify-center rounded-2xl border border-white/[0.09] bg-white/[0.04]">
                      <FiFileText className="text-xl text-neutral-300" />
                    </div>

                    <h1 className="text-3xl font-semibold tracking-tight">
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
                          rounded-xl
                          border
                          border-white/[0.07]
                          bg-white/[0.025]
                          p-4
                          text-left
                          transition
                          hover:border-white/[0.14]
                          hover:bg-white/[0.04]
                          disabled:opacity-50
                        "
                      >
                        <p className="text-xs font-medium text-neutral-300">
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
                          rounded-xl
                          border
                          border-white/[0.07]
                          bg-white/[0.025]
                          p-4
                          text-left
                          transition
                          hover:border-white/[0.14]
                          hover:bg-white/[0.04]
                          disabled:opacity-50
                        "
                      >
                        <p className="text-xs font-medium text-neutral-300">
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
                                    border-white/[0.08]
                                    bg-white/[0.07]
                                    px-4
                                    py-3
                                    shadow-sm
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
                                    flex
                                    h-8
                                    w-8
                                    shrink-0
                                    items-center
                                    justify-center
                                    rounded-xl
                                    border
                                    border-white/[0.08]
                                    bg-white/[0.04]
                                  "
                              >
                                <span className="text-[10px] font-semibold text-neutral-300">
                                  AI
                                </span>
                              </div>

                              {/* Assistant Content */}
                              <div className="min-w-0 flex-1">
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
                                    <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-neutral-500" />

                                    <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-neutral-500 [animation-delay:150ms]" />

                                    <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-neutral-500 [animation-delay:300ms]" />

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
                                                  rounded-xl
                                                  border
                                                  border-white/[0.06]
                                                  bg-white/[0.02]
                                                  px-4
                                                  py-3
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
                                                    "
                                                >
                                                  <FiFileText className="text-xs text-neutral-500" />
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
                <div className="mt-8 rounded-xl border border-red-500/10 bg-red-500/[0.04] px-4 py-3 text-xs text-red-400">
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
            <div className="pointer-events-none absolute inset-x-0 bottom-0 h-48 bg-gradient-to-t from-[#0d0d0d] via-[#0d0d0d]/95 to-transparent" />

            <div className="relative mx-auto w-full max-w-3xl px-4 pb-5 sm:px-6">
              {/* Composer */}
              <div className="pointer-events-auto rounded-2xl border border-white/[0.09] bg-[#151515]/95 p-2 shadow-2xl backdrop-blur-xl">
                <textarea
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask anything about your documents..."
                  rows={1}
                  disabled={loading}
                  className="
                    max-h-40
                    min-h-[52px]
                    w-full
                    resize-none
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
                      flex
                      h-9
                      w-9
                      items-center
                      justify-center
                      rounded-xl
                      bg-white
                      text-black
                      transition
                      hover:bg-neutral-200
                      disabled:cursor-not-allowed
                      disabled:bg-white/[0.08]
                      disabled:text-neutral-600
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
          bg-[#151515]
          text-neutral-300
          shadow-xl
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
