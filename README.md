# IELTS Personalised Learning Dashboard

An English, single-page Streamlit MVP for a discussion with Professor Maruf. It demonstrates descriptive learning analytics and explainable study recommendations. It is not an IELTS scoring engine or a validated learning intervention.

## Run locally

Python 3.10+ is required. From this directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

Open the localhost URL printed by Streamlit. No credentials, LLM, network service or database is needed to run the dashboard. Scores are stored in a local CSV; downloaded plans are saved through the browser. There is no data-entry or CSV-upload interface in this MVP.

## Deploy from GitHub with Streamlit Community Cloud

1. Create a GitHub repository and push this directory, including `app.py`, `learning.py`, `requirements.txt` and `data/demo_sessions.csv`.
2. In [Streamlit Community Cloud](https://share.streamlit.io/), choose **Deploy an app** and select the repository and branch.
3. Set the main file path to `app.py` (the file is at the repository root).
4. Deploy. Streamlit Cloud installs the packages from `requirements.txt`; no secrets are required for this MVP.

Keep `.streamlit/secrets.toml`, `.env` files and the local `.venv` out of GitHub. This app uses bundled synthetic data only and does not need a database or API key.

## Files

```text
app.py                   English dashboard and filters
learning.py              CSV validation, summaries and deterministic rules
feedback.py              Future feedback protocol, inactive
requirements.txt         Runtime dependencies
data/demo_sessions.csv   20 explicitly synthetic sessions
tests/test_dashboard.py  Analytics and Streamlit AppTest checks
```

## Data model

One row represents one supplied skill-level practice/result record, not one full IELTS examination. The bundled dataset is one fictional learner with five observations for each skill, dated 1–20 October 2026. Its illustrative scores are manually constructed fixture values, not model outputs or teacher marks. The demo dates are fixed for reproducibility; the UI initially anchors the evidence window to the latest dataset date rather than today.

| Field | Meaning |
| --- | --- |
| session_id | Required unique record ID; DEMO prefix in fixtures |
| learner_id | Required learner identifier |
| date | Observation date, ISO YYYY-MM-DD |
| skill | Listening, Reading, Writing or Speaking |
| task_type | Task 2 for Writing; Full practice or Timed set in other demo records |
| score_source | simulated_practice, human_assessed or official_ielts |
| is_demo | Explicit true/false; Demo rows must be simulated_practice |
| score | Supplied 0–9 score in half-band steps; never inferred |
| duration_minutes | Recorded practice duration, 1–1440 minutes |
| notes | Provenance/context text; fixture disclaimer on every row |
| task_response, coherence_cohesion | Writing Task 2 criteria |
| fluency_coherence, pronunciation | Speaking criteria |
| lexical_resource, grammar | Writing/Speaking criteria |

Criterion fields may be blank when unavailable; irrelevant criteria must be blank. Missing values are never imputed. Scores are validated for format and range, not authenticity. `official_ielts` represents externally obtained official results; `human_assessed` represents externally supplied human marks. Neither source has any fabricated sample rows. Do not add examiner criterion values to official results unless actually supplied. The app cannot authenticate certificates or assessor qualifications. It does not derive an official Writing score from criteria or combine Task 1 and Task 2; Writing Task 1 is outside this MVP.

Only add consented real records with `is_demo=false` and correct provenance. The source selector and Demo/Real selector keep analyses separate, including source categories with no data. Real records are not bundled. Local CSV storage has no authentication or multi-user access controls; use locally for this demonstration.

## Three modules

1. **Learning Overview:** per-skill recent means (up to three supplied scores), observed score history, practice counts and total minutes. No overall IELTS band is produced. Cards summarise skill-level records and can include different tasks; chart hovers expose task types.
2. **Weakness Analysis:** Writing Task 2 and Speaking criterion means, target gaps and observed history. Comparisons are grouped by skill and task. Six non-missing criterion observations are necessary for a recent-three versus previous-three change. With only five per skill in the fixture, change is intentionally unavailable.
3. **Personalised Study Plan:** concrete activities, time allocation and explanations, downloadable as CSV with evidence dates, target, provenance and Demo status.

## Transparent recommendation rules

- Filter to one learner, source, Demo status and inclusive evidence window ending on the chosen date. Sort by observation date, then session ID; same-day ID order is deterministic, not a claim of within-day chronology.
- Use up to three latest non-missing scores per criterion and task. A single observation can generate a tentative priority; its sample size is shown. No minimum-sample claim of reliability is made.
- Gap = max(0, target − recent mean). Decline bonus = 0.5 only if a full three-versus-three comparison exists and change is ≤ −0.5. Priority = gap + decline bonus.
- Rank positive criterion priorities descending. Ties use skill and criterion names, with task ordering inherited from the analysis. Generate a rubric-aligned exercise for each.
- Append diagnostic work for missing skills, requests for criterion feedback when Writing/Speaking lacks all criterion values, and Listening/Reading timed review. These are appended after criterion priorities; a full seven-item plan may defer them. Listening/Reading tasks do not claim question-level diagnosis.
- If no candidates exist, suggest maintenance and fresh feedback. Reaching the target in observations does not establish exam readiness.
- Select up to seven activities. Divide the weekly budget in five-minute units equally; give leftover units to earlier priorities. UI budgets are multiples of five, so the whole budget is allocated. Assign one activity per consecutive day starting at the selected plan date. This is an allocation heuristic, not an empirically optimised schedule.
- One target applies to each skill/criterion for simplicity. It is a configurable planning threshold, not an official band requirement or predicted result.

The UI exposes means, sample counts, gaps, changes and priority values, plus a reason per activity. Charts are descriptive; no causality, score prediction, statistical significance or improvement guarantee is claimed. Different tasks and difficulty levels can still limit comparability even within a source.

## Research and future NLP work

The MVP implements the analytics and transparent recommendation layer. It does not currently perform NLP, automatic essay assessment, speech analysis, emotion recognition or machine learning. scikit-learn is deliberately omitted because no trained model is needed. A later study could evaluate consented text features or feedback variants against teacher-labelled evidence and measure learning outcomes; the synthetic fixture cannot establish effectiveness.

`feedback.py` provides a `FeedbackContext` and `FeedbackProvider` protocol. It is not imported or invoked by the app. The future context reserves an optional **learner-reported** emotion and explicit consent flag. A future provider must enforce consent, minimise retained personal data, distinguish observations from inferred states, and avoid fabricating scores. No LLM implementation, provider credentials or API calls exist in version 1.

## Verification

```bash
python -m unittest discover -s tests -v
```

Checks cover fixture provenance, insufficient trend evidence, priority calculations, budget conservation, missing-data diagnostics, mixed-source rejection, malformed data and Streamlit default/empty-source/small-budget interactions. AppTest inspects app execution and controls; it does not verify browser pixel layout.

## Suggested demonstration

Use Demo / Simulated Practice with target 7.0 and 210 minutes. Show Writing grammar as a below-target priority, explain why the trend difference is blank, and export a plan. Reduce the budget to 35 minutes to show deterministic reallocation. Select Official IELTS to show that the app reports no evidence and proposes diagnostics rather than inventing results.

## Sources

- [IELTS Writing preparation and assessment criteria](https://ielts.org/take-a-test/preparation-resources/writing-test-resources)
- [IELTS Speaking assessment criteria](https://ielts.org/news-and-insights/demystifying-the-ielts-speaking-test)
- [Streamlit AppTest documentation](https://docs.streamlit.io/develop/api-reference/app-testing)

Official criterion names inform the schema; the recommendation formula and learning activities are project heuristics, not official IELTS recommendations.
