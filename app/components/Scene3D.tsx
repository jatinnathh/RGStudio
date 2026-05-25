'use client';

import { useRef, useMemo, useEffect } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { EffectComposer, Bloom, Vignette } from '@react-three/postprocessing';
import * as THREE from 'three';

/* ──────────────────── Constants ──────────────────── */
const PARTICLE_COUNT = 16000;
const COLOR_CYAN = new THREE.Color('#00e5ff');
const COLOR_VIOLET = new THREE.Color('#8b5cf6');
const COLOR_MAGENTA = new THREE.Color('#d946ef');

/* ──────────────────── Shape Generators ──────────────────── */
function generateTorusKnot(count: number): Float32Array {
  const pos = new Float32Array(count * 3);
  for (let i = 0; i < count; i++) {
    const t = (i / count) * Math.PI * 4;
    const p = 2, q = 3;
    const r = 2 + 0.8 * Math.cos(q * t);
    const jitter = 0.15;
    pos[i * 3]     = r * Math.cos(p * t) + (Math.random() - 0.5) * jitter;
    pos[i * 3 + 1] = r * Math.sin(p * t) + (Math.random() - 0.5) * jitter;
    pos[i * 3 + 2] = 0.8 * Math.sin(q * t) + (Math.random() - 0.5) * jitter;
  }
  return pos;
}

function generateSphere(count: number): Float32Array {
  const pos = new Float32Array(count * 3);
  for (let i = 0; i < count; i++) {
    const phi = Math.acos(2 * Math.random() - 1);
    const theta = Math.random() * Math.PI * 2;
    const r = 1.8 + Math.random() * 0.6;
    pos[i * 3]     = r * Math.sin(phi) * Math.cos(theta);
    pos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
    pos[i * 3 + 2] = r * Math.cos(phi);
  }
  return pos;
}

function generateScatter(count: number): Float32Array {
  const pos = new Float32Array(count * 3);
  for (let i = 0; i < count; i++) {
    const phi = Math.acos(2 * Math.random() - 1);
    const theta = Math.random() * Math.PI * 2;
    const r = 2.5 + Math.random() * 5;
    pos[i * 3]     = r * Math.sin(phi) * Math.cos(theta);
    pos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
    pos[i * 3 + 2] = r * Math.cos(phi);
  }
  return pos;
}

/* ──────────────────── Shaders ──────────────────── */
const vertexShader = /* glsl */ `
  uniform float uTime;
  uniform float uProgress;
  uniform float uSize;

  attribute vec3 aPos1;
  attribute vec3 aPos2;
  attribute vec3 aPos3;
  attribute float aRandom;

  varying float vAlpha;
  varying vec3 vColor;

  void main() {
    // Morph between shapes
    vec3 pos;
    if (uProgress < 0.4) {
      float t = smoothstep(0.0, 0.4, uProgress);
      pos = mix(aPos1, aPos2, t);
    } else {
      float t = smoothstep(0.4, 0.85, uProgress);
      pos = mix(aPos2, aPos3, t);
    }

    // Add floating motion
    float floatSpeed = 0.3 + aRandom * 0.4;
    pos.x += sin(uTime * floatSpeed + aRandom * 6.28) * 0.08;
    pos.y += cos(uTime * floatSpeed * 0.7 + aRandom * 4.0) * 0.08;
    pos.z += sin(uTime * floatSpeed * 0.5 + aRandom * 2.0) * 0.05;

    vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);

    // Size with attenuation
    float sizeVariation = 0.5 + aRandom * 1.0;
    gl_PointSize = uSize * sizeVariation * (1.0 / -mvPosition.z);
    gl_Position = projectionMatrix * mvPosition;

    // Color: cyan → violet → magenta based on random + progress
    vec3 cCyan    = vec3(0.0, 0.898, 1.0);
    vec3 cViolet  = vec3(0.545, 0.361, 0.965);
    vec3 cMagenta = vec3(0.851, 0.275, 0.937);
    float colorMix = fract(aRandom * 3.7 + uProgress * 0.5);
    if (colorMix < 0.5) {
      vColor = mix(cCyan, cViolet, colorMix * 2.0);
    } else {
      vColor = mix(cViolet, cMagenta, (colorMix - 0.5) * 2.0);
    }

    // Alpha based on distance
    float dist = length(pos);
    vAlpha = smoothstep(8.0, 1.0, dist) * (0.6 + aRandom * 0.4);
  }
`;

const fragmentShader = /* glsl */ `
  varying float vAlpha;
  varying vec3 vColor;

  void main() {
    float d = length(gl_PointCoord - vec2(0.5));
    if (d > 0.5) discard;

    float strength = 1.0 - d * 2.0;
    strength = pow(strength, 1.8);

    gl_FragColor = vec4(vColor, strength * vAlpha * 0.85);
  }
`;

/* ──────────────────── ParticleVortex ──────────────────── */
function ParticleVortex() {
  const pointsRef = useRef<THREE.Points>(null);
  const materialRef = useRef<THREE.ShaderMaterial>(null);

  const { positions, randoms, pos1, pos2, pos3 } = useMemo(() => {
    const p1 = generateTorusKnot(PARTICLE_COUNT);
    const p2 = generateSphere(PARTICLE_COUNT);
    const p3 = generateScatter(PARTICLE_COUNT);
    const r = new Float32Array(PARTICLE_COUNT);
    for (let i = 0; i < PARTICLE_COUNT; i++) r[i] = Math.random();
    return { positions: p1.slice(), randoms: r, pos1: p1, pos2: p2, pos3: p3 };
  }, []);

  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uProgress: { value: 0 },
      uSize: { value: 4.0 * Math.min(window.devicePixelRatio, 2) },
    }),
    []
  );

  useFrame(({ clock }) => {
    if (!materialRef.current) return;

    const scrollY = window.scrollY || 0;
    const maxScroll = Math.max(
      document.documentElement.scrollHeight - window.innerHeight,
      1
    );
    const progress = Math.min(scrollY / maxScroll, 1);

    materialRef.current.uniforms.uTime.value = clock.getElapsedTime();
    materialRef.current.uniforms.uProgress.value = progress;

    // Slow auto-rotation
    if (pointsRef.current) {
      pointsRef.current.rotation.y += 0.001;
      pointsRef.current.rotation.x = Math.sin(clock.getElapsedTime() * 0.1) * 0.05;
    }
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={PARTICLE_COUNT}
          array={positions}
          itemSize={3}
        />
        <bufferAttribute
          attach="attributes-aPos1"
          count={PARTICLE_COUNT}
          array={pos1}
          itemSize={3}
        />
        <bufferAttribute
          attach="attributes-aPos2"
          count={PARTICLE_COUNT}
          array={pos2}
          itemSize={3}
        />
        <bufferAttribute
          attach="attributes-aPos3"
          count={PARTICLE_COUNT}
          array={pos3}
          itemSize={3}
        />
        <bufferAttribute
          attach="attributes-aRandom"
          count={PARTICLE_COUNT}
          array={randoms}
          itemSize={1}
        />
      </bufferGeometry>
      <shaderMaterial
        ref={materialRef}
        vertexShader={vertexShader}
        fragmentShader={fragmentShader}
        uniforms={uniforms}
        transparent
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}

/* ──────────────────── CameraRig ──────────────────── */
function CameraRig() {
  const { camera } = useThree();
  const targetPos = useRef(new THREE.Vector3(0, 0, 6));
  const targetLookAt = useRef(new THREE.Vector3(0, 0, 0));
  const mouseRef = useRef({ x: 0, y: 0 });

  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      mouseRef.current.x = (e.clientX / window.innerWidth - 0.5) * 2;
      mouseRef.current.y = (e.clientY / window.innerHeight - 0.5) * 2;
    };
    window.addEventListener('mousemove', onMouseMove);
    return () => window.removeEventListener('mousemove', onMouseMove);
  }, []);

  useFrame(() => {
    const scrollY = window.scrollY || 0;
    const maxScroll = Math.max(
      document.documentElement.scrollHeight - window.innerHeight,
      1
    );
    const p = Math.min(scrollY / maxScroll, 1);

    // Camera path: 3 keyframes
    let tx: number, ty: number, tz: number;
    if (p < 0.33) {
      const t = p / 0.33;
      tx = THREE.MathUtils.lerp(0, 3.5, t);
      ty = THREE.MathUtils.lerp(0, 1.2, t);
      tz = THREE.MathUtils.lerp(6, 5, t);
    } else if (p < 0.66) {
      const t = (p - 0.33) / 0.33;
      tx = THREE.MathUtils.lerp(3.5, -1, t);
      ty = THREE.MathUtils.lerp(1.2, 0.5, t);
      tz = THREE.MathUtils.lerp(5, 3.5, t);
    } else {
      const t = (p - 0.66) / 0.34;
      tx = THREE.MathUtils.lerp(-1, 0, t);
      ty = THREE.MathUtils.lerp(0.5, 0, t);
      tz = THREE.MathUtils.lerp(3.5, 2, t);
    }

    // Mouse parallax
    const mx = mouseRef.current.x * 0.3;
    const my = mouseRef.current.y * -0.2;

    targetPos.current.set(tx + mx, ty + my, tz);
    camera.position.lerp(targetPos.current, 0.04);
    
    // Look at center with slight offset
    targetLookAt.current.set(mx * 0.1, my * 0.1, 0);
    camera.lookAt(targetLookAt.current);
  });

  return null;
}

/* ──────────────────── Main Scene ──────────────────── */
export default function Scene3D() {
  return (
    <Canvas
      className="scene-canvas"
      camera={{ position: [0, 0, 6], fov: 50, near: 0.1, far: 100 }}
      dpr={[1, 2]}
      gl={{ antialias: true, alpha: false }}
      onCreated={({ gl }) => {
        gl.setClearColor('#050508');
      }}
    >
      <fog attach="fog" args={['#050508', 5, 20]} />
      <ambientLight intensity={0.15} />
      <pointLight position={[5, 5, 5]} intensity={0.5} color="#00e5ff" />
      <pointLight position={[-5, -3, 3]} intensity={0.3} color="#8b5cf6" />

      <ParticleVortex />
      <CameraRig />

      <EffectComposer>
        <Bloom
          intensity={1.5}
          luminanceThreshold={0.1}
          luminanceSmoothing={0.9}
          mipmapBlur
        />
        <Vignette offset={0.3} darkness={0.7} />
      </EffectComposer>
    </Canvas>
  );
}
