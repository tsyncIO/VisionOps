"use client";

import { useState, useRef, useEffect } from "react";
import { uploadDocument, startRun, subscribeToEvents, getRunResult, VisionOpsEventPayload, RunResult } from "../lib/api";

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentStep, setCurrentStep] = useState<string>("Ready");
  const [runId, setRunId] = useState<string | null>(null);
  const [events, setEvents] = useState<VisionOpsEventPayload[]>([]);
  const [finalResult, setFinalResult] = useState<RunResult | null>(null);

  // Diagram Viewer Controls
  const [zoomLevel, setZoomLevel] = useState<number>(100);
  const [viewFitMode, setViewFitMode] = useState<"adaptive" | "fit" | "full">("full");

  const fileInputRef = useRef<HTMLInputElement>(null);

  const resetAllState = () => {
    setEvents([]);
    setFinalResult(null);
    setRunId(null);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      resetAllState();
      setCurrentStep("Document selected");
    }
  };

  const handleLoadSample = async () => {
    try {
      resetAllState();
      setCurrentStep("Loading 9_Profiling.pdf sample...");
      const res = await fetch("/9_Profiling.pdf");
      const blob = await res.blob();
      const sampleFile = new File([blob], "9_Profiling.pdf", { type: "application/pdf" });
      setFile(sampleFile);
      setCurrentStep("Sample 9_Profiling.pdf loaded");
    } catch (err) {
      console.error("Failed to load sample:", err);
      alert("Failed to load sample file.");
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setIsProcessing(true);
    resetAllState();
    setCurrentStep("Uploading PDF document...");

    try {
      // 1. Upload
      const uploadRes = await uploadDocument(file);
      setCurrentStep("Document uploaded. Launching agent graph...");
      
      // 2. Start Run
      const runRes = await startRun(uploadRes.document_id);
      setRunId(runRes.run_id);
      setCurrentStep("Agent analysis initiated");
    } catch (err: unknown) {
      console.error(err);
      setIsProcessing(false);
      setCurrentStep("Failed to start analysis");
      const msg = err instanceof Error ? err.message : "Failed to start analysis";
      alert(msg);
    }
  };

  useEffect(() => {
    if (!runId) return;

    // Guarantee past execution traces are cleared when a new run begins
    setEvents([]);
    setFinalResult(null);

    let isSubscribed = true;

    // 1. Subscribe to SSE
    const unsubscribe = subscribeToEvents(runId, (event) => {
      if (!isSubscribed) return;
      setEvents((prev) => [...prev, event]);
      
      // Update step description
      if (event.type === "document_ingested") setCurrentStep("Ingesting & rasterizing PDF pages...");
      else if (event.type === "concept_extraction_started") setCurrentStep("Extracting architectural concepts (vLLM)...");
      else if (event.type === "concepts_extracted") setCurrentStep("Concepts identified. Extracting relationships...");
      else if (event.type === "relationships_extracted") setCurrentStep("Relationships mapped. Planning diagram...");
      else if (event.type === "diagram_planned") setCurrentStep("Diagram planned. Compiling deterministic SVG...");
      else if (event.type === "diagram_rendered") setCurrentStep("Diagram rendered. Running visual critic...");
      else if (event.type === "critique_completed") setCurrentStep("Visual critique complete. Synthesizing explanation...");
      else if (event.type === "run_completed") {
        setCurrentStep("Analysis completed successfully");
        setIsProcessing(false);
        getRunResult(runId).then((res) => setFinalResult(res)).catch(console.error);
      } else if (event.type === "run_failed") {
        setCurrentStep("Analysis failed");
        setIsProcessing(false);
        getRunResult(runId).then((res) => setFinalResult(res)).catch(console.error);
      }
    });

    // 2. Polling fallback to guarantee state synchronization even if SSE is interrupted
    const pollInterval = setInterval(async () => {
      if (!isSubscribed) return;
      try {
        const res = await getRunResult(runId);
        if (res.status === "completed" || res.status === "failed") {
          setFinalResult(res);
          setIsProcessing(false);
          setCurrentStep(res.status === "completed" ? "Analysis completed" : "Analysis failed");
          clearInterval(pollInterval);
        } else if (res.concepts && res.concepts.length > 0) {
          setFinalResult((prev) => prev || res);
        }
      } catch (err) {
        console.error("Polling error:", err);
      }
    }, 2500);

    return () => {
      isSubscribed = false;
      clearInterval(pollInterval);
      unsubscribe();
    };
  }, [runId]);

  // Event Type Meta Formatting Helper
  const getEventMeta = (type: string) => {
    switch (type) {
      case "run_started":
        return { label: "Run Started", icon: "🚀", color: "text-blue-400", bg: "bg-blue-950/40 border-blue-800/50" };
      case "document_ingested":
        return { label: "Document Ingested", icon: "📄", color: "text-indigo-400", bg: "bg-indigo-950/40 border-indigo-800/50" };
      case "concept_extraction_started":
        return { label: "Extracting Concepts (vLLM)", icon: "🔍", color: "text-purple-400", bg: "bg-purple-950/40 border-purple-800/50" };
      case "concepts_extracted":
        return { label: "Concepts Extracted", icon: "💡", color: "text-emerald-400", bg: "bg-emerald-950/40 border-emerald-800/50" };
      case "relationships_extracted":
        return { label: "Relationships Mapped", icon: "🔗", color: "text-teal-400", bg: "bg-teal-950/40 border-teal-800/50" };
      case "equations_extracted":
        return { label: "Equations Extracted", icon: "🧮", color: "text-cyan-400", bg: "bg-cyan-950/40 border-cyan-800/50" };
      case "system_abstracted":
        return { label: "System Abstraction Planned", icon: "⚡", color: "text-amber-400", bg: "bg-amber-950/40 border-amber-800/50" };
      case "diagram_planned":
        return { label: "Diagram Spec Planned", icon: "📐", color: "text-sky-400", bg: "bg-sky-950/40 border-sky-800/50" };
      case "diagram_rendered":
        return { label: "SVG Rendered", icon: "🎨", color: "text-pink-400", bg: "bg-pink-950/40 border-pink-800/50" };
      case "critique_started":
        return { label: "Visual Critique Evaluated", icon: "👁️", color: "text-orange-400", bg: "bg-orange-950/40 border-orange-800/50" };
      case "critique_completed":
        return { label: "Critique Completed", icon: "📋", color: "text-yellow-400", bg: "bg-yellow-950/40 border-yellow-800/50" };
      case "refinement_started":
        return { label: "Refining Diagram Spec", icon: "↻", color: "text-violet-400", bg: "bg-violet-950/40 border-violet-800/50" };
      case "run_completed":
        return { label: "Run Completed", icon: "✅", color: "text-emerald-400", bg: "bg-emerald-950/50 border-emerald-700/60" };
      case "run_failed":
        return { label: "Run Failed", icon: "❌", color: "text-red-400", bg: "bg-red-950/50 border-red-800/60" };
      default:
        return { label: type, icon: "⚙️", color: "text-gray-400", bg: "bg-gray-900 border-gray-750" };
    }
  };

  return (
    <main className="min-h-screen bg-gray-900 text-gray-100 p-8">
      <div className="max-w-6xl mx-auto space-y-8">
        
        {/* Header */}
        <header className="border-b border-gray-800 pb-4 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
              VisionOps
            </h1>
            <p className="text-gray-400 mt-1">Agentic Multimodal Visual Analytics & Reasoning Platform</p>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
            <span className="text-xs font-mono text-gray-300">Local vLLM Inference Engine Online</span>
          </div>
        </header>

        {/* Upload & Action Section */}
        <section className="bg-gray-800 p-6 rounded-xl border border-gray-700 shadow-xl space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-3">
              <input 
                type="file" 
                accept=".pdf" 
                className="file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-600 file:text-white hover:file:bg-blue-700 cursor-pointer text-sm text-gray-300"
                onChange={handleFileChange}
                ref={fileInputRef}
                disabled={isProcessing}
              />
              <button
                type="button"
                onClick={handleLoadSample}
                disabled={isProcessing}
                className="text-xs px-3 py-2 bg-gray-700 hover:bg-gray-600 text-gray-200 rounded-lg border border-gray-600 transition"
              >
                📄 Use Sample: 9_Profiling.pdf
              </button>
            </div>

            <button 
              onClick={handleUpload}
              disabled={!file || isProcessing}
              className="px-6 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-medium rounded-full shadow-lg disabled:opacity-40 disabled:cursor-not-allowed transition-all flex items-center gap-2"
            >
              {isProcessing && (
                <svg className="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
                </svg>
              )}
              {isProcessing ? "Processing Analysis..." : "Analyze Document"}
            </button>
          </div>

          {/* Active status indicator */}
          <div className="flex items-center gap-3 pt-2 border-t border-gray-750 text-xs">
            <span className="text-gray-400 font-semibold uppercase tracking-wider">Status:</span>
            <span className={`font-mono ${isProcessing ? "text-purple-300 animate-pulse font-semibold" : "text-gray-300"}`}>
              {currentStep}
            </span>
            {file && (
              <span className="ml-auto text-gray-500 truncate max-w-xs">
                Selected: {file.name}
              </span>
            )}
          </div>
        </section>

        {/* Workspace Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Agent Execution Trace */}
          <div className="lg:col-span-1 bg-gray-800 p-6 rounded-xl border border-gray-700 overflow-y-auto max-h-[750px] shadow-xl flex flex-col">
            <div className="flex items-center justify-between mb-4 border-b border-gray-750 pb-3">
              <div>
                <h2 className="text-xl font-semibold text-gray-200">Execution Trace</h2>
                <p className="text-[11px] text-gray-400">Real-time Agentic Graph Decisions</p>
              </div>
              <div className="flex items-center gap-2">
                {events.length > 0 && (
                  <>
                    <span className="text-xs bg-purple-900/60 border border-purple-700/60 px-2.5 py-1 rounded-full text-purple-300 font-mono font-medium">
                      {events.length} events
                    </span>
                    <button
                      onClick={() => setEvents([])}
                      title="Clear trace history"
                      className="text-[11px] px-2 py-1 bg-gray-750 hover:bg-gray-700 text-gray-400 hover:text-gray-200 rounded border border-gray-650 transition"
                    >
                      🧹 Clear
                    </button>
                  </>
                )}
              </div>
            </div>

            <div className="space-y-3 flex-1 pr-1">
              {isProcessing && events.length === 0 && (
                <div className="p-4 bg-purple-950/30 border border-purple-800/50 rounded-lg text-purple-200 text-xs animate-pulse flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full bg-purple-400 animate-ping"></div>
                  <span>Connecting to live vLLM execution stream...</span>
                </div>
              )}

              {events.map((ev, index) => {
                const meta = getEventMeta(ev.type);
                const isLast = index === events.length - 1;
                const d = ev.data as Record<string, unknown>;

                return (
                  <div 
                    key={index}
                    className={`text-xs p-3.5 rounded-xl border transition-all ${meta.bg} ${isLast && isProcessing ? "ring-1 ring-purple-500/50 shadow-lg shadow-purple-950/50" : ""}`}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="flex items-center gap-2">
                        <span className="text-sm">{meta.icon}</span>
                        <span className={`font-semibold ${meta.color}`}>{meta.label}</span>
                      </div>
                      {isLast && isProcessing && (
                        <span className="w-2 h-2 rounded-full bg-purple-400 animate-ping"></span>
                      )}
                    </div>

                    {/* Formatted Event Details */}
                    {d && Object.keys(d).length > 0 && (
                      <div className="mt-2 text-[11px] text-gray-300 bg-black/40 p-2.5 rounded-lg border border-white/5 space-y-1 font-mono">
                        {d.count !== undefined && (
                          <div className="text-gray-300"><span className="text-gray-500">Items Identified:</span> {String(d.count)}</div>
                        )}
                        {d.pages !== undefined && (
                          <div className="text-gray-300"><span className="text-gray-500">Rasterized Pages:</span> {String(d.pages)}</div>
                        )}
                        {d.title !== undefined && (
                          <div className="text-purple-300"><span className="text-gray-500">Title:</span> {String(d.title)}</div>
                        )}
                        {d.score !== undefined && (
                          <div className="text-emerald-300"><span className="text-gray-500">Critique Score:</span> {String(d.score)} / 1.0 (Passed: {String(d.passed)})</div>
                        )}
                        {d.filename !== undefined && (
                          <div className="text-blue-300 truncate"><span className="text-gray-500">Output SVG:</span> {String(d.filename)}</div>
                        )}
                        {/* Fallback structured display */}
                        {Array.isArray(d.items) && d.items.length > 0 && (
                          <div className="text-[10px] text-gray-400 mt-1 flex flex-wrap gap-1">
                            {d.items.map((item: Record<string, unknown>, idx: number) => (
                              <span key={idx} className="bg-purple-900/40 text-purple-200 border border-purple-800/50 px-1.5 py-0.5 rounded">
                                {String(item.name || item.id)}
                              </span>
                            ))}
                          </div>
                        )}
                        {Array.isArray(d.links) && d.links.length > 0 && (
                          <div className="text-[10px] text-gray-400 mt-1 flex flex-wrap gap-1">
                            {d.links.map((link: Record<string, unknown>, idx: number) => (
                              <span key={idx} className="bg-teal-900/40 text-teal-200 border border-teal-800/50 px-1.5 py-0.5 rounded">
                                {String(link.source)} → {String(link.target)}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}

              {!runId && !isProcessing && events.length === 0 && (
                <div className="p-8 text-center border border-dashed border-gray-750 rounded-xl space-y-2">
                  <div className="text-2xl">🧠</div>
                  <p className="text-gray-400 text-xs font-medium">Agent Reasoning Stream</p>
                  <p className="text-gray-500 text-[11px]">Upload a PDF to view dynamic task steps, VLM reasoning, and self-critique decisions in real time.</p>
                </div>
              )}
            </div>
          </div>

          {/* Main Visual & Synthesis Area */}
          <div className="lg:col-span-2 space-y-6">
            
            {/* Failure Box */}
            {finalResult?.status === "failed" && (
              <div className="bg-red-950/40 border border-red-800 p-6 rounded-xl shadow-xl">
                <h2 className="text-lg font-semibold mb-2 text-red-400">Analysis Error</h2>
                <ul className="list-disc pl-5 text-red-300 text-sm space-y-1">
                  {finalResult.errors && finalResult.errors.length > 0 ? (
                    finalResult.errors.map((err: string, idx: number) => (
                      <li key={idx} className="font-mono text-xs">{err}</li>
                    ))
                  ) : (
                    <li>Execution halted unexpectedly. Check server logs.</li>
                  )}
                </ul>
              </div>
            )}

            {/* Generated Architecture Diagram */}
            <div className="bg-gray-800 p-6 rounded-xl border border-gray-700 shadow-xl flex flex-col">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-4 border-b border-gray-750 pb-3 gap-3">
                <div>
                  <h2 className="text-xl font-semibold text-gray-200">Real Project Workflow Diagram</h2>
                  <p className="text-[11px] text-gray-400">Contextual Software Engineering Process Pipeline</p>
                </div>

                {/* Adaptive View Controls Toolbar */}
                {finalResult?.rendered_diagram && (
                  <div className="flex items-center gap-2 bg-gray-900 p-1.5 rounded-lg border border-gray-700">
                    <div className="flex items-center bg-gray-800 rounded border border-gray-700">
                      <button 
                        onClick={() => setViewFitMode("adaptive")}
                        className={`px-2 py-1 text-[11px] font-medium rounded-l ${viewFitMode === "adaptive" ? "bg-purple-600 text-white" : "text-gray-400 hover:text-gray-200"}`}
                        title="Scrollable Crisp View"
                      >
                        ↔️ Crisp Scroll
                      </button>
                      <button 
                        onClick={() => setViewFitMode("fit")}
                        className={`px-2 py-1 text-[11px] font-medium border-l border-r border-gray-700 ${viewFitMode === "fit" ? "bg-purple-600 text-white" : "text-gray-400 hover:text-gray-200"}`}
                        title="Fit to Window"
                      >
                        🖼️ Fit Window
                      </button>
                      <button 
                        onClick={() => setViewFitMode("full")}
                        className={`px-2 py-1 text-[11px] font-medium rounded-r ${viewFitMode === "full" ? "bg-purple-600 text-white" : "text-gray-400 hover:text-gray-200"}`}
                        title="100% Full Width"
                      >
                        📐 Full Width
                      </button>
                    </div>

                    <div className="flex items-center gap-1 bg-gray-800 px-2 py-1 rounded border border-gray-700 text-xs font-mono">
                      <button 
                        onClick={() => setZoomLevel((z) => Math.max(50, z - 25))}
                        className="text-gray-400 hover:text-white px-1 text-sm font-bold"
                        title="Zoom Out"
                      >
                        -
                      </button>
                      <span className="text-purple-300 w-10 text-center text-[11px]">{zoomLevel}%</span>
                      <button 
                        onClick={() => setZoomLevel((z) => Math.min(250, z + 25))}
                        className="text-gray-400 hover:text-white px-1 text-sm font-bold"
                        title="Zoom In"
                      >
                        +
                      </button>
                      {zoomLevel !== 100 && (
                        <button 
                          onClick={() => setZoomLevel(100)}
                          className="text-[10px] text-gray-500 hover:text-gray-300 ml-1 underline"
                        >
                          Reset
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Diagram Rendering Viewport */}
              <div className="flex-1 bg-gray-950 rounded-xl border border-gray-750 flex items-center justify-center p-6 min-h-[500px] overflow-auto shadow-inner relative">
                {finalResult?.rendered_diagram ? (
                  <div className="w-full flex flex-col items-center overflow-auto py-2">
                    <div 
                      className="transition-transform duration-200 ease-out flex justify-center items-center w-full"
                      style={{ transform: `scale(${zoomLevel / 100})`, transformOrigin: "top center" }}
                    >
                      <img 
                        src={`http://localhost:8001/outputs/${finalResult.rendered_diagram.split('/').pop()}`}
                        alt="Real Project Workflow Diagram"
                        className={`rounded-xl bg-slate-950 p-6 shadow-2xl border border-indigo-900/50 transition-all ${
                          viewFitMode === "fit" 
                            ? "max-w-full max-h-[600px] object-contain" 
                            : viewFitMode === "full"
                            ? "w-full h-auto object-contain"
                            : "w-full max-w-3xl min-h-[480px] h-auto object-contain"
                        }`}
                      />
                    </div>
                    <div className="mt-4 flex items-center gap-4">
                      <a 
                        href={`http://localhost:8001/outputs/${finalResult.rendered_diagram.split('/').pop()}`} 
                        target="_blank" 
                        rel="noreferrer"
                        className="text-xs text-blue-400 hover:text-blue-300 hover:underline flex items-center gap-1 font-medium bg-blue-950/40 px-3 py-1.5 rounded-full border border-blue-800/50"
                      >
                        <span>Open Raw High-Res SVG in New Tab</span> ↗
                      </a>
                    </div>
                  </div>
                ) : isProcessing ? (
                  <div className="text-center space-y-3 py-12">
                    <div className="inline-block animate-spin rounded-full h-10 w-10 border-b-2 border-purple-400"></div>
                    <p className="text-xs text-gray-300 font-medium">Synthesizing real-world software process workflow...</p>
                  </div>
                ) : (
                  <div className="text-center py-16 text-gray-500 space-y-2">
                    <div className="text-3xl">📐</div>
                    <p className="text-sm">No diagram generated yet</p>
                    <p className="text-xs text-gray-600">Upload a PDF or click &apos;Use Sample&apos; to generate a process pipeline.</p>
                  </div>
                )}
              </div>
            </div>

            {/* Extracted Concepts Summary */}
            {finalResult?.concepts && finalResult.concepts.length > 0 && (
              <div className="bg-gray-800 p-6 rounded-xl border border-gray-700 shadow-xl space-y-3">
                <div className="flex items-center justify-between border-b border-gray-750 pb-2">
                  <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-300">
                    Project Components ({finalResult.concepts.length})
                  </h3>
                  <span className="text-[11px] text-gray-400">Hover for practical role</span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {finalResult.concepts.map((c: { id: string; name: string; description: string; role?: string }) => (
                    <span 
                      key={c.id} 
                      className="px-3 py-1.5 bg-gray-900 border border-gray-700 rounded-lg text-xs text-gray-200 shadow-sm"
                      title={c.description}
                    >
                      <strong className="text-purple-400">{c.name}</strong>
                      {c.role && <span className="text-gray-500 text-[10px] ml-1.5 font-mono">({c.role})</span>}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* System Explanation */}
            {finalResult?.explanation && (
              <div className="bg-gray-800 p-6 rounded-xl border border-gray-700 shadow-xl space-y-3">
                <div className="flex items-center justify-between border-b border-gray-750 pb-3">
                  <div>
                    <h2 className="text-xl font-semibold text-gray-200">Real Project Context Breakdown</h2>
                    <p className="text-[11px] text-gray-400">Plain English • Practical Dev Process • Maximum Learning Gain</p>
                  </div>
                  <span className="text-xs bg-emerald-950 border border-emerald-800 text-emerald-300 px-2.5 py-1 rounded-full font-medium">
                    Plain English
                  </span>
                </div>
                <div className="prose prose-invert max-w-none text-sm text-gray-200 leading-relaxed whitespace-pre-line bg-gray-900 p-5 rounded-xl border border-gray-750 shadow-inner font-sans">
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
