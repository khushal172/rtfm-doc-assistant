"use client";

import React, { useState, useEffect } from "react";
import { listDocuments, deleteDocument } from "@/lib/api";
import { useAuth } from "@clerk/nextjs";
import { useBrain } from "@/context/BrainContext";

interface DocumentMetadata {
  filename: string;
  version: string;
  ingested_at: string;
}

export function DocumentList() {
  const { getToken } = useAuth();
  const { activeBrainId } = useBrain();
  const [docs, setDocs] = useState<DocumentMetadata[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchDocs = async () => {
      try {
        const token = await getToken();
        if (!token) return;
        const data = await listDocuments(token, activeBrainId);
        setDocs(data);
      } catch (e) {
        console.error("Failed to fetch docs", e);
      } finally {
        setIsLoading(false);
      }
    };
    fetchDocs();

    // Listen for custom ingestion events
    window.addEventListener("document-ingested", fetchDocs);
    return () => window.removeEventListener("document-ingested", fetchDocs);
  }, [getToken, activeBrainId]);

  const handleDelete = async (filename: string) => {
    if (!confirm(`Are you sure you want to delete ${filename}?`)) return;
    try {
      const token = await getToken();
      if (!token) return;
      await deleteDocument(filename, token, activeBrainId);
      setDocs(docs.filter(d => d.filename !== filename));
    } catch (e) {
      console.error("Delete failed", e);
    }
  };

  if (isLoading) return <div className="animate-pulse text-[10px] uppercase tracking-widest opacity-30">Loading Registry...</div>;

  return (
    <div className="w-full bg-white/5 border border-white/10 rounded-2xl p-6 backdrop-blur-xl min-h-[100px] flex flex-col">
      <h3 className="text-xs font-bold uppercase tracking-[0.2em] mb-4 opacity-50 flex items-center justify-between">
         Knowledge Base 
         {docs.length > 0 && <span className="bg-indigo-500/10 text-indigo-400 px-2 py-0.5 rounded-full text-[9px]">{docs.length}</span>}
      </h3>
      
      {docs.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-2 opacity-20 py-4">
           <div className="w-8 h-8 rounded-full border border-dashed border-white/40 flex items-center justify-center text-lg">
             ∅
           </div>
           <span className="text-[10px] uppercase tracking-tighter">No Knowledge Ingested</span>
        </div>
      ) : (
        <div className="space-y-4 max-h-[300px] overflow-y-auto pr-2 custom-scrollbar">
          {docs.map((doc) => (
            <div key={doc.filename} className="flex items-center justify-between group">
              <div className="flex flex-col gap-0.5">
                <span className="text-sm font-medium text-white/80 group-hover:text-white transition-colors truncate max-w-[180px]">
                  {doc.filename}
                </span>
                <span className="text-[10px] font-mono opacity-40">
                  v{doc.version} • {new Date(doc.ingested_at).toLocaleTimeString()}
                </span>
              </div>
              <div className="flex items-center gap-3">
                <button 
                  onClick={() => handleDelete(doc.filename)}
                  className="opacity-0 group-hover:opacity-100 p-1.5 hover:bg-red-500/10 rounded-lg text-red-400/60 hover:text-red-400 transition-all"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
                </button>
                <div className="w-2 h-2 rounded-full bg-indigo-500 shadow-lg shadow-indigo-500/40"></div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
