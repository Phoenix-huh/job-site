"use client";

import { useEffect, useRef } from "react";

// The cinematic elements scattered throughout the entire scrollable journey.
// Since container is `fixed`, an element with `speed: -1.0` moves EXACTLY identically to your normal page content.
// `speed: -0.3` moves very slowly (extreme background depth).
// `speed: -1.5` moves extremely fast (foreground overlap depth).

const ELEMENTS = [
  // --- BOLD GORGEOUS AMBIENT ORBS (Deep Background) ---
  // Increased opacities so they are highly visible and vibrant behind sections
  { type: 'orb', top: '10vh', left: '-10vw', size: '60vw', color: 'rgba(16, 185, 129, 0.45)', blur: '100px', speed: -0.2, rot: 0 },
  { type: 'orb', top: '120vh', right: '-15vw', size: '70vw', color: 'rgba(232, 99, 82, 0.35)', blur: '120px', speed: -0.3, rot: 0 },
  { type: 'orb', top: '230vh', left: '5vw', size: '80vw', color: 'rgba(59, 130, 246, 0.4)', blur: '140px', speed: -0.15, rot: 0 },
  { type: 'orb', top: '350vh', right: '10vw', size: '50vw', color: 'rgba(245, 158, 11, 0.45)', blur: '90px', speed: -0.25, rot: 0 },

  // --- DISTINCT GEOMETRIC VECTORS (Midground / Layer 2) ---
  // Large stroke circles made slightly thicker and more vibrant
  { type: 'circle', top: '40vh', right: '5vw', size: '30vw', stroke: 'rgba(232, 99, 82, 0.4)', strokeWidth: '4px', speed: -0.6, rot: 0.02 },
  { type: 'circle', top: '160vh', left: '-5vw', size: '40vw', stroke: 'rgba(16, 185, 129, 0.4)', strokeWidth: '3px', speed: -0.5, rot: -0.01 },
  { type: 'circle', top: '280vh', right: '20vw', size: '25vw', stroke: 'rgba(59, 130, 246, 0.5)', strokeWidth: '6px', speed: -0.7, rot: 0.03 },

  // Elegant floating crosses (Threat Indicators)
  { type: 'cross', top: '20vh', left: '15vw', size: '40px', color: 'rgba(107, 107, 107, 0.6)', speed: -1.2, rot: 0.05 },
  { type: 'cross', top: '80vh', right: '25vw', size: '25px', color: 'rgba(232, 99, 82, 0.7)', speed: -1.4, rot: -0.08 },
  { type: 'cross', top: '180vh', left: '30vw', size: '50px', color: 'rgba(16, 185, 129, 0.6)', speed: -0.9, rot: 0.04 },
  { type: 'cross', top: '250vh', right: '10vw', size: '35px', color: 'rgba(59, 130, 246, 0.8)', speed: -1.5, rot: -0.06 },
  { type: 'cross', top: '320vh', left: '20vw', size: '60px', color: 'rgba(245, 158, 11, 0.6)', speed: -1.1, rot: 0.03 }
];

export default function CinematicParallax() {
  const containerRef = useRef(null);

  useEffect(() => {
    let rafId;
    let targetY = window.scrollY;
    let currentY = window.scrollY;

    const domElements = containerRef.current.querySelectorAll('.parallax-layer');

    const onScroll = () => {
      targetY = window.scrollY;
    };
    window.addEventListener("scroll", onScroll, { passive: true });

    // Force an immediate alignment to prevent layout jumping on load
    domElements.forEach(el => {
      const speed = parseFloat(el.getAttribute('data-speed'));
      const rotSpeed = parseFloat(el.getAttribute('data-rot'));
      el.style.transform = `translateY(${targetY * speed}px) rotate(${targetY * rotSpeed}deg)`;
    });

    const renderLoop = () => {
      // Butter-smooth standard lerp
      const diff = targetY - currentY;
      if (Math.abs(diff) > 0.1) {
        currentY += diff * 0.08;
        
        domElements.forEach(el => {
          const speed = parseFloat(el.getAttribute('data-speed'));
          const rotSpeed = parseFloat(el.getAttribute('data-rot'));
          const yOffset = currentY * speed;
          const rotOffset = currentY * rotSpeed;
          el.style.transform = `translateY(${yOffset}px) rotate(${rotOffset}deg)`;
        });
      }
      
      rafId = requestAnimationFrame(renderLoop);
    };
    renderLoop();

    return () => {
      window.removeEventListener("scroll", onScroll);
      cancelAnimationFrame(rafId);
    };
  }, []);

  return (
    <div 
      ref={containerRef}
      style={{
        position: 'fixed',
        inset: 0, // Cover entire viewport exactly
        width: '100vw',
        height: '100vh',
        pointerEvents: 'none', // Crucial to prevent blocking standard UI interactions
        zIndex: 0, // Render firmly behind the main `page-wrapper` content context
        overflow: 'hidden', // Anything outside the precise viewport is naturally clipped
      }}
    >
      {ELEMENTS.map((el, idx) => {
        
        // Base styling for all items
        const baseStyle = {
          position: 'absolute',
          top: el.top,
          left: el.left || undefined,
          right: el.right || undefined,
          width: el.size,
          height: el.size,
          willChange: 'transform',
        };

        if (el.type === 'orb') {
          return (
            <div 
              key={idx}
              className="parallax-layer"
              data-speed={el.speed}
              data-rot={el.rot}
              style={{
                ...baseStyle,
                background: el.color,
                borderRadius: '50%',
                filter: `blur(${el.blur})`,
              }}
            />
          );
        }

        if (el.type === 'circle') {
          return (
            <div 
              key={idx}
              className="parallax-layer"
              data-speed={el.speed}
              data-rot={el.rot}
              style={{
                ...baseStyle,
                border: `${el.strokeWidth} solid ${el.stroke}`,
                borderRadius: '50%',
              }}
            />
          );
        }

        if (el.type === 'cross') {
          return (
            <div 
              key={idx}
              className="parallax-layer"
              data-speed={el.speed}
              data-rot={el.rot}
              style={{
                ...baseStyle,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <div style={{ position: 'absolute', width: '100%', height: '2px', background: el.color }} />
              <div style={{ position: 'absolute', height: '100%', width: '2px', background: el.color }} />
            </div>
          );
        }

        if (el.type === 'dot') {
          return (
            <div 
              key={idx}
              className="parallax-layer"
              data-speed={el.speed}
              data-rot={el.rot}
              style={{
                ...baseStyle,
                background: el.color,
                borderRadius: '50%',
                opacity: 0.8
              }}
            />
          );
        }
        
        return null;
      })}
    </div>
  );
}
