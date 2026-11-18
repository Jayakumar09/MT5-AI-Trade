/**
 * SettingsPanel — editable AEGIS guardrails + strategy sliders, tooltips on
 * hover, and the MT5 connection card with a typed-confirmation live-mode toggle
 * and a minimum-lot test order against a connected demo terminal.
 */

import { useEffect, useState } from 'react';
import { apiGet, apiPost } from '../api/client';
import { useAppStore } from '../store/useAppStore';

function RuleField({ label, tooltip, value, min, max, step, suffix, onChange }: {
  label: string; tooltip: string; value: number; min: number; max: number; step: number; suffix: string; onChange: (v: number) => void;
}) {
  const [tip, setTip] = useState(false);
  return (
    <label className="relative block rounded-lg border border-white/10 bg-white/[0.03] p-2.5">
      <div className="flex items-center justify-between gap-2">
        <span className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.18em] text-slate-400">
          {label}
          <button type="button" aria-label="What is this?" onMouseEnter={() => setTip(true)} onMouseLeave={() => setTip(false)} onFocus={() => setTip(true)} onBlur={() => setTip(false)} className="flex h-4 w-4 items-center justify-center rounded-full border border-white/20 text-[8px] text-slate-500">i</button>
        </span>
        <span className="font-mono text-[11px] text-cyan-300">{value}{suffix}</span>
      </div>
      <input type="range" min={min} max={max} step={step} value={value} onChange={(e) => onChange(Number(e.target.value))} className="mt-2 w-full accent-violet-500" aria-label={label} />
      {tip && <div role="tooltip" className="absolute left-0 top-full z-20 mt-1 w-64 rounded-lg border border-violet-400/30 bg-[#0a0f22]/95 p-2 text-[10px] leading-snug text-violet-100/90 shadow-violet">{tooltip}</div>}
    </label>
  );
}

export default function SettingsPanel() {
  const mt5Status = useAppStore((s) => s.mt5Status);
  const setMt5Status = useAppStore((s) => s.setMt5Status);
  const pushToast = useAppStore((s) => s.pushToast);
  const mode = useAppStore((s) => s.mode);
  const [rules, setRules] = useState({
    minConfidence: 7, maxDailyDrawdown: 4, riskPerTrade: 1, spreadLimitXau: 35, maxOpenTrades: 5, minRR: 2,
  });
  const [livePhrase, setLivePhrase] = useState('');
  const [liveEnabled, setLiveEnabled] = useState(false);
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    apiGet('/api/mt5/status', null).then((s) => s && setMt5Status(s));
  }, [setMt5Status]);

  const saveToast = (label: string) => pushToast({ title: 'Saved', body: `${label} applied to AEGIS guardrails.`, tone: 'violet' });

  const testOrder = async () => {
    setTesting(true);
    const res = await apiPost('/api/mt5/test-order', {}, { ok: false, message: 'No connection' });
    pushToast({ title: res?.ok ? 'Test order routed' : 'Test order unavailable', body: res?.message ?? '', tone: res?.ok ? 'emerald' : 'amber' });
    setTesting(false);
  };

  const enableLive = () => {
    if (livePhrase.trim().toUpperCase() === 'I ACCEPT THE RISK') {
      setLiveEnabled(true);
      pushToast({ title: 'Live mode armed', body: 'Settings accepted — remember: paper remains the safest default.', tone: 'rose' });
    } else {
      pushToast({ title: 'Phrase mismatch', body: 'Type exactly: I ACCEPT THE RISK', tone: 'amber' });
    }
  };

  return (
    <section className="glass flex h-full flex-col gap-3 overflow-y-auto p-4">
      <h2 className="font-mono text-[10px] uppercase tracking-[0.3em] text-slate-500">Guardrails & Settings</h2>

      {/* AEGIS rules */}
      <div>
        <div className="mb-1.5 font-mono text-[9px] uppercase tracking-[0.25em] text-amber-300">AEGIS hard-coded vetoes</div>
        <div className="grid grid-cols-2 gap-2">
          <RuleField label="Spread limit XAU" tooltip="Max allowed spread in points before a new order is rejected outright. Gold rarely trades above ~30 pts in normal conditions." value={rules.spreadLimitXau} min={10} max={80} step={1} suffix=" pts" onChange={(v) => { setRules({ ...rules, spreadLimitXau: v }); saveToast('Spread limit'); }} />
          <RuleField label="Risk / trade" tooltip="Default fraction of equity risked per trade. AEGIS caps this at 2% no matter what the strategy asks." value={rules.riskPerTrade} min={0.25} max={2} step={0.25} suffix="%" onChange={(v) => { setRules({ ...rules, riskPerTrade: v }); saveToast('Risk per trade'); }} />
          <RuleField label="Daily DD kill" tooltip="If daily drawdown exceeds this level, all new orders are halted and a kill-switch event fires." value={rules.maxDailyDrawdown} min={2} max={10} step={0.5} suffix="%" onChange={(v) => { setRules({ ...rules, maxDailyDrawdown: v }); saveToast('Daily drawdown kill'); }} />
          <RuleField label="Max open trades" tooltip="Maximum concurrent positions. Prevents stacking correlated sweeps on the same level." value={rules.maxOpenTrades} min={1} max={10} step={1} suffix="" onChange={(v) => { setRules({ ...rules, maxOpenTrades: v }); saveToast('Max open trades'); }} />
          <RuleField label="Min RR" tooltip="Minimum risk-reward ratio (entry→TP1 vs entry→SL). Below 1:2 the Guardian vetoes the trade." value={rules.minRR} min={1} max={4} step={0.5} suffix=":1" onChange={(v) => { setRules({ ...rules, minRR: v }); saveToast('Min RR'); }} />
          <RuleField label="Min confidence" tooltip="Analyst confidence floor (1–10). Below this value AEGIS refuses to arm the Executioner." value={rules.minConfidence} min={5} max={10} step={0.5} suffix=" /10" onChange={(v) => { setRules({ ...rules, minConfidence: v }); saveToast('Min confidence'); }} />
        </div>
      </div>

      {/* MT5 connection card */}
      <div className="rounded-xl border border-amber-400/25 bg-amber-950/10 p-3">
        <div className="flex items-center justify-between">
          <div className="font-mono text-[9px] uppercase tracking-[0.25em] text-amber-300">MetaTrader 5 bridge</div>
          <span className={`rounded-full border px-2 py-0.5 font-mono text-[9px] uppercase ${mt5Status?.connected ? 'border-emerald-400/50 text-emerald-300' : 'border-slate-600 text-slate-500'}`}>
            {mt5Status?.connected ? `connected · ${mt5Status.account_mode}` : 'demo only'}
          </span>
        </div>
        <p className="mt-1.5 text-[10px] leading-snug text-slate-500">Windows-only terminal. Set ENABLE_MT5=true in .env, keep MT5_MODE=demo_only until you are ready; Demo stays the default.</p>
        <button onClick={testOrder} disabled={testing} data-cursor="Test order" className="mt-2 rounded-md border border-amber-400/40 bg-amber-500/10 px-3 py-1.5 font-mono text-[9px] uppercase tracking-widest text-amber-300 hover:bg-amber-500/20 disabled:opacity-50">
          {testing ? 'Routing…' : 'Minimum-lot test order'}
        </button>
      </div>

      {/* Live mode confirmation */}
      <div className="rounded-xl border border-rose-500/30 bg-rose-950/15 p-3">
        <div className="font-mono text-[9px] uppercase tracking-[0.25em] text-rose-300">Live mode (danger)</div>
        <p className="mt-1 text-[10px] leading-snug text-rose-200/70">Paper trading is the default. Live requires an explicit toggle <em>and</em> a typed confirmation phrase. The Guardian still gets the final veto.</p>
        <div className="mt-2 flex gap-2">
          <input value={livePhrase} onChange={(e) => { setLivePhrase(e.target.value); setLiveEnabled(false); }} placeholder="Type: I ACCEPT THE RISK" aria-label="Live mode confirmation phrase" className="w-full rounded-md border border-rose-500/30 bg-black/50 px-2 py-1.5 font-mono text-[10px] uppercase tracking-widest text-rose-200 placeholder-rose-900 outline-none focus:border-rose-400/60" />
          <button onClick={enableLive} data-cursor="Arm live" className="rounded-md border border-rose-500/60 bg-rose-600/20 px-3 py-1.5 font-mono text-[9px] font-bold uppercase tracking-widest text-rose-200 hover:bg-rose-600/30">Arm</button>
        </div>
        {liveEnabled && <p className="mt-1 font-mono text-[9px] uppercase tracking-widest text-rose-300">Live armed — Guardian still holds the final gate.</p>}
        <p className="mt-1 text-[9px] text-slate-600">Current app mode: <span className="text-slate-400">{mode}</span></p>
      </div>

      <p className="text-[9px] text-slate-600">No guaranteed profits. Educational use only — not financial advice. Trading involves risk of loss.</p>
    </section>
  );
}