/**
 * QUANT PILOT — App shell.
 * Intro (BootScene) → Launch Desk → dashboard with view tabs, WebSocket-driven
 * agent state, command palette (Ctrl/Cmd+K), custom cursor, toasts, footer.
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import Lenis from 'lenis';
import BootScene from './scenes/BootScene';
import ConstellationScene from './scenes/ConstellationScene';
import Cursor from './components/Cursor';
import TopBar from './components/TopBar';
import Footer from './components/Footer';
import Toasts from './components/Toasts';
import CommandDock from './components/CommandDock';
import CommandPalette from './components/CommandPalette';
import IntroOverlay from './components/IntroOverlay';
import HeroPanel from './components/HeroPanel';
import ChartPanel from './components/ChartPanel';
import SignalCard from './components/SignalCard';
import BacktestLab from './components/BacktestLab';
import JournalPanel from './components/JournalPanel';
import SettingsPanel from './components/SettingsPanel';
import AgentPanel from './components/AgentPanel';
import RiskShield from './components/RiskShield';
import SweepVisualizer from './components/SweepVisualizer';
import { useAppStore, type AgentName } from './store/useAppStore';
import { apiGet, wsClient, type WsEvent } from './api/client';

const AGENT_NAMES: AgentName[] = ['SCOUT', 'CARTOGRAPHER', 'HUNTER', 'ANALYST', 'GUARDIAN', 'EXECUTIONER', 'CHRONICLER'];

export default function App() {
  const showIntro = useAppStore((s) => s.showIntro);
  const setShowIntro = useAppStore((s) => s.setShowIntro);
  const setShowWelcome = useAppStore((s) => s.setShowWelcome);
  const activeTab = useAppStore((s) => s.activeTab);
  const setActiveTab = useAppStore((s) => s.setActiveTab);
  const wsConnected = useAppStore((s) => s.wsConnected);
  const setWsConnected = useAppStore((s) => s.setWsConnected);
  const upsertAgent = useAppStore((s) => s.upsertAgent);
  const setAccount = useAppStore((s) => s.setAccount);
  const setMode = useAppStore((s) => s.setMode);
  const setDemoBanner = useAppStore((s) => s.setDemoBanner);
  const setMt5Status = useAppStore((s) => s.setMt5Status);
  const setPositions = useAppStore((s) => s.setPositions);
  const setSession = useAppStore((s) => s.setSession);
  const setMt5StatusSafe = setMt5Status;
  const bumpJournal = useAppStore((s) => s.bumpJournal);
  const sound = useAppStore((s) => s.sound);
  const pushToast = useAppStore((s) => s.pushToast);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const audioRef = useRef<AudioContext | null>(null);

  // ── Lenis smooth scrolling (dashboard panes) ─────────────────────────────
  useEffect(() => {
    const lenis = new Lenis({ duration: 1.1, smoothWheel: true });
    let raf = 0;
    const tick = (time: number) => {
      lenis.raf(time);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(raf);
      lenis.destroy();
    };
  }, []);

  // ── WebSocket: live agent events ─────────────────────────────────────────
  useEffect(() => {
    wsClient.connect();
    const unsubscribe = wsClient.subscribe((ev: WsEvent) => {
      if (ev.type === 'connection') {
        setWsConnected(ev.status === 'open');
        return;
      }
      if (ev.type === 'agent_result' && ev.agent) {
        const name = ev.agent as AgentName;
        if ((AGENT_NAMES as string[]).includes(name)) {
          upsertAgent(name, {
            status: ev.status ?? 'OK',
            summary: String(ev.summary ?? '').slice(0, 220),
            confidence: typeof ev.confidence === 'number' ? ev.confidence : 0,
            latencyMs: Number(ev.data?.latency_ms ?? 0),
            data: ev.data,
            updatedAt: ev.ts,
          });
          if (sound && audioRef.current == null) {
            try { audioRef.current = new AudioContext(); } catch { /* no audio */ }
          }
          if (sound && audioRef.current) {
            try {
              const freq = { SCOUT: 520, CARTOGRAPHER: 560, HUNTER: 640, ANALYST: 720, GUARDIAN: 800, EXECUTIONER: 880, CHRONICLER: 960 }[name] ?? 660;
              const osc = audioRef.current.createOscillator();
              const gain = audioRef.current.createGain();
              osc.type = 'sine';
              osc.frequency.value = ev.status === 'VETOED' ? 220 : freq;
              gain.gain.setValueAtTime(0.0001, audioRef.current.currentTime);
              gain.gain.exponentialRampToValueAtTime(0.08, audioRef.current.currentTime + 0.02);
              gain.gain.exponentialRampToValueAtTime(0.0001, audioRef.current.currentTime + 0.35);
              osc.connect(gain).connect(audioRef.current.destination);
              osc.start();
              osc.stop(audioRef.current.currentTime + 0.4);
            } catch { /* ignore */ }
          }
          if (ev.status === 'VETOED') pushToast({ title: 'Guardian veto', body: String(ev.summary ?? 'Trade vetoed by AEGIS'), tone: 'rose' });
          if (ev.status === 'EXECUTED') pushToast({ title: 'Order filled', body: String(ev.summary ?? ''), tone: 'emerald' });
          bumpJournal();
        }
        return;
      }
      if (ev.type === 'cycle_end') {
        const outcome = ev.outcome as string | undefined;
        if (outcome === 'TAKEN') pushToast({ title: 'Cycle complete — TAKEN', body: 'Paper order filled; watch BE at 1R.', tone: 'emerald' });
      }
      if (ev.type === 'banner') {
        setDemoBanner(ev.kind === 'mt5_unavailable' ? true : true);
        if (ev.kind === 'mt5_unavailable') pushToast({ title: 'MT5 unavailable', body: String(ev.message ?? 'Running in Demo mode.'), tone: 'amber' });
      }
      if (ev.type === 'kill_switch') pushToast({ title: 'HALTED', body: 'New orders rejected; positions flattened.', tone: 'rose' });
    });
    return () => {
      unsubscribe();
      wsClient.disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── REST polling: account / positions / session / mt5 status every 3s ────
  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      const state = await apiGet<any>('/api/state', null);
      if (cancelled || !state) return;
      setAccount(state.account);
      setMode(state.mode ?? 'DEMO');
      setDemoBanner(Boolean(state.demo_mode ?? true));
      setMt5StatusSafe(state.mt5 ?? null);
      setPositions(Array.isArray(state.positions) ? state.positions : []);
      setSession(String(state.session ?? 'ASIAN'));
    };
    void poll();
    const id = window.setInterval(poll, 3000);
    return () => { cancelled = true; window.clearInterval(id); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Keyboard shortcuts ───────────────────────────────────────────────────
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const mod = e.ctrlKey || e.metaKey;
      if (mod && e.key.toLowerCase() === 'k') { e.preventDefault(); setPaletteOpen((v) => !v); return; }
      const tag = (e.target as HTMLElement)?.tagName?.toLowerCase();
      if (tag === 'input' || tag === 'textarea') return;
      const tabs = ['CONSTELLATION', 'CHART', 'SIGNALS', 'BACKTEST', 'JOURNAL', 'SETTINGS'] as const;
      const idx = Number(e.key) - 1;
      if (idx >= 0 && idx < tabs.length) setActiveTab(tabs[idx]);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [setActiveTab]);

  const launch = () => {
    setShowIntro(false);
    window.localStorage.setItem('qp-intro-seen', '1');
    if (!window.localStorage.getItem('qp-welcome-seen')) setShowWelcome(true);
  };

  // ── Intro screen ──────────────────────────────────────────────────────────
  if (showIntro) {
    return (
      <div className="relative h-screen w-screen overflow-hidden bg-[#05060F]">
        <BootScene active />
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-end pb-[12vh]">
          <div className="text-center">
            <h1 className="gradient-text font-display text-6xl font-bold tracking-[0.18em] drop-shadow-[0_0_40px_rgba(139,92,246,0.45)] md:text-7xl">QUANT PILOT</h1>
            <p className="mt-2 font-mono text-[11px] uppercase tracking-[0.5em] text-cyan-300/90">Liquidity Sweep · Multi-Agent Trading Desk</p>
            <p className="mt-1 text-[10px] uppercase tracking-[0.3em] text-slate-500">by JAYAKUMAR.ai · XAUUSD / BTCUSD</p>
          </div>
          <button
            data-cursor="Enter the desk"
            onClick={launch}
            className="pointer-events-auto mt-8 rounded-full border border-cyan-400/60 bg-cyan-500/10 px-10 py-3 font-display text-sm font-semibold uppercase tracking-[0.35em] text-cyan-200 shadow-neon transition-all duration-300 hover:scale-105 hover:bg-cyan-400/20 hover:shadow-[0_0_45px_rgba(34,211,238,0.5)]"
          >
            Launch Desk
          </button>
          <p className="pointer-events-auto mt-6 max-w-md text-center text-[10px] leading-relaxed text-slate-600">Educational use only. Not financial advice. Trading involves risk of loss.</p>
        </div>
        <Cursor />
      </div>
    );
  }

  // ── Dashboard ─────────────────────────────────────────────────────────────
  return (
    <div className="relative h-screen w-screen overflow-hidden bg-[#05060F] text-slate-100 viewport-grid">
      <TopBar />
      <Toasts />

      <main className="relative h-[calc(100vh-3rem-1.25rem)] w-full">
        {/* CONSTELLATION — hero view */}
        {activeTab === 'CONSTELLATION' && (
          <div className="absolute inset-0">
            <ConstellationScene />
            <AgentPanel />
            <div className="absolute right-3 top-3 z-20 hidden h-[calc(100%-24px)] w-[340px] xl:block">
              <SweepVisualizer />
            </div>
            <div className="absolute bottom-20 left-3 z-20 w-[340px]">
              <RiskShield>
                <HeroPanel />
              </RiskShield>
            </div>
          </div>
        )}

        {/* CHART */}
        {activeTab === 'CHART' && (
          <div className="absolute inset-0 grid grid-cols-1 gap-3 p-3 lg:grid-cols-3">
            <div className="lg:col-span-2"><ChartPanel /></div>
            <div className="flex min-h-0 flex-col gap-3"><SignalCard /></div>
          </div>
        )}

        {/* SIGNALS */}
        {activeTab === 'SIGNALS' && (
          <div className="absolute inset-0 grid grid-cols-1 gap-3 p-3 lg:grid-cols-2">
            <SignalCard />
            <SweepVisualizer />
          </div>
        )}

        {/* BACKTEST */}
        {activeTab === 'BACKTEST' && (
          <div className="absolute inset-0 p-3"><BacktestLab /></div>
        )}

        {/* JOURNAL */}
        {activeTab === 'JOURNAL' && (
          <div className="absolute inset-0 p-3"><JournalPanel /></div>
        )}

        {/* SETTINGS */}
        {activeTab === 'SETTINGS' && (
          <div className="absolute inset-0 p-3"><SettingsPanel /></div>
        )}
      </main>

      <CommandDock />
      <Footer />
      <IntroOverlay />
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
      <Cursor />
      {!wsConnected && (
        <div className="pointer-events-none absolute bottom-16 left-1/2 z-40 -translate-x-1/2 rounded-full border border-amber-400/40 bg-black/70 px-4 py-1 font-mono text-[9px] uppercase tracking-[0.3em] text-amber-300 backdrop-blur">
          Backend unreachable — start it with: python run.py
        </div>
      )}
    </div>
  );
}