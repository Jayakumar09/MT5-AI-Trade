/**
 * Signals view — the latest candidate with the Analyst's reasoning,
 * the Guardian's verdict, and the Executioner's result.
 */

import { useAppStore } from '../store/useAppStore';
import { apiPost } from '../api/client';

const VERDICT_STYLE: Record<string, string> = {
  OK: 'border-emerald-400/40 text-emerald-300',
  CANDIDATE: 'border-cyan-400/40 text-cyan-300',
  APPROVED: 'border-emerald-400/50 text-emerald-300',
  EXECUTED: 'border-emerald-400/50 text-emerald-300',
  VETOED: 'border-rose-400/50 text-rose-300',
  NO_TRADE: 'border-slate-600 text-slate-400',
  SKIPPED: 'border-slate-600 text-slate-400',
  REJECTED: 'border-rose-400/50 text-rose-300',
  ERROR: 'border-rose-500/60 text-rose-300',
};

function Row({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div className="flex items-center justify-between border-b border-white/5 py-1.5 last:border-0">
      <span className="font-mono text-[9px] uppercase tracking-[0.2em] text-slate-500">{label}</span>
      <span className={`font-mono text-[11px] ${tone ?? 'text-slate-200'}`}>{value}</span>
    </div>
  );
}

export default function SignalCard() {
  const agents = useAppStore((s) => s.agents);
  const hunter = agents.HUNTER;
  const analyst = agents.ANALYST;
  const guardian = agents.GUARDIAN;
  const executioner = agents.EXECUTIONER;
  const candidate = (hunter.data?.candidate as any) ?? null;
  const tradePlan = (analyst.data?.trade_plan as any) ?? null;
  const verdict = guardian.status;
  const fx = (n?: number) => (n == null ? '—' : Number(n).toFixed(2));

  return (
    <section className="glass flex h-full flex-col overflow-y-auto p-4">
      <div className="flex items-center justify-between">
        <h2 className="font-mono text-[10px] uppercase tracking-[0.3em] text-slate-500">Signal Pipeline</h2>
        <button data-cursor="Run cycle" onClick={() => apiPost('/api/run-cycle', { instrument: 'XAUUSD' })} className="rounded-md border border-cyan-400/40 bg-cyan-500/10 px-2.5 py-1 font-mono text-[9px] uppercase tracking-widest text-cyan-300 hover:bg-cyan-500/20">
          Run cycle
        </button>
      </div>

      {!candidate ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-3 py-10 text-center">
          <div className="shimmer h-14 w-40 rounded-lg border border-white/10" />
          <p className="text-xs text-slate-500">No candidate on the board — Hunter is scanning for sweeps.<br />Load Demo mode and watch the sweep form.</p>
        </div>
      ) : (
        <>
          {/* instrument + direction */}
          <div className="mt-3 flex items-center justify-between rounded-xl border border-cyan-400/20 bg-gradient-to-br from-cyan-950/40 to-violet-950/30 p-3">
            <div>
              <div className="font-mono text-[9px] uppercase tracking-[0.3em] text-slate-500">{candidate.instrument}</div>
              <div className={`font-display text-2xl font-bold ${candidate.direction === 'LONG' ? 'text-emerald-300' : 'text-rose-300'}`}>
                {candidate.direction === 'LONG' ? '▲ LONG' : '▼ SHORT'}
              </div>
            </div>
            <div className="text-right">
              <div className="font-mono text-[9px] uppercase tracking-[0.3em] text-slate-500">RR</div>
              <div className="font-mono text-xl font-bold text-amber-300">1:{fx(candidate.risk_reward_ratio)}</div>
            </div>
          </div>

          {/* trade plan */}
          <div className="mt-3">
            <div className="font-mono text-[9px] uppercase tracking-[0.3em] text-slate-600">Trade plan</div>
            <div className="mt-1">
              <Row label="Entry" value={fx(tradePlan?.entry_price ?? candidate.entry_price)} tone="text-cyan-300" />
              <Row label="Stop loss" value={fx(tradePlan?.stop_loss ?? candidate.stop_loss)} tone="text-rose-300" />
              <Row label="TP1 · opposite boundary" value={fx(tradePlan?.take_profit_1 ?? candidate.take_profit_1)} tone="text-emerald-300" />
              <Row label="TP2 · next pool" value={fx(tradePlan?.take_profit_2 ?? candidate.take_profit_2)} tone="text-emerald-300" />
              <Row label="Level targeted" value={String(candidate.htf_level_targeted ?? '—')} />
            </div>
          </div>

          {/* analyst verdict */}
          <div className="mt-3 rounded-lg border border-violet-400/15 bg-violet-950/15 p-2.5">
            <div className="font-mono text-[9px] uppercase tracking-[0.3em] text-violet-300">Analyst (Claude) reasoning</div>
            <p className="mt-1 text-[11px] leading-relaxed text-violet-100/90">{analyst.summary}</p>
          </div>

          {/* guardian verdict */}
          <div className={`mt-2 rounded-lg border p-2.5 ${VERDICT_STYLE[verdict]} bg-black/40`}>
            <div className="font-mono text-[9px] uppercase tracking-[0.3em] opacity-80">AEGIS Guardian verdict</div>
            <p className="mt-1 font-mono text-[11px] leading-snug">{guardian.summary}</p>
          </div>

          {/* executioner result */}
          <div className="mt-2 rounded-lg border border-white/10 bg-white/[0.03] p-2.5">
            <div className="font-mono text-[9px] uppercase tracking-[0.3em] text-slate-500">Executioner</div>
            <p className="mt-1 font-mono text-[11px] leading-snug text-slate-300">{executioner.summary}</p>
          </div>
        </>
      )}
    </section>
  );
}