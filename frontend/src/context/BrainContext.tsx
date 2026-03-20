"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { useAuth } from "@clerk/nextjs";
import { listBrains, createBrain, deleteBrain } from "@/lib/api";

interface BrainContextType {
  activeBrainId: string;
  setActiveBrainId: (id: string) => void;
  brains: string[];
  isLoading: boolean;
  refreshBrains: () => Promise<void>;
  createNewBrain: (id: string) => Promise<boolean>;
  removeBrain: (id: string) => Promise<boolean>;
}

const BrainContext = createContext<BrainContextType | undefined>(undefined);

export function BrainProvider({ children }: { children: ReactNode }) {
  const { getToken, isLoaded, userId } = useAuth();
  const [activeBrainId, setActiveBrainId] = useState("default");
  const [brains, setBrains] = useState<string[]>(["default"]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchBrains = async () => {
    try {
      const token = await getToken();
      if (!token) return;
      const data = await listBrains(token);
      setBrains(data);
      if (!data.includes(activeBrainId)) {
        setActiveBrainId(data[0] || "default");
      }
    } catch (e) {
      console.error("Failed to fetch brains", e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isLoaded && userId) {
      fetchBrains();
    }
  }, [isLoaded, userId, getToken]);

  const createNewBrain = async (id: string) => {
    const token = await getToken();
    if (!token) return false;
    const success = await createBrain(id, token);
    if (success) await fetchBrains();
    return success;
  };

  const removeBrain = async (id: string) => {
    const token = await getToken();
    if (!token) return false;
    const success = await deleteBrain(id, token);
    if (success) {
      await fetchBrains();
      if (activeBrainId === id) setActiveBrainId("default");
    }
    return success;
  };

  return (
    <BrainContext.Provider value={{ 
      activeBrainId, 
      setActiveBrainId, 
      brains, 
      isLoading, 
      refreshBrains: fetchBrains,
      createNewBrain,
      removeBrain
    }}>
      {children}
    </BrainContext.Provider>
  );
}

export function useBrain() {
  const context = useContext(BrainContext);
  if (context === undefined) {
    throw new Error("useBrain must be used within a BrainProvider");
  }
  return context;
}
