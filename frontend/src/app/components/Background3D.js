"use client";

import { useEffect, useRef, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Float, Icosahedron, MeshDistortMaterial } from "@react-three/drei";
import * as THREE from "three";

function ScrollShape({ position, scale, color, distort = false }) {
  const meshRef = useRef();
  
  // Store an initial offset based on random value so they don't all look identical
  const [offset] = useState(() => Math.random() * 100);

  useFrame((state, delta) => {
    if (!meshRef.current) return;
    // Gentle constant rotation
    meshRef.current.rotation.x += delta * 0.1;
    meshRef.current.rotation.y += delta * 0.15;
    
    // Add scroll parallax translation
    const scrollY = window.scrollY;
    // We lerp the position so it's buttery smooth when the user stops scrolling
    meshRef.current.position.y = THREE.MathUtils.lerp(
      meshRef.current.position.y,
      position[1] + scrollY * 0.003, // moves shape upwards slightly
      0.1
    );
  });

  return (
    <Float speed={1.5} rotationIntensity={1} floatIntensity={2}>
      <mesh ref={meshRef} position={position} scale={scale}>
        {distort ? (
          <Icosahedron args={[1, 0]}>
            <MeshDistortMaterial color={color} speed={2} distort={0.3} wireframe={true} transparent={true} opacity={0.6} />
          </Icosahedron>
        ) : (
          <Icosahedron args={[1, 1]}>
            <meshStandardMaterial color={color} wireframe transparent={true} opacity={0.4} />
          </Icosahedron>
        )}
      </mesh>
    </Float>
  );
}

function Scene() {
  const groupRef = useRef();
  
  useFrame(() => {
    if (groupRef.current) {
      const scrollY = window.scrollY;
      const progress = scrollY / (document.documentElement.scrollHeight - window.innerHeight || 1);
      
      // Rotate the entire scene gently based on scroll depth
      groupRef.current.rotation.y = THREE.MathUtils.lerp(
        groupRef.current.rotation.y,
        progress * Math.PI,
        0.05
      );
    }
  });

  return (
    <group ref={groupRef}>
      <ambientLight intensity={0.5} />
      <directionalLight position={[10, 10, 5]} intensity={1} />
      <directionalLight position={[-10, -10, -5]} intensity={0.5} />
      
      {/* Placed around the screen so they flow nicely */}
      <ScrollShape position={[-5, 3, -5]} scale={1.8} color="#E86352" distort={true} />
      <ScrollShape position={[6, -2, -8]} scale={2.5} color="#10b981" />
      <ScrollShape position={[-7, -6, -10]} scale={3.0} color="#f59e0b" distort={true} />
      <ScrollShape position={[5, 6, -6]} scale={1.5} color="#3b82f6" />
      <ScrollShape position={[0, -8, -4]} scale={2.2} color="#E86352" />
      <ScrollShape position={[-3, 8, -6]} scale={1.5} color="#6b6b6b" />
      <ScrollShape position={[8, 3, -12]} scale={3.5} color="#E86352" distort={true} />
    </group>
  );
}

export default function Background3D() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null; // Avoid hydration mismatch

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        width: "100vw",
        height: "100vh",
        zIndex: -1,
        pointerEvents: "none",
        background: "transparent",
      }}
    >
      <Canvas
        camera={{ position: [0, 0, 5], fov: 60 }}
        gl={{ alpha: true, antialias: true }}
      >
        <Scene />
      </Canvas>
    </div>
  );
}
