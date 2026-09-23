"use client";

import { useState, useRef, useEffect } from "react";
import { uploadDocument, startRun, subscribeToEvents, getRunResult } from "../lib/api";

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentStep, setCurrentStep] = useState<string>("Ready");
  const [runId, setRunId] = useState<string | null>(null);
  const [events, setEvents] = useState<{ type: string; data: any }[]>([]);
  const [finalResult, setFinalResult] = useState<any | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setFinalResult(null);
      setEvents([]);
      setCurrentStep("Document selected");
    }
  };

  const handleLoadSample = async () => {
    try {
      setCurrentStep("Loading 9_Profiling.pdf sample...");
      const res = await fetch("/9_Profiling.pdf");
      const blob = await res.blob();
      const sampleFile = new File([blob], "9_Profiling.pdf", { type: "application/pdf" });
      setFile(sampleFile);
      setFinalResult(null);
      setEvents([]);
      setCurrentStep("Sample 9_Profiling.pdf loaded");
    } catch (err) {
      console.error("Failed to load sample:", err);
      alert("Failed to load sample file.");
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setIsProcessing(true);
    setEvents([]);
    setFinalResult(null);
    setCurrentStep("Uploading PDF document...");

    try {
      // 1. Upload
      const uploadRes = await uploadDocument(file);
      setCurrentStep("Document uploaded. Launching agent graph...");
      
      // 2. Start Run
      const runRes = await startRun(uploadRes.document_id);
      setRunId(runRes.run_id);
      setCurrentStep("Agent analysis initiated");
    } catch (err: any) {
      console.error(err);
      setIsProcessing(false);
      setCurrentStep("Failed to start analysis");
      alert(err?.message || "Failed to start analysis");
    }
  };

  useEffect(() => {
    if (!runId) return;

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
        } else if (res.concepts && res.concepts.length > 0 && !finalResult?.concepts) {
          setFinalResult(res);
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
              {events.length > 0 && (
                <span className="text-xs bg-purple-900/60 border border-purple-700/60 px-2.5 py-1 rounded-full text-purple-300 font-mono font-medium">
                  {events.length} events
                </span>
              )}
            </div>

            <div className="space-y-3 flex-1 pr-1">
              {isProcessing && events.length === 0 && (
                <div className="p-4 bg-purple-950/30 border border-purple-800/50 rounded-lg text-purple-200 text-xs animate-pulse flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full bg-purple-400 animate-ping"></div>
                  <span>Connecting to live vLLM execution stream...</span>
                </div>
              )}

              {events.map((ev, i) => {
                const isLast = i === events.length - 1;
                const getEventMeta = (type: string) => {
                  switch (type) {
                    case "run_started": return { icon: "🚀", label: "Run Started", color: "text-blue-400", bg: "border-blue-800/60 bg-blue-950/20" };
                    case "document_ingested": return { icon: "📄", label: "Document Ingested", color: "text-indigo-400", bg: "border-indigo-800/60 bg-indigo-950/20" };
                    case "concept_extraction_started": return { icon: "🔍", label: "Extracting Concepts (vLLM)", color: "text-purple-400", bg: "border-purple-800/60 bg-purple-950/20" };
                    case "concepts_extracted": return { icon: "💡", label: "Concepts Extracted", color: "text-emerald-400", bg: "border-emerald-800/60 bg-emerald-950/20" };
                    case "relationships_extracted": return { icon: "🔗", label: "Relationships Mapped", color: "text-teal-400", bg: "border-teal-800/60 bg-teal-950/20" };
                    case "equations_extracted": return { icon: "𝝅", label: "Equations Extracted", color: "text-amber-400", bg: "border-amber-800/60 bg-amber-950/20" };
                    case "system_abstracted": return { icon: "🧠", label: "System Abstraction Planned", color: "text-cyan-400", bg: "border-cyan-800/60 bg-cyan-950/20" };
                    case "diagram_planned": return { icon: "📐", label: "Diagram Spec Formulated", color: "text-sky-400", bg: "border-sky-800/60 bg-sky-950/20" };
                    case "diagram_rendered": return { icon: "🎨", label: "Deterministic SVG Rendered", color: "text-fuchsia-400", bg: "border-fuchsia-800/60 bg-fuchsia-950/20" };
                    case "critique_started": return { icon: "👁️", label: "Visual Critique In Progress", color: "text-purple-400", bg: "border-purple-800/60 bg-purple-950/20" };
                    case "critique_completed": return { icon: "✅", label: "Visual Critique Completed", color: "text-emerald-400", bg: "border-emerald-800/60 bg-emerald-950/20" };
                    case "refinement_started": return { icon: "↻", label: "Refining Diagram Spec", color: "text-orange-400", bg: "border-orange-800/60 bg-orange-950/20" };
                    case "run_completed": return { icon: "✨", label: "Analysis Completed", color: "text-emerald-400 font-bold", bg: "border-emerald-700 bg-emerald-950/30" };
                    case "run_failed": return { icon: "❌", label: "Analysis Halted", color: "text-red-400", bg: "border-red-800 bg-red-950/30" };
                    default: return { icon: "⚡", label: ev.type, color: "text-gray-300", bg: "border-gray-750 bg-gray-900" };
                  }
                };

                const meta = getEventMeta(ev.type);

                return (
                  <div 
                    key={i} 
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
                    {ev.data && Object.keys(ev.data).length > 0 && (
                      <div className="mt-2 text-[11px] text-gray-300 bg-black/40 p-2.5 rounded-lg border border-white/5 space-y-1 font-mono">
                        {ev.data.count !== undefined && (
                          <div className="text-gray-300"><span className="text-gray-500">Items Identified:</span> {ev.data.count}</div>
                        )}
                        {ev.data.pages !== undefined && (
                          <div className="text-gray-300"><span className="text-gray-500">Rasterized Pages:</span> {ev.data.pages}</div>
                        )}
                        {ev.data.title && (
                          <div className="text-purple-300"><span className="text-gray-500">Title:</span> {ev.data.title}</div>
                        )}
                        {ev.data.score !== undefined && (
                          <div className="text-emerald-300"><span className="text-gray-500">Critique Score:</span> {ev.data.score} / 1.0 (Passed: {String(ev.data.passed)})</div>
                        )}
                        {ev.data.filename && (
                          <div className="text-blue-300 truncate"><span className="text-gray-500">Output SVG:</span> {ev.data.filename}</div>
                        )}
                        {/* Fallback structured display */}
                        {ev.data.items && ev.data.items.length > 0 && (
                          <div className="text-[10px] text-gray-400 mt-1 flex flex-wrap gap-1">
                            {ev.data.items.map((item: any, idx: number) => (
                              <span key={idx} className="bg-purple-900/40 text-purple-200 border border-purple-800/50 px-1.5 py-0.5 rounded">
                                {item.name || item.id}
                              </span>
                            ))}
                          </div>
                        )}
                        {ev.data.links && ev.data.links.length > 0 && (
                          <div className="text-[10px] text-gray-400 mt-1 flex flex-wrap gap-1">
                            {ev.data.links.map((link: any, idx: number) => (
                              <span key={idx} className="bg-teal-900/40 text-teal-200 border border-teal-800/50 px-1.5 py-0.5 rounded">
                                {link.source} → {link.target}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}

              {!runId && !isProcessing && (
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
            <div className="bg-gray-800 p-6 rounded-xl border border-gray-700 min-h-[350px] shadow-xl flex flex-col">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-gray-200">Generated System Diagram</h2>
                {finalResult?.diagram_spec?.title && (
                  <span className="text-xs text-purple-300 bg-purple-900/40 border border-purple-800 px-2 py-1 rounded">
                    {finalResult.diagram_spec.title}
                  </span>
                )}
              </div>

              <div className="flex-1 bg-gray-900 rounded-lg border border-gray-750 flex items-center justify-center p-6 overflow-auto min-h-[250px]">
                {finalResult?.rendered_diagram ? (
                  <div className="w-full flex flex-col items-center">
                    <img 
                      src={`http://localhost:8001/outputs/${finalResult.rendered_diagram.split('/').pop()}`}
                      alt="Generated Architecture Diagram"
                      className="max-w-full max-h-[550px] object-contain rounded bg-white/5 p-4 shadow-inner"
                    />
                    <div className="mt-3 flex items-center gap-3">
                      <a 
                        href={`http://localhost:8001/outputs/${finalResult.rendered_diagram.split('/').pop()}`} 
                        target="_blank" 
                        rel="noreferrer"
                        className="text-xs text-blue-400 hover:underline"
                      >
                        Open SVG in new tab ↗
                      </a>
                    </div>
                  </div>
                ) : isProcessing ? (
                  <div className="text-center space-y-2">
                    <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-purple-400"></div>
                    <p className="text-xs text-gray-400">Generating structured system representation...</p>
                  </div>
                ) : (
                  <p className="text-gray-600 text-sm">No diagram generated yet</p>
                )}
              </div>
            </div>

            {/* Extracted Concepts Summary */}
            {finalResult?.concepts && finalResult.concepts.length > 0 && (
              <div className="bg-gray-800 p-6 rounded-xl border border-gray-700 shadow-xl space-y-3">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-300">
                  Extracted Concepts ({finalResult.concepts.length})
                </h3>
                <div className="flex flex-wrap gap-2">
                  {finalResult.concepts.map((c: any) => (
                    <span 
                      key={c.id} 
                      className="px-2.5 py-1 bg-gray-900 border border-gray-700 rounded-md text-xs text-gray-300"
                      title={c.description}
                    >
                      <strong className="text-purple-400">{c.name}</strong>
                      {c.role && <span className="text-gray-500 text-[10px] ml-1.5">({c.role})</span>}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* System Explanation */}
            {finalResult?.explanation && (
              <div className="bg-gray-800 p-6 rounded-xl border border-gray-700 shadow-xl">
                <h2 className="text-xl font-semibold mb-3 text-gray-200">System Explanation</h2>
                <div className="prose prose-invert max-w-none text-sm text-gray-300 leading-relaxed whitespace-pre-line bg-gray-900 p-4 rounded-lg border border-gray-750">
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
