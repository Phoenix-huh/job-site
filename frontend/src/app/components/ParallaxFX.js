"use client";
import { useEffect, useState } from "react";

const SHAPES = [
  // Circle
  (color) => <svg width="100%" height="100%" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="3"><circle cx="12" cy="12" r="9"/></svg>,
  // Plus
  (color) => <svg width="100%" height="100%" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="3" strokeLinecap="round"><line x1="12" y1="4" x2="12" y2="20"/><line x1="4" y1="12" x2="20" y2="12"/></svg>,
  // Square
  (color) => <svg width="100%" height="100%" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="3"><rect x="4" y="4" width="16" height="16" rx="3" ry="3"/></svg>,
  // Triangle
  (color) => <svg width="100%" height="100%" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="3" strokeLinejoin="round"><polygon points="12 3 21 19 3 19 12 3"/></svg>,
  // Dots
  (color) => <svg width="100%" height="100%" viewBox="0 0 24 24" fill={color}><circle cx="6" cy="12" r="2.5"/><circle cx="18" cy="12" r="2.5"/></svg>
];

const COLORS = ['#E86352', '#10b981', '#f59e0b', '#3b82f6', '#1a1a1a'];

export default function ParallaxFX() {
  const [elements, setElements] = useState([]);
  const [scrollY, setScrollY] = useState(0);
  const [windowHeight, setWindowHeight] = useState(1000);

  useEffect(() => {
    setWindowHeight(window.innerHeight);
    const documentHeight = Math.max(document.body.scrollHeight, 5000);

    // Generate scattered elements across the entire document height
    const elts = Array.from({ length: 60 }).map((_, i) => ({
      id: i,
      x: Math.random() * 100, // viewport width %
      y: Math.random() * documentHeight, // vertical document spawn point
      size: 20 + Math.random() * 60,
      opacity: 0.15 + Math.random() * 0.35,
      // Parallax multiplier: negative moves faster up, positive moves slower up
      speed: (Math.random() - 0.5) * 1.5,
      rotation: Math.random() * 360,
      rotSpeed: (Math.random() - 0.5) * 0.4,
      shape: Math.floor(Math.random() * SHAPES.length),
      color: COLORS[Math.floor(Math.random() * COLORS.length)]
    }));
    setElements(elts);

    let rafId;
    let targetScroll = window.scrollY;

    const onScroll = () => {
      targetScroll = window.scrollY;
    };
    window.addEventListener("scroll", onScroll, { passive: true });

    // Smooth scroll interpolation loop
    const renderLoop = () => {
      setScrollY((prev) => {
        // smooth lerp
        const diff = targetScroll - prev;
        if (Math.abs(diff) < 0.1) return prev;
        return prev + diff * 0.15;
      });
      rafId = requestAnimationFrame(renderLoop);
    };
    renderLoop();

    return () => {
      window.removeEventListener("scroll", onScroll);
      cancelAnimationFrame(rafId);
    };
  }, []);

  if (elements.length === 0) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      width: '100vw',
      height: '100vh',
      pointerEvents: 'none',
      zIndex: 50,
      overflow: 'hidden'
    }}>
      {elements.map((el) => {
        const screenY = el.y - scrollY;
        const parallaxOffset = scrollY * el.speed;
        const finalY = screenY + parallaxOffset;
        
        // Culling: Skip rendering if WAY outside the viewport
        if (finalY < -150 || finalY > windowHeight + 150) return null;

        const currentRot = el.rotation + (scrollY * el.rotSpeed);
        return (
          <div
            key={el.id}
            style={{
              position: 'absolute',
              left: `${el.x}vw`,
              top: `${finalY}px`,
              width: `${el.size}px`,
              height: `${el.size}px`,
              opacity: el.opacity,
              transform: `rotate(${currentRot}deg)`,
              willChange: 'transform'
            }}
          >
            {SHAPES[el.shape](el.color)}
          </div>
        );
      })}
    </div>
  );
}
