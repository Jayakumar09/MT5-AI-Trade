export default function Footer() {
  return (
    <footer className="pointer-events-none absolute bottom-1 left-0 right-0 z-40 flex items-center justify-between px-4 text-[10px] uppercase tracking-[0.18em] text-slate-500">
      <span className="hidden sm:block">QUANT PILOT — by JAYAKUMAR.ai</span>
      <span className="mx-auto text-center text-[9px] text-slate-600">
        Educational use only. Not financial advice. Trading involves risk of loss.
      </span>
      <span className="hidden sm:block">v1.0.0 · XAUUSD / BTCUSD</span>
    </footer>
  );
}