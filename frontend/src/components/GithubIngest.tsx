import { useState, useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import { ingestGithub, getIngestStatus } from "@/lib/api";

export function GithubIngest({ activeBrainId }: { activeBrainId: string }) {
  const { getToken } = useAuth();
  const [url, setUrl] = useState("");
  const [pat, setPat] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState<{ processed_files: number; total_files: number; status: string; repo?: string } | null>(null);

  // Poll for ingestion progress
  useEffect(() => {
    let interval: NodeJS.Timeout;

    const checkStatus = async () => {
      try {
        const token = await getToken();
        if (!token) return;
        const currentStatus = await getIngestStatus(token);
        
        console.log("Current ingest status:", currentStatus);

        if (currentStatus && currentStatus.status !== "idle") {
          // Check for staleness (e.g., more than 2 minutes old)
          const statusTime = new Date(currentStatus.timestamp).getTime();
          const now = new Date().getTime();
          const isStale = currentStatus.status === "completed" && (now - statusTime > 120000);

          if (isStale) {
            setProgress(null);
            setLoading(false);
            return;
          }

          // If we just clicked Sync (loading is true), ignore any "completed" 
          // status because it MUST be from a previous run.
          if (loading && currentStatus.status === "completed") {
            return;
          }

          setProgress(currentStatus);
          
          if (currentStatus.status === "indexing") {
            setLoading(true);
          } else if (currentStatus.status === "completed") {
            setLoading(false);
          }
        } else {
          // IMPORTANT: If status is idle, clear the progress card!
          setProgress(null);
        }
      } catch (err) {
        console.error("Status polling failed:", err);
      }
    };

    checkStatus();
    interval = setInterval(checkStatus, 3000);
    return () => clearInterval(interval);
  }, [getToken, loading]);

  const handleIngest = async () => {
    if (!url) return;
    setLoading(true);
    setProgress(null); // Immediately clear old progress card
    setStatus("Initiating GitHub synchronization...");
    
    try {
      const token = await getToken();
      await ingestGithub(url, token!, activeBrainId, pat || undefined);
      setStatus(null);
      setUrl("");
    } catch (error) {
      setStatus(`Error: ${error instanceof Error ? error.message : "Unknown error"}`);
      setLoading(false);
    }
  };

  const percent = progress?.total_files ? Math.round((progress.processed_files / progress.total_files) * 100) : 0;

  return (
    <div className="w-full max-w-2xl p-8 rounded-3xl bg-white/[0.03] border border-white/10 space-y-6">
      <div className="space-y-2">
        <h2 className="text-2xl font-bold tracking-tight">GitHub Intelligence</h2>
        <p className="text-sm text-white/40 leading-relaxed">
          Paste a public repository URL to index its documentation and source code locally with zero rate limits.
        </p>
      </div>

      {progress && progress.status !== "idle" && (
        <div className="p-6 rounded-2xl bg-indigo-500/10 border border-indigo-500/30 space-y-4">
           <div className="flex items-start justify-between">
              <div className="space-y-1">
                <p className="text-[10px] uppercase tracking-widest font-bold text-indigo-400">Current Synchronization</p>
                <p className="text-sm font-semibold truncate max-w-[300px]">{progress.repo || "Unknown Repo"}</p>
              </div>
              <div className="text-right">
                <p className="text-xl font-bold text-indigo-300">{percent}%</p>
                <p className="text-[10px] opacity-40 uppercase tracking-tighter">Processed</p>
              </div>
           </div>

           <div className="w-full h-2 bg-white/10 rounded-full overflow-hidden">
              <div 
                className="h-full bg-indigo-500 transition-all duration-500"
                style={{ width: `${percent}%` }}
              ></div>
           </div>

           <div className="flex justify-between items-center text-[10px] font-medium opacity-60">
              <span>{progress.processed_files} / {progress.total_files} files indexed</span>
              <span className="capitalize px-2 py-0.5 rounded-full bg-white/10 border border-white/10">{progress.status}</span>
           </div>
        </div>
      )}

      <div className="space-y-4">
        <div className="space-y-2 text-left">
           <label className="text-[10px] uppercase tracking-widest font-bold opacity-40 ml-1">Repository URL</label>
           <input 
             type="text" 
             placeholder="https://github.com/owner/repo" 
             className="w-full bg-black/40 border border-white/5 rounded-2xl p-4 text-sm focus:outline-none focus:border-indigo-500/50 transition-all"
             value={url}
             onChange={(e) => setUrl(e.target.value)}
             disabled={loading}
           />
        </div>

        <div className="space-y-2 text-left">
           <label className="text-[10px] uppercase tracking-widest font-bold opacity-40 ml-1">GitHub Personal Access Token (Optional)</label>
           <input 
             type="password" 
             placeholder="ghp_xxxxxxxxxxxx" 
             className="w-full bg-black/40 border border-white/5 rounded-2xl p-4 text-sm focus:outline-none focus:border-indigo-500/50 transition-all"
             value={pat}
             onChange={(e) => setPat(e.target.value)}
             disabled={loading}
           />
           <p className="text-[9px] opacity-20 ml-1 italic">Optional for public repos, but resolves 403 bandwidth issues.</p>
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
          {loading ? "Synchronizing Codebase..." : "Sync Repository"}
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
