/**
 * RiskShield + Kill switch.
 * 3D-ish shield around the account panel (emerald when all checks pass, cracks
 * rose on veto/drawdown) and a big hold-to-confirm KILL SWITCH with a ring.
 */

import { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { useAppStore } from '../store/useAppStore';
import { apiPost } from '../api/client';

const HOLD_MS = 1100;

export function KillSwitch() {
  const [holding, setHolding] = useState(false);
  const [progress, setProgress] = useState(0);
  const raf = useRef<number>(0);
  const start = useRef(0);
  const pushToast = useAppStore((s) => s.pushToast);

  const begin = () => {
    setHolding(true);
    start.current = performance.now();
    const tick = () => {
      const p = Math.min(1, (performance.now() - start.current) / HOLD_MS);
      setProgress(p);
      if (p >= 1) {
        setHolding(false);
        setProgress(0);
        void apiPost('/api/kill-switch', { close_positions: true }).then(() =>
          pushToast({ title: 'KILL SWITCH ENGAGED', body: 'New orders halted; open positions flattened.', tone: 'rose' }),
        );
        return;
      }
      raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
  };

  const cancel = () => {
    setHolding(false);
    setProgress(0);
    cancelAnimationFrame(raf.current);
  };

  useEffect(() => () => cancelAnimationFrame(raf.current), []);

  const R = 34;
  const C = 2 * Math.PI * R;

  return (
    <div className="flex flex-col items-center">
      <button
        data-cursor="Hold to halt"
        onPointerDown={begin}
        onPointerUp={cancel}
        onPointerLeave={cancel}
        onContextMenu={(e) => e.preventDefault()}
        className="relative flex h-24 w-24 touch-none select-none items-center justify-center rounded-full border border-rose-500/60 bg-rose-950/40 transition-transform active:scale-95"
        aria-label="Hold to engage kill switch"
      >
        <svg className="absolute inset-0 h-full w-full -rotate-90" viewBox="0 0 80 80">
          <circle cx="40" cy="40" r={R * 0.52} fill="none" stroke="rgba(251,113,133,0.15)" strokeWidth="5" />
          <circle
            cx="40" cy="40" r={R * 0.52} fill="none" stroke="#FB7185" strokeWidth="5" strokeLinecap="round"
            strokeDasharray={C * 0.52}
            strokeDashoffset={C * 0.52 * (1 - progress)}
          />
        </svg>
        <div className="text-center">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#FDA4AF" strokeWidth="2" className="mx-auto"><path d="M12 3 3 8v6c0 4.5 3.8 8.4 9 10 5.2-1.6 9-5.5 9-10V8l-9-5z" strokeLinejoin="round" /><path d="M12 9v5M12 17h.01" strokeLinecap="round" /></svg>
          <div className="mt-1 font-mono text-[8px] font-bold uppercase tracking-[0.2em] text-rose-300">Kill<br />Switch</div>
        </div>
      </button>
      <div className="mt-1 text-[8px] uppercase tracking-[0.25em] text-slate-600">{holding ? 'KEEP HOLDING…' : 'hold to confirm'}</div>
    </div>
  );
}

export default function RiskShield({ children }: { children: React.ReactNode }) {
  const agents = useAppStore((s) => s.agents);
  const account = useAppStore((s) => s.account);
  const guardianOk = agents.GUARDIAN.status !== 'VETOED';
  const ddOk = (account?.daily_drawdown ?? 0) < 400;
  const healthy = guardianOk && ddOk;

  return (
    <div className="relative">
      {/* shield backdrop glow */}
      <div
        aria-hidden
        className="pointer-events-none absolute -inset-2 rounded-2xl border-2 transition-colors duration-700"
        style={{
          borderColor: healthy ? 'rgba(52,211,153,0.35)' : 'rgba(251,113,133,0.55)',
          boxShadow: healthy ? '0 0 34px rgba(52,211,153,0.18), inset 0 0 26px rgba(52,211,153,0.08)' : '0 0 40px rgba(251,113,133,0.3), inset 0 0 30px rgba(251,113,133,0.15)',
        }}
      />
      <div className="relative">{children}</div>
    </div>
  );
}