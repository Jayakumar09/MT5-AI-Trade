/**
 * Command dock — macOS-style magnification dock at the bottom.
 * Switches views: Constellation / Chart / Signals / Backtest / Journal / Settings.
 */

import { useRef, useState } from 'react';
import { useAppStore, type ViewTab } from '../store/useAppStore';

const ITEMS: { tab: ViewTab; label: string; icon: JSX.Element }[] = [
  {
    tab: 'CONSTELLATION',
    label: 'Constellation',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"><circle cx="12" cy="12" r="2.4" /><circle cx="4" cy="6" r="1.6" /><circle cx="20" cy="7" r="1.6" /><circle cx="6" cy="19" r="1.6" /><circle cx="19" cy="18" r="1.6" /><path d="M6 7l4.5 3.5M18 8l-4.5 2.8M7 17.5l3.6-3.6M17 17l-3.3-3.2" /></svg>
    ),
  },
  {
    tab: 'CHART',
    label: 'Chart',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"><path d="M4 19h16M7 16V8M12 16V5M17 16v-6" /><path d="M5 9l4-4 4 4 6-6" strokeLinecap="round" strokeLinejoin="round" /></svg>
    ),
  },
  {
    tab: 'SIGNALS',
    label: 'Signals',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"><circle cx="12" cy="12" r="2" /><path d="M8.5 8.5a5 5 0 0 0 0 7M15.5 8.5a5 5 0 0 1 0 7M5.6 5.6a9.5 9.5 0 0 0 0 12.8M18.4 5.6a9.5 9.5 0 0 1 0 12.8" strokeLinecap="round" /></svg>
    ),
  },
  {
    tab: 'BACKTEST',
    label: 'Backtest',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"><path d="M3 17l6-6 4 4 8-9" strokeLinecap="round" strokeLinejoin="round" /><path d="M3 21h18" strokeLinecap="round" opacity="0.5" /></svg>
    ),
  },
  {
    tab: 'JOURNAL',
    label: 'Journal',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"><path d="M6 3h12v18l-3-2-3 2-3-2-3 2V3z" strokeLinejoin="round" /><path d="M9.5 8h5M9.5 12h5" strokeLinecap="round" /></svg>
    ),
  },
  {
    tab: 'SETTINGS',
    label: 'Settings',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"><circle cx="12" cy="12" r="3.2" /><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M19.1 4.9L17 7M7 17l-2.1 2.1" strokeLinecap="round" /></svg>
    ),
  },
];

export default function CommandDock() {
  const activeTab = useAppStore((s) => s.activeTab);
  const setActiveTab = useAppStore((s) => s.setActiveTab);
  const ref = useRef<HTMLDivElement>(null);
  const [mouseX, setMouseX] = useState<number | null>(null);

  return (
    <div className="pointer-events-none absolute bottom-6 left-0 right-0 z-40 flex justify-center">
      <div
        ref={ref}
        onMouseMove={(e) => setMouseX(e.clientX)}
        onMouseLeave={() => setMouseX(null)}
        className="pointer-events-auto flex items-end gap-2 rounded-2xl border border-white/10 bg-black/55 px-4 py-2 shadow-[0_18px_50px_rgba(0,0,0,0.6)] backdrop-blur-xl"
      >
        {ITEMS.map((item) => {
          // macOS magnification: scale icon by distance to cursor
          let mag = 1;
          const btn = document.getElementById(`dock-${item.tab}`);
          if (mouseX !== null && btn) {
            const rect = btn.getBoundingClientRect();
            const center = rect.left + rect.width / 2;
            const dist = Math.abs(mouseX - center);
            mag = Math.max(1, 1.65 - dist / 140);
          }
          const active = activeTab === item.tab;
          return (
            <button
              key={item.tab}
              id={`dock-${item.tab}`}
              data-cursor={item.label}
              onClick={() => setActiveTab(item.tab)}
              aria-label={item.label}
              className="group relative flex w-14 flex-col items-center justify-end pb-1 pt-1 transition-transform"
              style={{ transform: `scale(${mag}) translateY(${active ? -6 : 0}px)`, transformOrigin: 'bottom center', transition: 'transform 120ms ease-out' }}
            >
              <span
                className={`flex h-12 w-12 items-center justify-center rounded-xl border transition-all duration-200 ${
                  active
                    ? 'border-cyan-400/60 bg-cyan-400/10 text-cyan-300 shadow-neon'
                    : 'border-white/10 bg-white/5 text-slate-300 group-hover:border-violet-400/50 group-hover:text-violet-300'
                }`}
              >
                <span className="h-6 w-6">{item.icon}</span>
              </span>
              <span className={`mt-1 text-[8px] font-semibold uppercase tracking-widest transition-opacity ${active ? 'text-cyan-300 opacity-100' : 'text-slate-500 opacity-0 group-hover:opacity-100'}`}>
                {item.label}
              </span>
              {active && <span className="absolute -bottom-1 h-1 w-6 rounded-full bg-cyan-400 shadow-neon" />}
            </button>
          );
        })}
      </div>
    </div>
  );
}