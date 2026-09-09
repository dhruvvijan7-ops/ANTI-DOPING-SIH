import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Bot, FileDown, HelpCircle, Lightbulb, Target } from "lucide-react";
import { aiApi } from "@/lib/api/endpoints";
import { useCan } from "@/stores/auth";
import type { AiResponse } from "@/lib/api/types";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Field, Textarea } from "@/components/ui/field";
import { ErrorState } from "@/components/ui/states";

type AiOp = "summary" | "gaps" | "questions" | "signal" | "draft";

export function InvAi({ id }: { id: string }) {
  const canUse = useCan("investigations:read");
  const [result, setResult] = useState<{ op: AiOp; data: AiResponse } | null>(null);
  const [draftSections, setDraftSections] = useState<boolean>(false);
  const [signalPrompt, setSignalPrompt] = useState("");

  const run = useMutation({
    mutationFn: async ({ op, prompt }: { op: AiOp; prompt?: string }) => {
      if (op === "summary") return { op, data: await aiApi.summary(id) };
      if (op === "gaps") return { op, data: await aiApi.informationGaps(id) };
      if (op === "questions") return { op, data: await aiApi.questions(id) };
      if (op === "signal") return { op, data: await aiApi.signalExplanation(id, { signal_type: prompt || undefined }) };
      return { op, data: await aiApi.reportDraft(id, {}) };
    },
    onSuccess: (r) => {
      setResult(r);
      if (r.op === "draft") setDraftSections(true);
    },
  });

  if (!canUse) {
    return <Card><CardBody className="text-sm text-ink-600">Access to the AI assistant requires investigation read access.</CardBody></Card>;
  }

  return (
    <div className="space-y-5">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Bot className="h-4 w-4 text-signal-600" /> Grounded intelligence assistant</CardTitle>
        </CardHeader>
        <CardBody className="space-y-3">
          <p className="text-sm text-ink-600">
            Responses are generated deterministically from case records and always reference the underlying data. Nothing here is speculative
            beyond what the case file contains.
          </p>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="secondary" loading={run.isPending && result?.op !== "summary"} onClick={() => run.mutate({ op: "summary" })} leadingIcon={<Lightbulb className="h-4 w-4" />}>
              Case summary
            </Button>
            <Button size="sm" variant="outline" loading={run.isPending && result?.op !== "gaps"} onClick={() => run.mutate({ op: "gaps" })} leadingIcon={<HelpCircle className="h-4 w-4" />}>
              Information gaps
            </Button>
            <Button size="sm" variant="outline" loading={run.isPending && result?.op !== "questions"} onClick={() => run.mutate({ op: "questions" })} leadingIcon={<Target className="h-4 w-4" />}>
              Suggested questions
            </Button>
            <Button size="sm" variant="secondary" loading={run.isPending && result?.op !== "draft"} onClick={() => run.mutate({ op: "draft" })} leadingIcon={<FileDown className="h-4 w-4" />}>
              Draft report from case
            </Button>
          </div>
          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              if (signalPrompt.trim()) run.mutate({ op: "signal", prompt: signalPrompt.trim() });
            }}
          >
            <Field label={undefined} className="flex-1">
              <Textarea value={signalPrompt} onChange={(e) => setSignalPrompt(e.target.value)} placeholder="Ask about a specific signal, e.g. 'rule-based signals' or 'network position'…" />
            </Field>
          </form>
          {run.isError ? <ErrorState title="The assistant could not complete this request" message={run.error instanceof Error ? run.error.message : undefined} /> : null}
        </CardBody>
      </Card>

      {result ? (
        <Card>
          <CardHeader>
            <CardTitle>{opTitle(result.op)}</CardTitle>
            <Badge tone="info" className="bg-signal-50 text-signal-800 ring-signal-200">{result.data.grounded ? "Grounded in case records" : "Not grounded"}</Badge>
          </CardHeader>
          <CardBody className="space-y-3">
            {result.data.content.length === 0 ? (
              <p className="text-sm text-ink-600">No content generated.</p>
            ) : (
              <ul className="space-y-2">
                {result.data.content.map((c, i) => (
                  <li key={`${c.claim_type}-${i}`} className="rounded-md border border-ink-100 p-3">
                    <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-ink-500">{claimLabel(c.claim_type)}</p>
                    <p className="text-sm text-ink-800">{c.statement}</p>
                  </li>
                ))}
              </ul>
            )}
            {draftSections && (result.data as AiResponse & { draft: import("@/lib/api/types").ReportSections }).draft ? (
              <DraftPreview sections={(result.data as AiResponse & { draft: import("@/lib/api/types").ReportSections }).draft} />
            ) : null}
            <p className="border-t border-ink-100 pt-2 text-xs text-ink-500">{result.data.disclaimer}</p>
          </CardBody>
        </Card>
      ) : (
        <Card><CardBody className="text-center"><p className="text-sm text-ink-500">Choose an operation to begin.</p></CardBody></Card>
      )}
    </div>
  );
}

function opTitle(op: AiOp): string {
  switch (op) {
    case "summary": return "Case summary";
    case "gaps": return "Information gaps";
    case "questions": return "Suggested questions";
    case "signal": return "Signal explanation";
    case "draft": return "Draft report sections";
  }
}

function claimLabel(claimType: string): string {
  return claimType.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function DraftPreview({ sections }: { sections: import("@/lib/api/types").ReportSections }) {
  const blocks: Array<[string, string]> = [
    ["Evidence", (sections.evidence ?? []).join("\n")],
    ["Findings", (sections.findings ?? []).join("\n")],
    ["Timeline", (sections.timeline ?? []).join("\n")],
    ["Unresolved questions", (sections.unresolved_questions ?? []).join("\n")],
    ["Outcome", sections.outcome],
  ];
  return (
    <div className="rounded-md border border-ink-100 bg-ink-50/50 p-3">
      <p className="mb-2 text-xs font-medium text-ink-800">Generated draft sections</p>
      {blocks.map(([label, body]) =>
        body ? (
          <div key={label} className="mb-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">{label}</p>
            <p className="whitespace-pre-wrap text-sm text-ink-800">{body}</p>
          </div>
        ) : null,
      )}
      {sections.audit_metadata ? (
        <p className="text-xs text-ink-500">
          Captured {sections.audit_metadata.recorded_audit_events} audit events, {sections.audit_metadata.notes_count} notes, {sections.audit_metadata.tasks_count} tasks.
        </p>
      ) : null}
    </div>
  );
}