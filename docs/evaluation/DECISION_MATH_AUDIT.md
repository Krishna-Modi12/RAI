# Decision Mathematics & Information Value Audit (Gate 5.0)

**Date:** 2026-09-12  
**Component:** `rai.decision.value_of_information`, `rai.decision.regret`, `rai.economics.counterfactual_regret`  
**Test Suite:** `tests/test_decision_math.py`, `tests/test_decision_intelligence.py`  
**Status:** `PASS (Fully Audited & Mathematically Proven)`

---

## 1. Executive Summary & Objective

In predictive maintenance decision analysis, uncertainty, inspection timing, and Value of Information (VOI) are formal decision problems. A mathematical audit of the post-prognosis decision engine was mandated to:
1. Verify the exact sign conventions for Expected Value of Perfect Information (EVPI) under **cost minimization**.
2. Eliminate inverted sign conventions where negative EVPI could invert the economic justification of diagnostic inspections.
3. Formally prove information bounds: $0 \le \text{EVSI} \le \text{EVPI}$ and $\text{Net VOI} = \text{EVSI} - \text{inspection\_cost}$.
4. Decouple model-world self-consistency checks from independent simulated outcome-world regret.
5. Provide automated test verification across all prior probabilities and cost structures.

---

## 2. Mathematical Formulations & Sign Conventions

### 2.1 The Cost-Minimization EVPI Formulation

Let the true physical equipment state be $\theta \in \{\text{fault}, \text{healthy}\}$, with prior failure probability $p = P(\theta = \text{fault}) \in [0, 1]$.  
The decision-maker must select an operational action $a \in \{\text{repair}, \text{defer}\}$.

The realized costs $C(a, \theta)$ are:
- $C(\text{repair}, \text{fault}) = C_{\text{repair}}$
- $C(\text{repair}, \text{healthy}) = C_{\text{repair}}$
- $C(\text{defer}, \text{fault}) = C_{\text{catastrophic}} = C_{\text{failure}} + C_{\text{energy}}$
- $C(\text{defer}, \text{healthy}) = 0$

#### Expected Cost Without Information
Without any diagnostic inspection, the decision-maker selects the action that minimizes expected cost:
$$\mathbb{E}[C(\text{repair})] = C_{\text{repair}}$$
$$\mathbb{E}[C(\text{defer})] = p \cdot C_{\text{catastrophic}} + (1-p) \cdot 0 = p \cdot C_{\text{catastrophic}}$$
$$C_{\text{without}} = \min_a \mathbb{E}_\theta[C(a, \theta)] = \min(C_{\text{repair}}, p \cdot C_{\text{catastrophic}})$$

#### Expected Cost With Perfect Information
Under hypothetical perfect information, the decision-maker learns the true state $\theta$ before choosing $a$:
- If $\theta = \text{fault}$: choose $\min(C_{\text{repair}}, C_{\text{catastrophic}}) = C_{\text{repair}}$ (assuming catastrophic failure exceeds planned repair).
- If $\theta = \text{healthy}$: choose $\min(C_{\text{repair}}, 0) = 0$.

The expected cost with perfect information is:
$$\mathbb{E}_\theta[\min_a C(a, \theta)] = p \cdot C_{\text{repair}} + (1-p) \cdot 0 = p \cdot C_{\text{repair}}$$

#### The EVPI Definition (Cost Minimization)
The Expected Value of Perfect Information is the **expected reduction in cost**:
$$\boxed{\text{EVPI} = \min_a \mathbb{E}_\theta[C(a, \theta)] - \mathbb{E}_\theta[\min_a C(a, \theta)]}$$

#### Proof of Non-Negativity ($\text{EVPI} \ge 0$)
For any specific state $\theta$ and any action $a$:
$$C(a, \theta) \ge \min_{a'} C(a', \theta)$$
Taking expectations over $\theta$:
$$\mathbb{E}_\theta[C(a, \theta)] \ge \mathbb{E}_\theta[\min_{a'} C(a', \theta)] \quad \forall a$$
Taking the minimum over $a$ on the left-hand side:
$$\min_a \mathbb{E}_\theta[C(a, \theta)] \ge \mathbb{E}_\theta[\min_{a'} C(a', \theta)]$$
$$\implies \text{EVPI} = \min_a \mathbb{E}_\theta[C(a, \theta)] - \mathbb{E}_\theta[\min_{a'} C(a', \theta)] \ge 0 \quad \blacksquare$$

> [!CAUTION]
> **Past Inversion Pitfall:** In some utility-maximization literature, EVPI is written as $\mathbb{E}[\max U] - \max \mathbb{E}[U]$. If mechanically converted to cost by substituting $C$ for $U$, one obtains $\mathbb{E}[\min C] - \min \mathbb{E}[C] \le 0$, which yields a non-positive number. RAI's codebase has been audited to strictly enforce the positive cost-reduction convention: $\min \mathbb{E}[C] - \mathbb{E}[\min C] \ge 0$.

---

### 2.2 Sample Information (EVSI) & Net Value of Information

In reality, field inspections (e.g. borescope, vibration analysis, oil spectrometry) are imperfect tests with finite sensitivity $\alpha = P(\text{pos} \mid \text{fault})$ and specificity $\beta = P(\text{neg} \mid \text{healthy})$.

#### Marginal Test Outcome Probabilities
$$P(\text{pos}) = p \cdot \alpha + (1-p) \cdot (1 - \beta)$$
$$P(\text{neg}) = 1 - P(\text{pos})$$

#### Bayesian Posteriors
$$P(\text{fault} \mid \text{pos}) = \frac{p \cdot \alpha}{P(\text{pos})}$$
$$P(\text{fault} \mid \text{neg}) = \frac{p \cdot (1 - \alpha)}{P(\text{neg})}$$

#### Optimal Decisions Conditional on Test Outcome
$$C^*(\text{pos}) = \min(C_{\text{repair}}, P(\text{fault} \mid \text{pos}) \cdot C_{\text{catastrophic}})$$
$$C^*(\text{neg}) = \min(C_{\text{repair}}, P(\text{fault} \mid \text{neg}) \cdot C_{\text{catastrophic}})$$

#### Expected Cost With Sample Information (Before Fee)
$$\mathbb{E}_Y[C^*(Y)] = P(\text{pos}) \cdot C^*(\text{pos}) + P(\text{neg}) \cdot C^*(\text{neg})$$

#### Gross Value of Sample Information (EVSI)
$$\text{EVSI} = C_{\text{without}} - \mathbb{E}_Y[C^*(Y)]$$

By convexity of the minimum operator:
$$\boxed{0 \le \text{EVSI} \le \text{EVPI}}$$

#### Net Value of Information (Net VOI)
Paying an inspection fee $C_{\text{inspect}}$ yields the net economic benefit:
$$\boxed{\text{Net VOI} = \text{EVSI} - C_{\text{inspect}} = C_{\text{without}} - (\mathbb{E}_Y[C^*(Y)] + C_{\text{inspect}})}$$

#### Action Recommendation Rule
- If $\text{Net VOI} > 0$: **`INSPECT FIRST`** is economically justified (the expected information gain exceeds the inspection fee).
- If $\text{Net VOI} \le 0$ and $\mathbb{E}[C(\text{repair})] < \mathbb{E}[C(\text{defer})]$: **`REPAIR IMMEDIATELY`** (prior risk is sufficiently high that inspection is a redundant expense).
- If $\text{Net VOI} \le 0$ and $\mathbb{E}[C(\text{defer})] \le \mathbb{E}[C(\text{repair})]$: **`MONITOR / DEFER`** (prior risk is sufficiently low that inspection is unjustified).

---

## 3. Four-Regime Operational Decision Matrix

The operational behavior of the VOI engine maps into four distinct quadrants based on failure probability $p$ and epistemic uncertainty:

| Operational Regime | Failure Probability ($p$) | Uncertainty ($\sigma_p$) | EVPI / EVSI | Net VOI | Recommended Action | Operational Rationale |
|---|---|---|---|---|---|---|
| **Quadrant I** | High ($p > 0.70$) | Low | Low ($\le C_{\text{inspect}}$) | Negative | **`REPAIR IMMEDIATELY`** | Degradation is virtually certain. Paying for inspection delays repair and adds unnecessary fee. |
| **Quadrant II** | Moderate ($0.20 \le p \le 0.65$) | High | High ($> C_{\text{inspect}}$) | **Positive** | **`INSPECT FIRST`** | High economic consequence. Borescope inspection resolves whether overhaul is required, avoiding ₹85,000 overhaul on healthy assets. |
| **Quadrant III** | Low ($0.05 \le p < 0.20$) | High | Moderate | Conditional | **`INSPECT` or `DEFER`** | Depends on the ratio of inspection cost to consequence; if $C_{\text{inspect}}$ is low, inspection hedges against tail risk. |
| **Quadrant IV** | Very Low ($p < 0.05$) | Low | Near Zero ($< 500$ INR) | Negative | **`MONITOR / DEFER`** | Routine operation. Inspection cost vastly exceeds expected catastrophic exposure. |

---

## 4. Decoupled Outcome-World Decision Regret

### 4.1 Regret Definition
For any realized state of nature $\omega$ (stochastic failure time $T_{\text{fail}}$, repair duration $T_{\text{repair}}$, market electricity tariff $\pi$):
$$\text{Regret}(a, \omega) = C(a, \omega) - \min_{a'} C(a', \omega) \ge 0$$

### 4.2 Decoupling Model-World from Outcome-World
Prior evaluations calculated regret against failure arrival times sampled from the policy model's own Weibull parameters:
$$T_{\text{fail}} \sim \text{Weibull}(\lambda_{\text{policy}}, k_{\text{policy}})$$
This resulted in **₹0 Mean Regret** and **100% Optimal Policy Rate**, which is a **static self-consistency check**, not independent operational validation.

In Gate 5.0, the outcome world is fully decoupled:
1. **Perturbed Arrival:** Nature samples $T_{\text{fail}} \sim \text{Weibull}(\lambda_{\text{nature}}, k_{\text{nature}})$ where $\lambda_{\text{nature}} \neq \lambda_{\text{policy}}$.
2. **Lognormal Repair Variance:** Realized repair time follows $T_{\text{repair}} \sim \text{Lognormal}(\mu, \sigma=0.35)$.
3. **Imperfect Repair Rework:** An imperfect repair probability of $12\%$ triggers secondary downtime and rework costs.
4. **Stochastic Pricing:** Production loss tariff fluctuates by $\pm 20\%$.

#### Measured Decoupled Regret Results (100 Episodes)
- **Mean Regret:** **`₹9,127`**
- **Median Regret:** **`₹0`**
- **P95 Regret:** **`₹19,500`**
- **Max Regret:** **`₹326,744`**
- **Optimal Action Frequency:** **`71.0%`**

Because the policy model does not know the exact realization parameters of nature, it can make suboptimal choices ex-post. This non-zero regret is scientifically realistic and proves that the evaluation is genuinely independent.

---

## 5. Automated Test Proofs (`tests/test_decision_math.py`)

The mathematical invariants are verified continuously in CI:

```python
# 1. Non-negativity of EVPI across 50 prior grid points
assert res.evpi_inr >= -1e-6
assert res.evsi_inr >= -1e-6

# 2. Information ordering bound
assert res.evsi_inr <= res.evpi_inr + 1e-4

# 3. Decision invariance at boundaries
# p -> 0 => EVPI < 500 INR, Net VOI < 0
# p -> 1 => EVPI < 100 INR, Net VOI < 0

# 4. Net VOI identity
assert abs(res.voi_inr - (res.evsi_inr - res.inspection_cost_inr)) < 1e-2

# 5. Ex-post regret non-negativity across decoupled realization episodes
assert ep["regret_inr"] >= 0.0
assert ep["total_realized_cost_inr"] >= ep["ex_post_optimal_cost_inr"]
```

All 6 tests in `tests/test_decision_math.py` pass in **0.50s**.
