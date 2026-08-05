"use client";

import React, { Suspense, useEffect, useRef, useState } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useGLTF, Html, useProgress } from "@react-three/drei";
import * as THREE from "three";
import Lenis from "lenis";
import HeroText from "./HeroText";
import { PopButton } from "./ui/pop-button";
import { useRouter } from "next/navigation";

function Loader() {
  const { progress } = useProgress();
  return (
    <Html center>
      <div className="flex flex-col items-center justify-center p-5 rounded-2xl bg-black/70 backdrop-blur-md border border-white/10 text-white shadow-2xl min-w-[200px]">
        <div className="w-10 h-10 rounded-full border-2 border-orange-400 border-t-transparent animate-spin mb-3" />
        <p className="text-xs font-semibold tracking-widest text-orange-200">
          LOADING 3D ART ({Math.round(progress)}%)
        </p>
      </div>
    </Html>
  );
}

function FirewatchModel({
  scrollProgress,
}: {
  scrollProgress: React.MutableRefObject<number>;
}) {
  const { scene } = useGLTF("/art.glb");
  const { camera } = useThree();

  const camConfig = useRef<{
    startPos: THREE.Vector3;
    endPos: THREE.Vector3;
    startTarget: THREE.Vector3;
    endTarget: THREE.Vector3;
  } | null>(null);

  const currentCamPos = useRef(new THREE.Vector3());
  const currentTarget = useRef(new THREE.Vector3());

  useEffect(() => {
    if (!scene) return;

    scene.traverse((child) => {
      if ((child as THREE.Mesh).isMesh) {
        const mesh = child as THREE.Mesh;
        if (mesh.material) {
          const mat = mesh.material as THREE.MeshStandardMaterial;
          if (mat.map) {
            mat.map.colorSpace = THREE.SRGBColorSpace;
          }
          mat.roughness = 0.65;
          mat.metalness = 0.05;
        }
      }
    });

    const sceneBox = new THREE.Box3().setFromObject(scene);
    const sceneSize = sceneBox.getSize(new THREE.Vector3());
    const sceneCenter = sceneBox.getCenter(new THREE.Vector3());

    // Find highest mesh point near center (the watchtower top)
    let highestPoint = -Infinity;
    const towerCenter = new THREE.Vector3().copy(sceneCenter);

    scene.traverse((child) => {
      if ((child as THREE.Mesh).isMesh) {
        const box = new THREE.Box3().setFromObject(child);
        const center = box.getCenter(new THREE.Vector3());
        if (
          Math.abs(center.x - sceneCenter.x) < sceneSize.x * 0.35 &&
          box.max.y > highestPoint
        ) {
          highestPoint = box.max.y;
          towerCenter.copy(center);
        }
      }
    });

    const span = Math.max(sceneSize.x, sceneSize.y);

    // Initial Wide Angle View — lower and closer
    const startPos = new THREE.Vector3(
      towerCenter.x,
      towerCenter.y - span * 0.02,
      towerCenter.z + span * 0.23
    );
    const startTarget = new THREE.Vector3(
      towerCenter.x,
      towerCenter.y - span * 0.04,
      towerCenter.z
    );

    // Final Zoomed-In View — at eye level, tight on the tower
    const endPos = new THREE.Vector3(
      towerCenter.x,
      towerCenter.y - span * 0.06,
      towerCenter.z + span * 0.035
    );
    const endTarget = new THREE.Vector3(
      towerCenter.x + span * 0.015, // Look slightly right so tower goes left
      towerCenter.y - span * 0.06,
      towerCenter.z
    );

    camConfig.current = {
      startPos,
      endPos,
      startTarget,
      endTarget,
    };

    camera.position.copy(startPos);
    camera.lookAt(startTarget);
    currentCamPos.current.copy(startPos);
    currentTarget.current.copy(startTarget);
  }, [scene, camera]);

  useFrame((state, delta) => {
    if (!camConfig.current) return;

    const { startPos, endPos, startTarget, endTarget } = camConfig.current;
    const progress = scrollProgress.current; // 0 to 1

    // Smoothstep easing for silky smooth scroll transition
    const p = THREE.MathUtils.smoothstep(progress, 0, 1);

    // Lerp positions between start and end
    const targetPos = new THREE.Vector3().lerpVectors(startPos, endPos, p);
    const targetLookAt = new THREE.Vector3().lerpVectors(
      startTarget,
      endTarget,
      p
    );

    // Subtle mouse parallax
    const mouseX = state.pointer.x * (1 - p * 0.6) * 0.35;
    const mouseY = state.pointer.y * (1 - p * 0.6) * 0.35;
    targetPos.x += mouseX;
    targetPos.y += mouseY;

    // Smooth frame lerp
    const lerpFactor = THREE.MathUtils.clamp(delta * 4.5, 0.02, 0.2);
    currentCamPos.current.lerp(targetPos, lerpFactor);
    currentTarget.current.lerp(targetLookAt, lerpFactor);

    camera.position.copy(currentCamPos.current);
    camera.lookAt(currentTarget.current);
  });

  return <primitive object={scene} />;
}

export default function ArtCanvas() {
  const [mounted, setMounted] = useState(false);
  const scrollProgress = useRef(0);
  const router = useRouter();

  useEffect(() => {
    requestAnimationFrame(() => {
      setMounted(true);
    });

    const lenis = new Lenis({
      duration: 1.2,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      smoothWheel: true,
    });

    function onScroll() {
      const scrollHeight =
        document.documentElement.scrollHeight - window.innerHeight;
      if (scrollHeight > 0) {
        scrollProgress.current = Math.min(
          1,
          Math.max(0, window.scrollY / scrollHeight)
        );
      }
    }

    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();

    function raf(time: number) {
      lenis.raf(time);
      requestAnimationFrame(raf);
    }
    const rafId = requestAnimationFrame(raf);

    return () => {
      window.removeEventListener("scroll", onScroll);
      cancelAnimationFrame(rafId);
      lenis.destroy();
    };
  }, []);

  if (!mounted) {
    return (
      <div className="fixed inset-0 bg-[#2b082a] flex items-center justify-center text-white">
        <div className="w-8 h-8 rounded-full border-2 border-orange-400 border-t-transparent animate-spin" />
      </div>
    );
  }

  return (
    <div className="relative w-full h-[600vh] bg-[#2a0729]">
      {/* Sunset Background Gradient matching user's reference images */}
      <div
        className="fixed inset-0 pointer-events-none z-0"
        style={{
          background:
            "linear-gradient(180deg, #fce0c6 0%, #f69d67 28%, #df4758 58%, #4a0a3d 90%, #2a0729 100%)",
        }}
      />

      {/* Sticky 3D Viewport */}
      <div className="sticky top-0 left-0 w-full h-screen overflow-hidden z-10">

        {/* Hero Text Behind the 3D Scene */}
        <div className="absolute top-[12%] w-full z-0 pointer-events-none">
          <HeroText text="RGSTUDIO" color="#ffffffff" />
        </div>

        <Canvas
          camera={{ fov: 45, near: 0.1, far: 2000 }}
          gl={{
            antialias: true,
            alpha: true,
            toneMapping: THREE.ACESFilmicToneMapping,
            toneMappingExposure: 1.15,
          }}
          className="w-full h-full relative z-10"
        >
          {/* Sunset Lighting */}
          <ambientLight intensity={2.0} color="#fff2e6" />

          {/* Main Key Sunset Light */}
          <directionalLight
            position={[25, 40, 30]}
            intensity={2.8}
            color="#ffa866"
          />

          {/* Fill Light */}
          <directionalLight
            position={[-20, 20, 20]}
            intensity={1.2}
            color="#e05588"
          />

          {/* Rim Light */}
          <directionalLight
            position={[0, 10, -20]}
            intensity={0.8}
            color="#ff5533"
          />

          <Suspense fallback={<Loader />}>
            <FirewatchModel scrollProgress={scrollProgress} />
          </Suspense>
        </Canvas>

        {/* Scroll Guidance UI Overlay */}
        <div className="pointer-events-none absolute bottom-8 left-1/2 -translate-x-1/2 z-20 flex flex-col items-center gap-2 text-white/90 select-none">
          <span className="text-xs uppercase tracking-[0.25em] font-semibold bg-black/40 px-4 py-1.5 rounded-full backdrop-blur-md border border-white/20 shadow-lg">
            Scroll to Zoom In
          </span>
          <div className="w-5 h-9 rounded-full border-2 border-white/40 flex justify-center p-1 bg-black/20 backdrop-blur-sm">
            <div className="w-1 h-2.5 bg-orange-400 rounded-full animate-bounce" />
          </div>
        </div>
      </div>

      {/* End of Scroll Action */}
      {/* End of Scroll Action */}
      <div className="absolute bottom-[35vh] right-10 z-30 pointer-events-auto">
        <PopButton onClick={() => { router.push("/home") }}>Continue to Dashboard</PopButton>
      </div>
    </div>
  );
}

useGLTF.preload("/art.glb");
