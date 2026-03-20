"use client";

import { useBrain } from "@/context/BrainContext";
import { Navbar } from "@/components/Navbar";
import { GithubIngest } from "@/components/GithubIngest";
import Link from "next/link";

export default function GithubPage() {
  const { activeBrainId } = useBrain();

  return (
    <div className="min-h-screen flex flex-col bg-black text-white selection:bg-indigo-500/30">
      <Navbar />
      
      <main className="flex-1 flex flex-col items-center p-8 space-y-12">
        <div className="z-10 max-w-5xl w-full flex flex-col items-center space-y-4">
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-[10px] font-bold uppercase tracking-[0.2em]">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-500"></span>
            </span>
            Codebase Intelligence
          </div>
          <h1 className="text-5xl font-extrabold tracking-tighter gradient-text">GITHUB SYNC</h1>
          <p className="text-sm font-mono opacity-50">Ingest entire repositories into your active brain context</p>
        </div>

        <GithubIngest activeBrainId={activeBrainId} />

        <div className="flex flex-col items-center gap-6">
          <Link href="/dashboard" className="px-6 py-3 rounded-2xl bg-white/5 hover:bg-white/10 transition-all font-medium text-sm border border-white/5">
             ← Back to Dashboard
          </Link>
          
          <div className="flex gap-4 opacity-10 text-[9px] uppercase tracking-[0.3em] font-medium font-mono">
            <span>Recursive Tree Parsing</span>
            <span>•</span>
            <span>Upstash Vector</span>
            <span>•</span>
            <span>Neural Indexing</span>
          </div>
        </div>
      </main>
    </div>
  );
}
