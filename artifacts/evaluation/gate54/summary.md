# Gate 5.4 — Cross-Farm Wind Transfer & Target-Normal Calibration Summary

## 1. Executive Transfer Scorecard

Evaluated all 6 directed cross-farm transfers across 95 CARE datasets in 509.99s.

| Source Farm | Target Farm | Frozen Source CARE | Calibrated CARE | Reference Target CARE | $\Delta_{\text{transfer}}$ | $\Delta_{\text{calibration}}$ | Gap Recovery |
|---|---|---|---|---|---|---|---|
| Wind Farm A | Wind Farm B | **0.5705** | **0.5650** | **0.5417** | +0.0288 | -0.0055 | 19.1% |
| Wind Farm A | Wind Farm C | **0.5927** | **0.5940** | **0.5521** | +0.0406 | +0.0013 | -3.2% |
| Wind Farm B | Wind Farm A | **0.5906** | **0.5806** | **0.5722** | +0.0184 | -0.0100 | 54.3% |
| Wind Farm B | Wind Farm C | **0.5977** | **0.5940** | **0.5521** | +0.0456 | -0.0037 | 8.1% |
| Wind Farm C | Wind Farm A | **0.4392** | **0.5806** | **0.5722** | -0.1330 | +0.1414 | 106.3% |
| Wind Farm C | Wind Farm B | **0.5452** | **0.5650** | **0.5417** | +0.0035 | +0.0198 | -565.7% |

## 2. Directional Asymmetry Analysis

| Pair | Forward Transfer ($S \to T$) | Reverse Transfer ($T \to S$) | Asymmetry (|$\Delta$|)
|---|---|---|---|
| Wind Farm A $\leftrightarrow$ Wind Farm B | +0.0288 (Frozen CARE 0.5705) | +0.0184 (Frozen CARE 0.5906) | **0.0104** |
| Wind Farm A $\leftrightarrow$ Wind Farm C | +0.0406 (Frozen CARE 0.5927) | -0.1330 (Frozen CARE 0.4392) | **0.1736** |
| Wind Farm B $\leftrightarrow$ Wind Farm C | +0.0456 (Frozen CARE 0.5977) | +0.0035 (Frozen CARE 0.5452) | **0.0421** |

## 3. Key Findings & Research Questions Answered
- **Transferability under Frozen Source:** How much performance is lost under direct frozen transfer?
- **Target-Normal Calibration:** Does adapting power/rotor curves on unlabelled normal target operation recover performance?
- **Asymmetry:** Are transfer penalties symmetric or directional?
- **Leakage Isolation:** Zero target fault labels or prediction-split data were accessed during calibration.