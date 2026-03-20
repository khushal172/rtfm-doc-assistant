import { ChatWindow } from "@/components/ChatWindow";
import { FileUpload } from "@/components/FileUpload";
import { MetricsDisplay } from "@/components/MetricsDisplay";
import { Navbar } from "@/components/Navbar";

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 flex flex-col items-center p-8 space-y-12">
      <div className="z-10 max-w-5xl w-full flex flex-col items-center space-y-2">
        <h1 className="text-5xl font-extrabold tracking-tighter gradient-text">RTFM AGENT</h1>
        <p className="text-sm font-mono opacity-50">v0.1.0-alpha // Neural Retrieval Engine</p>
      </div>

      <div className="flex flex-col lg:flex-row gap-12 w-full max-w-6xl items-start justify-center">
        <div className="flex flex-col gap-8 w-full lg:w-1/3">
          <FileUpload />
          <MetricsDisplay />
        </div>
        
        <div className="w-full lg:w-2/3 flex justify-center">
          <ChatWindow />
        </div>
      </div>

      <div className="flex gap-4 opacity-20 text-[10px] uppercase tracking-[0.2em] font-medium">
        <span>GEMINI 2.5 FLASH</span>
        <span>•</span>
        <span>UPSTASH VECTOR</span>
        <span>•</span>
        <span>FASTAPI</span>
      </div>
      </main>
    </div>
  );
}
