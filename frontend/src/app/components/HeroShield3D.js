"use client";

import { useRef, useState, useEffect } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Environment, MeshTransmissionMaterial, TorusKnot } from "@react-three/drei";
import * as THREE from "three";

function SpinningGlassKnot() {
  const groupRef = useRef();

  useFrame((state, delta) => {
    if (!groupRef.current) return;
    
    // Calculate scroll progress percentage (0 to 1)
    const scrollY = window.scrollY;
    // Estimate total document scrollable area
    const maxScroll = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
    const progress = Math.max(0, Math.min(1, scrollY / maxScroll));

    // Spin smoothly across the entire page scroll (two full spins)
    const targetRotationY = progress * Math.PI * 4;
    groupRef.current.rotation.y = THREE.MathUtils.lerp(
      groupRef.current.rotation.y,
      targetRotationY,
      0.1
    );
    
    groupRef.current.rotation.x = THREE.MathUtils.lerp(
      groupRef.current.rotation.x,
      progress * Math.PI,
      0.05
    );

    // Subtle floating bob
    const time = state.clock.getElapsedTime();
    const bobOffset = Math.sin(time) * 0.2;

    // Gentle swoop side to side
    const targetOffsetX = Math.sin(progress * Math.PI * 2) * 1.5;
    
    groupRef.current.position.y = THREE.MathUtils.lerp(
      groupRef.current.position.y,
      bobOffset,
      0.1
    );
    groupRef.current.position.x = THREE.MathUtils.lerp(
      groupRef.current.position.x,
      targetOffsetX,
      0.1
    );
  });

  return (
    <group ref={groupRef} scale={1.8}>
      <TorusKnot args={[1, 0.35, 128, 64]}>
        <MeshTransmissionMaterial 
          samples={16} // Quality
          resolution={512} // internal rendering res
          transmission={1} // High transparency
          roughness={0.05} // Crystal smooth
          thickness={0.5} // Light refraction depth
          ior={1.3} // Index of Refraction (glass/water like)
          chromaticAberration={0.06} // Split RGB lightly at edges
          anisotropy={0.1}
          distortion={0.1}
          distortionScale={0.3}
          temporalDistortion={0.1}
          color="#ffffff" // completely pure glass, inherits colors around it perfectly
        />
      </TorusKnot>
    </group>
  );
}

export default function HeroShield3D() {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  if (!mounted) return null;

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      width: '100vw',
      height: '100vh',
      zIndex: 50,
      pointerEvents: 'none',
      background: 'transparent'
    }}>
      <Canvas 
        camera={{ position: [0, 0, 8], fov: 45 }} 
        gl={{ alpha: true, antialias: true }}
        style={{ pointerEvents: 'none' }}
      >
        {/* We use an Environment mapping for incredibly realistic lighting reflections on the glass. No harsh 'orange spots'. */}
        <Environment preset="city" />
        <SpinningGlassKnot />
      </Canvas>
    </div>
  );
}
