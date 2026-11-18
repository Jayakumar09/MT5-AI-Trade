/**
 * SweepVisualizer — "Why this trade?" panel.
 * Animated SVG playback of the liquidity sweep (pool glow → wick spike →
 * displacement candle → entry → SL/TP ladder) with step controls, plus the
 * Guardian checklist and a circular confidence ring.
 */

import { useEffect } from 'react';
import { motion } from 'framer-motion';
import { useAppStore } from '../store/useAppStore';

const STEPS = ['Liquidity pool', 'Wick pierce', 'Displacement', 'Entry + SL', 'SL/TP ladder'];

const CHECKLIST = [
  'Level swept (PDH / PDL / equal highs-lows)',
  'Sweep depth in range (XAU 10–25 pips · BTC 0.15–0.4%)',
  'Displacement ≥ 1.2× average body',
  'Session filter passed (London / NY)',
  'Risk-reward ≥ 1:2',
  'Guardian approved',
];

function ConfidenceRing({ pct, label }: { pct: number; label: string }) {
  const R = 26;
  const C = 2 * Math.PI * R;
  return (
    <div className="flex flex-col items-center">
      <svg width="76" height="76" viewBox="0 0 76 76" className="-rotate-90">
        <circle cx="38" cy="38" r={R} fill="none" stroke="rgba(120,160,255,0.15)" strokeWidth="7" />
        <circle
          cx="38" cy="38" r={R} fill="none" stroke="url(#conf-grad)" strokeWidth="7" strokeLinecap="round"
          strokeDasharray={C}
          strokeDashoffset={C * (1 - pct / 100)}
          style={{ transition: 'stroke-dashoffset 800ms ease' }}
        />
        <defs>
          <linearGradient id="conf-grad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#22D3EE" />
            <stop offset="100%" stopColor="#8B5CF6" />
          </linearGradient>
        </defs>
      </svg>
      <div className="-mt-[52px] flex h-[52px] flex-col items-center justify-center">
        <span className="font-mono text-base font-bold text-cyan-300">{pct}</span>
        <span className="text-[8px] uppercase tracking-widest text-slate-500">/10</span>
      </div>
      <div className="mt-1 max-w-[130px] text-center font-mono text-[8px] uppercase leading-tight tracking-widest text-violet-300">{label}</div>
    </div>
  );
}

export default function SweepVisualizer() {
  const step = useAppStore((s) => s.sweepStep);
  const setStep = useAppStore((s) => s.setSweepStep);
  const playing = useAppStore((s) => s.sweepPlaying);
  const setPlaying = useAppStore((s) => s.setSweepPlaying);
  const agents = useAppStore((s) => s.agents);
  const analystSummary = agents.ANALYST.summary;
  const activeSweep = agents.HUNTER.status === 'CANDIDATE' || agents.HUNTER.status === 'OK';

  // autoplay while "playing" is true
  useEffect(() => {
    if (!playing) return;
    const id = window.setInterval(() => {
      if (useAppStore.getState().sweepStep >= 4) {
        setPlaying(false);
      } else {
        setStep(useAppStore.getState().sweepStep + 1);
      }
    }, 750);
    return () => window.clearInterval(id);
  }, [playing, setPlaying, setStep]);

  const play = () => {
    setStep(0);
    setPlaying(true);
  };

  // static geometry for the idealized sweep chart (SVG units)
  const W = 300, H = 150;
  const level = 96; // price line (equal lows)
  const poolLow = 122;
  const displacementTop = 26;

  const visiblePool = step >= 0;
  const visibleWick = step >= 1;
  const visibleDisplacement = step >= 2;
  const visibleEntry = step >= 3;
  const visibleLadder = step >= 4;

  return (
    <section className="glass flex h-full flex-col p-3">
      <div className="flex items-center justify-between">
        <h2 className="font-mono text-[10px] uppercase tracking-[0.3em] text-slate-500">Why this trade?</h2>
        <button
          data-cursor="Replay sweep"
          onClick={play}
          className="rounded-md border border-violet-400/50 bg-violet-500/10 px-2.5 py-1 font-mono text-[9px] uppercase tracking-widest text-violet-300 shadow-violet transition hover:bg-violet-500/20"
        >
          {playing ? 'Playing…' : 'Replay sweep'}
        </button>
      </div>

      {/* idealized chart */}
      <svg viewBox={`0 0 ${W} ${H}`} className="mt-2 w-full rounded-lg border border-white/5 bg-black/40">
        {/* grid */}
        {[0, 1, 2, 3].map((i) => (
          <line key={i} x1="0" x2={W} y1={20 + i * 36} y2={20 + i * 36} stroke="rgba(120,160,255,0.06)" strokeDasharray="2 5" />
        ))}
        {/* liquidity pool (equal lows) */}
        {visiblePool && (
          <g style={{ filter: 'drop-shadow(0 0 8px rgba(251,191,36,0.55))' }}>
            <line x1="16" x2={W - 16} y1={level} y2={level} stroke="#FBBF24" strokeWidth="2" strokeDasharray="6 4" />
            <circle cx="46" cy={level} r="4" fill="#FBBF24" />
            <circle cx="120" cy={level} r="4" fill="#FBBF24" />
            <circle cx="196" cy={level} r="4" fill="#FBBF24" />
            <text x="W - 20" y={level - 4} textAnchor="end" fontSize="7" fill="#FBBF24" fontFamily="JetBrains Mono">EQUAL LOWS</text>
          </g>
        )}
        {/* price wick piercing the pool */}
        {visibleWick && (
          <g>
            <line x1="196" y1="52" x2="196" y2={poolLow + 14} stroke="#FB7185" strokeWidth="3.4" strokeLinecap="round" />
            <rect x="190" y="52" width="12" height="26" fill="#FB7185" rx="1.5" opacity="0.9" />
            <text x="206" y={poolLow + 22} fontSize="7" fill="#FB7185" fontFamily="JetBrains Mono">SWEEP</text>
          </g>
        )}
        {/* displacement candle back inside */}
        {visibleDisplacement && (
          <g>
            <rect x="230" y={displacementTop} width="14" height={level - displacementTop - 6} fill="#34D399" rx="1.5" style={{ filter: 'drop-shadow(0 0 9px rgba(52,211,153,0.6))' }} />
            <line x1="237" y1={displacementTop - 5} x2="237" y2={level + 2} stroke="#34D399" strokeWidth="2.4" strokeLinecap="round" />
            <text x="252" y={displacementTop + 10} fontSize="7" fill="#34D399" fontFamily="JetBrains Mono">DISPLACE</text>
          </g>
        )}
        {/* entry line */}
        {visibleEntry && (
          <g>
            <line x1="10" x2={W - 10} y1={64} y2={64} stroke="#22D3EE" strokeWidth="1.6" />
            <text x="12" y="61" fontSize="7" fill="#22D3EE" fontFamily="JetBrains Mono">ENTRY</text>
          </g>
        )}
        {/* SL / TP ladder */}
        {visibleLadder && (
          <g fontFamily="JetBrains Mono" fontSize="7">
            <line x1="10" x2={W - 10} y1={level + 4} y2={level + 4} stroke="#FB7185" strokeWidth="1.4" strokeDasharray="4 3" />
            <text x="12" y={level + 15} fill="#FB7185">SL · beyond the wick + buffer</text>
            <line x1="10" x2={W - 10} y1="42" y2="42" stroke="#34D399" strokeWidth="1.4" strokeDasharray="4 3" />
            <text x="12" y="38" fill="#34D399">TP1 · opposite boundary · RR 1:2</text>
            <line x1="10" x2={W - 10} y1="26" y2="26" stroke="#34D399" strokeWidth="1.4" opacity="0.75" strokeDasharray="4 3" />
            <text x="12" y="17" fill="#34D399" opacity="0.85">TP2 · next liquidity pool · RR 1:3</text>
          </g>
        )}
      </svg>

      {/* scrubber */}
      <div className="mt-2 flex items-center gap-2">
        {STEPS.map((label, i) => (
          <button
            key={i}
            onClick={() => setStep(i)}
            data-cursor={label}
            aria-label={`Step ${i + 1}: ${label}`}
            className={`h-2 flex-1 rounded-full transition-all duration-300 ${i <= step ? 'bg-gradient-to-r from-cyan-400 to-violet-500 shadow-neon' : 'bg-white/10'}`}
          />
        ))}
      </div>
      <div className="mt-1 text-center font-mono text-[9px] uppercase tracking-[0.25em] text-slate-500">
        step {Math.min(step + 1, 5)}/5 — {STEPS[Math.min(step, 4)]}
      </div>

      {/* checklist + confidence */}
      <div className="mt-2 flex flex-1 gap-3">
        <ul className="flex-1 space-y-1.5">
          {CHECKLIST.map((item, i) => {
            const passed = activeSweep || i <= step;
            return (
              <li key={i} className="flex items-start gap-2 text-[10px] leading-snug text-slate-400">
                <span className={`mt-0.5 flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-sm border ${passed ? 'border-emerald-400/60 bg-emerald-400/15 text-emerald-400' : 'border-white/15 text-transparent'}`}>
                  <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="4"><path d="M4 12l6 6L20 6" /></svg>
                </span>
                {item}
              </li>
            );
          })}
        </ul>
        <div className="flex flex-col items-center justify-center gap-2">
          <ConfidenceRing pct={74} label="Analyst confidence" />
          <div className="max-w-[150px] text-center text-[9px] leading-snug text-violet-200/80">{analystSummary.slice(0, 140)}{analystSummary.length > 140 ? '…' : ''}</div>
        </div>
      </div>
    </section>
  );
}