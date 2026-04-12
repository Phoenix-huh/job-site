"use client";

import { useScroll, useTransform, motion } from "framer-motion";
import { useEffect, useState } from "react";

export default function GiganticParallax() {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  // Framer Motion hook tracking global vertical scroll progression from 0 to 1
  const { scrollYProgress } = useScroll();

  // Map scroll progress precisely to brand colors for a butter-smooth 'Gigantic Media' dual-tone shift
  // Approximate structure: 
  // 0% -> 15% (Hero section needs Coral)
  // 15% -> 40% (Threat Engine needs Cream)
  // 40% -> 70% (How it Works needs Dark)
  // 70% -> 100% (Job search tool needs Cream)
  const bgColor = useTransform(
    scrollYProgress,
    [0, 0.10, 0.25, 0.60, 0.85, 1],
    ['#E86352', '#E86352', '#EFE8E6', '#1a1a1a', '#EFE8E6', '#EFE8E6']
  );

  // Smooth CSS transform for the massive blueprint background lines moving slower than content (classic parallax)
  const bgY = useTransform(scrollYProgress, [0, 1], ['0%', '-50%']);

  if (!mounted) return null;

  return (
    <motion.div 
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: bgColor,
        zIndex: -1, // Firmly locked behind all standard content layers
        pointerEvents: 'none', // Prevents any click interceptions
        overflow: 'hidden'
      }}
    >
      <motion.div 
        style={{ 
          position: 'absolute', 
          inset: 0, 
          height: '200%', // Spans double the screen to allow for negative Y translation parallax
          y: bgY 
        }}
      >
        <svg fill="none" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
          {/* Gigantic-Media style architectural and highly structured line vectors representing technical intelligence grids */}
          
          {/* Central spine */}
          <line x1="50%" y1="0" x2="50%" y2="100%" stroke="rgba(120, 120, 120, 0.15)" strokeWidth="1.5" />
          
          {/* Top massive concentric rings acting as mathematical/scanning focal points */}
          <circle cx="50%" cy="20%" r="45vw" stroke="rgba(120, 120, 120, 0.08)" strokeWidth="1" />
          <circle cx="50%" cy="20%" r="35vw" stroke="rgba(120, 120, 120, 0.12)" strokeWidth="1" />
          <circle cx="50%" cy="20%" r="20vw" stroke="rgba(120, 120, 120, 0.15)" strokeWidth="1" />

          {/* Deep tracking margin lines */}
          <line x1="8%" y1="0" x2="8%" y2="100%" stroke="rgba(120, 120, 120, 0.08)" strokeWidth="1" />
          <line x1="92%" y1="0" x2="92%" y2="100%" stroke="rgba(120, 120, 120, 0.08)" strokeWidth="1" />
          
          {/* Offset technical crosshairs mapping the intelligence grid */}
          <path d="M 8vw 35vh L 8vw 40vh M 3vw 37.5vh L 13vw 37.5vh" stroke="rgba(120, 120, 120, 0.3)" strokeWidth="1" />
          <path d="M 92vw 65vh L 92vw 70vh M 87vw 67.5vh L 97vw 67.5vh" stroke="rgba(120, 120, 120, 0.3)" strokeWidth="1" />
          
          {/* Bottom massive focal ring mapping out deeper threats */}
          <circle cx="50%" cy="80%" r="55vw" stroke="rgba(120, 120, 120, 0.1)" strokeWidth="2" strokeDasharray="10 10" />
        </svg>
      </motion.div>
    </motion.div>
  );
}
