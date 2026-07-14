import { useCallback, useRef } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { uploadPdf, uploadImage } from '../services/api';
import useFileStore from '../store/fileStore';
import { validateFile, getFileType } from '../utils/fileValidation';
import { FILE_STATUS, MAX_CONCURRENT_UPLOADS } from '../constants/config';
import useHistoryStore from '../store/useHistoryStore';

/**
 * useFileUpload — orchestrates multi-file upload with a concurrency limit of 3.
 *
 * Responsibilities:
 *  1. Validate each file client-side (no wasted API calls)
 *  2. Add all files to the Zustand store immediately (IDLE or ERROR)
 *  3. Process up to MAX_CONCURRENT_UPLOADS files simultaneously
 *  4. Track per-file upload progress and status transitions
 */
export function useFileUpload() {
  const { addFiles, updateFile } = useFileStore();
  // Semaphore: tracks current active upload count
  const activeCount = useRef(0);
  // Queue of { id, file, fileType } pending processing
  const queue = useRef([]);

  /**
   * Enqueue new files dropped/picked by the user.
   * @param {File[]} files
   */
  const enqueueFiles = useCallback((files) => {
    const entries = [];
    const toQueue = [];

    for (const file of files) {
      const id = uuidv4();
      const { valid, error } = validateFile(file);
      const fileType = getFileType(file);

      const entry = {
        id,
        file,
        name: file.name,
        size: file.size,
        fileType,
        status: valid ? FILE_STATUS.IDLE : FILE_STATUS.ERROR,
        progress: 0,
        result: null,
        analysis: null,
        error: valid ? null : error,
      };

      entries.push(entry);
      if (valid) toQueue.push({ id, file, fileType });
    }

    addFiles(entries);

    // Push valid files into the processing queue
    queue.current.push(...toQueue);
    _drain();
  }, [addFiles]);

  /** Drain the queue up to MAX_CONCURRENT_UPLOADS active slots. */
  function _drain() {
    while (activeCount.current < MAX_CONCURRENT_UPLOADS && queue.current.length > 0) {
      const item = queue.current.shift();
      activeCount.current++;
      _processFile(item).finally(() => {
        activeCount.current--;
        _drain(); // check if more can be started
      });
    }
  }

  /** Process a single file through upload → extraction → done/error. */
  async function _processFile({ id, file, fileType }) {
    // --- UPLOADING ---
    updateFile(id, { status: FILE_STATUS.UPLOADING, progress: 0 });

    const onProgress = (percent) => {
      updateFile(id, { progress: percent });
      // Transition to EXTRACTING once bytes are fully sent (progress = 100)
      if (percent === 100) {
        updateFile(id, { status: FILE_STATUS.EXTRACTING });
      }
    };

    try {
      const uploadFn = fileType === 'pdf' ? uploadPdf : uploadImage;
      const result = await uploadFn(file, onProgress);

      // --- DONE ---
      updateFile(id, {
        status: FILE_STATUS.DONE,
        progress: 100,
        result,
        error: null,
      });

      // Add to history
      useHistoryStore.getState().addEntry({
        id,
        filename: file.name,
        timestamp: new Date().toISOString(),
        summary: {
          wordCount: result.metadata?.character_count ? Math.round(result.metadata.character_count / 5) : null,
        }
      });

      // Auto-select this file in results panel
      useFileStore.getState().setActiveFileId(id);
    } catch (error) {
      // error is already a normalized AppError from the Axios interceptor
      updateFile(id, {
        status: FILE_STATUS.ERROR,
        error: error,
      });
    }
  }

  return { enqueueFiles };
}
