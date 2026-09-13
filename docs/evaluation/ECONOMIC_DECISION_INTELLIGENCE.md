# Economic Decision Intelligence

## Decision

RAI now exposes a transparent decision-support adapter over the existing Python
economic engine. It compares explicit intervention assumptions and evidence
context, returning `INTERVENE`, `INSPECT`, `MONITOR`, `WAIT`, or `ABSTAIN`.
It is decision support under assumptions, not cost optimization or a failure
probability model.

### Research basis

The focused research reviewed NIST PHM standards and smart-manufacturing
performance guidance, plus a predictive-maintenance methods survey:

- https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=916376
- https://nvlpubs.nist.gov/nistpubs/jres/121/jres.121.013.pdf
- https://arxiv.org/html/2506.20090v1

These sources support lifecycle-cost, reliability, and information-use
decisions, but do not justify inventing fleet-specific probabilities or costs.

### Alternatives considered

| Approach | Data requirements | Defensibility | Complexity | Operator usefulness | False-precision risk |
|---|---|---|---|---|---|
| Expected-consequence counterfactuals over explicit cost assumptions | Existing risk/evidence plus named tariff, downtime, and component cost basis | High when inputs are labelled | Low | High | Moderate |
| Full EVPI/EVSI/VOI policy | Validated inspection sensitivity/specificity and state/outcome data | Currently insufficient | Medium/high | Potentially high | High without test data |
| Learned cost-sensitive policy | Real intervention outcomes, costs, and technician labels | Not currently available | High | Unknown | Very high |

RAI selected the first approach. `information_value_inr` remains `null`
because inspection sensitivity/specificity are not established. The existing
VOI module remains available for explicitly parameterized studies, but is not
silently applied to production decisions.

## Inputs and provenance

Every decision input is returned with a state: model risk is `INFERRED` and is
not an independently observed failure probability; environmental explanation is
`OBSERVED`; tariff, downtime, and component costs are `ASSUMED`; missing input
is `UNKNOWN`. Historical cases remain `INTERNAL_SYNTHETIC` context and are not
used as empirical probabilities.

## Consequence model

The existing Python engine reports energy loss, planned downtime cost,
intervention cost, expected failure-escalation cost, and expected exposure per
option. The adapter adds the waiting consequence, assumptions, uncertainty,
alternatives, and recommended option. Unknown values are `null`; zero is
reserved for a computed zero.

## Decision semantics

- `INTERVENE`: next-window intervention has the lowest computed exposure and evidence is attributable.
- `INSPECT`: environmental conflict or unresolved uncertainty makes information acquisition preferable.
- `MONITOR`: evidence exists, but inferred risk does not justify immediate intervention.
- `WAIT`: low inferred risk supports reassessment at a planned review window.
- `ABSTAIN`: required evidence, calibration, component basis, or sensor health is unavailable.

These are not guaranteed outcomes, ROI, savings, or universal thresholds.

## Evaluation and limitations

The deterministic suite covers intervention, monitor, wait, inspect-first,
insufficient data, conflicting environment, zero risk, unknown component,
sensor failure, and `UNKNOWN != ZERO`. Existing VOI mathematical tests remain
in place. No real intervention outcomes, validated inspection test
characteristics, decision regret, cost avoided, technician agreement, or
production savings are available.

## API and UI

- `GET /api/assets/{asset_id}/decision` returns the structured decision.
- `POST /api/assets/{asset_id}/investigate` includes `economic_decision`.
- Asset Deep-Dive displays decision, status, uncertainty, robustness, and
  intentional “not evaluated” states.
- The local agent receives deterministic economic output through
  `get_economic_options`; it does not perform arithmetic.
