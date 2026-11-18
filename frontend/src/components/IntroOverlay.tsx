/**
 * Intro overlay stack:
 *  - Welcome modal ("Support the creator") after the intro launch — remembered in localStorage
 *  - 5-step spotlight tour on first launch
 *  - Beginner / Pro toggle (inside the tour + dock settings shortcut is in TopBar/Settings)
 */

import { useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useAppStore } from '../store/useAppStore';
import { openSocial } from '../config/social';

const TOUR_STEPS: { title: string; body: string }[] = [
  { title: '1 · The Constellation', body: 'Seven AI agents work your sweep — from Scout (data) through Guardian (risk) to Chronicler (journal). Click any orb to inspect its live reasoning.' },
  { title: '2 · The Kill Switch', body: 'The amber shield around the account panel halts NEW orders and can close all open positions. Hold it to confirm.' },
  { title: '3 · Why this trade?', body: 'Every signal comes with an animated checklist — level swept, depth, displacement, session, RR ≥ 1:2, Guardian approval — plus Claude’s reasoning.' },
  { title: '4 · Backtest Lab', body: 'Replay the same Hunter + Guardian rules across synthetic history — equity curve, monthly heatmap, profit factor, max drawdown.' },
  { title: '5 · Journal', body: 'Every decision (taken, vetoed, skipped) lands in SQLite with the full agent trace. AI end-of-day review included.' },
];

export default function IntroOverlay() {
  const showWelcome = useAppStore((s) => s.showWelcome);
  const setShowWelcome = useAppStore((s) => s.setShowWelcome);
  const proMode = useAppStore((s) => s.proMode);
  const toggleProMode = useAppStore((s) => s.toggleProMode);
  const tourStep = useAppStore((s) => s.tourStep);
  const setTourStep = useAppStore((s) => s.setTourStep);
  const pushToast = useAppStore((s) => s.pushToast);

  useEffect(() => {
    if (showWelcome && typeof window !== 'undefined') {
      window.localStorage.setItem('qp-welcome-seen', '1');
    }
  }, [showWelcome]);

  const closeTour = () => {
    setTourStep(-1);
    window.localStorage.setItem('qp-intro-seen', '1');
  };

  return (
    <>
      {/* ── Welcome / support-the-creator modal ─────────────────────────── */}
      <AnimatePresence>
        {showWelcome && (
          <>
            <motion.div className="fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setShowWelcome(false)} />
            <motion.div
              role="dialog"
              aria-modal="true"
              aria-label="Support the creator"
              initial={{ opacity: 0, y: 42, scale: 0.94 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 20, scale: 0.96 }}
              transition={{ type: 'spring', stiffness: 300, damping: 26 }}
              className="glass fixed left-1/2 top-1/2 z-[85] w-[min(460px,92vw)] -translate-x-1/2 -translate-y-1/2 p-6 text-center"
            >
              <svg width="54" height="54" viewBox="0 0 64 64" className="mx-auto mb-3">
                <circle cx="32" cy="32" r="26" fill="none" stroke="#22D3EE" strokeWidth="4" strokeDasharray="70 40" strokeLinecap="round" />
                <circle cx="32" cy="32" r="13" fill="none" stroke="#8B5CF6" strokeWidth="3.5" strokeDasharray="44 30" strokeLinecap="round" />
                <circle cx="32" cy="32" r="5" fill="#22D3EE" />
              </svg>
              <h2 className="font-display text-lg font-semibold text-slate-100">Support the creator</h2>
              <p className="mt-1 text-xs text-slate-400">QUANT PILOT is free and open for education. If it helps your craft, subscribe — it genuinely supports future builds.</p>
              <div className="mt-4 flex flex-col gap-2">
                <button
                  data-cursor="Subscribe"
                  onClick={() => { openSocial('youtube'); pushToast({ title: 'Thanks!', body: 'Tap Subscribe in the tab that opened.', tone: 'rose' }); }}
                  className="rounded-xl border border-rose-500/50 bg-gradient-to-r from-rose-600/30 to-red-600/20 px-4 py-2.5 text-sm font-semibold text-rose-200 shadow-[0_0_20px_rgba(244,63,94,0.35)] transition hover:from-rose-600/40"
                >
                  Subscribe on YouTube — @sumedhhkumar
                </button>
                <button
                  data-cursor="Follow"
                  onClick={() => { openSocial('instagram'); pushToast({ title: 'Thanks!', body: 'Tap Follow in the tab that opened.', tone: 'violet' }); }}
                  className="rounded-xl border border-fuchsia-500/50 bg-gradient-to-r from-fuchsia-600/30 to-violet-600/25 px-4 py-2.5 text-sm font-semibold text-fuchsia-200 shadow-[0_0_20px_rgba(217,70,239,0.35)] transition hover:from-fuchsia-600/40"
                >
                  Follow on Instagram — @sumedhhkumar.ai
                </button>
              </div>
              <button onClick={() => setShowWelcome(false)} className="mt-4 text-[11px] uppercase tracking-widest text-slate-500 underline-offset-4 hover:text-slate-300 hover:underline">
                Skip for now
              </button>
              <p className="mt-2 text-[9px] text-slate-600">We never verify follows and never lock features behind them.</p>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* ── 5-step spotlight tour ───────────────────────────────────────── */}
      <AnimatePresence>
        {tourStep >= 0 && tourStep < TOUR_STEPS.length && (
          <>
            <motion.div className="fixed inset-0 z-[70] bg-black/55" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} />
            <motion.div
              key={tourStep}
              initial={{ opacity: 0, y: 26 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -14 }}
              className="glass fixed bottom-24 left-1/2 z-[75] w-[min(430px,92vw)] -translate-x-1/2 p-5"
            >
              <div className="flex items-center justify-between">
                <div className="font-mono text-[10px] uppercase tracking-[0.25em] text-cyan-300">Quick tour</div>
                <div className="flex items-center gap-1.5">
                  {TOUR_STEPS.map((_, i) => (
                    <span key={i} className={`h-1.5 rounded-full transition-all ${i === tourStep ? 'w-5 bg-cyan-400' : 'w-1.5 bg-white/15'}`} />
                  ))}
                </div>
              </div>
              <h3 className="mt-2 font-display text-base font-semibold text-slate-100">{TOUR_STEPS[tourStep].title}</h3>
              <p className="mt-1 text-xs leading-relaxed text-slate-400">{TOUR_STEPS[tourStep].body}</p>
              <div className="mt-4 flex items-center justify-between">
                <button onClick={toggleProMode} className="rounded-full border border-violet-400/40 bg-violet-500/10 px-3 py-1 font-mono text-[9px] uppercase tracking-widest text-violet-300">
                  Mode: {proMode ? 'PRO' : 'BEGINNER'}
                </button>
                <div className="flex gap-2">
                  <button onClick={closeTour} className="rounded-md px-3 py-1.5 text-[11px] text-slate-500 hover:text-slate-300">Skip tour</button>
                  <button
                    data-cursor="Next"
                    onClick={() => (tourStep === TOUR_STEPS.length - 1 ? closeTour() : setTourStep(tourStep + 1))}
                    className="rounded-md border border-cyan-400/50 bg-cyan-500/10 px-4 py-1.5 text-[11px] font-semibold text-cyan-300 shadow-neon"
                  >
                    {tourStep === TOUR_STEPS.length - 1 ? 'Enter the desk' : 'Next'}
                  </button>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}