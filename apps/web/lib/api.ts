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
      // Unpack nested payload if VisionOpsEvent wrapper was sent
      const payload = parsed.data !== undefined ? parsed.data : parsed;
      const eventType = parsed.event || type;
      onEvent({
        type: eventType,
        timestamp: parsed.timestamp || new Date().toISOString(),
        data: payload
      });
    } catch (err) {
      onEvent({ type, timestamp: new Date().toISOString(), data: { raw: rawData } });
    }
  };

  eventTypes.forEach((type) => {
    eventSource.addEventListener(type, (e) => {
      handleEvent(type, (e as MessageEvent).data);
    });
  });

  eventSource.onmessage = (e) => {
    handleEvent("message", e.data);
  };

  return () => eventSource.close();
}

export async function getRunResult(runId: string) {
  const res = await fetch(`${API_BASE}/runs/${runId}`);
  if (!res.ok) {
    throw new Error("Failed to fetch run result");
  }
  return res.json();
}
