import { useEffect, useMemo, useState } from "react";

import {
  FiChevronRight,
  FiDatabase,
  FiFileText,
  FiFolder,
  FiHardDrive,
  FiRefreshCw,
  FiTrash2,
  FiX,
} from "react-icons/fi";

import api from "../services/api";
import Navbar from "../components/Navbar";

function Dashboard({ user, onChat }) {
  const [folders, setFolders] = useState([]);

  const [selectedFolder, setSelectedFolder] = useState(null);

  const [selectedFiles, setSelectedFiles] = useState([]);

  const [loading, setLoading] = useState(true);

  const [loadingFiles, setLoadingFiles] = useState(false);

  const [error, setError] = useState("");

  const [deletingFolderId, setDeletingFolderId] = useState(null);

  const [deletingFileId, setDeletingFileId] = useState(null);

  // ==================================================
  // LOAD FOLDERS
  // ==================================================

  async function loadFolders() {
    try {
      setLoading(true);
      setError("");

      const response = await api.get("/api/folders");

      setFolders(response.data?.folders || []);
    } catch (error) {
      setError(
        error.response?.data?.detail || "Failed to load analyzed folders.",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadFolders();
  }, []);

  // ==================================================
  // TOTALS
  // ==================================================

  const totalFiles = useMemo(
    () =>
      folders.reduce(
        (total, folder) => total + Number(folder.file_count || 0),
        0,
      ),
    [folders],
  );

  const totalChunks = useMemo(
    () =>
      folders.reduce(
        (total, folder) => total + Number(folder.chunk_count || 0),
        0,
      ),
    [folders],
  );

  const totalFolders = folders.length;

  // ==================================================
  // OPEN FOLDER
  // ==================================================

  async function openFolder(folder) {
    try {
      setLoadingFiles(true);
      setError("");

      const response = await api.get(`/api/folders/${folder.folder_id}`);

      setSelectedFolder(response.data?.folder || folder);

      setSelectedFiles(response.data?.files || []);
    } catch (error) {
      setError(error.response?.data?.detail || "Failed to load folder files.");
    } finally {
      setLoadingFiles(false);
    }
  }

  // ==================================================
  // DELETE FILE
  // ==================================================

  async function deleteFile(folderId, file) {
    const confirmed = window.confirm(
      `Remove "${file.file_name}" from Zentra?\n\nThis deletes its indexed chunks from the database but does not delete the file from Google Drive.`,
    );

    if (!confirmed) {
      return;
    }

    try {
      setDeletingFileId(file.file_id);

      setError("");

      await api.delete(`/api/folders/${folderId}/files/${file.file_id}`);

      await openFolder({
        folder_id: folderId,
      });

      await loadFolders();
    } catch (error) {
      setError(error.response?.data?.detail || "Failed to delete file.");
    } finally {
      setDeletingFileId(null);
    }
  }

  // ==================================================
  // DELETE FOLDER
  // ==================================================

  async function deleteFolder(folder) {
    const confirmed = window.confirm(
      `Remove "${folder.folder_name}" from Zentra?\n\nAll indexed files and document chunks belonging to this folder will be deleted from the database.\n\nThe original Google Drive files will NOT be deleted.`,
    );

    if (!confirmed) {
      return;
    }

    try {
      setDeletingFolderId(folder.folder_id);

      setError("");

      await api.delete(`/api/folders/${folder.folder_id}`);

      setFolders((previous) =>
        previous.filter((item) => item.folder_id !== folder.folder_id),
      );

      if (selectedFolder?.folder_id === folder.folder_id) {
        setSelectedFolder(null);
        setSelectedFiles([]);
      }
    } catch (error) {
      setError(error.response?.data?.detail || "Failed to delete folder.");
    } finally {
      setDeletingFolderId(null);
    }
  }

  // ==================================================
  // FORMAT DATE
  // ==================================================

  function formatDate(value) {
    if (!value) {
      return "Unknown";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
      return "Unknown";
    }

    return date.toLocaleDateString(undefined, {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#090909] text-white">
      {/* BACKGROUND */}

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

      <div className="pointer-events-none fixed left-1/2 top-[-400px] h-[700px] w-[700px] -translate-x-1/2 rounded-full bg-white/[0.025] blur-[130px]" />

      {/* NAVBAR */}

      <Navbar
        user={user}
        showDashboard={true}
        showChat={true}
        showSync={true}
        activeTab="dashboard"
        onDashboard={() => navigate("/dashboard")}
        onChat={() => navigate("/chat")}
        onSyncAnotherFolder={() => navigate("/analyze")}
      />

      <main className="relative mx-auto w-full max-w-6xl px-5 py-8 sm:px-6 lg:px-8">
        {/* ==================================================
            HEADER
        ================================================== */}

        <div className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-[10px] uppercase tracking-[0.22em] text-neutral-700">
              Zentra
            </p>

            <h1 className="mt-2 text-3xl font-semibold tracking-[-0.025em] text-neutral-100">
              Knowledge dashboard
            </h1>

            <p className="mt-2 max-w-xl text-sm leading-6 text-neutral-500">
              Manage the Google Drive folders and files currently indexed in
              your Zentra knowledge base.
            </p>
          </div>

          {/* SYNC BUTTON */}

          <button
            type="button"
            onClick={() => (window.location.href = "/analyze")}
            className="
              inline-flex
              h-10
              shrink-0
              items-center
              justify-center
              gap-2
              rounded-xl
              border
              border-white/[0.08]
              bg-white/[0.04]
              px-4
              text-xs
              font-medium
              text-neutral-300
              transition
              hover:border-white/[0.14]
              hover:bg-white/[0.07]
              hover:text-white
            "
          >
            <FiRefreshCw />
            Sync Another Folder
          </button>
        </div>

        {/* ERROR */}

        {error && (
          <div className="mt-6 rounded-xl border border-red-500/[0.15] bg-red-500/[0.04] px-4 py-3 text-xs text-red-400">
            {error}
          </div>
        )}

        {/* ==================================================
            STAT CARDS
        ================================================== */}

        <section className="mt-8 grid grid-cols-1 gap-3 sm:grid-cols-3">
          <StatCard
            icon={<FiFileText />}
            label="Total Files Analyzed"
            value={loading ? "—" : totalFiles}
          />

          <StatCard
            icon={<FiFolder />}
            label="Folders"
            value={loading ? "—" : totalFolders}
          />

          <StatCard
            icon={<FiDatabase />}
            label="Indexed Chunks"
            value={loading ? "—" : totalChunks}
          />
        </section>

        {/* ==================================================
            FOLDERS
        ================================================== */}

        <section className="mt-10">
          <div className="mb-4">
            <h2 className="text-sm font-medium text-neutral-200">
              Your analyzed folders
            </h2>

            <p className="mt-1 text-[11px] text-neutral-600">
              Every folder below belongs only to your Google account.
            </p>
          </div>

          {loading ? (
            <div className="rounded-2xl border border-white/[0.07] bg-white/[0.02] p-6 text-xs text-neutral-600">
              <FiRefreshCw className="mr-2 inline animate-spin" />
              Loading folders...
            </div>
          ) : folders.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-white/[0.08] bg-white/[0.018] px-6 py-14 text-center">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl border border-white/[0.07] bg-white/[0.025]">
                <FiHardDrive className="text-neutral-600" />
              </div>

              <p className="mt-4 text-sm text-neutral-400">
                No folders analyzed yet.
              </p>

              <p className="mt-1 text-xs text-neutral-600">
                Use "Sync Another Folder" to add your first folder.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
              {folders.map((folder) => (
                <div
                  key={folder.folder_id}
                  className="
                      group
                      rounded-2xl
                      border
                      border-white/[0.07]
                      bg-white/[0.02]
                      p-5
                      transition
                      hover:border-white/[0.12]
                      hover:bg-white/[0.03]
                    "
                >
                  <div className="flex items-start gap-4">
                    <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-white/[0.07] bg-white/[0.035]">
                      <FiFolder className="text-neutral-400" />
                    </div>

                    <div className="min-w-0 flex-1">
                      <h3 className="truncate text-sm font-medium text-neutral-200">
                        {folder.folder_name || "Google Drive Folder"}
                      </h3>

                      <p className="mt-1 truncate text-[10px] text-neutral-700">
                        {folder.folder_id}
                      </p>

                      <div className="mt-4 flex flex-wrap gap-x-4 gap-y-2 text-[11px] text-neutral-500">
                        <span>{Number(folder.file_count || 0)} files</span>

                        <span>{Number(folder.chunk_count || 0)} chunks</span>

                        <span>
                          Analyzed{" "}
                          {formatDate(folder.analyzed_at || folder.updated_at)}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* ACTIONS */}

                  <div className="mt-5 flex items-center justify-between border-t border-white/[0.05] pt-4">
                    <button
                      type="button"
                      onClick={() => openFolder(folder)}
                      disabled={loadingFiles}
                      className="
                          inline-flex
                          items-center
                          gap-2
                          rounded-lg
                          px-2
                          py-1.5
                          text-xs
                          text-neutral-500
                          transition
                          hover:bg-white/[0.05]
                          hover:text-white
                        "
                    >
                      View Files
                      <FiChevronRight />
                    </button>

                    <button
                      type="button"
                      onClick={() => deleteFolder(folder)}
                      disabled={deletingFolderId === folder.folder_id}
                      className="
                          flex
                          h-8
                          w-8
                          items-center
                          justify-center
                          rounded-lg
                          text-neutral-700
                          transition
                          hover:bg-red-500/[0.08]
                          hover:text-red-400
                          disabled:opacity-40
                        "
                      title="Delete folder from Zentra"
                    >
                      {deletingFolderId === folder.folder_id ? (
                        <FiRefreshCw className="animate-spin text-xs" />
                      ) : (
                        <FiTrash2 className="text-xs" />
                      )}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </main>

      {/* ==================================================
          FILE MODAL
      ================================================== */}

      {selectedFolder && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <button
            type="button"
            aria-label="Close"
            onClick={() => {
              setSelectedFolder(null);
              setSelectedFiles([]);
            }}
            className="absolute inset-0"
          />

          <div className="relative z-10 flex max-h-[85vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-white/[0.08] bg-[#101010] shadow-2xl">
            {/* HEADER */}

            <div className="flex items-center justify-between border-b border-white/[0.06] px-5 py-4">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <FiFolder className="shrink-0 text-xs text-neutral-500" />

                  <h2 className="truncate text-sm font-medium text-neutral-200">
                    {selectedFolder.folder_name}
                  </h2>
                </div>

                <p className="mt-1 text-[10px] text-neutral-600">
                  {selectedFiles.length} indexed files
                </p>
              </div>

              <button
                type="button"
                onClick={() => {
                  setSelectedFolder(null);
                  setSelectedFiles([]);
                }}
                className="flex h-8 w-8 items-center justify-center rounded-lg text-neutral-600 hover:bg-white/[0.06] hover:text-white"
              >
                <FiX />
              </button>
            </div>

            {/* FILE LIST */}

            <div className="min-h-0 flex-1 overflow-y-auto p-4">
              {loadingFiles ? (
                <div className="py-12 text-center text-xs text-neutral-600">
                  <FiRefreshCw className="mr-2 inline animate-spin" />
                  Loading files...
                </div>
              ) : selectedFiles.length === 0 ? (
                <div className="py-12 text-center text-xs text-neutral-600">
                  No indexed files.
                </div>
              ) : (
                <div className="space-y-2">
                  {selectedFiles.map((file) => (
                    <div
                      key={file.file_id}
                      className="flex items-center gap-3 rounded-xl border border-white/[0.05] bg-white/[0.018] px-3 py-3"
                    >
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-white/[0.05] bg-white/[0.025]">
                        <FiFileText className="text-xs text-neutral-500" />
                      </div>

                      <div className="min-w-0 flex-1">
                        <p className="truncate text-xs text-neutral-300">
                          {file.file_name}
                        </p>

                        <p className="mt-1 truncate text-[10px] text-neutral-700">
                          {file.path || file.mime_type || "Indexed file"}
                        </p>

                        <div className="mt-1 flex gap-3 text-[10px] text-neutral-600">
                          <span>{Number(file.chunk_count || 0)} chunks</span>

                          {file.modified_time && (
                            <span>
                              Modified {formatDate(file.modified_time)}
                            </span>
                          )}
                        </div>
                      </div>

                      <button
                        type="button"
                        onClick={() =>
                          deleteFile(selectedFolder.folder_id, file)
                        }
                        disabled={deletingFileId === file.file_id}
                        className="
                            flex
                            h-8
                            w-8
                            shrink-0
                            items-center
                            justify-center
                            rounded-lg
                            text-neutral-700
                            hover:bg-red-500/[0.08]
                            hover:text-red-400
                            disabled:opacity-40
                          "
                      >
                        {deletingFileId === file.file_id ? (
                          <FiRefreshCw className="animate-spin text-xs" />
                        ) : (
                          <FiTrash2 className="text-xs" />
                        )}
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ==================================================
// STAT CARD
// ==================================================

function StatCard({ icon, label, value }) {
  return (
    <div className="rounded-2xl border border-white/[0.07] bg-white/[0.025] p-5">
      <div className="flex items-center justify-between">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/[0.07] bg-white/[0.035]">
          {icon}
        </div>

        <span className="text-[10px] uppercase tracking-[0.16em] text-neutral-700">
          Indexed
        </span>
      </div>

      <p className="mt-6 text-3xl font-semibold tracking-tight text-neutral-100">
        {value}
      </p>

      <p className="mt-1 text-xs text-neutral-500">{label}</p>
    </div>
  );
}

export default Dashboard;
