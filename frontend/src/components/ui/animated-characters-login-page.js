"use client";

import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Eye, EyeOff, Mail, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

const Pupil = ({ 
  size = 12, 
  maxDistance = 5,
  pupilColor = "black",
  forceLookX,
  forceLookY
}) => {
  const [mouseX, setMouseX] = useState(0);
  const [mouseY, setMouseY] = useState(0);
  const pupilRef = useRef(null);

  useEffect(() => {
    const handleMouseMove = (e) => {
      setMouseX(e.clientX);
      setMouseY(e.clientY);
    };

    window.addEventListener("mousemove", handleMouseMove);

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
    };
  }, []);

  const calculatePupilPosition = () => {
    if (!pupilRef.current) return { x: 0, y: 0 };

    if (forceLookX !== undefined && forceLookY !== undefined) {
      return { x: forceLookX, y: forceLookY };
    }

    const pupil = pupilRef.current.getBoundingClientRect();
    const pupilCenterX = pupil.left + pupil.width / 2;
    const pupilCenterY = pupil.top + pupil.height / 2;

    const deltaX = mouseX - pupilCenterX;
    const deltaY = mouseY - pupilCenterY;
    const distance = Math.min(Math.sqrt(deltaX ** 2 + deltaY ** 2), maxDistance);

    const angle = Math.atan2(deltaY, deltaX);
    const x = Math.cos(angle) * distance;
    const y = Math.sin(angle) * distance;

    return { x, y };
  };

  const pupilPosition = calculatePupilPosition();

  return (
    <div
      ref={pupilRef}
      className="rounded-full"
      style={{
        width: `${size}px`,
        height: `${size}px`,
        backgroundColor: pupilColor,
        transform: `translate(${pupilPosition.x}px, ${pupilPosition.y}px)`,
        transition: 'transform 0.1s ease-out',
      }}
    />
  );
};

const EyeBall = ({ 
  size = 48, 
  pupilSize = 16, 
  maxDistance = 10,
  eyeColor = "white",
  pupilColor = "black",
  isBlinking = false,
  forceLookX,
  forceLookY
}) => {
  const [mouseX, setMouseX] = useState(0);
  const [mouseY, setMouseY] = useState(0);
  const eyeRef = useRef(null);

  useEffect(() => {
    const handleMouseMove = (e) => {
      setMouseX(e.clientX);
      setMouseY(e.clientY);
    };

    window.addEventListener("mousemove", handleMouseMove);

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
    };
  }, []);

  const calculatePupilPosition = () => {
    if (!eyeRef.current) return { x: 0, y: 0 };

    if (forceLookX !== undefined && forceLookY !== undefined) {
      return { x: forceLookX, y: forceLookY };
    }

    const eye = eyeRef.current.getBoundingClientRect();
    const eyeCenterX = eye.left + eye.width / 2;
    const eyeCenterY = eye.top + eye.height / 2;

    const deltaX = mouseX - eyeCenterX;
    const deltaY = mouseY - eyeCenterY;
    const distance = Math.min(Math.sqrt(deltaX ** 2 + deltaY ** 2), maxDistance);

    const angle = Math.atan2(deltaY, deltaX);
    const x = Math.cos(angle) * distance;
    const y = Math.sin(angle) * distance;

    return { x, y };
  };

  const pupilPosition = calculatePupilPosition();

  return (
    <div
      ref={eyeRef}
      className="rounded-full flex items-center justify-center transition-all duration-150"
      style={{
        width: `${size}px`,
        height: isBlinking ? '2px' : `${size}px`,
        backgroundColor: eyeColor,
        overflow: 'hidden',
      }}
    >
      {!isBlinking && (
        <div
          className="rounded-full"
          style={{
            width: `${pupilSize}px`,
            height: `${pupilSize}px`,
            backgroundColor: pupilColor,
            transform: `translate(${pupilPosition.x}px, ${pupilPosition.y}px)`,
            transition: 'transform 0.1s ease-out',
          }}
        />
      )}
    </div>
  );
};

export default function LoginPage() {
  const [showPassword, setShowPassword] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [mouseX, setMouseX] = useState(0);
  const [mouseY, setMouseY] = useState(0);
  const [isPurpleBlinking, setIsPurpleBlinking] = useState(false);
  const [isBlackBlinking, setIsBlackBlinking] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [isLookingAtEachOther, setIsLookingAtEachOther] = useState(false);
  const [isPurplePeeking, setIsPurplePeeking] = useState(false);
  const purpleRef = useRef(null);
  const blackRef = useRef(null);
  const yellowRef = useRef(null);
  const orangeRef = useRef(null);

  useEffect(() => {
    const handleMouseMove = (e) => {
      setMouseX(e.clientX);
      setMouseY(e.clientY);
    };

    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, []);

  useEffect(() => {
    const getRandomBlinkInterval = () => Math.random() * 4000 + 3000;

    const scheduleBlink = () => {
      const blinkTimeout = setTimeout(() => {
        setIsPurpleBlinking(true);
        setTimeout(() => {
          setIsPurpleBlinking(false);
          scheduleBlink();
        }, 150);
      }, getRandomBlinkInterval());

      return blinkTimeout;
    };

    const timeout = scheduleBlink();
    return () => clearTimeout(timeout);
  }, []);

  useEffect(() => {
    const getRandomBlinkInterval = () => Math.random() * 4000 + 3000;

    const scheduleBlink = () => {
      const blinkTimeout = setTimeout(() => {
        setIsBlackBlinking(true);
        setTimeout(() => {
          setIsBlackBlinking(false);
          scheduleBlink();
        }, 150);
      }, getRandomBlinkInterval());

      return blinkTimeout;
    };

    const timeout = scheduleBlink();
    return () => clearTimeout(timeout);
  }, []);

  useEffect(() => {
    if (isTyping) {
      setIsLookingAtEachOther(true);
      const timer = setTimeout(() => {
        setIsLookingAtEachOther(false);
      }, 800);
      return () => clearTimeout(timer);
    } else {
      setIsLookingAtEachOther(false);
    }
  }, [isTyping]);

  useEffect(() => {
    if (password.length > 0 && showPassword) {
      const schedulePeek = () => {
        const peekInterval = setTimeout(() => {
          setIsPurplePeeking(true);
          setTimeout(() => {
            setIsPurplePeeking(false);
          }, 800);
        }, Math.random() * 3000 + 2000);
        return peekInterval;
      };

      const firstPeek = schedulePeek();
      return () => clearTimeout(firstPeek);
    } else {
      setIsPurplePeeking(false);
    }
  }, [password, showPassword, isPurplePeeking]);

  const calculatePosition = (ref) => {
    if (!ref.current) return { faceX: 0, faceY: 0, bodyRotation: 0 };

    const rect = ref.current.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 3;

    const deltaX = mouseX - centerX;
    const deltaY = mouseY - centerY;

    const faceX = Math.max(-15, Math.min(15, deltaX / 20));
    const faceY = Math.max(-10, Math.min(10, deltaY / 30));

    const bodySkew = Math.max(-6, Math.min(6, -deltaX / 120));

    return { faceX, faceY, bodySkew };
  };

  const purplePos = calculatePosition(purpleRef);
  const blackPos = calculatePosition(blackRef);
  const yellowPos = calculatePosition(yellowRef);
  const orangePos = calculatePosition(orangeRef);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    await new Promise(r => setTimeout(r, 400));

    if (email === "admin@shield.com" && password === "admin123") {
      localStorage.setItem("token", "hardcoded-admin-token");
      localStorage.setItem("user", JSON.stringify({ email, role: "admin" }));
      window.location.href = "/";
    } else {
      setError("Invalid email or password. Try admin@shield.com / admin123");
    }

    setIsLoading(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100 p-4">
      <div className="w-full max-w-[1000px] h-[640px] bg-white rounded-3xl overflow-hidden shadow-2xl flex flex-col md:flex-row">
        
        {/* Left Content Section */}
        <div className="relative hidden lg:flex flex-col justify-between w-1/2 p-8 bg-zinc-900 text-white">
          <div className="relative z-20 flex items-center gap-2 text-lg font-semibold cursor-default">
            <div className="size-8 rounded-lg bg-white/10 flex items-center justify-center">
              <Sparkles className="size-4 text-white" />
            </div>
            <span>Shield</span>
          </div>

          <div className="relative z-20 flex items-end justify-center h-full mt-10">
            {/* Cartoon Characters Container */}
            <div className="relative w-full h-[340px] flex items-end justify-center overflow-visible">
              
              {/* Purple tall rectangle character - Back layer */}
              <div 
                ref={purpleRef}
                className="absolute bottom-0 transition-all duration-700 ease-in-out"
                style={{
                  left: '10%',
                  width: '35%',
                  height: (isTyping || (password.length > 0 && !showPassword)) ? '340px' : '300px',
                  backgroundColor: '#7A40F2',
                  borderRadius: '16px 16px 0 0',
                  zIndex: 1,
                  transform: (password.length > 0 && showPassword)
                    ? `skewX(0deg)`
                    : (isTyping || (password.length > 0 && !showPassword))
                      ? `skewX(${(purplePos.bodySkew || 0) - 12}deg) translateX(20px)` 
                      : `skewX(${purplePos.bodySkew || 0}deg)`,
                  transformOrigin: 'bottom center',
                }}
              >
                {/* Eyes */}
                <div 
                  className="absolute flex gap-6 transition-all duration-700 ease-in-out"
                  style={{
                    left: (password.length > 0 && showPassword) ? `15px` : isLookingAtEachOther ? `35px` : `calc(50% - 25px + ${purplePos.faceX}px)`,
                    top: (password.length > 0 && showPassword) ? `30px` : isLookingAtEachOther ? `55px` : `calc(20% + ${purplePos.faceY}px)`,
                  }}
                >
                  <EyeBall 
                    size={16} 
                    pupilSize={6} 
                    maxDistance={4} 
                    isBlinking={isPurpleBlinking}
                    forceLookX={(password.length > 0 && showPassword) ? (isPurplePeeking ? 3 : -3) : isLookingAtEachOther ? 2 : undefined}
                    forceLookY={(password.length > 0 && showPassword) ? (isPurplePeeking ? 4 : -3) : isLookingAtEachOther ? 3 : undefined}
                  />
                  <EyeBall 
                    size={16} 
                    pupilSize={6} 
                    maxDistance={4} 
                    isBlinking={isPurpleBlinking}
                    forceLookX={(password.length > 0 && showPassword) ? (isPurplePeeking ? 3 : -3) : isLookingAtEachOther ? 2 : undefined}
                    forceLookY={(password.length > 0 && showPassword) ? (isPurplePeeking ? 4 : -3) : isLookingAtEachOther ? 3 : undefined}
                  />
                </div>
              </div>

              {/* Black tall rectangle character - Middle layer */}
              <div 
                ref={blackRef}
                className="absolute bottom-0 transition-all duration-700 ease-in-out"
                style={{
                  left: '42%',
                  width: '24%',
                  height: '240px',
                  backgroundColor: '#2A2A2B',
                  borderRadius: '12px 12px 0 0',
                  zIndex: 2,
                  transform: (password.length > 0 && showPassword)
                    ? `skewX(0deg)`
                    : isLookingAtEachOther
                      ? `skewX(${(blackPos.bodySkew || 0) * 1.5 + 8}deg) translateX(10px)`
                      : (isTyping || (password.length > 0 && !showPassword))
                        ? `skewX(${(blackPos.bodySkew || 0) * 1.5}deg)` 
                        : `skewX(${blackPos.bodySkew || 0}deg)`,
                  transformOrigin: 'bottom center',
                }}
              >
                {/* Eyes */}
                <div 
                  className="absolute flex gap-4 transition-all duration-700 ease-in-out"
                  style={{
                    left: (password.length > 0 && showPassword) ? `10px` : isLookingAtEachOther ? `22px` : `calc(50% - 18px + ${blackPos.faceX}px)`,
                    top: (password.length > 0 && showPassword) ? `25px` : isLookingAtEachOther ? `15px` : `calc(25% + ${blackPos.faceY}px)`,
                  }}
                >
                  <EyeBall 
                    size={14} 
                    pupilSize={5} 
                    maxDistance={3} 
                    isBlinking={isBlackBlinking}
                    forceLookX={(password.length > 0 && showPassword) ? -3 : isLookingAtEachOther ? 0 : undefined}
                    forceLookY={(password.length > 0 && showPassword) ? -3 : isLookingAtEachOther ? -3 : undefined}
                  />
                  <EyeBall 
                    size={14} 
                    pupilSize={5} 
                    maxDistance={3} 
                    isBlinking={isBlackBlinking}
                    forceLookX={(password.length > 0 && showPassword) ? -3 : isLookingAtEachOther ? 0 : undefined}
                    forceLookY={(password.length > 0 && showPassword) ? -3 : isLookingAtEachOther ? -3 : undefined}
                  />
                </div>
              </div>

              {/* Orange semi-circle character - Front left */}
              <div 
                ref={orangeRef}
                className="absolute bottom-0 transition-all duration-700 ease-in-out"
                style={{
                  left: '0%',
                  width: '50%',
                  height: '160px',
                  zIndex: 3,
                  backgroundColor: '#FD8A5E',
                  borderRadius: '160px 160px 0 0',
                  transform: (password.length > 0 && showPassword) ? `skewX(0deg)` : `skewX(${orangePos.bodySkew || 0}deg)`,
                  transformOrigin: 'bottom center',
                }}
              >
                {/* Eyes (Pupils only) */}
                <div 
                  className="absolute flex gap-[22px] transition-all duration-200 ease-out"
                  style={{
                    left: (password.length > 0 && showPassword) ? `25px` : `calc(50% - 16px + ${orangePos.faceX || 0}px)`,
                    top: (password.length > 0 && showPassword) ? `65px` : `calc(50% + ${orangePos.faceY || 0}px)`,
                  }}
                >
                  <Pupil size={10} maxDistance={4} forceLookX={(password.length > 0 && showPassword) ? -4 : undefined} forceLookY={(password.length > 0 && showPassword) ? -3 : undefined} />
                  <Pupil size={10} maxDistance={4} forceLookX={(password.length > 0 && showPassword) ? -4 : undefined} forceLookY={(password.length > 0 && showPassword) ? -3 : undefined} />
                </div>
              </div>

              {/* Yellow tall rectangle character - Front right */}
              <div 
                ref={yellowRef}
                className="absolute bottom-0 transition-all duration-700 ease-in-out"
                style={{
                  left: '58%',
                  width: '30%',
                  height: '180px',
                  backgroundColor: '#E7CE4F',
                  borderRadius: '80px 80px 0 0',
                  zIndex: 4,
                  transform: (password.length > 0 && showPassword) ? `skewX(0deg)` : `skewX(${yellowPos.bodySkew || 0}deg)`,
                  transformOrigin: 'bottom center',
                }}
              >
                {/* Eyes (Pupils only) */}
                <div 
                  className="absolute flex gap-[18px] transition-all duration-200 ease-out"
                  style={{
                    left: (password.length > 0 && showPassword) ? `15px` : `calc(50% - 15px + ${yellowPos.faceX || 0}px)`,
                    top: (password.length > 0 && showPassword) ? `30px` : `calc(25% + ${yellowPos.faceY || 0}px)`,
                  }}
                >
                  <Pupil size={9} maxDistance={4} forceLookX={(password.length > 0 && showPassword) ? -4 : undefined} forceLookY={(password.length > 0 && showPassword) ? -3 : undefined} />
                  <Pupil size={9} maxDistance={4} forceLookX={(password.length > 0 && showPassword) ? -4 : undefined} forceLookY={(password.length > 0 && showPassword) ? -3 : undefined} />
                </div>
                {/* Mouth */}
                <div 
                  className="absolute h-[3px] bg-[#2D2D2D] rounded-full transition-all duration-200 ease-out"
                  style={{
                    width: '45%',
                    left: (password.length > 0 && showPassword) ? `10%` : `calc(50% - 22% + ${yellowPos.faceX || 0}px)`,
                    top: (password.length > 0 && showPassword) ? `65px` : `calc(45% + ${yellowPos.faceY || 0}px)`,
                  }}
                />
              </div>

            </div>
          </div>

          <div className="relative z-20 flex items-center gap-8 text-sm text-zinc-400 mt-8 mb-2 px-2 object-bottom">
            <a href="#" className="hover:text-white transition-colors">Privacy Policy</a>
            <a href="#" className="hover:text-white transition-colors">Terms of Service</a>
            <a href="#" className="hover:text-white transition-colors">Contact</a>
          </div>
        </div>

        {/* Right Login Section */}
        <div className="w-full lg:w-1/2 flex items-center justify-center p-8 bg-white">
          <div className="w-full max-w-[360px]">
            <div className="lg:hidden flex items-center justify-center gap-2 text-lg font-semibold mb-10">
              <div className="size-8 rounded-lg bg-zinc-900 text-white flex items-center justify-center">
                <Sparkles className="size-4" />
              </div>
              <span className="text-zinc-900">Shield</span>
            </div>

            <div className="text-center mb-8">
              <h1 className="text-[28px] font-bold tracking-tight text-neutral-900 mb-2 font-inter">Welcome back!</h1>
              <p className="text-sm text-neutral-500">Please enter your details</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="email" className="text-[13px] font-semibold text-neutral-800">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="anna@gmail.com"
                  value={email}
                  autoComplete="off"
                  onChange={(e) => setEmail(e.target.value)}
                  onFocus={() => setIsTyping(true)}
                  onBlur={() => setIsTyping(false)}
                  required
                  className="h-11 bg-white border-neutral-200 text-neutral-900 placeholder:text-neutral-400 focus:border-zinc-800 focus:ring-zinc-800 rounded-lg transition-colors"
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="password" className="text-[13px] font-semibold text-neutral-800">Password</Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    className="h-11 pr-10 bg-white border-neutral-200 text-neutral-900 placeholder:text-neutral-400 focus:border-zinc-800 focus:ring-zinc-800 rounded-lg transition-colors"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-600 transition-colors"
                  >
                    {showPassword ? <EyeOff className="size-[18px]" /> : <Eye className="size-[18px]" />}
                  </button>
                </div>
              </div>

              <div className="flex items-center justify-between pt-1">
                <div className="flex items-center space-x-2">
                  <Checkbox 
                    id="remember" 
                    className="border-neutral-300 data-[state=checked]:bg-zinc-900 data-[state=checked]:border-zinc-900 size-4 rounded-[4px]" 
                  />
                  <Label htmlFor="remember" className="text-[13px] font-medium text-neutral-700 cursor-pointer">
                    Remember for 30 days
                  </Label>
                </div>
                <a href="#" className="text-[13px] text-zinc-900 hover:underline font-semibold">
                  Forgot password?
                </a>
              </div>

              {error && (
                <div className="p-3 text-[13px] text-red-600 bg-red-50 border border-red-100 rounded-lg font-medium">
                  {error}
                </div>
              )}

              <Button 
                type="submit" 
                className="w-full h-11 text-[14px] font-semibold bg-zinc-900 hover:bg-zinc-800 text-white rounded-lg mt-2 transition-colors" 
                disabled={isLoading}
              >
                {isLoading ? "Signing in..." : "Log in"}
              </Button>
            </form>

            <div className="text-center text-[13px] text-neutral-500 mt-6">
              Don't have an account?{" "}
              <a href="/register" className="text-zinc-900 font-bold hover:underline">
                Sign Up
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
