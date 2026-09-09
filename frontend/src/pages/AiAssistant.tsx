import { useState } from "react";
import { useInvestigationsQuery } from "@/lib/api/queries";
import { InvAi } from "@/features/investigation/InvAi";
import { PageHeader } from "@/components/ui/states";
import { Card, CardBody } from "@/components/ui/card";
import { Field, Select } from "@/components/ui/field";
import { EmptyState, ErrorState } from "@/components/ui/states";

export default function AiAssistant() {
  const [selected, setSelected] = useState("");
  const invs = useInvestigationsQuery({});

  const options = invs.data?.investigations ?? [];

  return (
    <div>
      <PageHeader
        eyebrow="Grounded assistance"
        title="AI Assistant"
        description="Deterministic, evidence-grounded analysis of a chosen case — summaries, gaps, suggested questions and draft report sections."
      />

      <Card>
        <CardBody>
          <Field label="Investigation" id="ai-investigation" description="Select the case you want to work with.">
            <Select
              id="ai-investigation"
              value={selected}
              onChange={(e) => setSelected(e.target.value)}
              disabled={invs.isLoading}
            >
              <option value="">Choose a case…</option>
              {options.map((inv) => (
                <option key={inv.id} value={inv.id}>
                  {inv.case_ref} — {inv.title}
                </option>
              ))}
            </Select>
          </Field>
        </CardBody>
      </Card>

      {invs.isError ? <ErrorState title="Could not load investigations" onRetry={() => void invs.refetch()} /> : null}
      {options.length === 0 && !invs.isLoading && !invs.isError ? (
        <EmptyState title="No investigations available" className="mt-6" />
      ) : null}

      {selected ? <div className="mt-6"><InvAi id={selected} /></div> : null}
    </div>
  );
}