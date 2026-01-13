"use client";

import { useMemo, useState } from "react";
import {
  uploadPdf,
  summarize,
  askQuestion,
  pdfUrl,
  type AskResponse,
  type Evidence,
} from "@/lib/api";
import { SourcesPanel } from "@/components/ui/SourcesPanel";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

import { useEffect } from "react";
import { listDocs } from "@/lib/api";

type Message = { role: "user" | "assistant"; content: string };

type Doc = {
  doc_id: string;
  doc_name: string;
  active: boolean; // included in queries
};

const EXAMPLE_QUESTIONS = [
  "Summarize the report and list the key themes.",
  "What does the report say about secondaries and liquidity?",
  "What does it say about private credit outlook for 2026?",
  "What is asset-based finance and why is it growing?",
];



function EvidenceBadge({ evidence }: { evidence?: Evidence }) {
  if (!evidence) return null;

  const quality = evidence.quality;
  const variant = quality === "HIGH" ? "default" : quality === "MEDIUM" ? "secondary" : "outline";

  const pct = Math.round((evidence.citation_coverage ?? 0) * 100);

  return (
    <Badge variant={variant} title="Evidence meter">
      Evidence: {quality} · {pct}% cited · {evidence.distinct_pages_cited} pages
    </Badge>
  );
}

export default function HomePage() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [activeDocIdForViewer, setActiveDocIdForViewer] = useState<string | null>(null);
  const [activePageForViewer, setActivePageForViewer] = useState<number | undefined>(undefined);

  const [messages, setMessages] = useState<Message[]>([]);
  const [sources, setSources] = useState<AskResponse["sources"]>([]);
  const [evidence, setEvidence] = useState<Evidence | undefined>(undefined);
  const [routedDocIds, setRoutedDocIds] = useState<string[] | null | undefined>(undefined);

  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [routerOn, setRouterOn] = useState(true);

  const activeDocs = useMemo(() => docs.filter((d) => d.active), [docs]);
  const activeDocIds = useMemo(() => activeDocs.map((d) => d.doc_id), [activeDocs]);

  const queryDocIds = useMemo(() => {
    // For ASK (questions): use active toggles if any, otherwise fall back to viewer doc
    if (activeDocIds.length > 0) return activeDocIds;
    if (activeDocIdForViewer) return [activeDocIdForViewer];
    return [];
  }, [activeDocIds, activeDocIdForViewer]);

  const summaryDocId = useMemo(() => {
    // For SUMMARY: always summarize the doc currently in the viewer if possible
    if (activeDocIdForViewer) return activeDocIdForViewer;
    if (activeDocIds.length > 0) return activeDocIds[0];
    return null;
  }, [activeDocIdForViewer, activeDocIds]);


  const canAsk = queryDocIds.length > 0 && !busy;

  const headerStatus = useMemo(() => {
    if (docs.length === 0) return { text: "No reports uploaded", variant: "secondary" as const };
    if (activeDocs.length === 0) return { text: `Uploaded ${docs.length} · none selected`, variant: "outline" as const };

    const primary = activeDocs[0];
    return {
      text:
        activeDocs.length === 1
          ? `Loaded: ${primary.doc_name} · doc_id ${primary.doc_id.slice(0, 8)}…`
          : `Loaded ${activeDocs.length}/${docs.length} reports`,
      variant: "outline" as const,
    };
  }, [docs, activeDocs]);

  useEffect(() => {
  (async () => {
    try {
      const items = await listDocs();
      setDocs(items.map((x) => ({ ...x, active: true })));
      if (items.length > 0 && !activeDocIdForViewer) {
        setActiveDocIdForViewer(items[0].doc_id);
        setActivePageForViewer(1);
      }
    } catch (e) {
      // optional: show a message if you want
    }
  })();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function onUploadFiles(files: File[]) {
    if (files.length === 0) return;
    setBusy(true);

    try {
      const newlyAdded: Doc[] = [];
      for (const f of files) {
        const res = await uploadPdf(f);
        newlyAdded.push({
          doc_id: res.doc_id,
          doc_name: res.doc_name ?? f.name,
          active: true,
        });
      }

      setDocs((prev) => {
        const merged = [...newlyAdded, ...prev];
        return merged;
      });

      // set viewer to first uploaded
      setActiveDocIdForViewer(newlyAdded[0].doc_id);
      setActivePageForViewer(1);

      setMessages([
        {
          role: "assistant",
          content:
            newlyAdded.length === 1
              ? "Report uploaded. Click **Generate Summary** or ask a question."
              : `Uploaded ${newlyAdded.length} reports. Select which ones are active, then ask a question.`,
        },
      ]);
      setSources([]);
      setEvidence(undefined);
      setRoutedDocIds(undefined);
    } catch (e: any) {
      setMessages([{ role: "assistant", content: `Upload failed: ${e.message}` }]);
    } finally {
      setBusy(false);
    }
  }


  async function onSummarize() {
    if (!summaryDocId) return;

    setBusy(true);
    setMessages((m) => [...m, { role: "user", content: "Generate a summary." }]);

    try {
      // summarize ONLY the doc you are viewing
      const docToSummarize = activeDocIdForViewer ?? activeDocIds[0];
      const res = await summarize({ doc_ids: [docToSummarize], route: false });
      setMessages((m) => [...m, { role: "assistant", content: res.answer }]);
      setSources(res.sources ?? []);
      setEvidence(res.evidence);
      setRoutedDocIds(res.routed_doc_ids);

      // viewer stays on the summarized doc
      setActiveDocIdForViewer(summaryDocId);
      setActivePageForViewer(1);
    } catch (e: any) {
      setMessages((m) => [...m, { role: "assistant", content: `Summarize failed: ${e.message}` }]);
    } finally {
      setBusy(false);
    }
  }

  async function onAsk(q?: string) {
    const finalQ = (q ?? question).trim();
    if (activeDocIds.length === 0 || !finalQ) return;

    setBusy(true);
    setMessages((m) => [...m, { role: "user", content: finalQ }]);
    setQuestion("");

    try {
      const res = await askQuestion(finalQ, { doc_ids: queryDocIds, route: routerOn });
      setMessages((m) => [...m, { role: "assistant", content: res.answer }]);
      setSources(res.sources ?? []);
      setEvidence(res.evidence);
      setRoutedDocIds(res.routed_doc_ids);

      if (res.routed_doc_ids && res.routed_doc_ids.length > 0) {
        setActiveDocIdForViewer(res.routed_doc_ids[0]);
      }
    } catch (e: any) {
      setMessages((m) => [...m, { role: "assistant", content: `Ask failed: ${e.message}` }]);
    } finally {
      setBusy(false);
    }
  }

  function toggleDocActive(doc_id: string) {
    setDocs((prev) => prev.map((d) => (d.doc_id === doc_id ? { ...d, active: !d.active } : d)));
  }

  function setPrimaryForViewer(doc_id: string) {
    setActiveDocIdForViewer(doc_id);
    setActivePageForViewer(1);
  }

  const viewerSrc =
    activeDocIdForViewer ? pdfUrl(activeDocIdForViewer, activePageForViewer) : null;

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-7xl px-6 py-8">
        {/* Header */}
        <div className="flex items-center justify-between gap-4">
          <div>
            <div className="text-2xl font-semibold tracking-tight">Report Intelligence</div>
            <div className="text-sm text-muted-foreground mt-1">
              Grounded summaries + Q&A with page-cited sources.
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap justify-end">
            <EvidenceBadge evidence={evidence} />
            {routedDocIds && routedDocIds.length > 0 ? (
              <Badge variant="secondary" title="Router selected docs">
                Routed: {routedDocIds.length}
              </Badge>
            ) : null}
            <Badge variant={headerStatus.variant}>{headerStatus.text}</Badge>
          </div>
        </div>

        <Separator className="my-6" />

        {/* 3-panel layout (Right panel wider) */}
        <div className="grid grid-cols-12 gap-6">
          {/* Left panel */}
          <div className="col-span-12 lg:col-span-3 space-y-4">
            <Card className="p-4">
              <div className="text-sm font-semibold">Upload report(s)</div>
              <div className="text-xs text-muted-foreground mt-1">
                PDF → indexed → ask questions with citations.
              </div>

              <div className="mt-4 space-y-3">
                <Input
                  type="file"
                  accept="application/pdf"
                  multiple
                  disabled={busy}
                  onChange={(e) => {
                    const list = Array.from(e.target.files ?? []);
                    if (list.length) onUploadFiles(list);
                    e.currentTarget.value = "";
                  }}
                />

                <div className="flex items-center justify-between gap-2">
                  <Button className="w-full" disabled={!canAsk || busy} onClick={onSummarize}>
                    {busy ? "Working…" : "Generate Summary"}
                  </Button>
                </div>

                <div className="text-xs text-muted-foreground mt-1">
                  Summary doc:{" "}
                  <span className="font-medium">
                    {docs.find((d) => d.doc_id === summaryDocId)?.doc_name ?? "(click a doc)"}
                  </span>
                </div>

                <div className="flex items-center justify-between gap-2">
                  <div className="text-xs text-muted-foreground">Router</div>
                  <Button
                    size="sm"
                    variant={routerOn ? "default" : "secondary"}
                    onClick={() => setRouterOn((v) => !v)}
                    disabled={busy}
                  >
                    {routerOn ? "ON" : "OFF"}
                  </Button>
                </div>
              </div>
            </Card>

            <Card className="p-4">
              <div className="text-sm font-semibold">Document library</div>
              <div className="text-xs text-muted-foreground mt-1">
                Select active docs for retrieval. Click a doc to open in viewer.
              </div>

              <div className="mt-3 space-y-2">
                {docs.length === 0 ? (
                  <div className="text-sm text-muted-foreground">No documents yet.</div>
                ) : (
                  docs.map((d) => (
                    <div key={d.doc_id} className="flex items-center gap-2 rounded-lg border p-2">
                      <button
                        className="text-left min-w-0 flex-1"
                        onClick={() => setPrimaryForViewer(d.doc_id)}
                        type="button"
                      >
                        <div className="text-sm font-medium truncate">{d.doc_name}</div>
                        <div className="text-xs text-muted-foreground truncate">
                          {d.doc_id.slice(0, 8)}…
                        </div>
                      </button>

                      <Button
                        size="sm"
                        variant={d.active ? "default" : "secondary"}
                        className="h-7 px-2 shrink-0"
                        onClick={() => toggleDocActive(d.doc_id)}
                        type="button"
                      >
                        {d.active ? "Active" : "Off"}
                      </Button>
                    </div>
                  ))
                )}
              </div>
            </Card>

            <Card className="p-4">
              <div className="text-sm font-semibold">Example questions</div>
              <div className="mt-3 flex flex-col gap-2">
                {EXAMPLE_QUESTIONS.map((q) => (
                  <Button
                    key={q}
                    variant="secondary"
                    className="justify-start whitespace-normal h-auto"
                    disabled={!canAsk}
                    onClick={() => onAsk(q)}
                  >
                    {q}
                  </Button>
                ))}
              </div>
            </Card>

            <Card className="p-4">
              <div className="text-sm font-semibold">Notes</div>
              <div className="text-xs text-muted-foreground mt-2 leading-relaxed">
                Router demonstrates how the system scales from 1 → 50 PDFs: it selects the most relevant docs first,
                then retrieval runs only on those docs.
              </div>
            </Card>
          </div>

          {/* Middle panel */}
          <div className="col-span-12 lg:col-span-6">
            <Card className="p-4 h-[calc(100vh-220px)] flex flex-col">
              <div className="flex items-center justify-between">
                <div className="text-sm font-semibold">Conversation</div>
                <Badge variant="secondary">{messages.length} msgs</Badge>
              </div>

              <div className="mt-4 flex-1 overflow-auto rounded-lg border p-3 space-y-3">
                {messages.length === 0 ? (
                  <div className="text-sm text-muted-foreground">Upload PDF(s) to begin.</div>
                ) : (
                  messages.map((m, i) => (
                    <div key={i} className="space-y-1">
                      <div className="text-xs text-muted-foreground">
                        {m.role === "user" ? "You" : "Assistant"}
                      </div>
                      <div className="text-sm whitespace-pre-wrap">{m.content}</div>
                    </div>
                  ))
                )}
              </div>

              <div className="mt-4 space-y-2">
                <Textarea
                  value={question}
                  placeholder={canAsk ? "Ask a question about the report(s)…" : "Upload/select a report to ask questions…"}
                  disabled={!canAsk || busy}
                  onChange={(e) => setQuestion(e.target.value)}
                />
                <div className="flex justify-end">
                  <Button
                    disabled={!canAsk || busy || question.trim().length === 0}
                    onClick={() => onAsk()}
                  >
                    Ask
                  </Button>
                </div>
              </div>
            </Card>
          </div>

          {/* Right panel (wider) */}
          <div className="col-span-12 lg:col-span-3">
            <Card className="p-4 h-[calc(100vh-220px)]">
              <SourcesPanel
                sources={sources}
                onSelect={(doc_id, page) => {
                  setActiveDocIdForViewer(doc_id);
                  setActivePageForViewer(page);
                }}
              />
            </Card>
          </div>
        </div>

        {/* PDF viewer at bottom */}
        <div className="mt-6">
          <Card className="p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="text-sm font-semibold">PDF Viewer</div>
                <div className="text-xs text-muted-foreground mt-1">
                  Click any source “Open” to jump to the cited page.
                </div>
              </div>

              {activeDocIdForViewer ? (
                <Badge variant="secondary">doc_id {activeDocIdForViewer.slice(0, 8)}…</Badge>
              ) : (
                <Badge variant="outline">No PDF selected</Badge>
              )}
            </div>

            <div className="mt-4 h-[70vh] w-full rounded-lg border overflow-hidden bg-white">
              {viewerSrc ? (
                <iframe
                  key={viewerSrc}
                  src={viewerSrc}
                  className="h-full w-full"
                  title="PDF Viewer"
                />
              ) : (
                <div className="h-full w-full flex items-center justify-center text-sm text-muted-foreground">
                  Upload a PDF to view it here.
                </div>
              )}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
