/**
 * ConstellationScene — hero view. Seven glowing agent orbs float in R3F,
 * linked by animated light beams (Scout → Cartographer → Hunter → Analyst →
 * Guardian → Executioner → Chronicler). The active agent glows; a vetoed
 * agent flashes rose. Click an orb to select it (camera flight handled by
 * OrbitControls re-target + panel open). Auto-rotates when idle.
 */

import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Html, Line } from '@react-three/drei';
import { EffectComposer, Bloom, Vignette } from '@react-three/postprocessing';
import { Suspense, useMemo, useRef } from 'react';
import * as THREE from 'three';
import { useAppStore, type AgentName } from '../store/useAppStore';

const AGENT_ORDER: AgentName[] = ['SCOUT', 'CARTOGRAPHER', 'HUNTER', 'ANALYST', 'GUARDIAN', 'EXECUTIONER', 'CHRONICLER'];

const ORB_POSITIONS: Record<AgentName, [number, number, number]> = {
  SCOUT: [-4.6, 1.5, 2.2],
  CARTOGRAPHER: [-3.1, 3.0, -1.2],
  HUNTER: [-1.6, -2.3, 1.6],
  ANALYST: [0.4, 1.9, -2.4],
  GUARDIAN: [2.2, -0.8, 2.4],
  EXECUTIONER: [4.0, 1.7, -1.6],
  CHRONICLER: [5.6, -1.9, 0.6],
};

const AGENT_COLORS: Record<AgentName, string> = {
  SCOUT: '#22D3EE',
  CARTOGRAPHER: '#38BDF8',
  HUNTER: '#34D399',
  ANALYST: '#8B5CF6',
  GUARDIAN: '#FBBF24',
  EXECUTIONER: '#FB7185',
  CHRONICLER: '#A78BFA',
};

const AGENT_ROLES: Record<AgentName, string> = {
  SCOUT: 'DATA',
  CARTOGRAPHER: 'LIQUIDITY MAP',
  HUNTER: 'SWEEP DETECTOR',
  ANALYST: 'CLAUDE LLM',
  GUARDIAN: 'RISK GUARDIAN',
  EXECUTIONER: 'ORDER BRIDGE',
  CHRONICLER: 'JOURNAL',
};

function Orb({ name, position }: { name: AgentName; position: [number, number, number] }) {
  const ref = useRef<THREE.Mesh>(null);
  const lightRef = useRef<THREE.PointLight>(null);
  const status = useAppStore((s) => s.agents[name].status);
  const confidence = useAppStore((s) => s.agents[name].confidence);
  const activeAgent = useAppStore((s) => s.activeAgent);
  const setActiveAgent = useAppStore((s) => s.setActiveAgent);
  const color = AGENT_COLORS[name];
  const isSelected = activeAgent === name;
  const vetoed = status === 'VETOED';
  const active = status === 'CANDIDATE' || status === 'APPROVED' || status === 'EXECUTED' || status === 'OK';

  useFrame(({ clock }) => {
    if (!ref.current) return;
    const t = clock.getElapsedTime();
    const bob = Math.sin(t * 1.1 + position[0]) * 0.14;
    ref.current.position.y = position[1] + bob;
    const targetScale = isSelected ? 1.5 : active ? 1.18 + Math.sin(t * 2.4) * 0.05 : 1.0;
    ref.current.scale.setScalar(THREE.MathUtils.lerp(ref.current.scale.x, targetScale, 0.12));
    if (lightRef.current) lightRef.current.intensity = isSelected ? 26 : active ? 16 : 9;
  });

  return (
    <group position={[position[0], position[1], position[2]]}>
      <pointLight ref={lightRef} color={vetoed ? '#FB7185' : color} intensity={10} distance={7} />
      <mesh
        ref={ref}
        onClick={(e) => {
          e.stopPropagation();
          setActiveAgent(isSelected ? null : name);
        }}
      >
        <sphereGeometry args={[0.62, 32, 32]} />
        <meshStandardMaterial
          color={vetoed ? '#3b0a12' : '#0a0f22'}
          emissive={vetoed ? '#FB7185' : color}
          emissiveIntensity={vetoed ? 2.4 : isSelected ? 1.9 : 1.15}
          roughness={0.18}
          metalness={0.6}
        />
      </mesh>
      <Html position={[0, 1.25, 0]} center distanceFactor={9} style={{ pointerEvents: 'auto' }}>
        <button
          onClick={() => setActiveAgent(isSelected ? null : name)}
          className="whitespace-nowrap rounded-md border px-2 py-0.5 font-mono text-[10px] tracking-widest backdrop-blur-md transition-all"
          style={{
            borderColor: vetoed ? '#FB7185' : color,
            color: vetoed ? '#FB7185' : color,
            background: 'rgba(5,6,15,0.72)',
            boxShadow: `0 0 12px ${vetoed ? '#FB7185' : color}44`,
          }}
        >
          {name} <span className="opacity-70">{Math.round(confidence * 100)}%</span>
        </button>
      </Html>
    </group>
  );
}

function Beam({ from, to, index }: { from: [number, number, number]; to: [number, number, number]; index: number }) {
  const ref = useRef<any>(null);
  useFrame(({ clock }) => {
    if (ref.current?.material) {
      ref.current.material.opacity = 0.35 + 0.45 * (0.5 + 0.5 * Math.sin(clock.getElapsedTime() * 2.2 + index * 0.9));
    }
  });
  const points = useMemo(() => [new THREE.Vector3(...from), new THREE.Vector3(...to)], [from, to]);
  return <Line ref={ref} points={points} color="#67E8F9" lineWidth={2.2} transparent opacity={0.5} />;
}

export default function ConstellationScene({ interactive = true }: { interactive?: boolean }) {
  const beamPairs = useMemo(
    () => AGENT_ORDER.slice(0, -1).map((a, i) => [ORB_POSITIONS[a], ORB_POSITIONS[AGENT_ORDER[i + 1]]] as const),
    [],
  );

  return (
    <Canvas
      camera={{ position: [0.4, 0.8, 11.5], fov: 55 }}
      dpr={[1, 1.6]}
      gl={{ antialias: true, powerPreference: 'high-performance', alpha: true }}
    >
      <Suspense fallback={null}>
        <ambientLight intensity={0.4} />
        <directionalLight position={[5, 8, 6]} intensity={0.7} />
        {beamPairs.map(([from, to], i) => (
          <Beam key={i} from={[from[0], from[1], from[2]]} to={[to[0], to[1], to[2]]} index={i} />
        ))}
        {AGENT_ORDER.map((name) => (
          <Orb key={name} name={name} position={ORB_POSITIONS[name]} />
        ))}
        {interactive && <OrbitControls makeDefault autoRotate autoRotateSpeed={0.55} enablePan={false} minDistance={6} maxDistance={18} />}
      </Suspense>
      <EffectComposer multisampling={0}>
        <Bloom intensity={1.15} luminanceThreshold={0.12} luminanceSmoothing={0.85} radius={0.8} />
        <Vignette eskil={false} offset={0.2} darkness={0.7} />
      </EffectComposer>
    </Canvas>
  );
}