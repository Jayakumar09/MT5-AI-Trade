/**
 * Custom cursor: glowing dot + trailing ring that grows on hover with a
 * contextual label ("Inspect", "Close trade"), soft particle trail, and a
 * cursor-following spotlight glow. Respects prefers-reduced-motion.
 */

import { useEffect, useRef, useState } from 'react';

interface TrailDot { id: number; x: number; y: number; life: number }

export default function Cursor() {
  const dotRef = useRef<HTMLDivElement>(null);
  const ringRef = useRef<HTMLDivElement>(null);
  const glowRef = useRef<HTMLDivElement>(null);
  const [label, setLabel] = useState<string | null>(null);
  const [hovering, setHovering] = useState(false);
  const [trail, setTrail] = useState<TrailDot[]>([]);
  const pos = useRef({ x: -100, y: -100 });
  const ring = useRef({ x: -100, y: -100 });
  const reduced = typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  useEffect(() => {
    if (reduced) return;
    let raf = 0;
    let lastTrail = 0;
    let trailId = 0;

    const onMove = (e: MouseEvent) => {
      pos.current = { x: e.clientX, y: e.clientY };
      const target = e.target as HTMLElement | null;
      const hoverEl = target?.closest?.('[data-cursor]') as HTMLElement | null;
      setHovering(!!hoverEl);
      setLabel(hoverEl?.dataset.cursor ?? null);
      const now = performance.now();
      if (now - lastTrail > 28) {
        lastTrail = now;
        setTrail((t) => [...t.slice(-14), { id: trailId++, x: e.clientX, y: e.clientY, life: 1 }]);
      }
    };

    const tick = () => {
      ring.current.x += (pos.current.x - ring.current.x) * 0.16;
      ring.current.y += (pos.current.y - ring.current.y) * 0.16;
      if (dotRef.current) dotRef.current.style.transform = `translate3d(${pos.current.x}px, ${pos.current.y}px, 0) translate(-50%, -50%)`;
      if (ringRef.current) {
        const size = hovering ? 46 : 26;
        ringRef.current.style.width = `${size}px`;
        ringRef.current.style.height = `${size}px`;
        ringRef.current.style.transform = `translate3d(${ring.current.x}px, ${ring.current.y}px, 0) translate(-50%, -50%)`;
      }
      if (glowRef.current) glowRef.current.style.transform = `translate3d(${pos.current.x}px, ${pos.current.y}px, 0) translate(-50%, -50%)`;
      setTrail((t) => t.map((d) => ({ ...d, life: d.life - 0.05 })).filter((d) => d.life > 0));
      raf = requestAnimationFrame(tick);
    };

    window.addEventListener('mousemove', onMove);
    raf = requestAnimationFrame(tick);
    return () => {
      window.removeEventListener('mousemove', onMove);
      cancelAnimationFrame(raf);
    };
  }, [reduced, hovering]);

  if (reduced) return null;

  return (
    <>
      {/* particle trail */}
      {trail.map((d) => (
        <div
          key={d.id}
          className="pointer-events-none fixed z-[9998] h-1.5 w-1.5 rounded-full"
          style={{ left: d.x, top: d.y, opacity: d.life * 0.7, background: '#22D3EE', filter: 'blur(0.6px)', boxShadow: '0 0 6px #22D3EE' }}
        />
      ))}
      {/* spotlight glow following cursor */}
      <div
        ref={glowRef}
        className="pointer-events-none fixed z-[1] h-64 w-64 rounded-full"
        style={{ background: 'radial-gradient(circle, rgba(139,92,246,0.12) 0%, rgba(34,211,238,0.05) 40%, transparent 70%)' }}
      />
      {/* trailing ring */}
      <div
        ref={ringRef}
        className="pointer-events-none fixed z-[9999] flex items-center justify-center rounded-full border transition-[width,height] duration-150"
        style={{ borderColor: hovering ? '#FBBF24' : 'rgba(34,211,238,0.75)', boxShadow: hovering ? '0 0 18px rgba(251,191,36,0.5)' : '0 0 14px rgba(34,211,238,0.4)' }}
      >
        {label && (
          <span className="absolute top-full mt-2 whitespace-nowrap rounded border border-amber-400/40 bg-black/80 px-2 py-0.5 font-mono text-[9px] uppercase tracking-[0.2em] text-amber-300">
            {label}
          </span>
        )}
      </div>
      {/* dot */}
      <div ref={dotRef} className="pointer-events-none fixed z-[9999] h-2.5 w-2.5 rounded-full" style={{ background: '#22D3EE', boxShadow: '0 0 10px #22D3EE, 0 0 26px rgba(34,211,238,0.6)' }} />
    </>
  );
}