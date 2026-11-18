/**
 * ChartPanel — TradingView Lightweight Charts with candlesticks + volume,
 * instrument switcher (XAUUSD / BTCUSD), timeframe switch (5M / 15M / 4H / 1D).
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import { createChart, type IChartApi, type ISeriesApi, type UTCTimestamp, type SeriesMarker } from 'lightweight-charts';
import { apiGet } from '../api/client';

const SYMBOL_COLORS: Record<string, string> = { XAUUSD: '#FBBF24', BTCUSD: '#8B5CF6' };

export default function ChartPanel() {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volumeRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  const [symbol, setSymbol] = useState<'XAUUSD' | 'BTCUSD'>('XAUUSD');
  const [tf, setTf] = useState<'5m' | '15m' | '4h' | '1d'>('5m');
  const [loading, setLoading] = useState(true);
  const accent = SYMBOL_COLORS[symbol];

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      layout: { background: { color: 'transparent' }, textColor: '#94A3B8', fontFamily: 'JetBrains Mono' },
      grid: { vertLines: { color: 'rgba(120,160,255,0.06)' }, horzLines: { color: 'rgba(120,160,255,0.06)' } },
      crosshair: { mode: 0 },
      rightPriceScale: { borderColor: 'rgba(120,160,255,0.15)' },
      timeScale: { borderColor: 'rgba(120,160,255,0.15)', timeVisible: true, secondsVisible: false },
      width: containerRef.current.clientWidth,
      height: containerRef.current.clientHeight,
    });
    chartRef.current = chart;

    const candles = chart.addCandlestickSeries({
      upColor: '#34D399', downColor: '#FB7185', wickUpColor: '#34D399', wickDownColor: '#FB7185',
      borderUpColor: '#34D399', borderDownColor: '#FB7185',
    });
    candleRef.current = candles;
    const volume = chart.addHistogramSeries({ priceScaleId: '', color: 'rgba(139,92,246,0.5)', priceFormat: { type: 'volume' } });
    volume.priceScale().applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
    volumeRef.current = volume;

    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        chart.applyOptions({ width: entry.contentRect.width, height: entry.contentRect.height });
      }
    });
    ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    apiGet(`/api/candles/${symbol}?interval=${tf}&limit=220`, { candles: [] as any[] }).then((data) => {
      if (cancelled || !chartRef.current || !candleRef.current || !volumeRef.current) return;
      const raw = (data?.candles ?? []) as { ts: string; open: number; high: number; low: number; close: number; volume: number }[];
      const seen = new Set<number>();
      const rows = raw
        .map((c) => ({ time: Math.floor(new Date(c.ts).getTime() / 1000) as UTCTimestamp, open: c.open, high: c.high, low: c.low, close: c.close, volume: c.volume }))
        .filter((r) => Number.isFinite(r.time) && !seen.has(r.time) && seen.add(r.time))
        .sort((a, b) => (a.time as number) - (b.time as number));
      candleRef.current.setData(rows.map(({ time, open, high, low, close }) => ({ time, open, high, low, close })));
      volumeRef.current.setData(rows.map(({ time, volume, close, open }) => ({
        time, value: volume, color: close >= open ? 'rgba(52,211,153,0.45)' : 'rgba(251,113,133,0.45)',
      })));
      // markers on the final two candles to visualize the demo sweep
      const last = rows[rows.length - 1];
      const prev = rows[rows.length - 2];
      if (last && prev) {
        const markers: SeriesMarker<UTCTimestamp>[] = [
          { time: prev.time, position: 'belowBar', color: '#FBBF24', shape: 'arrowUp', text: 'sweep' },
          { time: last.time, position: 'belowBar', color: '#34D399', shape: 'arrowUp', text: 'displacement LONG' },
        ];
        candleRef.current.setMarkers(markers);
      }
      chartRef.current.timeScale().fitContent();
      setLoading(false);
    });
    return () => { cancelled = true; };
  }, [symbol, tf]);

  return (
    <section className="glass flex h-full min-h-[420px] flex-col p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full" style={{ background: accent, boxShadow: `0 0 10px ${accent}` }} />
          <h2 className="font-display text-sm font-semibold tracking-wide text-slate-100">{symbol} <span className="text-slate-500">· Liquidity Sweep</span></h2>
        </div>
        <div className="flex items-center gap-1.5">
          {(['XAUUSD', 'BTCUSD'] as const).map((s) => (
            <button
              key={s}
              data-cursor="Switch symbol"
              onClick={() => setSymbol(s)}
              className={`rounded-md border px-2 py-1 font-mono text-[10px] uppercase tracking-widest transition ${symbol === s ? 'border-amber-400/50 text-amber-300' : 'border-white/10 text-slate-500 hover:text-slate-300'}`}
            >
              {s === 'XAUUSD' ? 'Gold' : 'BTC'}
            </button>
          ))}
          <span className="mx-1 h-4 w-px bg-white/10" />
          {(['5m', '15m', '4h', '1d'] as const).map((t) => (
            <button
              key={t}
              data-cursor="Timeframe"
              onClick={() => setTf(t)}
              className={`rounded-md border px-2 py-1 font-mono text-[10px] uppercase tracking-widest transition ${tf === t ? 'border-cyan-400/50 text-cyan-300' : 'border-white/10 text-slate-500 hover:text-slate-300'}`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>
      <div className="relative min-h-0 flex-1">
        <div ref={containerRef} className="absolute inset-0" />
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-[#05060F]/40 backdrop-blur-[2px]">
            <div className="shimmer h-24 w-48 rounded-lg border border-white/10" />
          </div>
        )}
      </div>
      <div className="mt-1 flex items-center justify-between font-mono text-[9px] uppercase tracking-[0.2em] text-slate-600">
        <span>Sweep markers: amber = wick pierce · emerald = displacement</span>
        <span className="text-amber-500/80">paused at candle close — demo replay</span>
      </div>
    </section>
  );
}