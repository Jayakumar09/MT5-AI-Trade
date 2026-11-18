/**
 * AgentPanel — clicking an orb in the constellation opens this panel with the
 * agent's live reasoning, inputs, outputs, and latency.
 */

import { AnimatePresence, motion } from 'framer-motion';
import { useAppStore, type AgentName } from '../store/useAppStore';

const AGENT_META: Record<AgentName, { role: string; color: string; desc: string }> = {
  SCOUT: { role: 'Data · MT5 / Demo', color: '#22D3EE', desc: 'Pulls OHLCV (5M/15M/4H/1D), spread, and account info. Falls back to synthetic Demo candles when no broker is connected.' },
  CARTOGRAPHER: { role: 'Liquidity Mapper', color: '#38BDF8', desc: 'PDH/PDL, session ranges (Asian/London/New York), swing highs/lows, equal-high/low clusters — deterministic Python.' },
  HUNTER: { role: 'Sweep Detector', color: '#34D399', desc: 'Rule-based stop-hunt reversal detector: wick pierces a known liquidity level, displacement candle closes back inside.' },
  ANALYST: { role: 'Claude · LLM', color: '#8B5CF6', desc: 'Receives the Hunter candidate + compact context. Returns strict JSON (bias, confidence 1–10, trade plan). May only refine or reject — never invent prices.' },
  GUARDIAN: { role: 'AEGIS · Risk Guardian', color: '#FBBF24', desc: 'Hard-coded vetoes: spread 35 pts (XAU), 1% risk (max 2%), 4% daily DD kill, max trades, min RR 1:2, min confidence 7, cooldown, session filter.' },
  EXECUTIONER: { role: 'Order Bridge · MT5 / Paper', color: '#FB7185', desc: 'Places market orders via MT5 (demo or live) or the paper engine. BE at 1R, partial close 50% at TP1, trails to TP2. Idempotent by signal_id.' },
  CHRONICLER: { role: 'Journal · SQLite', color: '#A78BFA', desc: 'Logs every decision (taken, vetoed, skipped) with the full agent trace; writes the AI end-of-day review.' },
};

export default function AgentPanel() {
  const activeAgent = useAppStore((s) => s.activeAgent);
  const setActiveAgent = useAppStore((s) => s.setActiveAgent);
  const agents = useAppStore((s) => s.agents);
  const proMode = useAppStore((s) => s.proMode);

  const state = activeAgent ? agents[activeAgent] : null;
  const meta = activeAgent ? AGENT_META[activeAgent] : null;

  return (
    <AnimatePresence>
      {activeAgent && state && meta && (
        <motion.aside
          key={activeAgent}
          initial={{ opacity: 0, x: -40 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -40 }}
          transition={{ type: 'spring', stiffness: 260, damping: 28 }}
          className="glass absolute left-3 top-14 z-30 w-[min(380px,92vw)] p-4"
        >
          <div className="flex items-start justify-between">
            <div>
              <div className="font-mono text-[10px] uppercase tracking-[0.3em]" style={{ color: meta.color }}>{meta.role}</div>
              <h3 className="gradient-text font-display text-2xl font-bold">{activeAgent}</h3>
            </div>
            <button data-cursor="Close" onClick={() => setActiveAgent(null)} className="rounded-md p-1.5 text-slate-500 hover:bg-white/5 hover:text-slate-200" aria-label="Close panel">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M6 6l12 12M18 6L6 18" /></svg>
            </button>
          </div>

          <p className="mt-2 text-[11px] leading-relaxed text-slate-400">{meta.desc}</p>

          <div className="mt-3 flex items-center gap-3 font-mono text-[10px] text-slate-500">
            <span className="rounded border border-white/10 bg-white/5 px-2 py-0.5">status: <span className="text-cyan-300">{state.status}</span></span>
            <span className="rounded border border-white/10 bg-white/5 px-2 py-0.5">latency: <span className="text-emerald-300">{state.latencyMs} ms</span></span>
            <span className="rounded border border-white/10 bg-white/5 px-2 py-0.5">conf: <span className="text-violet-300">{Math.round(state.confidence * 100)}%</span></span>
          </div>

          <div className="mt-3">
            <div className="font-mono text-[9px] uppercase tracking-[0.3em] text-slate-600">Latest summary</div>
            <p className="mt-1 rounded-lg border border-cyan-400/15 bg-cyan-950/20 p-2 font-mono text-[11px] leading-snug text-cyan-100">{state.summary}</p>
          </div>

          {proMode && state.data && (
            <div className="mt-3 max-h-44 overflow-auto rounded-lg border border-white/10 bg-black/50 p-2">
              <div className="font-mono text-[9px] uppercase tracking-[0.3em] text-slate-600">Raw payload</div>
              <pre className="mt-1 whitespace-pre-wrap break-all font-mono text-[9px] leading-snug text-slate-400">
                {JSON.stringify(state.data, null, 1).slice(0, 1600)}
              </pre>
            </div>
          )}
        </motion.aside>
      )}
    </AnimatePresence>
  );
}