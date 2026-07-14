import { create } from 'zustand';
import { FILE_STATUS } from '../constants/config';

/**
 * @typedef {Object} FileEntry
 * @property {string} id - UUID
 * @property {File} file - Raw File object
 * @property {string} name - Filename
 * @property {number} size - File size in bytes
 * @property {'pdf'|'image'} fileType - Detected type
 * @property {string} status - One of FILE_STATUS values
 * @property {number} progress - Upload progress 0–100
 * @property {Object|null} result - ExtractionResponse from backend
 * @property {Object|null} analysis - AnalysisResponse from backend
 * @property {{code:string, message:string}|null} error - Normalized error
 */

const useFileStore = create((set, get) => ({
  // ── State ──────────────────────────────────────────────────────────────────
  files: [],           // FileEntry[]
  activeFileId: null,  // string | null — selected result tab

  // Backend pre-warm status
  prewarmStatus: 'idle', // 'idle' | 'pinging' | 'ready' | 'failed'

  // ── File queue actions ─────────────────────────────────────────────────────

  /** Add new FileEntry objects to the queue */
  addFiles: (newEntries) =>
    set((state) => ({
      files: [...state.files, ...newEntries],
      // Auto-select first newly added file if nothing is selected
      activeFileId: state.activeFileId ?? newEntries[0]?.id ?? null,
    })),

  /** Partially update a FileEntry by id */
  updateFile: (id, updates) =>
    set((state) => ({
      files: state.files.map((f) => (f.id === id ? { ...f, ...updates } : f)),
    })),

  /** Remove a file from the queue entirely */
  removeFile: (id) =>
    set((state) => {
      const remaining = state.files.filter((f) => f.id !== id);
      const newActive =
        state.activeFileId === id
          ? (remaining.find((f) => f.status === FILE_STATUS.DONE)?.id ?? remaining[0]?.id ?? null)
          : state.activeFileId;
      return { files: remaining, activeFileId: newActive };
    }),

  /** Clear all files (start fresh) */
  clearAll: () => set({ files: [], activeFileId: null }),

  /** Set the active (selected) file tab */
  setActiveFileId: (id) => set({ activeFileId: id }),

  // ── Pre-warm status ────────────────────────────────────────────────────────
  setPrewarmStatus: (status) => set({ prewarmStatus: status }),

  // ── Derived selectors (computed on read, no extra re-renders) ──────────────
  getFile: (id) => get().files.find((f) => f.id === id),
  getDoneFiles: () => get().files.filter((f) => f.status === FILE_STATUS.DONE),
  getActiveFile: () => {
    const { files, activeFileId } = get();
    return files.find((f) => f.id === activeFileId) ?? null;
  },
}));

export default useFileStore;
