"use client";

import React, { useState, useEffect } from "react";
import { listDocuments, deleteDocument, bulkDeleteDocuments, deleteAllDocuments } from "@/lib/api";
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
  const [selectedDocs, setSelectedDocs] = useState<Set<string>>(new Set());
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    const fetchDocs = async () => {
      try {
        const token = await getToken();
        if (!token) return;
        const data = await listDocuments(token, activeBrainId);
        setDocs(data);
        setSelectedDocs(new Set());
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
    setIsDeleting(true);
    try {
      const token = await getToken();
      if (!token) return;
      await deleteDocument(filename, token, activeBrainId);
      setDocs(docs.filter(d => d.filename !== filename));
      const newSelected = new Set(selectedDocs);
      newSelected.delete(filename);
      setSelectedDocs(newSelected);
    } catch (e) {
      console.error("Delete failed", e);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleSelectAll = () => {
    if (selectedDocs.size === docs.length) {
      setSelectedDocs(new Set());
    } else {
      setSelectedDocs(new Set(docs.map(d => d.filename)));
    }
  };

  const handleSelect = (filename: string) => {
    const newSet = new Set(selectedDocs);
    if (newSet.has(filename)) newSet.delete(filename);
    else newSet.add(filename);
    setSelectedDocs(newSet);
  };

  const handleBulkDelete = async () => {
    if (selectedDocs.size === 0) return;
    if (!confirm(`Are you sure you want to delete ${selectedDocs.size} documents?`)) return;
    setIsDeleting(true);
    try {
      const token = await getToken();
      if (!token) return;
      await bulkDeleteDocuments(Array.from(selectedDocs), token, activeBrainId);
      setDocs(docs.filter(d => !selectedDocs.has(d.filename)));
      setSelectedDocs(new Set());
    } catch (e) {
      console.error("Bulk delete failed", e);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleDeleteAll = async () => {
    if (docs.length === 0) return;
    if (!confirm(`DANGER: Are you sure you want to completely wipe ALL documents from this Brain?`)) return;
    setIsDeleting(true);
    try {
      const token = await getToken();
      if (!token) return;
      await deleteAllDocuments(token, activeBrainId);
      setDocs([]);
      setSelectedDocs(new Set());
    } catch (e) {
      console.error("Delete all failed", e);
    } finally {
      setIsDeleting(false);
    }
  };

  if (isLoading) return <div className="animate-pulse text-[10px] uppercase tracking-widest opacity-30">Loading Registry...</div>;

  const isAllSelected = docs.length > 0 && selectedDocs.size === docs.length;

  return (
    <div className="w-full bg-white/5 border border-white/10 rounded-2xl p-6 backdrop-blur-xl min-h-[100px] flex flex-col">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-4 gap-2">
        <h3 className="text-xs font-bold uppercase tracking-[0.2em] opacity-50 flex items-center gap-2">
           Knowledge Base 
           {docs.length > 0 && <span className="bg-indigo-500/10 text-indigo-400 px-2 py-0.5 rounded-full text-[9px]">{docs.length}</span>}
        </h3>
        
        {docs.length > 0 && (
          <div className="flex flex-wrap items-center gap-2">
            {selectedDocs.size > 0 && (
              <button 
                onClick={handleBulkDelete}
                disabled={isDeleting}
                className="text-[10px] uppercase font-bold text-red-400 hover:bg-red-500/10 px-2 py-1 rounded border border-red-500/20 transition-all opacity-80 hover:opacity-100 disabled:opacity-30 cursor-pointer"
              >
                Delete Selected ({selectedDocs.size})
              </button>
            )}
            <button 
              onClick={handleDeleteAll}
              disabled={isDeleting}
              className="text-[10px] uppercase font-bold text-red-500 hover:bg-red-500/20 px-2 py-1 rounded border border-red-500/30 transition-all opacity-80 hover:opacity-100 disabled:opacity-30 cursor-pointer"
            >
              Wipe Brain
            </button>
          </div>
        )}
      </div>
      
      {docs.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-2 opacity-20 py-4">
           <div className="w-8 h-8 rounded-full border border-dashed border-white/40 flex items-center justify-center text-lg">
             ∅
           </div>
           <span className="text-[10px] uppercase tracking-tighter">No Knowledge Ingested</span>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-3 px-2 mb-2">
            <input 
              type="checkbox" 
              checked={isAllSelected}
              onChange={handleSelectAll}
              disabled={isDeleting}
              className="w-3.5 h-3.5 rounded bg-white/10 border-white/20 text-indigo-500 focus:ring-indigo-500 cursor-pointer"
            />
            <span className="text-[10px] uppercase tracking-widest opacity-40 cursor-pointer" onClick={handleSelectAll}>Select All</span>
          </div>
          
          <div className="space-y-2 max-h-[300px] overflow-y-auto pr-2 custom-scrollbar">
            {docs.map((doc) => (
              <div 
                key={doc.filename} 
                className={`flex items-center justify-between group p-2 rounded-lg transition-colors border cursor-pointer ${
                  selectedDocs.has(doc.filename) ? 'bg-indigo-500/10 border-indigo-500/20' : 'bg-white/5 border-transparent hover:border-white/10'
                }`}
                onClick={() => handleSelect(doc.filename)}
              >
                <div className="flex items-center gap-3 w-full">
                  <input 
                    type="checkbox" 
                    checked={selectedDocs.has(doc.filename)}
                    onChange={() => {}} // Handled by parent div
                    disabled={isDeleting}
                    className="w-3.5 h-3.5 rounded bg-white/10 border-white/20 text-indigo-500 focus:ring-indigo-500 cursor-pointer flex-shrink-0"
                  />
                  <div className="flex flex-col gap-0.5 flex-1 min-w-0">
                    <span className="text-sm font-medium text-white/80 group-hover:text-white transition-colors truncate">
                      {doc.filename}
                    </span>
                    <span className="text-[10px] font-mono opacity-40 truncate">
                      v{doc.version} • {new Date(doc.ingested_at).toLocaleTimeString()}
                    </span>
                  </div>
                  
                  <button 
                    onClick={(e) => { e.stopPropagation(); handleDelete(doc.filename); }}
                    disabled={isDeleting}
                    className="opacity-0 group-hover:opacity-100 p-1.5 hover:bg-red-500/10 rounded-lg text-red-400/60 hover:text-red-400 transition-all flex-shrink-0 disabled:opacity-30"
                    title="Delete item"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
