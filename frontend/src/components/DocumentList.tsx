"use client";

import React, { useState, useEffect } from "react";
import { listDocuments } from "@/lib/api";
import { useAuth } from "@clerk/nextjs";

interface DocumentMetadata {
  filename: string;
  version: string;
  ingested_at: string;
}

export function DocumentList() {
  const { getToken } = useAuth();
  const [docs, setDocs] = useState<DocumentMetadata[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchDocs = async () => {
      try {
        const token = await getToken();
        if (!token) return;
        const data = await listDocuments(token);
        setDocs(data);
      } catch (e) {
        console.error("Failed to fetch docs", e);
      } finally {
        setIsLoading(false);
      }
    };
    fetchDocs();
  }, [getToken]);

  if (isLoading) return <div className="animate-pulse text-[10px] uppercase tracking-widest opacity-30">Loading Registry...</div>;
  if (docs.length === 0) return null;

  return (
    <div className="w-full bg-white/5 border border-white/10 rounded-2xl p-6 backdrop-blur-xl">
      <h3 className="text-xs font-bold uppercase tracking-[0.2em] mb-4 opacity-50 flex items-center justify-between">
         Knowledge Base 
         <span className="bg-indigo-500/10 text-indigo-400 px-2 py-0.5 rounded-full text-[9px]">{docs.length}</span>
      </h3>
      <div className="space-y-4 max-h-[300px] overflow-y-auto pr-2 custom-scrollbar">
        {docs.map((doc) => (
          <div key={doc.filename} className="flex items-center justify-between group">
            <div className="flex flex-col gap-0.5">
              <span className="text-sm font-medium text-white/80 group-hover:text-white transition-colors truncate max-w-[180px]">
                {doc.filename}
              </span>
              <span className="text-[10px] font-mono opacity-40">
                v{doc.version} • {new Date(doc.ingested_at).toLocaleDateString()}
              </span>
            </div>
            <div className="w-2 h-2 rounded-full bg-indigo-500 shadow-lg shadow-indigo-500/40"></div>
          </div>
        ))}
      </div>
    </div>
  );
}
