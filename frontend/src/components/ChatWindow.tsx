"use client";

import React, { useState, useRef, useEffect } from "react";
import { ChatMessage, streamChat } from "@/lib/api";
import { v4 as uuidv4 } from "uuid";
import { useAuth } from "@clerk/nextjs";
import { useBrain } from "@/context/BrainContext";

export function ChatWindow() {
  const { getToken } = useAuth();
  const { activeBrainId } = useBrain();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sessionId] = useState(() => uuidv4());
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Clear chat when switching brains
  useEffect(() => {
    setMessages([]);
  }, [activeBrainId]);

  useEffect(() => {
    if (scrollRef.current) {
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMsg: ChatMessage = { role: "user", content: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    try {
      const token = await getToken();
      if (!token) throw new Error("Not authenticated");

      let aiContent = "";
      const aiMsg: ChatMessage = { role: "assistant", content: "" };
      setMessages((prev) => [...prev, aiMsg]);

      for await (const chunk of streamChat(input, token, sessionId, activeBrainId)) {
        aiContent += chunk;
        setMessages((prev) => {
          const newMsgs = [...prev];
          newMsgs[newMsgs.length - 1] = { role: "assistant", content: aiContent };
          return newMsgs;
        });
      }
    } catch (error) {
      console.error("Chat error:", error);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "⚠️ Sorry, I encountered an error connecting to the brain center." },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[600px] w-full max-w-2xl glass rounded-2xl overflow-hidden">
      <div className="p-4 border-b border-white/10 bg-white/5">
        <h2 className="text-sm font-semibold uppercase tracking-wider opacity-60">RTFM Assistant</h2>
      </div>

      <div ref={scrollRef} className="flex-1 p-4 overflow-y-auto space-y-4">
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center opacity-40 text-center space-y-2">
            <p className="text-2xl font-light">Welcome, Commander.</p>
            <p className="text-sm">Upload a document to begin the briefing.</p>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[85%] p-3 rounded-2xl text-sm leading-relaxed ${
                msg.role === "user" ? "chat-bubble-user rounded-tr-none" : "chat-bubble-ai rounded-tl-none"
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
        {isLoading && messages[messages.length - 1]?.content === "" && (
          <div className="flex justify-start">
             <div className="chat-bubble-ai p-3 rounded-2xl rounded-tl-none animate-pulse">
                ...
             </div>
          </div>
        )}
      </div>

      <form onSubmit={handleSend} className="p-4 border-t border-white/10 bg-white/5 flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about the documentation..."
          className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500 transition-all"
        />
        <button
          type="submit"
          disabled={isLoading}
          className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 px-6 py-2 rounded-xl text-sm font-medium transition-all shadow-lg active:scale-95"
        >
          Send
        </button>
      </form>
    </div>
  );
}
