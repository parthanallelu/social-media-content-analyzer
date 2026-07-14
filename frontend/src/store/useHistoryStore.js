import { create } from 'zustand';
import { persist } from 'zustand/middleware';

const useHistoryStore = create(
  persist(
    (set) => ({
      history: [], // Array of { id, filename, timestamp, summary: { sentiment, wordCount } }
      isModalOpen: false,

      addEntry: (entry) =>
        set((state) => ({
          history: [entry, ...state.history],
        })),

      updateEntry: (id, summary) =>
        set((state) => ({
          history: state.history.map((entry) =>
            entry.id === id ? { ...entry, summary: { ...entry.summary, ...summary } } : entry
          ),
        })),

      clearHistory: () => set({ history: [] }),
      
      setModalOpen: (isOpen) => set({ isModalOpen: isOpen }),
    }),
    {
      name: 'upload-history',
      partialize: (state) => ({ history: state.history }), // only persist history
    }
  )
);

export default useHistoryStore;
