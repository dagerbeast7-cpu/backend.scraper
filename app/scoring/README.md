# 📊 Lead Quality Scoring Module (`app/scoring/`)

This directory contains the lead quality scoring engine rules and point calculator.

---

## 📁 File Manifest & Responsibilities

### 1. `engine.py`
* **Purpose**: Evaluates prospect data completeness and assigns a score from 0 to 100.
* **Point Allocation Rules**:
  * **WhatsApp Present**: `+30 points`
  * **Verified Phone**: `+20 points`
  * **Email Present**: `+20 points`
  * **Website Present**: `+15 points`
  * **Active Business**: `+15 points`
  * **Recently Updated (< 30 days)**: `+10 points`
* **Functions**:
  * `score_prospect(prospect)`: Calculates point total, clamped to 100 maximum.
  * `apply_score(prospect)`: Updates `prospect.score` field in place.
