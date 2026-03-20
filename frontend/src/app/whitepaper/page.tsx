"use client";

import Link from "next/link";

export default function Whitepaper() {
  return (
    <div className="min-h-screen bg-black text-white selection:bg-indigo-500/30 font-sans">
      {/* Minimalist Nav */}
      <nav className="fixed top-0 w-full z-50 border-b border-white/5 bg-black/40 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3 hover:opacity-80 transition-opacity">
            <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center font-bold text-xl shadow-lg shadow-indigo-500/30">
              R
            </div>
            <span className="font-bold tracking-tighter text-2xl gradient-text">RTFM Agent</span>
          </Link>
          
          <Link href="/dashboard" className="px-5 py-2.5 rounded-full bg-indigo-600 hover:bg-indigo-500 transition-all font-medium text-sm shadow-lg shadow-indigo-600/20">
            Go to Dashboard
          </Link>
        </div>
      </nav>

      <main className="max-w-4xl mx-auto pt-40 pb-32 px-6 space-y-24">
        {/* Header */}
        <div className="space-y-6">
           <h1 className="text-5xl lg:text-7xl font-black tracking-tight leading-tight">
             ARCHITECTURAL <br/>
             <span className="gradient-text uppercase">Whitepaper v1.0</span>
           </h1>
           <p className="text-xl text-white/50 leading-relaxed max-w-2xl">
             An in-depth look at the neural retrieval strategies, security protocols, and performance optimizations powering the RTFM Agent.
           </p>
        </div>

        {/* Section 1 */}
        <section className="space-y-8">
           <div className="text-indigo-500 font-mono text-sm tracking-widest uppercase">[01] Neural Retrieval Engine</div>
           <h2 className="text-3xl font-bold">Semantic Over Keyword</h2>
           <p className="text-white/60 leading-relaxed text-lg">
             Traditional documentation search relies on keyword matching, leading to "no results" for semantically similar queries. RTFM Agent utilizes the **Gemini 2.5 Pro Embedding Model**, mapping documents into a high-dimensional vector space (1536 dimensions). 
           </p>
           <div className="p-6 rounded-2xl bg-white/[0.03] border border-white/10 font-mono text-xs text-indigo-400/80">
              Similarity(A, B) = (A · B) / (||A|| * ||B||) // Cosine Similarity at the core
           </div>
        </section>

        {/* Section 2 */}
        <section className="space-y-8">
           <div className="text-indigo-500 font-mono text-sm tracking-widest uppercase">[02] Multi-Brain Isolation</div>
           <h2 className="text-3xl font-bold">Cryptographically Scoped Contexts</h2>
           <p className="text-white/60 leading-relaxed text-lg">
             Data privacy is non-negotiable. Every document segment (vector) is tagged with a composite metadata key: `user_id` + `brain_id`. Our backend performs strict **Metadata Filtering** at the database layer (Upstash Vector), ensuring that cross-project data leakage is mathematically impossible.
           </p>
        </section>

        {/* Section 3 */}
        <section className="space-y-8">
           <div className="text-indigo-500 font-mono text-sm tracking-widest uppercase">[03] Performance Architecture</div>
           <h2 className="text-3xl font-bold">Edge-Side Semantic Caching</h2>
           <p className="text-white/60 leading-relaxed text-lg">
             To reduce LLM latency and API costs, we implemented a custom **Semantic Cache** using Upstash Redis. Identical or highly similar questions (Threshold &gt; 0.98) are intercepted. This results in response times as low as **40ms**, compared to the typical 2-4 seconds for a fresh LLM generation.
           </p>
        </section>

        {/* Section 4 */}
        <section className="space-y-8">
           <div className="text-indigo-500 font-mono text-sm tracking-widest uppercase">[04] Security & Auth</div>
           <h2 className="text-3xl font-bold">JWT Verification via JWKS</h2>
           <p className="text-white/60 leading-relaxed text-lg">
             Identity is managed by **Clerk**. The FastAPI backend verifies the authenticity of every request by fetching and caching the Public Keys (JWKS) from Clerk's servers, ensuring tokens are signed, not expired, and belong to the authorized user.
           </p>
        </section>

        <div className="pt-20 border-t border-white/5 flex flex-col items-center gap-8">
           <div className="text-center space-y-2">
             <h3 className="text-2xl font-bold">Ready to try it yourself?</h3>
             <p className="text-white/40">Launch your first neural brain in minutes.</p>
           </div>
           <Link href="/dashboard" className="px-10 py-5 rounded-2xl bg-white text-black hover:bg-white/90 font-bold transition-all shadow-xl shadow-white/10">
              Get Started Now
           </Link>
        </div>
      </main>

      <footer className="py-20 border-t border-white/5 text-center text-white/20 text-xs font-mono tracking-widest">
         RTFM-PAPER-RELEASE // 2026.03.20
      </footer>
    </div>
  );
}
