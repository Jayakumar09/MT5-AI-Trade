/**
 * Top bar: mode pill (DEMO / PAPER / MT5 DEMO / MT5 LIVE), session badge with
 * day-night arc, sound toggle, connection status, social pills, demo scenario.
 */

import { useAppStore } from '../store/useAppStore';
import { openSocial } from '../config/social';
import { apiPost } from '../api/client';

const MODE_STYLE: Record<string, string> = {
  DEMO: 'border-cyan-400/50 text-cyan-300 shadow-neon',
  PAPER: 'border-violet-400/50 text-violet-300 shadow-violet',
  MT5_DEMO: 'border-amber-400/50 text-amber-300',
  MT5_LIVE: 'border-rose-500 text-rose-300 shadow-rose',
};

function SessionArc({ session }: { session: string }) {
  // Day-night arc: crescent marker position by session
  const t = session === 'ASIAN' ? 0.14 : session === 'LONDON' ? 0.38 : session === 'NEW_YORK' ? 0.72 : 0.5;
  const angle = Math.PI * (1 - t);
  const cx = 34 + Math.cos(angle) * 30;
  const cy = 34 - Math.sin(angle) * 26;
  return (
    <div className="flex items-center gap-2" title="Session (IST/UTC)">
      <svg width="68" height="38" viewBox="0 0 68 38">
        <path d="M2 34 A32 26 0 0 1 66 34" fill="none" stroke="rgba(120,160,255,0.25)" strokeWidth="2" strokeDasharray="3 3" />
        <circle cx={cx} cy={cy} r="4.5" fill="#FBBF24" opacity="0.9">
          <animate attributeName="opacity" values="0.9;0.5;0.9" dur="2.4s" repeatCount="indefinite" />
        </circle>
      </svg>
      <div className="leading-tight">
        <div className="font-mono text-[10px] uppercase tracking-widest text-amber-200">{session.replace('_', ' ')}</div>
        <div className="text-[9px] text-slate-500">IST / UTC</div>
      </div>
    </div>
  );
}

export default function TopBar() {
  const mode = useAppStore((s) => s.mode);
  const demoBanner = useAppStore((s) => s.demoBanner);
  const wsConnected = useAppStore((s) => s.wsConnected);
  const sound = useAppStore((s) => s.sound);
  const toggleSound = useAppStore((s) => s.toggleSound);
  const session = useAppStore((s) => s.session);
  const masterConfig = MODE_STYLE[mode] ?? MODE_STYLE.DEMO;

  return (
    <header className="relative z-40 flex h-12 items-center justify-between border-b border-white/5 bg-black/45 px-3 backdrop-blur-md">
      {/* logo mark */}
      <div className="flex items-center gap-2">
        <svg width="26" height="26" viewBox="0 0 64 64" aria-hidden>
          <circle cx="32" cy="32" r="26" fill="none" stroke="#22D3EE" strokeWidth="5" strokeDasharray="70 40" strokeLinecap="round" opacity="0.9" />
          <circle cx="32" cy="32" r="13" fill="none" stroke="#8B5CF6" strokeWidth="4" strokeDasharray="44 30" strokeLinecap="round" />
          <circle cx="32" cy="32" r="5" fill="#22D3EE" />
        </svg>
        <div className="leading-none">
          <div className="gradient-text font-display text-[15px] font-bold tracking-[0.14em]">QUANT PILOT</div>
          <div className="text-[8px] uppercase tracking-[0.3em] text-slate-500">by JAYAKUMAR.ai</div>
        </div>
      </div>

      {/* center: mode pill + session + connection */}
      <div className="absolute left-1/2 flex -translate-x-1/2 items-center gap-4">
        <div className={`flex items-center gap-2 rounded-full border bg-black/60 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.22em] ${masterConfig}`}>
          <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-current" />
          {mode.replace('_', ' ')}
        </div>
        <SessionArc session={session} />
        <div className="hidden items-center gap-1.5 text-[9px] uppercase tracking-widest text-slate-500 lg:flex">
          <span className={`h-1.5 w-1.5 rounded-full ${wsConnected ? 'bg-emerald-400' : 'bg-rose-400'}`} />
          {wsConnected ? 'LIVE FEED' : 'RECONNECTING'}
        </div>
      </div>

      {/* right: sound, socials, demo scenario */}
      <div className="flex items-center gap-2">
        <button
          data-cursor="Toggle sound"
          onClick={toggleSound}
          className="rounded-md border border-white/10 bg-white/5 p-1.5 text-slate-300 transition hover:border-cyan-400/40 hover:text-cyan-300"
          aria-label="Toggle sound"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M11 5 6 9H2v6h4l5 4V5z" />
            {sound ? <path d="M15.5 8.5a5 5 0 0 1 0 7M19 5a9 9 0 0 1 0 14" /> : <path d="M16 9l6 6M22 9l-6 6" />}
          </svg>
        </button>
        <button
          data-cursor="Subscribe"
          onClick={() => openSocial('youtube')}
          className="hidden items-center gap-1.5 rounded-full border border-rose-500/50 bg-rose-950/40 px-3 py-1 text-[10px] font-semibold uppercase tracking-widest text-rose-300 shadow-[0_0_16px_rgba(244,63,94,0.35)] transition hover:bg-rose-900/50 sm:flex"
        >
          Subscribe on YouTube
        </button>
        <button
          data-cursor="Follow"
          onClick={() => openSocial('instagram')}
          className="hidden items-center gap-1.5 rounded-full border border-fuchsia-500/50 bg-gradient-to-r from-fuchsia-950/50 to-violet-950/50 px-3 py-1 text-[10px] font-semibold uppercase tracking-widest text-fuchsia-300 shadow-[0_0_16px_rgba(217,70,239,0.3)] transition hover:from-fuchsia-900/60 hover:to-violet-900/60 sm:flex"
        >
          Follow on Instagram
        </button>
        <button
          data-cursor="Run scenario"
          onClick={() => apiPost('/api/run-demo-scenario', { symbol: 'XAUUSD' })}
          className="hidden rounded-full border border-cyan-400/50 bg-cyan-950/40 px-3 py-1 font-mono text-[10px] uppercase tracking-widest text-cyan-300 shadow-neon transition hover:bg-cyan-900/50 md:block"
        >
          Run Demo Scenario
        </button>
      </div>

      {demoBanner && (
        <div className="absolute left-0 top-full -z-10 mt-0 w-full border-b border-amber-400/30 bg-amber-500/10 px-3 py-1 text-center text-[9px] font-medium uppercase tracking-[0.2em] text-amber-300">
          Demo mode — synthetic data, no broker / no API key required
        </div>
      )}
    </header>
  );
}