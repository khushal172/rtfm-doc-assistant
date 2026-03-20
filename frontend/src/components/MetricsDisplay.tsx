"use client";

import React, { useState, useEffect } from "react";
import { getMetrics } from "@/lib/api";
import { useAuth } from "@clerk/nextjs";
import { useBrain } from "@/context/BrainContext";

export function MetricsDisplay() {
  const { getToken } = useAuth();
  const { activeBrainId } = useBrain();
  const [metrics, setMetrics] = useState<{ hits: number; misses: number; hit_rate: string } | null>(null);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const token = await getToken();
        if (!token) return;
        
        const data = await getMetrics(token, activeBrainId);
        setMetrics(data);
      } catch (e) {
        console.error("Metrics fail", e);
      }
    };
    
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 10000); // 10s refresh
    return () => clearInterval(interval);
  }, [getToken, activeBrainId]);

  if (!metrics) return null;

  return (
    <div className="w-full max-w-md p-6 glass rounded-2xl">
      <h3 className="text-xs font-semibold uppercase tracking-widest opacity-40 mb-6">Efficiency Engine</h3>
      
      <div className="grid grid-cols-2 gap-4">
        <div className="p-4 bg-white/5 rounded-xl border border-white/5">
          <div className="text-2xl font-bold">{metrics.hits}</div>
          <div className="text-[10px] opacity-40 uppercase tracking-tighter">Semantic Hits</div>
        </div>
        <div className="p-4 bg-white/5 rounded-xl border border-white/5">
          <div className="text-2xl font-bold">{metrics.hit_rate}</div>
          <div className="text-[10px] opacity-40 uppercase tracking-tighter">Cache Rate</div>
        </div>
      </div>
      
      <div className="mt-4 pt-4 border-t border-white/5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse shadow-[0_0_8px_rgba(34,197,94,0.5)]"></div>
          <span className="text-[10px] uppercase opacity-40">System Online</span>
        </div>
        <div className="text-[10px] uppercase opacity-40">Misses: {metrics.misses}</div>
      </div>
    </div>
  );
}
