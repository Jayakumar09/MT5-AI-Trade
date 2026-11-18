/**
 * BacktestLab — replay the Hunter + Guardian rules over synthetic history.
 * Self-drawing equity curve, monthly returns heatmap, PF / MDD / win-rate stats.
 */

import { useEffect, useState } from 'react';
import { apiPost } from '../api/client';
import { useAppStore } from '../store/useAppStore';

interface BacktestResult {
  symbol: string;
  trades: number;
  win_rate: number;
  profit_factor: number;
  max_drawdown_pct: number;
  equity_curve: { i: number; equity: number }[];
  monthly_returns: { month: string; ret_pct: number }[];
  error?: string;
}

export default function BacktestLab() {
  const [symbol, setSymbol] = useState<'XAUUSD' | 'BTCUSD'>('XAUUSD');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [drawn, setDrawn] = useState(false);
  const pushToast = useAppStore((s) => s.pushToast);

  const run = async () => {
    setLoading(true);
    setDrawn(false);
    const res = await apiPost<BacktestResult>('/api/backtest', { symbol }, undefined);
    if (res) setResult(res);
    setLoading(false);
    window.setTimeout(() => setDrawn(true), 150);
  };

  useEffect(() => { void run(); /* eslint-disable-line react-hooks/exhaustive-deps */ }, [symbol]);

  const curvePath = (() => {
    if (!result?.equity_curve?.length) return { line: '', area: '' };
    const pts = result.equity_curve;
    const W = 560, H = 150, PAD = 8;
    const vals = pts.map((p) => p.equity);
    const min = Math.min(...vals), max = Math.max(...vals);
    const xy = pts.map((p, i) => [(i / (pts.length - 1)) * (W - PAD * 2) + PAD, H - PAD - ((p.equity - min) / Math.max(1e-9, max - min)) * (H - PAD * 2)]);
    const line = xy.map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`).join(' ');
    return { line, area: `${line} L${W - PAD},${H - PAD} L${PAD},${H - PAD} Z` };
  })();

  return (
    <section className="glass flex h-full flex-col overflow-y-auto p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="font-mono text-[10px] uppercase tracking-[0.3em] text-slate-500">Backtest Lab · synthetic replay</h2>
          <p className="text-[10px] text-slate-600">Hunter sweep rules + Guardian vetoes, replayed over built-in price action.</p>
        </div>
        <div className="flex items-center gap-2">
          {(['XAUUSD', 'BTCUSD'] as const).map((s) => (
            <button key={s} onClick={() => setSymbol(s)} data-cursor="Symbol" className={`rounded-md border px-2.5 py-1 font-mono text-[10px] uppercase tracking-widest ${symbol === s ? 'border-amber-400/50 text-amber-300' : 'border-white/10 text-slate-500'}`}>{s === 'XAUUSD' ? 'Gold' : 'BTC'}</button>
          ))}
          <button onClick={run} data-cursor="Re-run" className="rounded-md border border-cyan-400/40 bg-cyan-500/10 px-3 py-1 font-mono text-[10px] uppercase tracking-widest text-cyan-300 hover:bg-cyan-500/20">
            {loading ? 'Running…' : 'Re-run'}
          </button>
        </div>
      </div>

      {/* stats row */}
      <div className="mt-3 grid grid-cols-4 gap-2">
        {[
          { label: 'Trades', value: result ? String(result.trades) : '—' },
          { label: 'Win rate', value: result ? `${result.win_rate}%` : '—' },
          { label: 'Profit factor', value: result ? result.profit_factor.toFixed(2) : '—' },
          { label: 'Max DD', value: result ? `${result.max_drawdown_pct}%` : '—' },
        ].map((s, i) => (
          <div key={i} className="rounded-xl border border-white/10 bg-white/[0.03] p-2.5 text-center">
            <div className="font-mono text-[9px] uppercase tracking-[0.2em] text-slate-500">{s.label}</div>
            <div className="tabular mt-0.5 font-mono text-lg font-bold text-cyan-300">{s.value}</div>
          </div>
        ))}
      </div>

      {/* equity replay */}
      <div className="mt-3">
        <div className="mb-1 font-mono text-[9px] uppercase tracking-[0.2em] text-slate-600">Backtest equity replay</div>
        <svg viewBox="0 0 560 150" className="w-full rounded-lg border border-white/5 bg-black/40">
          <defs>
            <linearGradient id="bt-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#22D3EE" stopOpacity="0.3" />
              <stop offset="100%" stopColor="#22D3EE" stopOpacity="0.02" />
            </linearGradient>
          </defs>
          <path d={curvePath.area} fill="url(#bt-fill)" opacity={drawn ? 1 : 0} style={{ transition: 'opacity 900ms ease 400ms' }} />
          <path d={curvePath.line} fill="none" stroke="#22D3EE" strokeWidth="2" strokeLinecap="round"
            strokeDasharray="1400" strokeDashoffset={drawn ? 0 : 1400} style={{ transition: 'stroke-dashoffset 1800ms cubic-bezier(0.4,0,0.2,1)' }} />
        </svg>
      </div>

      {/* monthly heatmap */}
      <div className="mt-3">
        <div className="mb-1 font-mono text-[9px] uppercase tracking-[0.2em] text-slate-600">Monthly returns heatmap</div>
        <div className="grid grid-cols-6 gap-1.5">
          {(result?.monthly_returns ?? []).map((m) => {
            const positive = m.ret_pct >= 0;
            const intensity = Math.min(1, Math.abs(m.ret_pct) / 6);
            return (
              <div
                key={m.month}
                className="rounded-md border border-white/5 p-1.5 text-center"
                style={{ background: positive ? `rgba(52,211,153,${0.08 + intensity * 0.32})` : `rgba(251,113,133,${0.08 + intensity * 0.32})` }}
              >
                <div className="font-mono text-[8px] uppercase text-slate-500">{m.month}</div>
                <div className={`tabular font-mono text-[11px] font-bold ${positive ? 'text-emerald-300' : 'text-rose-300'}`}>
                  {positive ? '+' : ''}{m.ret_pct.toFixed(1)}%
                </div>
              </div>
            );
          })}
          {!result?.monthly_returns?.length && [...Array(12)].map((_, i) => <div key={i} className="shimmer h-12 rounded-md border border-white/5" />)}
        </div>
      </div>
      <p className="mt-3 text-[9px] leading-snug text-slate-600">Educational use only. Backtest results on synthetic data do not predict future performance. Trading involves risk of loss.</p>
    </section>
  );
}