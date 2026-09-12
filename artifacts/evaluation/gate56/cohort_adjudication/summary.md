# Gate 5.6B -- PVDAQ Cohort Adjudication & Modeling Readiness

## NO MODELING WAS PERFORMED. This gate is adjudication-only.

## 1. Is every selected timestamp axis defensible?
No, not uniformly. Systems 1239, 1283, 34 have real, ground-truth `utc_measured_on` (0% null) -- fully defensible. Systems 1430 and 1433 have `utc_measured_on` null for 100% of records; their local-time convention could only be established by strong circumstantial analogy to sibling system 1283 (whose real UTC ground truth PROVES its own `measured_on` is fixed UTC-7/MST, not DST-aware civil time, despite systems.csv declaring a DST-aware zone) -- not independently confirmed for 1430/1433 themselves. Both are classified TIMESTAMP_AMBIGUOUS. See timestamp_adjudication.csv.

## 2. Which systems have trustworthy power targets?
1239=VALID_GENERATION_POWER, 1283=VALID_SIGNED_POWER, 34=VALID_SIGNED_POWER, 1430=VALID_GENERATION_POWER, 1433=VALID_SIGNED_POWER
All 5 have a documented classification; none are marked AMBIGUOUS after investigation (system 1283's 39.5%-negative channel was investigated in depth and classified VALID_SIGNED_POWER -- see system_1283_power_semantics.md).

## 3. What is the meaning of the negative 1283 readings?
Legitimate nighttime station-service/parasitic-load grid draw on a whole-site bidirectional net meter. 100% of negative readings occur when real measured POA irradiance is 0; 0% occur during any daytime interval. The existing Gate 5.5 NIGHT quality filter already removes/flags nighttime records before generation-performance evaluation, so this finding does not require a channel change or value correction -- only explicit documentation that the target is a NET (not pure-generation) meter. Full evidence in system_1283_power_semantics.md.

## 4. Which systems are empirical-ready?
1239=True, 1283=True, 34=True, 1430=True, 1433=True

## 5. Which systems are physics-ready?
1239=True (all required real inputs present and cross-validated), 1283=True (all required real inputs present and cross-validated), 34=True (all required real inputs present and cross-validated), 1430=False (missing real geometry; no CEC module parameter match; timestamp not independently UTC-verified), 1433=False (no CEC module parameter match; timestamp not independently UTC-verified)
Real evidence used: pvlib's bundled CEC module database (21,535 entries) contains a near-exact name match for 1239 (Sharp ND-224UC1), 1283 (SunPower SPR-315E-WHT-D), and 34 (Sharp NU-U240F1) -- in all three cases the matched module's STC power x real installed quantity reproduces the system's independently-declared total capacity to within rounding, cross-validating the match. No CEC match exists for 1430's Sanyo HIP-195BA3 or 1433's Sanyo HIT-205A modules (older/discontinued products). 1430 is additionally a single-axis tracker whose real Mount metadata leaves axis tilt/azimuth/gcr/backtrack entirely blank (a genuine gap, not filled here). Temperature and AOI model parameters are NOT available per-system for any of the 5 systems; a physics-ready classification here means the STANDARD pvlib preset tables (keyed by real racking type) could be used as a disclosed modeling assumption, not that a per-system measured coefficient exists.

## 6. Which systems are validation-ready?
1239=True, 1283=True, 34=True, 1430=False, 1433=False

## 7. What is the final frozen cohort for Gate 5.6C?
Development: [1239, 1283, 34]. Validation: [] (status: INSUFFICIENT_DATA). Secondary-only: [1430, 1433]. Excluded: []. See cohort_freeze_v2.json.

## 8. What alignment policy will Gate 5.6C use?
FASTEST_SIGNAL_GRID_WITH_BACKWARD_HOLD: align onto the AC power signal's native interval; slower context signals (temperature, wind) use backward-only hold with a 90-minute staleness cap (else NaN); POA is matched exact-or-within-5-minutes (no backward hold, since irradiance changes too fast for a stale value to be representative). No interpolation, no future-value use. See alignment_policy.json.

## 9. Which pvlib configuration is possible for each physics-ready system?
For 1239/1283/34 (the only candidates with a matched CEC module): dc_model=cec (pending explicit inverter-parameter confirmation -- a CEC inverter database name match exists but was NOT independently capacity-cross-validated in this gate the way modules were), temperature_model=sapm_temp using a racking-type-appropriate pvlib preset (a disclosed standard assumption), aoi_model=ashrae with pvlib's default b=0.05 (also a disclosed standard assumption, not measured). See pvlib_readiness.csv for the per-system reason field.

## 10. Is system-level holdout still statistically meaningful?
With zero systems in VALIDATION role, a system-level external holdout is NOT currently statistically meaningful -- there is nothing to hold out. Gate 5.6C's author must decide, and explicitly justify, a fallback design (e.g. a temporal holdout within the 3 development systems) rather than treating this as resolved. This decision is NOT made here -- Gate 5.6B's role is adjudication, not modeling design.

## Per-system classification
- System 1239: **READY** (final_role=DEVELOPMENT)
- System 1283: **READY** (final_role=DEVELOPMENT)
- System 34: **READY** (final_role=DEVELOPMENT)
- System 1430: **READY_WITH_LIMITATIONS** (final_role=SECONDARY_ONLY)
- System 1433: **READY_WITH_LIMITATIONS** (final_role=SECONDARY_ONLY)

## STOP RULE compliance
No expected-power model was built or fit. No ModelChain was run. No Gate 5.6C, 5.7, Needle, Qwen, or RAG work was started. This gate stops here pending the user's audit.