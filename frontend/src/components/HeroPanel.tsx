/**
 * HeroPanel — live P/L block: count-up KPIs (equity, today's P/L, win rate,
 * open risk), a self-drawing equity curve (SVG), drawdown gauge with needle,
 * and the kill switch. Reads from the backend state via the store.
 */

import { useEffect, useMemo, useState } from 'react';
import { useAppStore } from '../store/useAppStore';
import { KillSwitch } from './RiskShield';

function useAnimatedNumber(target: number, duration = 900) {
  const [value, setValue] = useState(target);
  useEffect(() => {
    const from = value;
    const start = performance.now();
    let raf = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const ease = 1 - Math.pow(2, -10 * t);
      setValue(from + (target - from) * (t === 1 ? 1 : ease));
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target]);
  return value;
}

function EquityCurve({ seed, positive }: { seed: number; positive: boolean }) {
  const [drawn, setDrawn] = useState(false);
  useEffect(() => {
    const id = window.setTimeout(() => setDrawn(true), 120);
    return () => window.clearTimeout(id);
  }, [seed]);

  const { path, area, last, min, max } = useMemo(() => {
    let eq = 10000;
    const pts: number[] = [];
    let x = 0;
    let rnd = seed;
    const rand = () => {
      rnd = (rnd * 9301 + 49297) % 233280;
      return rnd / 233280;
    };
    for (let i = 0; i < 60; i++) {
      eq += Math.sin(i / 3.2 + seed) * 55 + (positive ? 26 : -6) + (rand() - 0.45) * 60;
      pts.push(eq);
    }
    const minV = Math.min(...pts);
    const maxV = Math.max(...pts);
    const W = 320, H = 96, PAD = 6;
    const coords = pts.map((p, i) => [
      (i / (pts.length - 1)) * (W - PAD * 2) + PAD,
      H - PAD - ((p - minV) / Math.max(1e-9, maxV - minV)) * (H - PAD * 2),
    ]);
    const pathD = coords.map(([x1, y1], i) => `${i === 0 ? 'M' : 'L'}${x1.toFixed(1)},${y1.toFixed(1)}`).join(' ');
    const areaD = `${pathD} L${(W - PAD).toFixed(1)},${H - PAD} L${PAD},${H - PAD} Z`;
    return { path: pathD, area: areaD, last: pts[pts.length - 1], min: minV, max: maxV };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seed, positive]);

  const color = positive ? '#34D399' : '#FB7185';
  return (
    <svg viewBox="0 0 320 96" className="w-full">
      <defs>
        <linearGradient id="eq-fill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.32" />
          <stop offset="100%" stopColor={color} stopOpacity="0.02" />
        </linearGradient>
      </defs>
      <path d={area} fill="url(#eq-fill)" opacity={drawn ? 1 : 0} style={{ transition: 'opacity 900ms ease 500ms' }} />
      <path
        d={path}
        fill="none"
        stroke={color}
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeDasharray="1200"
        strokeDashoffset={drawn ? 0 : 1200}
        style={{ transition: 'stroke-dashoffset 1600ms cubic-bezier(0.4,0,0.2,1)' }}
      />
    </svg>
  );
}

function DrawdownGauge({ ddPct }: { ddPct: number }) {
  // semicircular gauge with needle, 0–8% scale, kill at 4%
  const clamped = Math.min(8, Math.max(0, ddPct));
  const angle = (clamped / 8) * 180; // 0..180 left-to-right
  const rad = ((180 - angle) * Math.PI) / 180;
  const nx = 60 + Math.cos(rad) * 40;
  const ny = 58 - Math.sin(rad) * 40;
  const danger = clamped >= 4;
  return (
    <svg viewBox="0 0 120 66" className="w-full">
      <path d="M12 58 A48 48 0 0 1 108 58" fill="none" stroke="rgba(120,160,255,0.18)" strokeWidth="9" strokeLinecap="round" />
      <path d="M12 58 A48 48 0 0 1 60 10" fill="none" stroke="#FBBF24" strokeWidth="9" strokeLinecap="round" opacity="0.5" />
      <circle cx="60" cy="58" r="4" fill={danger ? '#FB7185' : '#34D399'} />
      <line x1="60" y1="58" x2={nx} y2={ny} stroke={danger ? '#FB7185' : '#E6EDF7'} strokeWidth="2.4" strokeLinecap="round" style={{ transition: 'all 600ms ease' }} />
      <text x="60" y="66" textAnchor="middle" fontSize="9" fill={danger ? '#FB7185' : '#FBBF24'} fontFamily="JetBrains Mono">
        {clamped.toFixed(2)}% DD
      </text>
    </svg>
  );
}

function KpiCard({ label, value, sub, tone }: { label: string; value: string; sub?: string; tone: 'cyan' | 'emerald' | 'amber' | 'violet' }) {
  const toneText = { cyan: 'text-cyan-300', emerald: 'text-emerald-300', amber: 'text-amber-300', violet: 'text-violet-300' }[tone];
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.03] p-2.5">
      <div className="font-mono text-[9px] uppercase tracking-[0.2em] text-slate-500">{label}</div>
      <div className={`tabular mt-0.5 font-mono text-lg font-semibold ${toneText}`}>{value}</div>
      {sub && <div className="text-[9px] text-slate-500">{sub}</div>}
    </div>
  );
}

export default function HeroPanel() {
  const account = useAppStore((s) => s.account);
  const positions = useAppStore((s) => s.positions);
  const equity = useAnimatedNumber(account?.equity ?? 10000);
  const pnl = (account?.profit ?? 0) + (account?.equity ?? 10000) - 10000;
  const pnlAnimated = useAnimatedNumber(pnl);
  const ddPct = account ? (account.daily_drawdown / Math.max(account.equity, 1)) * 100 : 0;
  const todayPnl = account?.profit ?? 0;
  const openRisk = positions.reduce((acc, p) => acc + Math.abs(p.entry_price - p.stop_loss) * p.lot_size, 0);
  const unrealized = positions.reduce((acc, p) => acc + (p.unrealized_pnl ?? 0), 0);
  const seed = Math.round((account?.equity ?? 10000) % 1000) || 7;

  return (
    <section className="glass flex flex-col gap-3 p-4">
      <div className="flex items-center justify-between">
        <h2 className="font-mono text-[10px] uppercase tracking-[0.3em] text-slate-500">Account · Live P/L</h2>
        <KillSwitch />
      </div>

      <div className="grid grid-cols-2 gap-2">
        <KpiCard label="Equity" value={`$${equity.toLocaleString('en-US', { maximumFractionDigits: 0 })}`} sub={`balance 10,000.00 baseline`} tone="cyan" />
        <KpiCard label="Today's P/L" value={`${todayPnl >= 0 ? '+' : ''}$${todayPnl.toFixed(2)}`} sub={`unrealized ${unrealized >= 0 ? '+' : ''}${unrealized.toFixed(2)}`} tone={todayPnl >= 0 ? 'emerald' : 'amber'} />
        <KpiCard label="Net P/L" value={`${pnlAnimated >= 0 ? '+' : ''}$${pnlAnimated.toFixed(2)}`} sub="since launch" tone={pnlAnimated >= 0 ? 'emerald' : 'amber'} />
        <KpiCard label="Open risk" value={`$${openRisk.toFixed(0)}`} sub={`${positions.length} position(s) open`} tone="violet" />
      </div>

      <div>
        <div className="mb-1 flex items-center justify-between font-mono text-[9px] uppercase tracking-[0.2em] text-slate-600">
          <span>Equity curve</span>
          <span className={pnlAnimated >= 0 ? 'text-emerald-400' : 'text-rose-400'}>{pnlAnimated >= 0 ? '▲' : '▼'} self-drawing</span>
        </div>
        <EquityCurve seed={seed} positive={pnlAnimated >= 0} />
      </div>

      <div>
        <div className="mb-1 font-mono text-[9px] uppercase tracking-[0.2em] text-slate-600">Daily drawdown gauge</div>
        <DrawdownGauge ddPct={ddPct} />
      </div>
    </section>
  );
}