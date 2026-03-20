"use client";

import Link from "next/link";
import Image from "next/image";
import { SignInButton, SignUpButton, useUser } from "@clerk/nextjs";

export default function LandingPage() {
  const { isSignedIn, isLoaded } = useUser();

  return (
    <div className="min-h-screen bg-black text-white selection:bg-indigo-500/30">
      {/* Minimalist Nav */}
      <nav className="fixed top-0 w-full z-50 border-b border-white/5 bg-black/40 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center font-bold text-xl shadow-lg shadow-indigo-500/30">
              R
            </div>
            <span className="font-bold tracking-tighter text-2xl gradient-text">RTFM Agent</span>
          </div>
          
          <div className="flex items-center gap-4">
            {isLoaded && (
              <>
                {isSignedIn ? (
                  <Link href="/dashboard" className="px-5 py-2.5 rounded-full bg-white/10 hover:bg-white/20 transition-all font-medium text-sm border border-white/10">
                    Dashboard
                  </Link>
                ) : (
                  <>
                    <SignInButton mode="modal">
                      <button className="px-5 py-2.5 rounded-full bg-white/10 hover:bg-white/20 transition-all font-medium text-sm border border-white/10">
                        Sign In
                      </button>
                    </SignInButton>
                    <SignUpButton mode="modal">
                      <button className="px-5 py-2.5 rounded-full bg-indigo-600 hover:bg-indigo-500 transition-all font-medium text-sm shadow-lg shadow-indigo-600/20">
                        Get Started
                      </button>
                    </SignUpButton>
                  </>
                )}
              </>
            )}
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative pt-40 pb-20 px-6 overflow-hidden">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full -z-10 opacity-40">
           <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[600px] bg-indigo-600/20 blur-[120px] rounded-full"></div>
        </div>
        
        <div className="max-w-7xl mx-auto flex flex-col lg:flex-row items-center gap-16">
          <div className="flex-1 text-center lg:text-left space-y-8">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-[10px] font-bold uppercase tracking-[0.2em]">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-500"></span>
              </span>
              Next-Gen Retrieval Engine
            </div>
            
            <h1 className="text-6xl lg:text-8xl font-black tracking-tight leading-[0.9] text-white">
              YOUR DOCS,<br/>
              <span className="gradient-text">BUT SMARTER.</span>
            </h1>
            
            <p className="text-xl text-white/50 max-w-xl mx-auto lg:mx-0 leading-relaxed">
              RTFM Agent is a high-performance documentation assistant. It uses proprietary neural indexing to provide context-aware answers in milliseconds.
            </p>
            
            <div className="flex flex-col sm:flex-row gap-4 justify-center lg:justify-start pt-4">
              <Link href={isSignedIn ? "/dashboard" : "/sign-up"} className="px-8 py-4 rounded-2xl bg-indigo-600 hover:bg-indigo-500 transition-all font-bold text-lg shadow-xl shadow-indigo-600/30 text-center">
                Launch Application
              </Link>
              <button className="px-8 py-4 rounded-2xl bg-white/5 hover:bg-white/10 transition-all font-bold text-lg border border-white/10 text-center">
                Read Whitepaper
              </button>
            </div>
          </div>
          
          <div className="flex-1 relative w-full lg:w-auto h-[400px] lg:h-[600px] rounded-3xl overflow-hidden border border-white/10 shadow-2xl skew-y-3 lg:-skew-y-3 hover:skew-y-0 transition-transform duration-700">
             <Image 
               src="/hero.png" 
               alt="Neural Indexing" 
               fill 
               className="object-cover"
             />
             <div className="absolute inset-0 bg-gradient-to-t from-black via-transparent to-transparent"></div>
          </div>
        </div>
      </section>

      {/* Feature Section */}
      <section className="py-32 px-6 border-t border-white/5 bg-white/[0.01]">
        <div className="max-w-7xl mx-auto space-y-20">
          <div className="text-center space-y-4">
            <h2 className="text-4xl font-bold tracking-tight">ENGINEERED FOR PRECISION</h2>
            <p className="text-white/40 max-w-2xl mx-auto">Built on a foundation of vector-native technologies and large language models.</p>
          </div>
          
          <div className="grid md:grid-cols-3 gap-8">
            <FeatureCard 
              title="Multi-Brain Isolation" 
              desc="Create distinct knowledge spaces for different projects. Data is cryptographically isolated per brain."
              icon="🧠"
              delay="delay-100"
            />
            <FeatureCard 
              title="Semantic Caching" 
              desc="Identical queries are intercepted at the edge. Instant responses with zero GPU compute overhead."
              icon="⚡"
              delay="delay-200"
            />
            <FeatureCard 
              title="Long-Term Memory" 
              desc="Persistent context extraction across sessions. The agent learns your preferences and project details."
              icon="💾"
              delay="delay-300"
            />
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-20 bg-indigo-600 text-center">
          <div className="max-w-7xl mx-auto px-6 grid grid-cols-2 md:grid-cols-4 gap-12 text-white font-bold">
            <div className="space-y-1">
              <div className="text-4xl tracking-tighter">1536</div>
              <div className="text-[10px] uppercase opacity-60 tracking-widest">Dimensions</div>
            </div>
            <div className="space-y-1">
              <div className="text-4xl tracking-tighter">~240ms</div>
              <div className="text-[10px] uppercase opacity-60 tracking-widest">Latency</div>
            </div>
            <div className="space-y-1">
              <div className="text-4xl tracking-tighter">99.9%</div>
              <div className="text-[10px] uppercase opacity-60 tracking-widest">Recall</div>
            </div>
            <div className="space-y-1">
              <div className="text-4xl tracking-tighter">Gemini 2.5</div>
              <div className="text-[10px] uppercase opacity-60 tracking-widest">Model Core</div>
            </div>
          </div>
      </section>
      
      {/* Footer */}
      <footer className="py-20 border-t border-white/5 text-center text-white/20 text-xs font-mono tracking-widest">
         RTFM-AGENT-ALPHA // NO RIGHTS RESERVED // 2026.03.20
      </footer>
    </div>
  );
}

function FeatureCard({ title, desc, icon, delay }: { title: string, desc: string, icon: string, delay: string }) {
  return (
    <div className={`p-8 rounded-3xl bg-white/[0.03] border border-white/5 space-y-6 hover:bg-white/[0.05] transition-all group hover:-translate-y-2 duration-300 ${delay}`}>
      <div className="text-4xl opacity-50 group-hover:opacity-100 transition-opacity">{icon}</div>
      <h3 className="text-2xl font-bold tracking-tight">{title}</h3>
      <p className="text-white/40 leading-relaxed text-sm">{desc}</p>
    </div>
  )
}
