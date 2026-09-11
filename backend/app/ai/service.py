"""AI service abstraction (STAGE H).

Design: the application depends only on :class:`AIService`. Two implementations
ship with the backend:

* :class:`LLMAIService` -- external model provider (optional, used only when the
  environment provides LLM credentials). Never instantiated when unconfigured.
* :class:`DeterministicFallbackAIService` -- structured, fully-grounded summaries
  assembled from retrieved case records. This is the default, so the UI keeps
  working when no LLM is configured.

Every operation is decision support only: it classifies statements and never
determines guilt, recommends sanctions or fabricates records.
"""
from __future__ import annotations

import json
import urllib.request
from abc import ABC, abstractmethod
from typing import Any

from app.ai.retrieval import CaseContext
from app.core.config import settings

# Distinct statement kinds (directive §5).
RECORDED_FACT = "RECORDED_FACT"
ANALYTICAL_SIGNAL = "ANALYTICAL_SIGNAL"
INFERENCE = "INFERENCE"
INVESTIGATIVE_QUESTION = "INVESTIGATIVE_QUESTION"

CLAIM_TYPES = (RECORDED_FACT, ANALYTICAL_SIGNAL, INFERENCE, INVESTIGATIVE_QUESTION)

NOT_DETERMINED = "The available case records do not establish this."

SAFETY_POLICY = [
    "This is decision support, not an autonomous anti-doping decision maker.",
    "Never determine guilt, a violation, or recommend a sanction.",
    "Never invent evidence, sources, dates, relationships or accusations.",
    "Only state factual information that exists in the retrieved records.",
    "Distinguish RECORDED_FACT, ANALYTICAL_SIGNAL, INFERENCE and INVESTIGATIVE_QUESTION.",
    "If information is unavailable state: " + NOT_DETERMINED,
]

DISCLAIMER = (
    "Decision-support output. It does not determine guilt or recommend sanctions, "
    "and must be reviewed by a human investigator before any action."
)

PROHIBITED_TERMS = ("guilty", "sanction", "prohibited substance detected", "confirmed doping")


class AIService(ABC):
    """Contract all AI implementations fulfil."""

    provider_name: str = "AIService"

    @abstractmethod
    def case_summary(self, ctx: CaseContext) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def timeline_summary(self, ctx: CaseContext) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def signal_explanation(self, ctx: CaseContext, signal_type: str | None = None) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def information_gaps(self, ctx: CaseContext) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def investigation_questions(self, ctx: CaseContext) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def report_draft(
        self,
        ctx: CaseContext,
        purpose: str | None = None,
        outcome: str | None = None,
        unresolved_questions: list[str] | None = None,
    ) -> dict[str, Any]:
        ...

    @abstractmethod
    def report_document_draft(self, ctx: CaseContext, purpose: str | None = None) -> list[dict[str, Any]]:
        """Return a structured rich-text block list (AI-generated) grounded in the
        case context. Never invents data; missing categories are stated as such."""
        ...

    @abstractmethod
    def report_section_assist(self, ctx: CaseContext, section: str) -> list[dict[str, Any]]:
        """Produce an AI-assisted block (or blocks) for a named report section,
        grounded strictly in available case context."""
        ...

    def respond(self, operation: str, content: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "provider": self.provider_name,
            "operation": operation,
            "grounded": True,
            "disclaimer": DISCLAIMER,
            "content": content,
        }


class DeterministicFallbackAIService(AIService):
    """Grounded structured output built only from :class:`CaseContext` records."""

    provider_name = "DeterministicFallbackAIService"

    # ------------------------------------------------------------- build helpers
    def _fact(self, statement: str) -> dict:
        return {"claim_type": RECORDED_FACT, "statement": statement}

    def _signal(self, statement: str) -> dict:
        return {"claim_type": ANALYTICAL_SIGNAL, "statement": statement}

    def _inference(self, statement: str) -> dict:
        return {"claim_type": INFERENCE, "statement": statement}

    def _question(self, statement: str) -> dict:
        return {"claim_type": INVESTIGATIVE_QUESTION, "statement": statement}

    # ------------------------------------------------------------- case summary
    def case_summary(self, ctx: CaseContext) -> list[dict[str, Any]]:
        out = [
            self._fact(f"Investigation {ctx.case_ref} ('{ctx.title}') is {ctx.status} with priority {ctx.priority}."),
            self._fact(f"The case subject is {ctx.subject_type} {ctx.subject_label or ctx.subject_id}."),
        ]
        if ctx.alert_ref:
            out.append(self._signal(f"The originating alert {ctx.alert_ref} recorded priority level {ctx.alert_level}"
                                    f"{f' (score {ctx.alert_score:.0f}/100)' if ctx.alert_score is not None else ''}."))
        if ctx.signals:
            kinds = sorted({s["type"] for s in ctx.signals})
            out.append(self._signal(f"The originating run produced analytical signals of type(s): {', '.join(kinds)}."))
        if ctx.features:
            contrib = [f for f in ctx.features if f.get("contribution") is not None]
            if contrib:
                top = sorted(contrib, key=lambda f: abs(f.get("contribution") or 0), reverse=True)[:3]
                names = ", ".join(f.get("feature_id", "?") for f in top)
                out.append(self._signal(f"Highest-magnitude feature contributions recorded: {names}."))
        out.append(self._fact(f"{len(ctx.intelligence)} intelligence report(s), {len(ctx.events)} event record(s), "
                              f"{len(ctx.relationships)} relationship edge(s) and {len(ctx.evidence)} evidence item(s) "
                              f"are linked to this case."))
        if ctx.findings:
            out.append(self._fact(f"{len(ctx.findings)} finding(s) have been recorded by the investigator."))
        return out

    # --------------------------------------------------------- timeline summary
    def timeline_summary(self, ctx: CaseContext) -> list[dict[str, Any]]:
        out = [self._fact(f"The case chronology covers {len(ctx.events)} event record(s).")]
        if not ctx.events:
            out.append(self._fact(NOT_DETERMINED + " No event records are linked to this subject."))
            return out
        ordered = sorted(ctx.events, key=lambda e: e.get("occurred_on") or "")
        first, last = ordered[0], ordered[-1]
        out.append(self._fact(f"The earliest recorded event is {first.get('category')} on {first.get('occurred_on')}; "
                              f"the latest is {last.get('category')} on {last.get('occurred_on')}."))
        for item in ordered[:6]:
            out.append(self._fact(f"{item.get('occurred_on')} - {item.get('category')}: {item.get('detail')}"))
        if len(ordered) > 6:
            out.append(self._fact(f"{len(ordered) - 6} further event record(s) are present in the case file."))
        if ctx.alert_ref:
            out.append(self._signal(f"Alert {ctx.alert_ref} marks the analytical point at which this case was opened."))
        return out

    # ----------------------------------------------------- signal explanation
    def signal_explanation(self, ctx: CaseContext, signal_type: str | None = None) -> list[dict[str, Any]]:
        if not ctx.signals:
            return [self._fact(NOT_DETERMINED + " No analytical signals are linked to this case.")]
        out = []
        for sig in ctx.signals:
            if signal_type and sig["type"] != signal_type:
                continue
            out.append(self._signal(_describe_signal(sig)))
        if not out:
            out.append(self._fact(NOT_DETERMINED + f" No signals of type '{signal_type}' are linked to this case."))
        return out

    # -------------------------------------------------------- information gaps
    def information_gaps(self, ctx: CaseContext) -> list[dict[str, Any]]:
        out = []
        if not ctx.intelligence:
            out.append(self._fact("The available case records contain no intelligence reports for this subject."))
        if not ctx.events:
            out.append(self._fact("The available case records contain no event records for this subject."))
        if not ctx.evidence:
            out.append(self._fact("The available case records contain no evidence items."))
        if not ctx.notes:
            out.append(self._fact("The available case records contain no investigator notes."))
        if not ctx.findings:
            out.append(self._fact("The available case records contain no recorded findings."))
        if not ctx.relationships:
            out.append(self._fact("The available case records contain no relationship edges."))
        if not out:
            out.append(self._fact("The case file contains records in every tracked category."))
        return out

    # -------------------------------------------------- investigation questions
    def investigation_questions(self, ctx: CaseContext) -> list[dict[str, Any]]:
        questions = [self._question("Which specific records drove the analytical priority, and are they independently corroborated?")]
        if not ctx.evidence:
            questions.append(self._question("What documentary or physical evidence could substantiate or refute the analytical signals?"))
        if ctx.signals and not ctx.notes:
            questions.append(self._question("Has the interplay of the recorded signals been assessed by an investigator in the notes?"))
        if ctx.intelligence:
            questions.append(self._question("Have the source reliability and possible duplication of the intelligence reports been assessed?"))
        return questions

    # -------------------------------------------------------------- report draft
    def report_draft(
        self,
        ctx: CaseContext,
        purpose: str | None = None,
        outcome: str | None = None,
        unresolved_questions: list[str] | None = None,
    ) -> dict[str, Any]:
        sections = {
            "case_metadata": {
                "case_ref": ctx.case_ref,
                "title": ctx.title,
                "status": ctx.status,
                "priority": ctx.priority,
                "subject": f"{ctx.subject_type} {ctx.subject_label or ctx.subject_id}",
                "originating_alert": ctx.alert_ref,
            },
            "purpose": purpose or "To document the review of the recorded analytical signals for this case.",
            "intelligence": [{"title": r["title"], "source": r["source"], "report_date": r["report_date"], "reliability": r["reliability"]} for r in ctx.intelligence],
            "analytical_signals": [self._sig_line(s) for s in ctx.signals],
            "timeline": [f"{e.get('occurred_on')} - {e.get('category')}: {e.get('detail')}" for e in sorted(ctx.events, key=lambda e: e.get("occurred_on") or "")],
            "relationships": [f"{r['type']} (confidence {r.get('confidence')}) - {r['other_entity']}" for r in ctx.relationships],
            "evidence": [e["title"] for e in ctx.evidence],
            "findings": [f"{f['title']}: {f['statement']}" for f in ctx.findings],
            "unresolved_questions": list(unresolved_questions or [
                q["statement"] for q in self.investigation_questions(ctx)
            ]),
            "outcome": outcome or "TBD - to be determined by the investigating officer.",
            "audit_metadata": {
                "version": 1,
                "recorded_audit_events": ctx.audit_count,
                "notes_count": len(ctx.notes),
                "tasks_count": len(ctx.tasks),
            },
        }
        return {"sections": sections}

    def _sig_line(self, sig: dict[str, Any]) -> str:
        return _describe_signal(sig)

    # --------------------------------------------------- structured report draft
    def report_document_draft(self, ctx: CaseContext, purpose: str | None = None) -> list[dict[str, Any]]:
        import uuid  # noqa: PLC0415
        nid = uuid.uuid4

        def block(btype: str, *, text: str = "", items: list[str] | None = None,
                  head: list[str] | None = None, rows: list[list[str]] | None = None,
                  level: int = 2, refs: list[dict[str, Any]] | None = None) -> dict[str, Any]:
            return {
                "id": f"ai-{nid().hex[:8]}",
                "type": btype,
                "text": text or None,
                "attrs": {"level": level} if btype == "heading" else {},
                "items": items or [],
                "head": head or [],
                "rows": rows or [],
                "provenance": {"kind": "ai", "refs": refs or []},
            }

        out: list[dict[str, Any]] = []
        na = "Information not available in the current case record."

        out.append(block("heading", text="Executive summary", level=1))
        out.append(block("paragraph", text=(
            f"This draft summarises investigation {ctx.case_ref} ('{ctx.title}'), which is {ctx.status} "
            f"with priority {ctx.priority}. The subject is {ctx.subject_type} {ctx.subject_label or ctx.subject_id}."
        )))
        if ctx.alert_ref:
            out.append(block("paragraph", text=(
                f"The originating alert {ctx.alert_ref} records priority level {ctx.alert_level}"
                f"{f' (score {ctx.alert_score:.0f}/100)' if ctx.alert_score is not None else ''}."
            )))

        out.append(block("heading", text="Subject", level=1))
        out.append(block("paragraph", text=(
            f"Subject: {ctx.subject_type} {ctx.subject_label or ctx.subject_id}. Stability and identity are "
            "established from the case record." if ctx.subject_label else f"Subject identifier: {ctx.subject_id}. {na}"
        )))

        out.append(block("heading", text="Scope", level=1))
        out.append(block("paragraph", text=(
            "This report covers the recorded intelligence, events, relationships, evidence and findings "
            "linked to the case at the time the AI draft was generated."
        )))

        out.append(block("heading", text="Methodology", level=1))
        out.append(block("paragraph", text=(
            "This AI-generated draft was produced as decision support from the verified case record. "
            "It does not determine guilt or recommend sanctions and must be reviewed by an investigator."
        )))

        out.append(block("heading", text="Timeline", level=1))
        if ctx.events:
            ordered = sorted(ctx.events, key=lambda e: e.get("occurred_on") or "")
            rows = [[e.get("occurred_on") or "", e.get("category") or "", e.get("detail") or ""] for e in ordered]
            out.append(block("table", head=["Date", "Category", "Detail"], rows=rows))
        else:
            out.append(block("paragraph", text=na))

        out.append(block("heading", text="Intelligence", level=1))
        if ctx.intelligence:
            rows = [[i.get("source") or "", i.get("title") or "", i.get("report_date") or "", i.get("reliability") or ""]
                    for i in ctx.intelligence]
            out.append(block("table", head=["Source", "Title", "Date", "Reliability"], rows=rows))
        else:
            out.append(block("paragraph", text=na))

        out.append(block("heading", text="Evidence", level=1))
        if ctx.evidence:
            rows = [[e.get("title") or "", e.get("evidence_type") or "", e.get("classification") or ""]
                    for e in ctx.evidence]
            out.append(block("table", head=["Title", "Type", "Classification"], rows=rows))
        else:
            out.append(block("paragraph", text=na))

        out.append(block("heading", text="Findings", level=1))
        if ctx.findings:
            for f in ctx.findings:
                out.append(block("paragraph", text=f"{f.get('title')}: {f.get('statement')}"))
        else:
            out.append(block("paragraph", text=na))

        out.append(block("heading", text="Relationships", level=1))
        if ctx.relationships:
            items = [f"{r.get('type')} (confidence {r.get('confidence')}) - {r.get('other_entity')}" for r in ctx.relationships]
            out.append(block("list", items=items))
        else:
            out.append(block("paragraph", text=na))

        out.append(block("heading", text="Assessment", level=1))
        if ctx.signals:
            for s in ctx.signals:
                out.append(block("paragraph", text=_describe_signal(s)))
        else:
            out.append(block("paragraph", text="No analytical signals are linked to this case."))

        out.append(block("heading", text="Gaps", level=1))
        for gap in self.information_gaps(ctx):
            out.append(block("paragraph", text=gap["statement"]))

        out.append(block("heading", text="Recommendations", level=1))
        for q in self.investigation_questions(ctx):
            out.append(block("paragraph", text=f"Investigate: {q['statement']}"))

        if purpose:
            out.insert(1, block("heading", text="Purpose", level=1))
            out.insert(2, block("paragraph", text=purpose))

        return out

    def report_section_assist(self, ctx: CaseContext, section: str) -> list[dict[str, Any]]:
        import uuid  # noqa: PLC0415

        def block(text: str, *, refs: list[dict[str, Any]] | None = None) -> dict[str, Any]:
            return {
                "id": f"ai-sec-{uuid.uuid4().hex[:8]}",
                "type": "paragraph",
                "text": text,
                "attrs": {},
                "items": [],
                "head": [],
                "rows": [],
                "provenance": {"kind": "ai", "refs": refs or []},
            }

        s = section.strip().lower()
        if s in ("timeline", "timeline summary", "summarize timeline"):
            if not ctx.events:
                return [block("Information not available in the current case record.")]
            rows = [[e.get("occurred_on") or "", e.get("category") or "", e.get("detail") or ""]
                    for e in sorted(ctx.events, key=lambda e: e.get("occurred_on") or "")]
            return [{"id": f"ai-sec-{uuid.uuid4().hex[:8]}", "type": "table", "text": None, "attrs": {},
                     "items": [], "head": ["Date", "Category", "Detail"], "rows": rows,
                     "provenance": {"kind": "ai", "refs": []}}]
        if s in ("evidence", "evidence summary", "draft evidence summary", "summarize evidence"):
            if not ctx.evidence:
                return [block("Information not available in the current case record.")]
            rows = [[e.get("title") or "", e.get("evidence_type") or "", e.get("classification") or ""]
                    for e in ctx.evidence]
            return [{"id": f"ai-sec-{uuid.uuid4().hex[:8]}", "type": "table", "text": None, "attrs": {},
                     "items": [], "head": ["Title", "Type", "Classification"], "rows": rows,
                     "provenance": {"kind": "ai", "refs": []}}]
        if s in ("findings", "draft findings", "summarize findings"):
            if not ctx.findings:
                return [block("Information not available in the current case record.")]
            return [block(f"{f.get('title')}: {f.get('statement')}") for f in ctx.findings]
        if s in ("intelligence", "draft intelligence assessment", "summarize intelligence"):
            if not ctx.intelligence:
                return [block("Information not available in the current case record.")]
            items = [f"{i.get('source') or ''} - {i.get('title')} ({i.get('report_date')}, {i.get('reliability')})"
                     for i in ctx.intelligence]
            return [{"id": f"ai-sec-{uuid.uuid4().hex[:8]}", "type": "list", "text": None, "attrs": {},
                     "items": items, "head": [], "rows": [],
                     "provenance": {"kind": "ai", "refs": []}}]
        if s in ("relationships", "relationship summary", "summarize relationships"):
            if not ctx.relationships:
                return [block("Information not available in the current case record.")]
            items = [f"{r.get('type')} (confidence {r.get('confidence')}) - {r.get('other_entity')}"
                     for r in ctx.relationships]
            return [{"id": f"ai-sec-{uuid.uuid4().hex[:8]}", "type": "list", "text": None, "attrs": {},
                     "items": items, "head": [], "rows": [],
                     "provenance": {"kind": "ai", "refs": []}}]
        if s in ("gaps", "identify gaps"):
            return [block(g["statement"]) for g in self.information_gaps(ctx)]
        if s in ("questions", "generate investigative questions", "investigative questions"):
            return [block(q["statement"]) for q in self.investigation_questions(ctx)]
        if s in ("assessment", "draft intelligence assessment"):
            if not ctx.signals:
                return [block("No analytical signals are linked to this case.")]
            return [block(_describe_signal(sig)) for sig in ctx.signals]
        return [block(f"Section '{section}' is not a supported AI assistance request. Choose a supported section.")]


class LLMAIService(AIService):
    """Base for provider-backed implementations.

    A provider is only constructed when credentials are configured; the fallback
    service is the default, so the platform never pretends an LLM produced output
    it did not.
    """

    provider_name = "LLMAIService"

    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    def _generate(self, prompt: str) -> str:
        """Hook for a concrete provider. Default raises: unconfigured."""
        raise RuntimeError("No LLM provider implementation is configured")

    def _run(self, operation: str, ctx: CaseContext) -> list[dict[str, Any]]:
        raise RuntimeError("LLMAIService requires a concrete provider implementation")

    def case_summary(self, ctx: CaseContext) -> list[dict[str, Any]]:
        return self._run("case_summary", ctx)

    def timeline_summary(self, ctx: CaseContext) -> list[dict[str, Any]]:
        return self._run("timeline_summary", ctx)

    def signal_explanation(self, ctx: CaseContext, signal_type: str | None = None) -> list[dict[str, Any]]:
        return self._run("signal_explanation", ctx)

    def information_gaps(self, ctx: CaseContext) -> list[dict[str, Any]]:
        return self._run("information_gaps", ctx)

    def investigation_questions(self, ctx: CaseContext) -> list[dict[str, Any]]:
        return self._run("investigation_questions", ctx)

    def report_draft(
        self,
        ctx: CaseContext,
        purpose: str | None = None,
        outcome: str | None = None,
        unresolved_questions: list[str] | None = None,
    ) -> dict[str, Any]:
        return self._run("report_draft", ctx)

    def report_document_draft(self, ctx: CaseContext, purpose: str | None = None) -> list[dict[str, Any]]:
        # Structured block drafts are favoured for safety and testability; the
        # provider path reuses the deterministic, grounded construction which is
        # already scoped to retrieved case data.
        return DeterministicFallbackAIService().report_document_draft(ctx, purpose=purpose)

    def report_section_assist(self, ctx: CaseContext, section: str) -> list[dict[str, Any]]:
        return DeterministicFallbackAIService().report_section_assist(ctx, section)


class OpenAICompatibleLLMService(LLMAIService):
    """Thin OpenAI-compatible chat-completion provider (optional)."""

    provider_name = "LLMAIService"

    def _chat(self, messages: list[dict[str, Any]]) -> str:
        payload = json.dumps({"model": self.model, "messages": messages}).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=30) as resp:  # noqa: S310 - LLM endpoint is operator-configured
            body = json.loads(resp.read().decode("utf-8"))
        return body["choices"][0]["message"]["content"]

    def _generate(self, prompt: str) -> str:
        messages = [
            {"role": "system", "content": _system_prompt()},
            {"role": "user", "content": prompt},
        ]
        return self._chat(messages)

    def _run(self, operation: str, ctx: CaseContext) -> list[dict[str, Any]]:
        import uuid  # noqa: PLC0415

        executed = _deterministic()._run(operation, ctx)
        raw = self._generate(f"Operation: {operation}\nCase: {json.dumps(executed)}")
        return [
            {"claim_type": infer_claim(raw), "statement": raw, "provider_note": f"draft_id={uuid.uuid4().hex[:8]}"}
        ]


class AIProvider:
    """Resolve the active service. When no LLM is configured the UI transparently
    receives deterministic output labelled as such."""

    def __init__(self) -> None:
        self._service: AIService | None = None

    def get(self) -> AIService:
        if self._service is None:
            self._service = build_service()
        return self._service


def build_service() -> AIService:
    if settings.ai_configured:
        return OpenAICompatibleLLMService(
            base_url=settings.ai_base_url,
            api_key=settings.ai_api_key,
            model=settings.ai_model,
        )
    return DeterministicFallbackAIService()


_provider = AIProvider()


def get_ai_service() -> AIService:
    return _provider.get()


def _deterministic() -> DeterministicFallbackAIService:
    return DeterministicFallbackAIService()


def _system_prompt() -> str:
    lines = ["You are decision support for anti-doping investigations."]
    lines.extend(SAFETY_POLICY)
    lines.append("Return strictly JSON matching the request schema.")
    return "\n".join(lines)


def _describe_signal(sig: dict[str, Any]) -> str:
    kind = sig.get("type")
    if kind == "RULE":
        state = "triggered" if sig.get("triggered") else "not triggered"
        return f"Rule {sig.get('rule_id')} ('{sig.get('name')}', severity {sig.get('severity')}) was {state}."
    if kind == "ANOMALY":
        flag = "flagged" if sig.get("is_anomaly") else "not flagged"
        return (f"Anomaly detection scored {sig.get('normalized_score')} and was {flag}; "
                f"contributing features: {', '.join(c.get('feature', '?') for c in (sig.get('contributions') or []))}.")
    if kind in ("TEMPORAL", "CROSS_SOURCE"):
        return (f"{kind} correlation scored {sig.get('score')} across {sig.get('signal_count')} signal(s) "
                f"in a {sig.get('window_days')}-day window ({sig.get('category_count')} categories).")
    if kind == "NETWORK":
        return (f"Network relevance scored {sig.get('score')} with degree {sig.get('degree')} "
                f"and {sig.get('connected_priority_count')} connected high-priority subject(s).")
    return f"Analytical signal of type {kind} is linked to this case."


def _run_deterministic(operation: str, ctx: CaseContext, **kwargs: Any) -> list[dict[str, Any]]:
    service = _deterministic()
    method = getattr(service, operation, None)
    if method is None:
        return [{"claim_type": RECORDED_FACT, "statement": NOT_DETERMINED}]
    return method(ctx, **kwargs)


def infer_claim(raw: str) -> str:
    """Heuristic tag for provider output used by the demo provider wrapper."""
    lowered = raw.lower()
    if any(word in lowered for word in ("question", "could you", "consider")):
        return INVESTIGATIVE_QUESTION
    if any(word in lowered for word in ("recorded", "dated", "reported", "stated")):
        return RECORDED_FACT
    return INFERENCE