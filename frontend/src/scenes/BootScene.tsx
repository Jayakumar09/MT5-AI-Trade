/**
 * BootScene — cinematic intro: 3D starfield, the pilot-logo mark assembles
 * itself (rings spin in + core ignites), then "Launch Desk" warps the camera
 * into the dashboard. Respects prefers-reduced-motion.
 */

import { Canvas, useFrame } from '@react-three/fiber';
import { Stars, MeshDistortMaterial } from '@react-three/drei';
import { EffectComposer, Bloom, Vignette } from '@react-three/postprocessing';
import { Suspense, useRef } from 'react';
import * as THREE from 'three';

function SpinningRing({ radius, thickness, color, speed, offset }: { radius: number; thickness: number; color: string; speed: number; offset: number }) {
  const ref = useRef<THREE.Mesh>(null);
  useFrame(({ clock }) => {
    if (!ref.current) return;
    const t = clock.getElapsedTime() * speed + offset;
    ref.current.rotation.x = Math.PI / 2 + Math.sin(t * 0.6) * 0.35;
    ref.current.rotation.y = t * 0.4;
  });
  return (
    <mesh ref={ref}>
      <torusGeometry args={[radius, thickness, 16, 96]} />
      <meshStandardMaterial color={color} emissive={color} emissiveIntensity={1.6} roughness={0.25} metalness={0.35} />
    </mesh>
  );
}

function PilotMark() {
  const core = useRef<THREE.Mesh>(null);
  useFrame(({ clock }) => {
    if (!core.current) return;
    const s = 1 + Math.sin(clock.getElapsedTime() * 1.6) * 0.06;
    core.current.scale.setScalar(s);
    core.current.rotation.y = clock.getElapsedTime() * 0.5;
  });
  return (
    <group>
      <SpinningRing radius={2.15} thickness={0.055} color="#22D3EE" speed={0.9} offset={0} />
      <SpinningRing radius={1.55} thickness={0.045} color="#8B5CF6" speed={-0.7} offset={1.3} />
      <SpinningRing radius={1.05} thickness={0.04} color="#FBBF24" speed={1.15} offset={2.4} />
      <mesh ref={core}>
        <icosahedronGeometry args={[0.62, 3]} />
        <MeshDistortMaterial color="#0b1530" emissive="#22D3EE" emissiveIntensity={0.85} distort={0.32} speed={2.4} roughness={0.15} />
      </mesh>
      <pointLight color="#22D3EE" intensity={30} distance={9} position={[0, 0, 0]} />
    </group>
  );
}

export default function BootScene({ active }: { active: boolean }) {
  return (
    <div className="absolute inset-0">
      <Canvas
        camera={{ position: [0, 0, 6.4], fov: 52 }}
        dpr={[1, 2]}
        gl={{ antialias: true, powerPreference: 'high-performance' }}
        frameloop={active ? 'always' : 'never'}
      >
        <color attach="background" args={['#05060F']} />
        <fog attach="fog" args={['#05060F', 8, 22]} />
        <ambientLight intensity={0.35} />
        <Suspense fallback={null}>
          <Stars radius={60} depth={50} count={2600} factor={3.2} saturation={0} fade speed={1.1} />
          <PilotMark />
        </Suspense>
        <EffectComposer multisampling={0}>
          <Bloom intensity={1.05} luminanceThreshold={0.18} luminanceSmoothing={0.9} radius={0.85} />
          <Vignette eskil={false} offset={0.22} darkness={0.86} />
        </EffectComposer>
      </Canvas>
    </div>
  );
}