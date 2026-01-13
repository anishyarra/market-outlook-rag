"use client";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type { Source } from "@/lib/api";

export function SourcesPanel({
  sources,
  onSelect,
}: {
  sources: Source[];
  onSelect?: (doc_id: string, page?: number) => void;
}) {
  if (!sources || sources.length === 0) {
    return <div className="text-sm text-muted-foreground">No sources yet.</div>;
  }

  return (
    <div className="h-full overflow-auto space-y-3">
      {sources.map((s, idx) => {
        const docId = s.metadata?.doc_id ?? "";
        const page = s.metadata?.page;
        const name = s.metadata?.doc_name ?? "report";
        const snippet = s.snippet ?? s.text?.slice(0, 220) ?? "";

        return (
          <Card key={idx} className="p-3">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <div className="text-sm font-semibold truncate">{name}</div>
                <div className="text-xs text-muted-foreground">
                  {page ? `p.${page}` : "p.?"} · {docId ? docId.slice(0, 8) + "…" : "no doc_id"}
                </div>
              </div>

              {onSelect && docId ? (
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => onSelect(docId, page)}
                  type="button"
                >
                  Open
                </Button>
              ) : null}
            </div>

            <div className="mt-2 text-xs text-muted-foreground whitespace-pre-wrap">
              {snippet}
            </div>
          </Card>
        );
      })}
    </div>
  );
}