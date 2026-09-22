"use client";

import { useState, useRef, useEffect } from "react";
import { uploadDocument, startRun, subscribeToEvents, getRunResult } from "../lib/api";

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [runId, setRunId] = useState<string | null>(null);
  const [events, setEvents] = useState<{ type: string; data: any }[]>([]);
  const [finalResult, setFinalResult] = useState<any | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setEvents([]);
    setFinalResult(null);

    try {
      // 1. Upload
      const uploadRes = await uploadDocument(file);
      
      // 2. Start Run
      const runRes = await startRun(uploadRes.document_id);
      setRunId(runRes.run_id);
    } catch (err) {
      console.error(err);
      alert("Failed to start analysis");
    } finally {
      setUploading(false);
    }
  };

  useEffect(() => {
    if (!runId) return;

    const unsubscribe = subscribeToEvents(runId, (event) => {
      setEvents((prev) => [...prev, event]);
      
      if (event.type === "run_completed" || event.type === "run_failed") {
        // Fetch final state
        getRunResult(runId).then((res) => {
          setFinalResult(res);
        }).catch(console.error);
      }
    });

    return () => unsubscribe();
  }, [runId]);

  return (
    <main className="min-h-screen bg-gray-900 text-gray-100 p-8">
      <div className="max-w-6xl mx-auto space-y-8">
        
        <header className="border-b border-gray-800 pb-4">
          <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
            VisionOps
          </h1>
          <p className="text-gray-400 mt-2">Agentic Multimodal Visual Analytics</p>
        </header>

        {/* Upload Section */}
        <section className="bg-gray-800 p-6 rounded-xl border border-gray-700 shadow-xl">
          <div className="flex items-center gap-4">
            <input 
              type="file" 
              accept=".pdf" 
              className="file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-600 file:text-white hover:file:bg-blue-700 cursor-pointer"
              onChange={handleFileChange}
              ref={fileInputRef}
            />
            <button 
              onClick={handleUpload}
              disabled={!file || uploading}
              className="px-6 py-2 bg-purple-600 text-white font-medium rounded-full hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {uploading ? "Analyzing..." : "Analyze Document"}
            </button>
          </div>
        </section>

        {/* Workspace Area */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Agent Trace */}
          <div className="lg:col-span-1 bg-gray-800 p-6 rounded-xl border border-gray-700 overflow-y-auto max-h-[600px] shadow-xl">
            <h2 className="text-xl font-semibold mb-4 text-gray-200">Execution Trace</h2>
            <div className="space-y-4">
              {events.map((ev, i) => (
                <div key={i} className="text-sm p-3 bg-gray-900 rounded-lg border border-gray-750">
                  <span className="font-mono text-blue-400">{ev.type}</span>
                  {ev.data && Object.keys(ev.data).length > 0 && (
                    <pre className="mt-2 text-xs text-gray-500 overflow-x-auto">
                      {JSON.stringify(ev.data, null, 2)}
                    </pre>
                  )}
                </div>
              ))}
              {!runId && <p className="text-gray-500 italic">No active run</p>}
            </div>
          </div>

          {/* Main Content Area */}
          <div className="lg:col-span-2 space-y-8">
            
            {/* SVG Viewer */}
            <div className="bg-gray-800 p-6 rounded-xl border border-gray-700 min-h-[300px] shadow-xl flex flex-col">
              <h2 className="text-xl font-semibold mb-4 text-gray-200">Generated Diagram</h2>
              <div className="flex-1 bg-gray-900 rounded-lg border border-gray-750 flex items-center justify-center p-4">
                {finalResult?.rendered_diagram ? (
                   // Typically we would host the SVGs as static files or have an API endpoint to fetch them.
                   // For MVP, we can instruct the user or provide a link to it, or render inline if we add an endpoint.
                   <div className="text-center">
                     <p className="text-green-400 mb-2">Diagram rendered successfully!</p>
                     <p className="text-xs text-gray-500">{finalResult.rendered_diagram}</p>
                     <p className="text-sm mt-4 text-gray-400">
                       (Add a static file route in FastAPI to view the SVG here)
                     </p>
                   </div>
                ) : (
                  <p className="text-gray-600">Waiting for agent...</p>
                )}
              </div>
            </div>

            {/* Explanation */}
            {finalResult?.explanation && (
              <div className="bg-gray-800 p-6 rounded-xl border border-gray-700 shadow-xl">
                <h2 className="text-xl font-semibold mb-4 text-gray-200">Explanation</h2>
                <div className="prose prose-invert max-w-none">
                  {finalResult.explanation}
                </div>
              </div>
            )}
            
          </div>
        </div>
      </div>
    </main>
  );
}
