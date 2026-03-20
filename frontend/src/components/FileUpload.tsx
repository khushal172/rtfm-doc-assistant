"use client";

import React, { useState } from "react";
import { ingestDocument } from "@/lib/api";

export function FileUpload() {
  const [isUploading, setIsUploading] = useState(false);
  const [status, setStatus] = useState<"idle" | "success" | "error">("idle");

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setStatus("idle");
    try {
      await ingestDocument(file);
      setStatus("success");
    } catch (error) {
      console.error("Upload error:", error);
      setStatus("error");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="w-full max-w-md p-6 glass rounded-2xl space-y-4">
      <div className="space-y-1">
        <h3 className="text-lg font-medium gradient-text">Ingest Documentation</h3>
        <p className="text-xs opacity-50">Upload Markdown or Text files to train your agent.</p>
      </div>

      <label className="flex flex-col items-center justify-center h-32 w-full border-2 border-dashed border-white/10 rounded-xl hover:bg-white/5 transition-all cursor-pointer group">
        <div className="flex flex-col items-center justify-center pt-5 pb-6">
          <svg className="w-8 h-8 mb-3 text-white/30 group-hover:text-indigo-400 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
          <p className="text-sm text-white/40 group-hover:text-white/60 transition-colors">
            {isUploading ? "Uploading..." : "Click to select file"}
          </p>
        </div>
        <input type="file" className="hidden" accept=".md,.txt" onChange={handleFileChange} disabled={isUploading} />
      </label>

      {status === "success" && (
        <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/20 text-green-400 text-xs flex items-center gap-2">
           <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M5 13l4 4L19 7" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
           Brain updated successfully.
        </div>
      )}

      {status === "error" && (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-2">
           <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
           Critial error during ingestion.
        </div>
      )}
    </div>
  );
}
