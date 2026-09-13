"""InvestigatorAgent: Structured evidence and bounded tool execution engine.

Strict execution path:
USER QUESTION -> AGENT -> BOUNDED TOOLS -> NUMERICAL/RAG ENGINE -> STRUCTURED EVIDENCE -> SYNTHESIS -> RESPONSE

Enforces the core RAI invariant:
Python computes. The agent inspects, selects bounded read-only tools, classifies evidence states
(OBSERVED, RETRIEVED, INFERRED, UNKNOWN, ABSTAINED), preserves provenance, and explicitly
abstains or qualifies rather than inventing failure claims.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from rai.agent import tools
from rai.agent.runtime import needle_available
from rai.config import FLEET_BY_ID
from rai.schemas import (
    EvidenceState,
    HistoricalSourceType,
)


class AgentQueryStatus(str, Enum):
    ANSWERED = "ANSWERED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
    QUALIFIED = "QUALIFIED"
    PROPOSAL_ONLY = "PROPOSAL_ONLY"


@dataclass
class EvidenceItem:
    claim: str
    state: EvidenceState
    source: str
    source_type: HistoricalSourceType | str = "NUMERICAL_ENGINE"
    case_id: str | None = None
    limitations: list[str] = field(default_factory=list)


@dataclass
class AgentResponse:
    question: str
    asset_id: str | None
    status: AgentQueryStatus
    tools_called: list[str]
    tool_results: dict[str, Any]
    evidence_items: list[EvidenceItem]
    answer: str
    hypotheses: list[str]
    unsupported_claims: list[str]
    requires_human_review: bool
    model_used: str
    confidence: float
    recommendation: str | None = None


class InvestigatorAgent:
    """Bounded agent for renewable asset investigation and technical query resolution."""

    def __init__(self, force_deterministic: bool = False) -> None:
        self.force_deterministic = force_deterministic
        self._needle_ok, _ = needle_available()

    def select_tools(
        self, question: str, asset_id: str | None = None
    ) -> list[tuple[str, dict[str, Any]]]:
        """Select minimal bounded tools based on the question intent."""
        q = question.lower()
        selected: list[tuple[str, dict[str, Any]]] = []

        # Extract explicit case ID if mentioned (e.g. CASE-W-001)
        case_match = re.search(r"\b(case-[ws]-\d{3})\b", q)
        target_case_id = case_match.group(1).upper() if case_match else None

        # Extract asset ID if present in question and not explicitly passed
        if not asset_id:
            asset_match = re.search(r"\b(wt-\d{3}|inv-\d{3})\b", q)
            if asset_match:
                asset_id = asset_match.group(1).upper()

        # 1. Specific Historical Case comparison / details
        if target_case_id:
            if "compare" in q or "differ" in q or "match" in q:
                if asset_id:
                    selected.append(("compare_case", {"asset_id": asset_id, "case_id": target_case_id}))
                selected.append(("get_case_details", {"case_id": target_case_id}))
            else:
                selected.append(("get_case_details", {"case_id": target_case_id}))
            return selected

        # 2. General Historical retrieval
        if any(w in q for w in ["similar", "seen before", "history", "historical", "past", "precedent"]):
            if asset_id:
                selected.append(("retrieve_historical_cases", {"asset_id": asset_id, "k": 3}))
            return selected

        # 3. Economic intervention / costing options
        if any(w in q for w in ["cost", "economic", "option", "intervention", "npv", "financial", "exposure", "tariff"]):
            if asset_id:
                selected.append(("get_economic_options", {"asset_id": asset_id}))
            return selected

        # 4. Procedure / OEM manual knowledge search
        if any(w in q for w in ["procedure", "sop", "manual", "oem", "guideline", "standard"]):
            # Extract clean search query
            clean_q = re.sub(r"[^a-zA-Z0-9\s]", " ", question).strip()
            selected.append(("search_knowledge", {"query": clean_q, "k": 3}))
            return selected

        # 5. Weather / environmental context
        if any(w in q for w in ["weather", "wind", "irradiance", "curtail", "ambient", "temperature"]):
            if asset_id:
                selected.append(("get_weather_context", {"asset_id": asset_id}))
            return selected

        # 6. Soiling estimate
        if "soiling" in q or "cleaning" in q or "dust" in q or "dirt" in q:
            if asset_id:
                selected.append(("get_soiling_estimate", {"asset_id": asset_id}))
            return selected

        # 7. Action / maintenance ticket proposal
        if any(w in q for w in ["propose", "ticket", "inspect", "schedule maintenance", "dispatch"]):
            if asset_id:
                selected.append(
                    ("create_inspection_ticket", {
                        "asset_id": asset_id,
                        "component": "gearbox" if "wt" in (asset_id or "").lower() else "inverter",
                        "action": "Inspect component per evidence recommendation",
                        "deadline_hours": 72,
                    })
                )
            return selected

        # 8. Default: Asset status / evidence (Current State or Provenance)
        if asset_id:
            selected.append(("get_asset_status", {"asset_id": asset_id}))
            selected.append(("get_weather_context", {"asset_id": asset_id}))
        return selected

    def execute_tools(
        self, tool_calls: list[tuple[str, dict[str, Any]]]
    ) -> tuple[dict[str, Any], list[str]]:
        """Safely execute registered tools against the Python engine."""
        results: dict[str, Any] = {}
        invoked: list[str] = []

        for name, kwargs in tool_calls:
            fn = tools.TOOL_BY_NAME.get(name)
            if not fn:
                results[name] = {"available": False, "error": f"Tool '{name}' not found in registry"}
                continue
            invoked.append(name)
            try:
                out = fn(**kwargs)
                results[name] = out
            except Exception as exc:
                results[name] = {"available": False, "error": f"{type(exc).__name__}: {exc}"}

        return results, invoked

    def answer_query(self, question: str, asset_id: str | None = None) -> AgentResponse:
        """Run bounded investigation for the question, producing structured evidence and verdict."""
        # Auto-extract asset ID from question if needed
        if not asset_id:
            m = re.search(r"\b(wt-\d{3}|inv-\d{3})\b", question, re.IGNORECASE)
            if m:
                asset_id = m.group(1).upper()

        tool_calls = self.select_tools(question, asset_id)
        tool_results, invoked = self.execute_tools(tool_calls)

        return self._synthesize(question, asset_id, tool_results, invoked)

    def _synthesize(
        self,
        question: str,
        asset_id: str | None,
        tool_results: dict[str, Any],
        invoked: list[str],
    ) -> AgentResponse:
        q_lower = question.lower()
        evidence_items: list[EvidenceItem] = []
        hypotheses: list[str] = []
        model_name = "needle2" if (self._needle_ok and not self.force_deterministic) else "deterministic_reasoner"

        # Check for asset validity if asset_id is provided
        if asset_id and asset_id not in FLEET_BY_ID:
            return AgentResponse(
                question=question,
                asset_id=asset_id,
                status=AgentQueryStatus.INSUFFICIENT_EVIDENCE,
                tools_called=invoked,
                tool_results=tool_results,
                evidence_items=[
                    EvidenceItem(
                        claim=f"Asset '{asset_id}' is not in the active fleet registry.",
                        state=EvidenceState.ABSTAINED,
                        source="asset_registry",
                    )
                ],
                answer=f"Abstaining: asset '{asset_id}' does not exist in the fleet registry. Cannot evaluate evidence.",
                hypotheses=[],
                unsupported_claims=[],
                requires_human_review=True,
                model_used=model_name,
                confidence=0.0,
            )

        # -------------------------------------------------------------
        # SCENARIO 1: Proposal action (create_inspection_ticket)
        # -------------------------------------------------------------
        if "create_inspection_ticket" in tool_results:
            res = tool_results["create_inspection_ticket"]
            if res.get("created"):
                evidence_items.append(
                    EvidenceItem(
                        claim=f"Inspection ticket {res.get('ticket_id')} proposed.",
                        state=EvidenceState.INFERRED,
                        source="tools.create_inspection_ticket",
                    )
                )
                return AgentResponse(
                    question=question,
                    asset_id=asset_id,
                    status=AgentQueryStatus.PROPOSAL_ONLY,
                    tools_called=invoked,
                    tool_results=tool_results,
                    evidence_items=evidence_items,
                    answer=(
                        f"Inspection ticket {res.get('ticket_id')} has been drafted with status: "
                        f"'{res.get('status')}'. Note: The agent cannot dispatch work; human authorization is required."
                    ),
                    hypotheses=["Inspection proposal awaiting supervisor sign-off"],
                    unsupported_claims=[],
                    requires_human_review=True,
                    model_used=model_name,
                    confidence=1.0,
                )

        # -------------------------------------------------------------
        # SCENARIO 2: Specific Case Details & Comparison
        # -------------------------------------------------------------
        if "get_case_details" in tool_results or "compare_case" in tool_results:
            case_det = tool_results.get("get_case_details", {})

            # Case not found -> ABSTAIN
            if case_det.get("status") == "INSUFFICIENT_EVIDENCE" or not case_det.get("available"):
                return AgentResponse(
                    question=question,
                    asset_id=asset_id,
                    status=AgentQueryStatus.INSUFFICIENT_EVIDENCE,
                    tools_called=invoked,
                    tool_results=tool_results,
                    evidence_items=[
                        EvidenceItem(
                            claim="Requested historical case not found in case memory.",
                            state=EvidenceState.ABSTAINED,
                            source="rai.memory.retrieval",
                        )
                    ],
                    answer="Abstaining: Historical case not found in case database. No comparison can be made.",
                    hypotheses=[],
                    unsupported_claims=[],
                    requires_human_review=True,
                    model_used=model_name,
                    confidence=0.0,
                )

            case_data = case_det.get("case", {})
            case_id = case_data.get("case_id", "UNKNOWN")
            source_type = case_data.get("source_type", HistoricalSourceType.INTERNAL_SYNTHETIC.value)
            fault_mode = case_data.get("fault_mode", "Unspecified")
            outcome = case_data.get("outcome", "No outcome recorded")
            why_matched = case_data.get("why_matched", [])
            what_differs = case_data.get("what_is_different", [])
            why_not_apply = case_data.get("why_may_not_apply", [])

            evidence_items.append(
                EvidenceItem(
                    claim=f"Historical Case {case_id} ({fault_mode}) retrieved.",
                    state=EvidenceState.RETRIEVED,
                    source="synthetic_case_library",
                    source_type=source_type,
                    case_id=case_id,
                    limitations=why_not_apply or ["Contextual reference only; not confirmed diagnosis."],
                )
            )

            # Check if user query is testing an irrelevant case
            is_irrelevant_query = any(w in q_lower for w in ["irrelevant", "not apply", "differ", "dissimilar"])
            if is_irrelevant_query or ("curtail" in fault_mode and "wt" in (asset_id or "").lower()):
                status = AgentQueryStatus.QUALIFIED
                qual_text = (
                    f"Historical case {case_id} relates to '{fault_mode}', but differs materially: "
                    f"{', '.join(what_differs[:3]) or 'operating context differs'}. "
                    f"It should NOT be treated as a confirmed diagnosis for {asset_id or 'the asset'}."
                )
            else:
                status = AgentQueryStatus.ANSWERED
                qual_text = (
                    f"Historical case {case_id} shows similar trajectory features ({', '.join(why_matched[:2]) or 'residuals'}). "
                    f"Key differences: {', '.join(what_differs[:2]) or 'none recorded'}. "
                    f"Outcome was: '{outcome}'. This provides historical context, NOT a confirmed equipment diagnosis."
                )

            return AgentResponse(
                question=question,
                asset_id=asset_id,
                status=status,
                tools_called=invoked,
                tool_results=tool_results,
                evidence_items=evidence_items,
                answer=qual_text,
                hypotheses=[f"Analogous to {fault_mode} with differences: {', '.join(what_differs[:2])}"],
                unsupported_claims=[],
                requires_human_review=True,
                model_used=model_name,
                confidence=0.82,
            )

        # -------------------------------------------------------------
        # SCENARIO 3: Historical Retrieval Query
        # -------------------------------------------------------------
        if "retrieve_historical_cases" in tool_results or "search_similar_cases" in tool_results:
            case_res = tool_results.get("retrieve_historical_cases") or tool_results.get("search_similar_cases", {})
            cases_list = case_res.get("cases", [])
            if not cases_list:
                return AgentResponse(
                    question=question,
                    asset_id=asset_id,
                    status=AgentQueryStatus.INSUFFICIENT_EVIDENCE,
                    tools_called=invoked,
                    tool_results=tool_results,
                    evidence_items=[
                        EvidenceItem(
                            claim="No similar historical cases found above retrieval threshold.",
                            state=EvidenceState.ABSTAINED,
                            source="rai.memory.retrieval",
                        )
                    ],
                    answer="Abstaining: No matching historical episodes found for the current asset state.",
                    hypotheses=[],
                    unsupported_claims=[],
                    requires_human_review=True,
                    model_used=model_name,
                    confidence=0.0,
                )

            for c in cases_list:
                evidence_items.append(
                    EvidenceItem(
                        claim=f"Similar episode {c['case_id']} (similarity {c['similarity']:.0%}, {c['component']}).",
                        state=EvidenceState.RETRIEVED,
                        source=c.get("source", "synthetic_case_library"),
                        source_type=c.get("source_type", HistoricalSourceType.INTERNAL_SYNTHETIC.value),
                        case_id=c["case_id"],
                        limitations=c.get("why_may_not_apply", ["Contextual historical match only"]),
                    )
                )

            top = cases_list[0]
            answer = (
                f"Retrieved {len(cases_list)} similar historical episodes. Top match is {top['case_id']} "
                f"at {top['similarity']:.0%} similarity ({top['component']}: {top['fault_mode']}). "
                f"Why matched: {' '.join(top.get('why_matched', [])[:2])}. "
                f"What differs: {', '.join(top.get('what_is_different', [])[:2]) or 'no major differences'}. "
                f"Provenance: {top.get('source_type')}. Note: Historical matches are contextual references and do not prove failure."
            )
            return AgentResponse(
                question=question,
                asset_id=asset_id,
                status=AgentQueryStatus.ANSWERED,
                tools_called=invoked,
                tool_results=tool_results,
                evidence_items=evidence_items,
                answer=answer,
                hypotheses=[f"Hypothesis {top['component']}: {top['fault_mode']} (similarity {top['similarity']:.0%})"],
                unsupported_claims=[],
                requires_human_review=True,
                model_used=model_name,
                confidence=float(top["similarity"]),
            )

        # -------------------------------------------------------------
        # SCENARIO 4: Economic Options
        # -------------------------------------------------------------
        if "get_economic_options" in tool_results or "estimate_economic_impact" in tool_results:
            econ = tool_results.get("get_economic_options") or tool_results.get("estimate_economic_impact", {})
            if not econ.get("available", True) and "detail" in econ:
                return AgentResponse(
                    question=question,
                    asset_id=asset_id,
                    status=AgentQueryStatus.INSUFFICIENT_EVIDENCE,
                    tools_called=invoked,
                    tool_results=tool_results,
                    evidence_items=[],
                    answer=f"Abstaining: Economics engine unavailable ({econ.get('detail')}).",
                    hypotheses=[],
                    unsupported_claims=[],
                    requires_human_review=True,
                    model_used=model_name,
                    confidence=0.0,
                )

            options = econ.get("options", [])
            rec_id = econ.get("recommended_option_id")
            avoidable = econ.get("avoidable_exposure_inr")

            for opt in options:
                evidence_items.append(
                    EvidenceItem(
                        claim=f"Option {opt['option_id']} (delay {opt['delay_days']}d): exposure INR {opt['expected_exposure_inr']:,.0f}",
                        state=EvidenceState.INFERRED,
                        source="rai.economics.engine",
                        source_type="NUMERICAL_NPV",
                    )
                )

            if avoidable is None or rec_id is None:
                return AgentResponse(
                    question=question,
                    asset_id=asset_id,
                    status=AgentQueryStatus.INSUFFICIENT_EVIDENCE,
                    tools_called=invoked,
                    tool_results=tool_results,
                    evidence_items=evidence_items,
                    answer="Abstaining: Economic consequence is not estimable from the available inputs.",
                    hypotheses=[],
                    unsupported_claims=[],
                    requires_human_review=True,
                    model_used=model_name,
                    confidence=0.0,
                )

            answer = (
                f"Economic analysis evaluated {len(options)} intervention options. "
                f"Recommended option: '{rec_id}' with avoidable financial exposure of INR {avoidable:,.0f}. "
                f"All computations are deterministic arithmetic from tariff {econ.get('tariff_inr_per_kwh')} INR/kWh."
            )
            return AgentResponse(
                question=question,
                asset_id=asset_id,
                status=AgentQueryStatus.ANSWERED,
                tools_called=invoked,
                tool_results=tool_results,
                evidence_items=evidence_items,
                answer=answer,
                hypotheses=[f"Recommended intervention: {rec_id}"],
                unsupported_claims=[],
                requires_human_review=False,
                model_used=model_name,
                confidence=0.90,
            )

        # -------------------------------------------------------------
        # SCENARIO 5: Asset Status / Provenance / Current State
        # -------------------------------------------------------------
        status_res = tool_results.get("get_asset_status") or tool_results.get("get_asset_evidence", {})
        weather_res = tool_results.get("get_weather_context", {})

        if not status_res or not status_res.get("signals"):
            # Missing or sparse telemetry -> ABSTAIN
            return AgentResponse(
                question=question,
                asset_id=asset_id,
                status=AgentQueryStatus.INSUFFICIENT_EVIDENCE,
                tools_called=invoked,
                tool_results=tool_results,
                evidence_items=[
                    EvidenceItem(
                        claim="Telemetry is empty or insufficient to evaluate asset state.",
                        state=EvidenceState.ABSTAINED,
                        source="rai.models.pipeline",
                    )
                ],
                answer="Abstaining: Insufficient telemetry evidence available for this asset. No conclusion can be drawn.",
                hypotheses=[],
                unsupported_claims=[],
                requires_human_review=True,
                model_used=model_name,
                confidence=0.0,
            )

        # Extract OBSERVED vs INFERRED
        signals = status_res.get("signals", {})
        risk_score = status_res.get("risk", 0.0)
        risk_band = status_res.get("risk_band", "low")
        anomaly_score = status_res.get("anomaly_score", 0.0)
        persistence = status_res.get("persistence_hours", 0.0)
        sensor_health = weather_res.get("sensor_health", "ok")
        curtailed = weather_res.get("curtailment_detected", False)
        explains_fraction = weather_res.get("explains_fraction", 0.0)

        # Build OBSERVED items
        for sig_name, sig_data in signals.items():
            z = sig_data.get("z", 0.0)
            pct = sig_data.get("pct")
            evidence_items.append(
                EvidenceItem(
                    claim=f"Signal {sig_name}: z-score {z:+.2f}" + (f", {pct:+.1f}%" if pct is not None else ""),
                    state=EvidenceState.OBSERVED,
                    source="SCADA_TELEMETRY",
                )
            )

        evidence_items.append(
            EvidenceItem(
                claim=f"Environmental sensor health: {sensor_health}, Curtailment: {curtailed}, Weather explains: {explains_fraction:.0%}",
                state=EvidenceState.OBSERVED,
                source="ENVIRONMENT_PIPELINE",
            )
        )

        # Build INFERRED items
        evidence_items.append(
            EvidenceItem(
                claim=f"Anomaly score {anomaly_score:.2f}, Risk score {risk_score:.2f} ({risk_band} band), Persistence {persistence:.1f}h",
                state=EvidenceState.INFERRED,
                source="CARE_ANOMALY_PIPELINE",
            )
        )

        # -------------------------------------------------------------
        # Check for Conflicting Evidence
        # (e.g. anomaly present, but weather explains >= 60% OR curtailment OR sensor suspect/failed)
        # -------------------------------------------------------------
        if anomaly_score > 0.4 and (explains_fraction >= 0.60 or curtailed or sensor_health in ["suspect", "failed"]):
            conflict_reason = []
            if explains_fraction >= 0.60:
                conflict_reason.append(f"weather explains {explains_fraction:.0%} of the deviation")
            if curtailed:
                conflict_reason.append("grid curtailment is commanded")
            if sensor_health != "ok":
                conflict_reason.append(f"sensor health is flagged as {sensor_health}")

            hypotheses = [
                f"Operational / Environmental effect ({', '.join(conflict_reason)})",
                "Apparent asset deviation without confirmed internal degradation",
            ]
            answer = (
                f"Conflicting Evidence: While residual anomaly score is elevated ({anomaly_score:.2f}), "
                f"the deviation is substantially accounted for by operational/external factors: {', '.join(conflict_reason)}. "
                f"Evidence states distinguished: OBSERVED (sensor residuals & environment readings) vs INFERRED (anomaly score). "
                f"Equipment failure cannot be asserted."
            )
            return AgentResponse(
                question=question,
                asset_id=asset_id,
                status=AgentQueryStatus.CONFLICTING_EVIDENCE,
                tools_called=invoked,
                tool_results=tool_results,
                evidence_items=evidence_items,
                answer=answer,
                hypotheses=hypotheses,
                unsupported_claims=[],
                requires_human_review=True,
                model_used=model_name,
                confidence=0.75,
            )

        # -------------------------------------------------------------
        # Standard Current State / Provenance Response
        # -------------------------------------------------------------
        top_sig = max(signals.items(), key=lambda item: abs(item[1].get("z", 0.0))) if signals else ("none", {})
        top_name, top_val = top_sig

        if anomaly_score > 0.6 and persistence >= 12.0:
            hypotheses = [f"Possible equipment degradation in {top_name.replace('_', ' ')}"]
            answer = (
                f"Asset {asset_id} shows sustained residual deviation ({top_name} z={top_val.get('z', 0.0):+.2f}) "
                f"persisting for {persistence:.1f} hours with risk band '{risk_band}' ({risk_score:.2f}). "
                f"Environment explains only {explains_fraction:.0%}. "
                f"Evidence states: OBSERVED ({len(signals)} SCADA signals), INFERRED (anomaly & risk scores). "
                f"Recommendation: Inspect {top_name.split('_')[0]} condition; do NOT assume definite mechanical failure without physical inspection."
            )
        else:
            hypotheses = ["Normal operating conditions with negligible residual drift"]
            answer = (
                f"Asset {asset_id} is operating within nominal parameters. Anomaly score: {anomaly_score:.2f}, "
                f"risk band: '{risk_band}', persistence: {persistence:.1f} hours. "
                f"Evidence states: OBSERVED ({len(signals)} telemetry channels), INFERRED (risk rating)."
            )

        return AgentResponse(
            question=question,
            asset_id=asset_id,
            status=AgentQueryStatus.ANSWERED,
            tools_called=invoked,
            tool_results=tool_results,
            evidence_items=evidence_items,
            answer=answer,
            hypotheses=hypotheses,
            unsupported_claims=[],
            requires_human_review=(risk_band in ["high", "critical"]),
            model_used=model_name,
            confidence=0.88,
        )

    def evaluate_unsupported_claims(self, response: AgentResponse) -> list[str]:
        """Detect any claims that contradict the evidence or assert premature certainty."""
        unsupported: list[str] = []
        ans = response.answer.lower()

        # 1. Definite failure claim without corroboration or under conflicting evidence
        if response.status == AgentQueryStatus.CONFLICTING_EVIDENCE and any(
            phrase in ans for phrase in ["has definitely failed", "broken down", "gearbox failed", "catastrophic failure"]
        ):
            unsupported.append("Claimed definite failure despite conflicting environmental evidence.")

        # 2. Treating historical case as confirmed diagnosis
        if any(phrase in ans for phrase in ["confirms the current failure", "proves this asset has failed", "definite match diagnosis"]):
            unsupported.append("Treated historical case as confirmed diagnosis rather than contextual reference.")

        # 3. Answering when abstention was required
        if (
            response.status == AgentQueryStatus.INSUFFICIENT_EVIDENCE
            and any(term in ans for term in ["nominal", "healthy", "gearbox"])
            and not any(w in ans for w in ["abstaining", "insufficient", "cannot"])
        ):
            unsupported.append("Provided concrete diagnosis despite insufficient evidence.")

        return unsupported
