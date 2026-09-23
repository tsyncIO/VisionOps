const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001/api";

export interface VisionOpsEventPayload {
  type: string;
  timestamp: string;
  data: Record<string, unknown>;
}

export interface RunResult {
  run_id: string;
  skill: string;
  input_document?: string;
  page_images: string[];
  concepts: Array<{ id: string; name: string; description: string; role?: string }>;
  relationships: Array<{ source: string; target: string; relationship: string }>;
  diagram_spec?: {
    title: string;
    nodes: Array<{ id: string; label: string; type: string }>;
    edges: Array<{ source: string; target: string; label?: string }>;
    layout: string;
  };
  rendered_diagram?: string;
  critique?: Record<string, unknown>;
  explanation?: string;
  status: string;
  errors: string[];
}

export async function uploadDocument(file: File): Promise<{ document_id: string; filename: string; status: string }> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/documents`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    throw new Error(`Failed to upload document: ${res.statusText}`);
  }

  return res.json();
}

export async function startRun(documentId: string, skill: string = "technical_document_to_diagram"): Promise<{ run_id: string; status: string }> {
  const res = await fetch(`${API_BASE}/runs`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      document_id: documentId,
      skill: skill,
    }),
  });

  if (!res.ok) {
    throw new Error(`Failed to start run: ${res.statusText}`);
  }

  return res.json();
}

export function subscribeToEvents(runId: string, onEvent: (event: VisionOpsEventPayload) => void) {
  const eventSource = new EventSource(`${API_BASE}/runs/${runId}/events`);
  
  const eventTypes = [
    "run_started",
    "document_ingested",
    "concept_extraction_started",
    "concepts_extracted",
    "relationships_extracted",
    "equations_extracted",
    "system_abstracted",
    "diagram_planned",
    "diagram_rendered",
    "critique_started",
    "critique_completed",
    "refinement_started",
    "final_result",
    "run_completed",
    "run_failed",
  ];
  
  const handleEvent = (type: string, rawData: string) => {
    try {
      const parsed = JSON.parse(rawData);
      const payload = parsed.data !== undefined ? parsed.data : parsed;
      const eventType = parsed.event || type;
      onEvent({
        type: eventType,
        timestamp: parsed.timestamp || new Date().toISOString(),
        data: payload
      });
    } catch {
      onEvent({ type, timestamp: new Date().toISOString(), data: { raw: rawData } });
    }
  };

  eventTypes.forEach((type) => {
    eventSource.addEventListener(type, (e: MessageEvent) => {
      handleEvent(type, e.data);
    });
  });

  // Catch generic messages
  eventSource.onmessage = (e: MessageEvent) => {
    handleEvent("message", e.data);
  };

  eventSource.onerror = () => {
    // Keep connection alive or allow fallback polling
  };

  return () => {
    eventSource.close();
  };
}

export async function getRunResult(runId: string): Promise<RunResult> {
  const res = await fetch(`${API_BASE}/runs/${runId}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch run result: ${res.statusText}`);
  }
  return res.json();
}
