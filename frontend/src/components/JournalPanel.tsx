/**
 * JournalPanel — timeline of every decision (taken / vetoed / skipped) with
 * expandable agent traces, plus the AI end-of-day review paragraph.
 */

import { useEffect, useState } from 'react';
import { apiGet } from '../api/client';
import { useAppStore } from '../store/useAppStore';

const OUTCOME_TONE: Record<string, string> = {
  TAKEN: 'text-emerald-300 border-emerald-400/40',
  VETOED: 'text-rose-300 border-rose-400/40',
  SKIPPED: 'text-slate-400 border-slate-600',
  NO_TRADE: 'text-slate-400 border-slate-600',
};

interface Decision {
  id: number;
  instrument: string;
  direction: string;
  entry_price: number;
  stop_loss: number;
  take_profit_1: number;
  risk_reward: number;
  confidence: number;
  outcome: string;
  reason: string;
  trace: Record<string, string>;
  created_at: string;
}

export default function JournalPanel() {
  const journalRefresh = useAppStore((s) => s.journalRefresh);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [review, setReview] = useState<{ summary: string; decisions: number; counts?: Record<string, number> }>({ summary: '', decisions: 0 });
  const [expanded, setExpanded] = useState<number | null>(null);

  useEffect(() => {
    apiGet('/api/journal?limit=40', { decisions: [] as Decision[] }).then((d) => setDecisions(d.decisions ?? []));
    apiGet('/api/eod-review', { summary: '', decisions: 0 }).then(setReview);
  }, [journalRefresh]);

  return (
    <section className="glass flex h-full flex-col overflow-hidden p-4">
      <div className="flex items-center justify-between">
        <h2 className="font-mono text-[10px] uppercase tracking-[0.3em] text-slate-500">Chronicler · Decision Journal</h2>
        <span className="rounded border border-white/10 bg-white/5 px-2 py-0.5 font-mono text-[9px] text-slate-500">{decisions.length} rows · SQLite</span>
      </div>

      {/* AI end-of-day review */}
      <div className="mt-3 rounded-lg border border-violet-400/20 bg-violet-950/20 p-3">
        <div className="font-mono text-[9px] uppercase tracking-[0.3em] text-violet-300">AI · End-of-day review</div>
        <p className="mt-1 text-[11px] leading-relaxed text-violet-100/90">{review.summary || 'Waiting for the first cycle of the day…'}</p>
        {review.counts && (
          <div className="mt-2 flex gap-2 font-mono text-[9px] text-slate-500">
            {Object.entries(review.counts).map(([k, v]) => (
              <span key={k} className="rounded border border-white/10 px-1.5 py-0.5">{k}: <span className="text-slate-300">{v}</span></span>
            ))}
          </div>
        )}
      </div>

      {/* timeline */}
      <div className="mt-3 min-h-0 flex-1 overflow-y-auto pr-1">
        {decisions.length === 0 && <p className="py-6 text-center text-xs text-slate-600">Journal is empty — decisions will appear here after each cycle.</p>}
        <ol className="relative border-l border-white/10 pl-4">
          {decisions.map((d) => (
            <li key={d.id} className="relative mb-3">
              <span className="absolute -left-[21px] top-1.5 h-2.5 w-2.5 rounded-full border border-cyan-400/50 bg-[#05060F]" />
              <button onClick={() => setExpanded(expanded === d.id ? null : d.id)} className="w-full text-left" data-cursor="Expand trace">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 font-mono text-[10px]">
                    <span className={`rounded border px-1.5 py-0.5 ${OUTCOME_TONE[d.outcome] ?? OUTCOME_TONE.SKIPPED}`}>{d.outcome}</span>
                    <span className="text-slate-400">{d.instrument}</span>
                    <span className="text-slate-500">{new Date(d.created_at).toLocaleTimeString('en-IN', { hour12: false })}</span>
                  </div>
                  <span className="font-mono text-[9px] text-slate-600">#{d.id}</span>
                </div>
                <div className="mt-0.5 font-mono text-[10px] text-slate-500">
                  {d.direction} @ {d.entry_price?.toFixed?.(2) ?? '—'} · RR {d.risk_reward?.toFixed?.(2) ?? '—'} · conf {d.confidence}
                </div>
                <div className="text-[9px] italic text-slate-600">{d.reason}</div>
              </button>
              {expanded === d.id && d.trace && (
                <div className="mt-1.5 grid gap-1 rounded-lg border border-white/5 bg-black/40 p-2">
                  {Object.entries(d.trace).map(([agent, line]) => (
                    <div key={agent} className="grid grid-cols-[86px_1fr] gap-2 text-[9px] leading-snug">
                      <span className="font-mono uppercase text-cyan-500/80">{agent}</span>
                      <span className="text-slate-400">{line ?? '—'}</span>
                    </div>
                  ))}
                </div>
              )}
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}