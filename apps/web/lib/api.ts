const API_BASE = "http://localhost:8001/api";

export async function uploadDocument(file: File) {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/documents`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    throw new Error("Upload failed");
  }

  return res.json();
}

export async function startRun(documentId: string) {
  const res = await fetch(`${API_BASE}/runs`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ document_id: documentId, skill: "technical_document_to_diagram" }),
  });

  if (!res.ok) {
    throw new Error("Failed to start run");
  }

  return res.json();
}

export function subscribeToEvents(runId: string, onEvent: (event: any) => void) {
  const eventSource = new EventSource(`${API_BASE}/runs/${runId}/events`);
  
  // You might want to handle specific named events if you used named SSE
  // Our backend sends "event: name\ndata: {...}\n\n", which triggers standard message or named event listeners.
  // We'll listen to all events.
  const eventTypes = [
    "run_started",
    "document_ingested",
    "concept_extraction_started",
    "concepts_extracted",
    "relationships_extracted",
    "equations_extracted",
    "diagram_planned",
    "diagram_rendered",
    "critique_started",
    "critique_completed",
    "refinement_started",
    "final_result",
    "run_completed",
    "run_failed",
  ];
  
  eventTypes.forEach((type) => {
    eventSource.addEventListener(type, (e) => {
      onEvent({ type, data: JSON.parse((e as MessageEvent).data) });
    });
  });

  return () => eventSource.close();
}

export async function getRunResult(runId: string) {
  const res = await fetch(`${API_BASE}/runs/${runId}`);
  if (!res.ok) {
    throw new Error("Failed to fetch run result");
  }
  return res.json();
}
