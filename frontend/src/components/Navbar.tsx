"use client";

import { UserButton } from "@clerk/nextjs";

export function Navbar() {
  return (
    <nav className="w-full border-b border-white/5 bg-black/20 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
        <div className="flex items-center gap-2">
           <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center font-bold text-white shadow-lg shadow-indigo-500/20">
              R
           </div>
           <span className="font-bold tracking-tighter text-lg gradient-text">RTFM Agent</span>
        </div>
        
        <div className="flex items-center gap-6">
           <div className="hidden md:flex items-center gap-4 text-[10px] uppercase tracking-widest opacity-40">
              <span>Secure Session</span>
              <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></div>
           </div>
           <UserButton />
        </div>
      </div>
    </nav>
  );
}
