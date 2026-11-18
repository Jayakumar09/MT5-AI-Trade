import { AnimatePresence, motion } from 'framer-motion';
import { useAppStore } from '../store/useAppStore';

const TONE_RING: Record<string, string> = {
  cyan: 'border-cyan-400/40 shadow-neon',
  rose: 'border-rose-400/40 shadow-rose',
  emerald: 'border-emerald-400/40 shadow-emerald',
  amber: 'border-amber-400/40',
  violet: 'border-violet-400/40 shadow-violet',
};
const TONE_TEXT: Record<string, string> = {
  cyan: 'text-cyan-300',
  rose: 'text-rose-300',
  emerald: 'text-emerald-300',
  amber: 'text-amber-300',
  violet: 'text-violet-300',
};

export default function Toasts() {
  const toasts = useAppStore((s) => s.toasts);
  const dismiss = useAppStore((s) => s.dismissToast);
  return (
    <div className="pointer-events-none fixed right-4 top-16 z-[100] flex w-80 flex-col gap-2">
      <AnimatePresence>
        {toasts.map((t) => (
          <motion.button
            key={t.id}
            layout
            initial={{ x: 120, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 120, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 320, damping: 28 }}
            onClick={() => dismiss(t.id)}
            className={`pointer-events-auto glass border ${TONE_RING[t.tone]} p-3 text-left`}
          >
            <div className={`font-mono text-[10px] uppercase tracking-[0.22em] ${TONE_TEXT[t.tone]}`}>{t.title}</div>
            {t.body && <div className="mt-1 text-xs leading-snug text-slate-200">{t.body}</div>}
          </motion.button>
        ))}
      </AnimatePresence>
    </div>
  );
}