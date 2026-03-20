"use client";

import { useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { ingestGithub } from "@/lib/api";

export function GithubIngest({ activeBrainId }: { activeBrainId: string }) {
  const { getToken } = useAuth();
  const [url, setUrl] = useState("");
  const [pat, setPat] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleIngest = async () => {
    if (!url) return;
    setLoading(true);
    setStatus("Initiating GitHub synchronization...");
    
    try {
      const token = await getToken();
      await ingestGithub(url, token!, activeBrainId, pat || undefined);
      setStatus("Successfully queued for background indexing. This may take a few minutes for larger repos.");
      setUrl("");
    } catch (error) {
      setStatus(`Error: ${error instanceof Error ? error.message : "Unknown error"}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-2xl p-8 rounded-3xl bg-white/[0.03] border border-white/10 space-y-6">
      <div className="space-y-2">
        <h2 className="text-2xl font-bold tracking-tight">GitHub Intelligence</h2>
        <p className="text-sm text-white/40 leading-relaxed">
          Paste a public repository URL to index its documentation and source code into your active brain.
        </p>
      </div>

      <div className="space-y-4">
        <div className="space-y-2">
           <label className="text-[10px] uppercase tracking-widest font-bold opacity-40 ml-1">Repository URL</label>
           <input 
             type="text" 
             placeholder="https://github.com/owner/repo" 
             className="w-full bg-black/40 border border-white/5 rounded-2xl p-4 text-sm focus:outline-none focus:border-indigo-500/50 transition-all"
             value={url}
             onChange={(e) => setUrl(e.target.value)}
           />
        </div>

        <div className="space-y-2">
           <label className="text-[10px] uppercase tracking-widest font-bold opacity-40 ml-1">GitHub Personal Access Token (Optional)</label>
           <input 
             type="password" 
             placeholder="ghp_xxxxxxxxxxxx" 
             className="w-full bg-black/40 border border-white/5 rounded-2xl p-4 text-sm focus:outline-none focus:border-indigo-500/50 transition-all"
             value={pat}
             onChange={(e) => setPat(e.target.value)}
           />
           <p className="text-[9px] opacity-20 ml-1 italic">Providing a PAT ensures higher rate limits for large repositories.</p>
        </div>

        <button 
          onClick={handleIngest}
          disabled={loading || !url}
          className={`w-full py-4 rounded-2xl font-bold transition-all shadow-xl flex items-center justify-center gap-2 ${
            loading || !url 
              ? "bg-white/5 text-white/20 cursor-not-allowed" 
              : "bg-indigo-600 hover:bg-indigo-500 shadow-indigo-600/20"
          }`}
        >
          {loading && <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin"></div>}
          {loading ? "Synchronizing..." : "Sync Repository"}
        </button>

        {status && (
          <div className={`p-4 rounded-xl text-xs font-medium border ${
            status.includes("Error") ? "bg-red-500/10 border-red-500/20 text-red-400" : "bg-indigo-500/10 border-indigo-500/20 text-indigo-300"
          }`}>
            {status}
          </div>
        )}
      </div>
    </div>
  );
}
