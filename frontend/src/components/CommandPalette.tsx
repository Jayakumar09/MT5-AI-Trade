/**
 * Command palette — Ctrl/Cmd+K. Fuzzy-ish filter over desk actions.
 */

import { useEffect, useMemo, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useAppStore, type ViewTab } from '../store/useAppStore';
import { apiPost } from '../api/client';
import { openSocial } from '../config/social';

interface Command {
  id: string;
  title: string;
  hint: string;
  run: () => void;
}

export default function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const setActiveTab = useAppStore((s) => s.setActiveTab);
  const toggleSound = useAppStore((s) => s.toggleSound);
  const toggleProMode = useAppStore((s) => s.toggleProMode);
  const [query, setQuery] = useState('');
  const [index, setIndex] = useState(0);

  const commands = useMemo<Command[]>(() => {
    const go = (tab: ViewTab) => () => { setActiveTab(tab); onClose(); };
    return [
      { id: 'constellation', title: 'Go to Constellation', hint: 'view', run: go('CONSTELLATION') },
      { id: 'chart', title: 'Go to Chart', hint: 'view', run: go('CHART') },
      { id: 'signals', title: 'Go to Signals', hint: 'view', run: go('SIGNALS') },
      { id: 'backtest', title: 'Go to Backtest Lab', hint: 'view', run: go('BACKTEST') },
      { id: 'journal', title: 'Go to Journal', hint: 'view', run: go('JOURNAL') },
      { id: 'settings', title: 'Go to Settings & Guardrails', hint: 'view', run: go('SETTINGS') },
      { id: 'demo-scenario', title: 'Run Demo Scenario (perfect sweep)', hint: 'action', run: () => { void apiPost('/api/run-demo-scenario', { symbol: 'XAUUSD' }); onClose(); } },
      { id: 'cycle', title: 'Run Orchestrator Cycle now', hint: 'action', run: () => { void apiPost('/api/run-cycle', { instrument: 'XAUUSD' }); onClose(); } },
      { id: 'kill', title: 'KILL SWITCH — halt new orders + close positions', hint: 'danger', run: () => { void apiPost('/api/kill-switch', { close_positions: true }); onClose(); } },
      { id: 'sound', title: 'Toggle sound', hint: 'toggle', run: () => { toggleSound(); onClose(); } },
      { id: 'pro', title: 'Toggle Beginner / Pro mode', hint: 'toggle', run: () => { toggleProMode(); onClose(); } },
      { id: 'youtube', title: 'Subscribe on YouTube', hint: 'social', run: () => { openSocial('youtube'); onClose(); } },
      { id: 'instagram', title: 'Follow on Instagram', hint: 'social', run: () => { openSocial('instagram'); onClose(); } },
    ];
  }, [setActiveTab, onClose, toggleSound, toggleProMode]);

  const filtered = useMemo(
    () => commands.filter((c) => c.title.toLowerCase().includes(query.toLowerCase())),
    [commands, query],
  );

  useEffect(() => { setIndex(0); }, [query, open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowDown') { e.preventDefault(); setIndex((i) => Math.min(i + 1, filtered.length - 1)); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); setIndex((i) => Math.max(i - 1, 0)); }
      else if (e.key === 'Enter') { e.preventDefault(); filtered[index]?.run(); }
      else if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, filtered, index, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div className="fixed inset-0 z-[90] bg-black/60 backdrop-blur-sm" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} />
          <motion.div
            initial={{ opacity: 0, y: -18, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -12, scale: 0.97 }}
            transition={{ type: 'spring', stiffness: 380, damping: 30 }}
            className="fixed left-1/2 top-28 z-[95] w-[min(560px,92vw)] -translate-x-1/2 overflow-hidden rounded-2xl border border-white/10 bg-[#0a0f22]/95 shadow-[0_30px_80px_rgba(0,0,0,0.7)] backdrop-blur-2xl"
          >
            <div className="flex items-center gap-3 border-b border-white/10 px-4 py-3">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#22D3EE" strokeWidth="2"><circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" /></svg>
              <input
                autoFocus
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Type a command… (e.g. 'backtest', 'kill', 'demo')"
                className="w-full bg-transparent font-mono text-sm text-cyan-100 placeholder-slate-600 outline-none"
              />
              <kbd className="rounded border border-white/10 bg-white/5 px-1.5 py-0.5 text-[10px] text-slate-500">ESC</kbd>
            </div>
            <ul className="max-h-80 overflow-y-auto p-2">
              {filtered.map((c, i) => (
                <li key={c.id}>
                  <button
                    data-cursor="Run"
                    onMouseEnter={() => setIndex(i)}
                    onClick={() => c.run()}
                    className={`flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm transition ${
                      i === index ? 'bg-cyan-400/10 text-cyan-200' : 'text-slate-300'
                    }`}
                  >
                    <span>{c.title}</span>
                    <span className={`font-mono text-[9px] uppercase tracking-widest ${c.hint === 'danger' ? 'text-rose-400' : 'text-slate-600'}`}>{c.hint}</span>
                  </button>
                </li>
              ))}
              {filtered.length === 0 && <li className="px-3 py-4 text-center text-xs text-slate-600">No commands match “{query}”.</li>}
            </ul>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}