"use client";

import { useRef, useMemo, useState, useEffect } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Float, Tetrahedron, Torus, Sphere } from "@react-three/drei";
import * as THREE from "three";

// High performance basic mesh, represents data stream points
function DataNode({ position, scale, parallaxSpeed, color }) {
  const meshRef = useRef();
  
  useFrame((state, delta) => {
    if (!meshRef.current) return;
    meshRef.current.rotation.x += delta * 1;
    meshRef.current.rotation.y += delta * 1.2;
    
    const scrollY = window.scrollY;
    // Translate upwards on scroll
    meshRef.current.position.y = THREE.MathUtils.lerp(
      meshRef.current.position.y,
      position[1] + scrollY * parallaxSpeed,
      0.1
    );
  });

  return (
    <Float speed={2} rotationIntensity={1} floatIntensity={0.5}>
      <mesh ref={meshRef} position={position} scale={scale}>
        <Tetrahedron args={[1, 0]}>
          <meshStandardMaterial color={color} roughness={0.4} metalness={0.6} />
        </Tetrahedron>
        
        {/* Core glow */}
        <Sphere args={[0.3, 16, 16]}>
          <meshBasicMaterial color="#ffffff" />
        </Sphere>
      </mesh>
    </Float>
  );
}

function TechRing({ position, scale, parallaxSpeed, color }) {
  const meshRef = useRef();
  
  useFrame((state, delta) => {
    if (!meshRef.current) return;
    meshRef.current.rotation.x += delta * 0.5;
    meshRef.current.rotation.z += delta * 0.5;
    
    const scrollY = window.scrollY;
    // Translate upwards on scroll
    meshRef.current.position.y = THREE.MathUtils.lerp(
      meshRef.current.position.y,
      position[1] + scrollY * parallaxSpeed,
      0.1
    );
  });

  return (
    <Float speed={1.5} rotationIntensity={2} floatIntensity={1}>
      <mesh ref={meshRef} position={position} scale={scale}>
        <Torus args={[1, 0.15, 16, 64]}>
          <meshStandardMaterial color={color} roughness={0.2} metalness={0.8} />
        </Torus>
      </mesh>
    </Float>
  );
}

function Scene() {
  const elements = useMemo(() => Array.from({ length: 70 }).map((_, i) => {
    // Crucial Logic: Confine elements STRICTLY to left and right margins!
    // Center viewport (roughly X between -6 and +6) will be completely clean.
    const isLeft = Math.random() > 0.5;
    const xPos = isLeft ? (-14 + Math.random() * 6) : (8 + Math.random() * 6);
    
    const colors = ['#E86352', '#10b981', '#3b82f6'];

    return {
      id: i,
      type: Math.random() > 0.5 ? 'node' : 'ring',
      position: [
         xPos,
         (Math.random() * 160) - 80, // Y spread (covers massive scroll heights)
         (Math.random() * -15) - 2   // Z depth
      ],
      scale: 0.2 + Math.random() * 0.6,
      parallaxSpeed: 0.015 + Math.random() * 0.03, // Variable parallax drift
      color: colors[Math.floor(Math.random() * colors.length)]
    }
  }), [])

  const groupRef = useRef();

  useFrame(() => {
     if (groupRef.current) {
        // Apply a gentle global spin to the entire network relative to scroll
        const progress = window.scrollY / 4000;
        groupRef.current.rotation.y = THREE.MathUtils.lerp(groupRef.current.rotation.y, progress * Math.PI, 0.05);
     }
  });

  return (
    <group ref={groupRef}>
      <ambientLight intensity={0.5} />
      <directionalLight position={[10, 10, 5]} intensity={1.5} />
      <directionalLight position={[-10, -10, -5]} intensity={1} color="#E86352" />
      
      {elements.map(el => el.type === 'node' ? 
        <DataNode key={el.id} position={el.position} scale={el.scale} parallaxSpeed={el.parallaxSpeed} color={el.color} /> :
        <TechRing key={el.id} position={el.position} scale={el.scale} parallaxSpeed={el.parallaxSpeed} color={el.color} />
      )}
    </group>
  );
}

export default function SideParallax3D() {
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
        camera={{ position: [0, 0, 10], fov: 60 }} 
        gl={{ alpha: true, antialias: true, powerPreference: "high-performance" }}
        style={{ pointerEvents: 'none' }}
      >
        <Scene />
      </Canvas>
    </div>
  );
}
