import { BACKEND_URL } from "./config";

export type Source = {
  text: string;
  snippet?: string;
  metadata?: {
    doc_id?: string;
    doc_name?: string;
    page?: number;
  };
  distance?: number;
  penalty?: number;
  boost?: number;
};

export type EvidenceQuality = "HIGH" | "MEDIUM" | "LOW";

export type Evidence = {
  quality: EvidenceQuality;
  citation_coverage?: number;      // 0..1
  distinct_pages_cited: number;    // integer
  notes?: string;
};

export type AskResponse = {
  answer: string;
  sources: Source[];
  evidence?: Evidence;
  routed_doc_ids?: string[];
};

export type DocListItem = { doc_id: string; doc_name: string; uploaded_at?: number };

export function pdfUrl(doc_id: string, page?: number) {
  const p = page ?? 1;
  return `${BACKEND_URL}/pdf/${encodeURIComponent(doc_id)}#page=${p}`;
}

export async function listDocs(): Promise<DocListItem[]> {
  const res = await fetch(`${BACKEND_URL}/docs`);
  if (!res.ok) throw new Error(`Docs failed: ${res.status} ${res.statusText}`);
  return res.json();
}

// POST /upload (multipart form-data: "file")
export async function uploadPdf(file: File): Promise<{ doc_id: string; doc_name: string }> {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${BACKEND_URL}/upload`, { method: "POST", body: form });
  if (!res.ok) throw new Error(`Upload failed: ${res.status} ${res.statusText}`);
  return res.json();
}

type AskOptions = { doc_ids: string[]; route?: boolean };

// POST /chat
export async function askQuestion(question: string, opts: AskOptions): Promise<AskResponse> {
  const res = await fetch(`${BACKEND_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question,
      doc_ids: opts.doc_ids,
      route: opts.route ?? true,
    }),
  });

  if (!res.ok) throw new Error(`Chat failed: ${res.status} ${res.statusText}`);
  return res.json();
}

// Summarize = /chat with fixed prompt
export async function summarize(opts: AskOptions): Promise<AskResponse> {
  const prompt =
    "Summarize the report in analyst format with sections:\n" +
    "ANSWER:\n" +
    "KEY THEMES (bullets, each ends with (p.X)):\n" +
    "WHAT TO FOCUS ON IN 2026 (bullets, each ends with (p.X)):\n" +
    "GAPS:\n" +
    "Rules: Use only the provided document. Use 1–2 citations per bullet max. " +
    "If missing, say 'Not enough information in the provided excerpts.'";

  return askQuestion(prompt, opts);
}

export async function getBackendConfig() {
  const res = await fetch(`${BACKEND_URL}/config`);
  if (!res.ok) throw new Error(`Config failed: ${res.status} ${res.statusText}`);
  return res.json();
}
