"use client";

import React, { useState } from "react";
import { useBrain } from "@/context/BrainContext";

export function BrainSelector() {
  const { activeBrainId, setActiveBrainId, brains, createNewBrain, removeBrain } = useBrain();
  const [isOpen, setIsOpen] = useState(false);
  const [newBrainName, setNewBrainName] = useState("");
  const [isCreating, setIsCreating] = useState(false);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newBrainName.trim()) return;
    const success = await createNewBrain(newBrainName.trim());
    if (success) {
      setNewBrainName("");
      setIsCreating(false);
    }
  };

  return (
    <div className="relative">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-all group"
      >
        <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 shadow-[0_0_8px_rgba(99,102,241,0.6)]"></div>
        <span className="text-xs font-mono uppercase tracking-tighter opacity-70 group-hover:opacity-100">{activeBrainId}</span>
        <svg className={`w-3 h-3 transition-transform ${isOpen ? "rotate-180" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M19 9l-7 7-7-7" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
      </button>

      {isOpen && (
        <div className="absolute top-full mt-2 right-0 w-56 glass rounded-xl border border-white/10 shadow-2xl z-50 overflow-hidden animate-in fade-in slide-in-from-top-2">
          <div className="p-2 space-y-1">
            {brains.map((id) => (
              <div key={id} className="flex items-center group">
                <button
                  onClick={() => { setActiveBrainId(id); setIsOpen(false); }}
                  className={`flex-1 text-left px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                    activeBrainId === id ? "bg-indigo-600 text-white" : "hover:bg-white/10 text-white/60"
                  }`}
                >
                  {id}
                </button>
                {id !== "default" && (
                  <button 
                    onClick={() => removeBrain(id)}
                    className="p-2 opacity-0 group-hover:opacity-100 text-white/20 hover:text-red-500 transition-all"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
                  </button>
                )}
              </div>
            ))}
          </div>

          <div className="p-2 border-t border-white/10 bg-white/5">
            {isCreating ? (
              <form onSubmit={handleCreate} className="flex gap-2">
                <input 
                  autoFocus
                  value={newBrainName}
                  onChange={(e) => setNewBrainName(e.target.value)}
                  placeholder="Space Name..."
                  className="flex-1 bg-black/40 border border-white/10 rounded-md px-2 py-1 text-[10px] focus:outline-none focus:border-indigo-500"
                />
                <button type="submit" className="text-[10px] text-indigo-400 font-bold uppercase">Add</button>
              </form>
            ) : (
              <button 
                onClick={() => setIsCreating(true)}
                className="w-full text-center py-1 text-[10px] uppercase tracking-widest opacity-40 hover:opacity-100 transition-all"
              >
                + New Space
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
