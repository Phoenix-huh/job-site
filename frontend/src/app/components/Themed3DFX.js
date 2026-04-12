"use client";

import { useRef, useMemo, useState, useEffect } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Float, Icosahedron, Octahedron, MeshDistortMaterial } from "@react-three/drei";
import * as THREE from "three";

function Scam({ position, scale, parallaxSpeed }) {
  const meshRef = useRef();
  
  useFrame((state, delta) => {
    if (!meshRef.current) return;
    // Fast, chaotic rotation for scams
    meshRef.current.rotation.x += delta * 1.5;
    meshRef.current.rotation.y += delta * 2;
    
    const scrollY = window.scrollY;
    // Translate upwards on scroll
    meshRef.current.position.y = THREE.MathUtils.lerp(
      meshRef.current.position.y,
      position[1] + scrollY * parallaxSpeed,
      0.1
    );
  });

  return (
    <Float speed={4} rotationIntensity={2} floatIntensity={1}>
      <mesh ref={meshRef} position={position} scale={scale}>
        {/* A spiky, unstable red mass representing a threat/scam */}
        <Icosahedron args={[1, 2]}>
          <MeshDistortMaterial color="#ef4444" speed={5} distort={0.6} roughness={0.3} metalness={0.7} />
        </Icosahedron>
      </mesh>
    </Float>
  );
}

function Shield({ position, scale, parallaxSpeed }) {
  const meshRef = useRef();
  
  useFrame((state, delta) => {
    if (!meshRef.current) return;
    // Smooth, confident rotation for shields
    meshRef.current.rotation.y += delta * 0.4;
    meshRef.current.rotation.z += delta * 0.1;
    
    const scrollY = window.scrollY;
    meshRef.current.position.y = THREE.MathUtils.lerp(
      meshRef.current.position.y,
      position[1] + scrollY * parallaxSpeed,
      0.1
    );
  });

  return (
    <Float speed={1.5} rotationIntensity={0.5} floatIntensity={3}>
      <group ref={meshRef} position={position} scale={scale}>
        {/* A sturdy emerald crystal representing protection */}
        <Octahedron args={[1, 0]}>
          <meshStandardMaterial color="#10b981" roughness={0.1} metalness={0.9} />
        </Octahedron>
        {/* A protective forcefield ring orbiting the shield */}
        <mesh rotation-x={Math.PI / 2}>
           <torusGeometry args={[1.5, 0.05, 16, 100]} />
           <meshStandardMaterial color="#6ee7b7" emissive="#10b981" emissiveIntensity={0.8} />
        </mesh>
      </group>
    </Float>
  );
}

function Scene() {
  const elements = useMemo(() => Array.from({ length: 50 }).map((_, i) => ({
    id: i,
    type: Math.random() > 0.6 ? 'shield' : 'scam', // 40% shields, 60% scams
    position: [
       (Math.random() - 0.5) * 22, // X spread wide
       (Math.random() * 120) - 80, // Y spawn depth
       (Math.random() * -15) - 3    // Z depth receding
    ],
    scale: 0.4 + Math.random() * 0.8,
    parallaxSpeed: 0.015 + Math.random() * 0.03 // Varying parallax lifts
  })), [])

  const groupRef = useRef();

  useFrame(() => {
     if (groupRef.current) {
        // Apply a gentle global spin to the entire swarm on scroll
        const progress = window.scrollY / 4000;
        groupRef.current.rotation.y = THREE.MathUtils.lerp(groupRef.current.rotation.y, progress * Math.PI, 0.05);
     }
  });

  return (
    <group ref={groupRef}>
      <ambientLight intensity={0.6} />
      <directionalLight position={[10, 10, 5]} intensity={1.5} />
      <directionalLight position={[-10, -10, -5]} intensity={0.8} color="#E86352" />
      
      {elements.map(el => el.type === 'scam' ? 
        <Scam key={el.id} position={el.position} scale={el.scale} parallaxSpeed={el.parallaxSpeed} /> :
        <Shield key={el.id} position={el.position} scale={el.scale} parallaxSpeed={el.parallaxSpeed} />
      )}
    </group>
  );
}

export default function Themed3DFX() {
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
      <Canvas camera={{ position: [0, 0, 10], fov: 60 }} gl={{ alpha: true, antialias: true }}>
        <Scene />
      </Canvas>
    </div>
  );
}
