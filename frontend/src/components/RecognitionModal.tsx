import { AnimatePresence, motion } from 'framer-motion';
import { CSSProperties, useCallback, useEffect, useRef, useState } from 'react';
import { api, RecognizeResponse } from '../services/api';
import { useGameStore } from '../store/useGameStore';

interface RecognitionModalProps {
  open: boolean;
  onClose: () => void;
  file: File | null;
}

type Stage = 'preview' | 'analyzing' | 'success' | 'error';

export default function RecognitionModal({ open, onClose, file }: RecognitionModalProps) {
  const [stage, setStage] = useState<Stage>('preview');
  const [preview, setPreview] = useState<string | null>(null);
  const [result, setResult] = useState<RecognizeResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState('');
  const loadFromRecognition = useGameStore((s) => s.loadFromRecognition);
  const abortRef = useRef(false);

  // Generate preview when file changes
  useEffect(() => {
    if (!file) { setPreview(null); return; }
    const url = URL.createObjectURL(file);
    setPreview(url);
    setStage('preview');
    setResult(null);
    setErrorMsg('');
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const handleAnalyze = useCallback(async () => {
    if (!file) return;
    abortRef.current = false;
    setStage('analyzing');

    try {
      const res = await api.recognizeBoard(file);
      if (abortRef.current) return;

      if (!res.fen || res.confidence === 0) {
        setStage('error');
        setErrorMsg(res.description || '未能识别棋盘');
        return;
      }
      setResult(res);
      setStage('success');
    } catch (e: any) {
      if (abortRef.current) return;
      setStage('error');
      setErrorMsg(e?.response?.data?.detail || e?.message || '识别请求失败');
    }
  }, [file]);

  const handleApply = useCallback(() => {
    if (!result) return;
    loadFromRecognition(result.board, result.fen);
    onClose();
  }, [result, loadFromRecognition, onClose]);

  const handleClose = useCallback(() => {
    abortRef.current = true;
    onClose();
  }, [onClose]);

  // Auto-analyze on open
  useEffect(() => {
    if (open && file && stage === 'preview') {
      // Small delay for the preview image to render first
      const t = setTimeout(handleAnalyze, 400);
      return () => clearTimeout(t);
    }
  }, [open, file, stage, handleAnalyze]);

  if (!open) return null;

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          key="recognition-backdrop"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
          style={styles.backdrop}
          onClick={handleClose}
        >
          <motion.div
            key="recognition-card"
            initial={{ opacity: 0, scale: 0.88, y: 32 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.92, y: 18 }}
            transition={{ duration: 0.36, ease: [0.16, 1, 0.3, 1] }}
            style={styles.card}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div style={styles.header}>
              <div style={styles.headerTitle}>棋盘识别</div>
              <button type="button" onClick={handleClose} style={styles.closeBtn}>✕</button>
            </div>

            {/* Image area: YOLO annotated (success) or original preview */}
            {(preview || (stage === 'success' && result?.annotated_image)) && (
              <div style={styles.imageWrap}>
                <motion.img
                  key={stage === 'success' && result?.annotated_image ? 'annotated' : 'preview'}
                  src={
                    stage === 'success' && result?.annotated_image
                      ? `data:image/webp;base64,${result.annotated_image}`
                      : preview ?? ''
                  }
                  alt={stage === 'success' ? 'YOLO 识别结果' : '棋盘预览'}
                  style={styles.previewImg}
                  initial={{ opacity: 0, scale: 0.98 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
                />

                {/* Scanning overlay during analysis */}
                <AnimatePresence>
                  {stage === 'analyzing' && (
                    <motion.div
                      key="scan-overlay"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      style={styles.scanOverlay}
                    >
                      <motion.div
                        style={styles.scanLine}
                        animate={{ top: ['0%', '100%', '0%'] }}
                        transition={{ duration: 2.4, repeat: Infinity, ease: 'easeInOut' }}
                      />
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )}

            {/* Status / Result Area */}
            <div style={styles.body}>
              <AnimatePresence mode="wait">
                {stage === 'analyzing' && (
                  <motion.div
                    key="analyzing"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -6 }}
                    style={styles.statusRow}
                  >
                    <div style={styles.spinner} />
                    <span style={styles.statusText}>AI 正在识别棋盘...</span>
                  </motion.div>
                )}

                {stage === 'success' && result && (
                  <motion.div
                    key="success"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -6 }}
                    style={styles.resultArea}
                  >
                    <div style={styles.resultHeader}>
                      <span style={styles.successDot} />
                      <span style={styles.resultLabel}>
                        识别成功 · {result.pieces_detected} 枚棋子
                      </span>
                      <span style={styles.confidenceBadge}>
                        {Math.round(result.confidence * 100)}%
                      </span>
                    </div>
                    {result.description && (
                      <div style={styles.description}>{result.description}</div>
                    )}
                  </motion.div>
                )}

                {stage === 'error' && (
                  <motion.div
                    key="error"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -6 }}
                    style={styles.resultArea}
                  >
                    <div style={styles.resultHeader}>
                      <span style={styles.errorDot} />
                      <span style={styles.resultLabel}>识别失败</span>
                    </div>
                    <div style={styles.errorText}>{errorMsg}</div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Action Buttons */}
            <div style={styles.footer}>
              {stage === 'success' && (
                <motion.button
                  type="button"
                  onClick={handleApply}
                  style={styles.applyBtn}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.97 }}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ type: 'spring', stiffness: 400, damping: 24 }}
                >
                  应用到棋盘
                </motion.button>
              )}
              {stage === 'error' && (
                <motion.button
                  type="button"
                  onClick={handleAnalyze}
                  style={styles.retryBtn}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.97 }}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                >
                  重新识别
                </motion.button>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

/* ── Apple-quality glassmorphism styles ── */

const styles: Record<string, CSSProperties> = {
  backdrop: {
    position: 'fixed',
    inset: 0,
    zIndex: 1000,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'rgba(0, 0, 0, 0.55)',
    backdropFilter: 'blur(20px) saturate(140%)',
    WebkitBackdropFilter: 'blur(20px) saturate(140%)',
  },
  card: {
    width: 380,
    maxWidth: 'calc(100vw - 40px)',
    borderRadius: 28,
    background: 'linear-gradient(170deg, rgba(38,42,56,0.88) 0%, rgba(22,24,34,0.92) 100%)',
    border: '1px solid rgba(255,255,255,0.14)',
    boxShadow:
      '0 32px 80px rgba(0,0,0,0.55), 0 0 0 0.5px rgba(255,255,255,0.08) inset, 0 1px 0 rgba(255,255,255,0.12) inset',
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '18px 22px 12px',
  },
  headerTitle: {
    fontSize: 17,
    fontWeight: 600,
    color: 'rgba(244, 241, 222, 0.96)',
    letterSpacing: '-0.01em',
  },
  closeBtn: {
    width: 28,
    height: 28,
    borderRadius: 14,
    border: 'none',
    background: 'rgba(255,255,255,0.08)',
    color: 'rgba(244, 241, 222, 0.55)',
    fontSize: 13,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'background 0.2s',
  },
  imageWrap: {
    position: 'relative',
    margin: '0 18px',
    borderRadius: 18,
    overflow: 'hidden',
    background: 'rgba(0,0,0,0.25)',
    aspectRatio: '1 / 1',
  },
  previewImg: {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
    borderRadius: 18,
  },
  scanOverlay: {
    position: 'absolute',
    inset: 0,
    borderRadius: 18,
    overflow: 'hidden',
    background: 'rgba(72, 177, 255, 0.06)',
  },
  scanLine: {
    position: 'absolute',
    left: 0,
    right: 0,
    height: 2,
    background: 'linear-gradient(90deg, transparent, rgba(100, 210, 255, 0.7), transparent)',
    boxShadow: '0 0 18px 4px rgba(100, 210, 255, 0.35)',
  },
  body: {
    padding: '14px 22px 8px',
    minHeight: 52,
  },
  statusRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
  },
  spinner: {
    width: 18,
    height: 18,
    borderRadius: 9,
    border: '2px solid rgba(100, 210, 255, 0.25)',
    borderTopColor: 'rgba(100, 210, 255, 0.9)',
    animation: 'spin 0.8s linear infinite',
  },
  statusText: {
    fontSize: 13,
    color: 'rgba(180, 220, 255, 0.9)',
    fontWeight: 500,
  },
  resultArea: {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  },
  resultHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  },
  successDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    background: '#34d399',
    boxShadow: '0 0 8px rgba(52, 211, 153, 0.5)',
    flexShrink: 0,
  },
  errorDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    background: '#f87171',
    boxShadow: '0 0 8px rgba(248, 113, 113, 0.5)',
    flexShrink: 0,
  },
  resultLabel: {
    fontSize: 13,
    fontWeight: 600,
    color: 'rgba(244, 241, 222, 0.92)',
    flex: 1,
  },
  confidenceBadge: {
    fontSize: 11,
    fontWeight: 600,
    padding: '2px 8px',
    borderRadius: 8,
    background: 'rgba(52, 211, 153, 0.15)',
    color: 'rgba(52, 211, 153, 0.95)',
    border: '1px solid rgba(52, 211, 153, 0.25)',
  },
  description: {
    fontSize: 12,
    lineHeight: 1.6,
    color: 'rgba(244, 241, 222, 0.62)',
    maxHeight: 72,
    overflow: 'auto',
  },
  errorText: {
    fontSize: 12,
    lineHeight: 1.5,
    color: 'rgba(248, 113, 113, 0.85)',
  },
  footer: {
    padding: '8px 18px 18px',
    display: 'flex',
    gap: 10,
  },
  applyBtn: {
    flex: 1,
    height: 44,
    borderRadius: 14,
    border: 'none',
    background: 'linear-gradient(180deg, rgba(52, 211, 153, 0.24) 0%, rgba(16, 185, 129, 0.16) 100%)',
    borderWidth: 1,
    borderStyle: 'solid',
    borderColor: 'rgba(52, 211, 153, 0.40)',
    color: 'rgba(200, 255, 230, 0.96)',
    fontSize: 14,
    fontWeight: 600,
    cursor: 'pointer',
    letterSpacing: '0.01em',
    boxShadow: '0 8px 24px rgba(16, 185, 129, 0.18)',
  },
  retryBtn: {
    flex: 1,
    height: 44,
    borderRadius: 14,
    border: '1px solid rgba(255,255,255,0.18)',
    background: 'linear-gradient(180deg, rgba(255,255,255,0.10) 0%, rgba(255,255,255,0.04) 100%)',
    color: 'rgba(244, 241, 222, 0.9)',
    fontSize: 14,
    fontWeight: 600,
    cursor: 'pointer',
    letterSpacing: '0.01em',
  },
};
