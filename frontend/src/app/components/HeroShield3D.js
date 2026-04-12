"use client";

import { useRef, useState, useEffect } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Octahedron, Sphere } from "@react-three/drei";
import * as THREE from "three";

function SpinningHeroShield() {
  const groupRef = useRef();

  useFrame((state, delta) => {
    if (!groupRef.current) return;
    
    // Calculate scroll progress percentage (0 to 1)
    const scrollY = window.scrollY;
    // Estimate total document scrollable area
    const maxScroll = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
    const progress = Math.max(0, Math.min(1, scrollY / maxScroll));

    // Spin exactly 2 full rotations as the user reaches the bottom
    const targetRotationY = progress * Math.PI * 4;
    groupRef.current.rotation.y = THREE.MathUtils.lerp(
      groupRef.current.rotation.y,
      targetRotationY,
      0.1
    );

    // Add a very subtle organic floating "bob" independent of scroll
    const time = state.clock.getElapsedTime();
    const bobOffset = Math.sin(time) * 0.2;

    // Shift left and right gracefully as the user scrolls
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
    <group ref={groupRef} scale={3}>
      {/* Core crystalline shield shape */}
      <Octahedron args={[1, 0]}>
        <meshStandardMaterial color="#10b981" roughness={0.1} metalness={0.9} />
      </Octahedron>
      
      {/* Glowing inner core */}
      <Sphere args={[0.5, 32, 32]}>
        <meshStandardMaterial color="#6ee7b7" emissive="#10b981" emissiveIntensity={2} />
      </Sphere>

      {/* Outer metallic orbital forcefield rings */}
      <mesh rotation-x={Math.PI / 2}>
         <torusGeometry args={[1.6, 0.04, 16, 100]} />
         <meshStandardMaterial color="#3b82f6" metalness={1} roughness={0.2} emissive="#3b82f6" emissiveIntensity={0.5} />
      </mesh>
      
      <mesh rotation-x={Math.PI / 2} rotation-y={Math.PI / 4} scale={1.2}>
         <torusGeometry args={[1.6, 0.02, 16, 100]} />
         <meshStandardMaterial color="#E86352" metalness={1} roughness={0.2} emissive="#E86352" emissiveIntensity={0.5} />
      </mesh>
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
      pointerEvents: 'none', // Critical to allow clicking underneath
      background: 'transparent'
    }}>
      {/* Adding pointerEvents string directly to canvas container ensures R3F doesn't block */}
      <Canvas 
        camera={{ position: [0, 0, 10], fov: 50 }} 
        gl={{ alpha: true, antialias: true }}
        style={{ pointerEvents: 'none' }}
      >
        <ambientLight intensity={0.8} />
        <directionalLight position={[10, 10, 5]} intensity={2} color="#ffffff" />
        <directionalLight position={[-10, -10, -5]} intensity={1} color="#E86352" />
        
        <SpinningHeroShield />
      </Canvas>
    </div>
  );
}
