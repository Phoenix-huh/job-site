"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Sparkles, Eye, EyeOff } from "lucide-react";

export default function RegisterPage() {
  const [showPassword, setShowPassword] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setIsLoading(true);

    await new Promise(r => setTimeout(r, 400));

    if (!email || !password) {
      setError("Please fill in all fields.");
    } else if (password.length < 4) {
      setError("Password must be at least 4 characters.");
    } else {
      localStorage.setItem("registered_user", JSON.stringify({ email, password }));
      setSuccess("Registration successful! Redirecting to login...");
      setTimeout(() => { window.location.href = "/login"; }, 1500);
    }

    setIsLoading(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-8 bg-background">
      <div className="w-full max-w-[420px]">
        <div className="flex items-center justify-center gap-2 text-lg font-semibold mb-12">
          <div className="size-8 rounded-lg bg-primary/10 flex items-center justify-center">
            <Sparkles className="size-4 text-primary" />
          </div>
          <span>Shield</span>
        </div>

        <div className="text-center mb-10">
          <h1 className="text-3xl font-bold tracking-tight mb-2">Create an account</h1>
          <p className="text-muted-foreground text-sm">Sign up to get started</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-2">
            <Label htmlFor="email" className="text-sm font-medium">Email</Label>
            <Input
              id="email"
              type="email"
              placeholder="anna@gmail.com"
              value={email}
              autoComplete="off"
              onChange={(e) => setEmail(e.target.value)}
              required
              className="h-12 bg-background border-border/60 focus:border-primary"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="password" className="text-sm font-medium">Password</Label>
            <div className="relative">
              <Input
                id="password"
                type={showPassword ? "text" : "password"}
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="h-12 pr-10 bg-background border-border/60 focus:border-primary"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
              >
                {showPassword ? (
                  <EyeOff className="size-5" />
                ) : (
                  <Eye className="size-5" />
                )}
              </button>
            </div>
          </div>

          {error && (
            <div className="p-3 text-sm text-red-400 bg-red-950/20 border border-red-900/30 rounded-lg">
              {error}
            </div>
          )}
          {success && (
            <div className="p-3 text-sm text-green-400 bg-green-950/20 border border-green-900/30 rounded-lg">
              {success}
            </div>
          )}

          <Button 
            type="submit" 
            className="w-full h-12 text-base font-medium" 
            size="lg" 
            disabled={isLoading}
          >
            {isLoading ? "Signing up..." : "Sign up"}
          </Button>
        </form>

        <div className="text-center text-sm text-muted-foreground mt-8">
          Already have an account?{" "}
          <a href="/login" className="text-foreground font-medium hover:underline">
            Log in
          </a>
        </div>
      </div>
    </div>
  );
}
