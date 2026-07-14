import { useCallback } from 'react';
import { analyzeContent } from '../services/api';
import useFileStore from '../store/fileStore';
import useHistoryStore from '../store/useHistoryStore';
import { FILE_STATUS } from '../constants/config';

/**
 * useAnalysis — triggers the optional /analyze endpoint for a specific file.
 *
 * Deliberately decoupled from the upload pipeline:
 * the user must manually click "Run Analysis" to trigger this.
 *
 * @param {string} fileId - The FileEntry id to analyze
 * @returns {{ runAnalysis: function(string): Promise<void> }}
 */
export function useAnalysis(fileId) {
  const { updateFile, getFile } = useFileStore();

  const runAnalysis = useCallback(async (platform = 'general') => {
    const entry = getFile(fileId);
    if (!entry?.result?.content?.blocks?.length) return;

    // Prevent double-click
    if (entry.status === FILE_STATUS.ANALYZING) return;

    updateFile(fileId, { status: FILE_STATUS.ANALYZING });

    try {
      const analysisResult = await analyzeContent(entry.result.content.blocks, platform);
      updateFile(fileId, {
        status: FILE_STATUS.DONE, // revert to DONE — analysis is non-fatal
        analysis: analysisResult,
      });

      useHistoryStore.getState().updateEntry(fileId, {
        sentiment: analysisResult.sentiment?.label,
      });
    } catch (error) {
      // Analysis failure is non-fatal: preserve extracted text, show error in analysis pane only
      updateFile(fileId, {
        status: FILE_STATUS.DONE,
        analysis: null,
        // Store analysis-specific error separately from extraction error
        analysisError: error,
      });
    }
  }, [fileId, updateFile, getFile]);

  return { runAnalysis };
}
