# LifeOS

A personal Study, Health, and Finance analytics platform, designed to be opened
every day — not a portfolio demo. Built to also demonstrate real SQL, Python,
and applied ML skills along the way.

## Overview

LifeOS tracks three areas of daily life — study, health/fitness, and personal
finance — in one SQLite-backed Streamlit app, with an Overview dashboard that
pulls them together, and an Insights tab that applies real machine learning to
your own logged data.

## Problem

Tracking study time, meals/workouts, and expenses across separate apps makes it
hard to see patterns or stay consistent. LifeOS puts all three in one place with
meaningful analytics instead of just storing numbers.

## Solution

Three independent modules (Study, Health, Finance) that each feel like a
complete mini-application, plus a combined Overview and an Insights tab with
real SQL analytics and two ML models trained on your own history.

## Key Features

- **Onboarding choice**: Start Fresh (empty personal database) or Explore Demo
  Data (clearly labeled, resettable sample data) — no fake data silently
  injected into a real account.
- **Automatic health targets**: BMR (Mifflin-St Jeor), TDEE, calorie target,
  protein target, and BMI are all calculated from your profile — you never
  enter maintenance calories manually. Recalculates instantly when you edit
  your profile.
- **Fast daily logging**: quick-add food (with a Recent Foods shortcut),
  one-tap water logging, a real study session timer that auto-saves on finish,
  and a quick expense entry form.
- **Edit/delete everywhere**: every logged record (food, workout, weight,
  study session, task, expense) can be edited or deleted, not just added.
- **Personal Consistency Score**: a simple, user-configurable weighted average
  across the three modules — explicitly *not* presented as an objective "life
  score." Weights are adjustable in Settings.
- **Cross-domain insights**: patterns like "your study time is 18% higher than
  last week" or "your highest spending day has been Saturday," generated from
  real stored data (never hardcoded), and phrased as observed patterns, not
  causation.
- **Real ML**: a supervised model predicting weekly study-goal achievement and
  an unsupervised model clustering days into interpretable behavior types —
  both trained on-demand via an explicit "Train Models" button, never silently
  retrained on every page load.
- **CSV export** for Study, Health, Finance, and combined data.

## Architecture

```
lifeos/
├── app.py                   # Entry point: onboarding gate + navigation
├── config.py                 # Paths, constants, default weights/goals
├── database/
│   ├── models.py              # SQLAlchemy models (indexed, Numeric money, constraints)
│   ├── connection.py          # Engine/session setup
│   ├── init_db.py             # Table creation, column migration, demo data seeding
│   └── raw_queries.py         # Hand-written SQL: CTEs, window functions, JOINs, HAVING
├── modules/
│   ├── study/                  # Tasks, sessions, timer, streaks, subjects
│   ├── health/                  # Nutrition, water, workouts, weight, targets
│   ├── finance/                  # Expenses, categories, budgets, insights
│   ├── dashboard/                 # Overview aggregation + Personal Consistency Score
│   ├── insights/                   # Cross-domain analytics + ML UI
│   └── settings/                    # Onboarding, profile, score weights, export, reset
├── ml/
│   ├── preprocessing.py         # Daily/weekly feature engineering, leakage-safe
│   ├── supervised_model.py       # Logistic Regression, chronological split
│   ├── unsupervised_model.py      # KMeans, baseline-relative cluster labeling
│   ├── train.py                    # Training workflow + DB metadata persistence
│   ├── evaluate.py                  # Metric/summary formatting
│   └── models/                       # Saved model artifacts (gitignored)
├── utils/
│   ├── health_calc.py            # BMR/TDEE/BMI/calorie-target formulas
│   ├── validation.py              # Shared input validation
│   ├── charts.py                   # Plotly chart builders
│   ├── export.py                    # CSV export
│   ├── date_helpers.py               # Date/week utilities
│   └── ui_components.py               # Shared CSS, empty states, progress widgets
└── tests/                        # 74 tests across all modules
```

## Tech Stack

Python · Streamlit · SQLite · SQLAlchemy · raw SQL · Pandas · NumPy · Plotly ·
scikit-learn · Pytest · Git/GitHub

No FastAPI, Docker, React, or additional databases — kept deliberately to this
stack, since the goal is depth within it, not technology count.

## Database Design

- Every table is indexed on `user_id`, on date columns, and on `(user_id, date)`
  composites, since nearly every query filters on both.
- Money fields (`Expense.amount`, `Budget.limit_amount`, `UserProfile.monthly_budget`)
  use `Numeric(10, 2)`, not `Float`, to avoid floating-point rounding errors in
  financial totals.
- `CheckConstraint`s enforce basic sanity (amounts/durations can't be negative)
  at the DB level as a second line of defense behind `utils/validation.py`.
- Calculated health values (BMR, TDEE, targets, BMI) are **never stored** — only
  the raw profile inputs are. Targets are recomputed on every read, so they can
  never drift out of sync with the profile.

## SQL Highlights

All in `database/raw_queries.py`, actually used by the app (not decorative):

- **Streak calculation** — a "gaps and islands" CTE using `ROW_NUMBER()` and
  date-subtraction to group consecutive study days into islands.
- **True calendar-day rolling windows** — weight trend, weekly study minutes,
  and rolling spend all use a correlated subquery with `BETWEEN date-6 AND date`,
  *not* `ROWS BETWEEN 6 PRECEDING`. The row-based version would silently produce
  wrong "weekly" totals whenever a day was skipped (7 rows ≠ 7 calendar days
  once there are gaps) — this was caught and fixed during development.
- **`HAVING`** — categories over budget are found with `GROUP BY ... HAVING
  SUM(amount) > limit`, since the filter depends on an aggregate.
- **Self-joins** — month-over-month category comparison joins `this_month` and
  `last_month` CTEs on category.
- **`LEFT JOIN`** — subject/category breakdowns include zero-activity rows
  (e.g. a subject with no sessions still shows 0 minutes, not a missing row).

## Analytics

Each module (Study/Health/Finance) exposes 7-day/30-day averages, consistency
percentages, and trend charts, all built on the raw SQL above via Pandas.
Finance additionally generates plain-language insights (month-over-month
category change, weekday spending patterns, largest expenses) — only surfaced
when the underlying data actually supports the claim (e.g. a month-over-month
comparison is skipped entirely if last month has no data).

## Machine Learning

### Supervised Learning
- **Problem**: predict whether the user will hit their weekly study goal.
- **Features**: the *previous* week's study minutes, average calories, workout
  minutes, average sleep, total expenses, and task completion rate.
- **Target**: current week's `goal_hit` (1/0), based on the user's own
  `daily_study_goal_minutes × 7`.
- **Leakage avoidance**: features are shifted by exactly one week (`shift(1)`)
  before being paired with the label — a week's own data is never used to
  predict its own outcome. Verified by `tests/test_ml_preprocessing.py::test_weekly_features_no_target_leakage`.
- **Model**: Logistic Regression (scikit-learn), `StandardScaler`-normalized.
- **Data splitting**: **chronological**, not random — the earliest weeks are
  always training data, the most recent weeks are always the test set. A
  random split would let the model "test" on the past using information from
  the future, which doesn't reflect the real forecasting task. Verified by
  `tests/test_ml_models.py::test_chronological_split_test_set_is_always_the_most_recent`.
- **Evaluation**: accuracy, precision, recall, F1, and a full confusion matrix
  — only computed and shown once at least `MIN_WEEKS_FOR_SUPERVISED_EVAL` (6)
  weeks of history exist. Below that threshold, the app explicitly states
  "not enough historical data" rather than reporting a number computed on 1-2
  test points.
- **Known edge case, handled**: if all available weeks share the same label
  (goal always hit or always missed), scikit-learn's `LogisticRegression`
  cannot fit at all (it requires 2 classes). This is detected before fitting
  and reported as "not enough label variation yet" rather than crashing —
  caught during development and covered by
  `tests/test_ml_models.py::test_supervised_model_single_class_does_not_crash`.

### Unsupervised Learning
- **Problem**: identify recurring "day types" from combined study, health, and
  finance activity.
- **Features**: study minutes, calories, workout minutes, sleep hours, and
  expense amount, per day.
- **Algorithm**: KMeans (scikit-learn), `k` chosen automatically by trying
  `k=2..5` and picking the best silhouette score.
- **Evaluation**: silhouette score, always shown alongside results.
- **Interpretability**: cluster labels (e.g. "High Study & Active") are
  generated by comparing each cluster's mean feature values against the
  **user's own** overall mean/standard deviation (a z-score-style comparison)
  — not fixed universal thresholds. This means "high study" is meaningful
  whether the user studies 30 minutes/day or 4 hours/day on average.

### Training Architecture
Database → feature engineering (`ml/preprocessing.py`) → training
(`ml/train.py`) → evaluation → model + metadata saved → loaded for display.
Training only happens when the user clicks **Train Models** on the Insights
page — the app does not retrain on every page load. Each training run also
writes a row to `MLModelMetadata` (algorithm, sample count, feature names,
data period, metrics) so "last trained on X" can be shown without re-running
anything.

## Installation

```bash
git clone <your-repo-url>
cd lifeos
pip install -r requirements.txt
```

## Running Locally

```bash
streamlit run app.py
```

On first launch, you'll be asked to **Start Fresh** or **Explore Demo Data**.
No database file or fake data is created until you choose.

## Database Initialization

Tables are created automatically on first run (`database/init_db.ensure_tables()`,
called from `app.py`). To manually create tables and load demo data from the
command line instead:

```bash
python database/init_db.py
```

## Demo Data

Demo data (profile + ~5 weeks of study/health/finance history) is clearly
flagged (`UserProfile.is_demo = True`) and shown with a banner in the app.
Reset it any time from **Settings → Data Management → Reset Demo Data**, or
delete it entirely to switch to your own real data.

## Training Models

From the app: **Insights → Machine Learning → Train Models**.

From the command line:
```bash
python ml/train.py
```

## Testing

```bash
pytest
```

74 tests covering: BMR/TDEE/BMI/calorie-target calculations (including the
no-universal-1200-floor requirement), study streaks and completion, finance
budgets and category totals, raw SQL (JOINs, CTEs, `HAVING`, calendar-based
rolling windows, missing-date behavior), ML preprocessing (no NaNs, no target
leakage), ML models (chronological splitting, insufficient-data handling,
single-class training safety), input validation, and the Personal Consistency
Score formula.

## Deployment

Target: **Streamlit Community Cloud**. The app works from a clean environment
with no local paths or personal data baked in — `data/lifeos.db` and
`ml/models/*.pkl` are gitignored, and the onboarding flow means a fresh
deployment starts empty (or with demo data, by the visitor's own choice).

## Limitations

- **Single-user**: no authentication. `DEFAULT_USER_ID` is used throughout;
  the schema is `user_id`-keyed everywhere so multi-user support wouldn't
  require a schema rewrite, but auth itself isn't implemented.
- **ML accuracy on small datasets**: with only a few weeks of real history,
  the supervised model will usually report "not enough data" rather than a
  metric — this is intentional (see Machine Learning section above), but it
  means the ML tab won't show impressive numbers until you've used the app
  for 6+ weeks.
- **7700 kcal/kg rule of thumb**: the optional adaptive maintenance estimate
  (Health → Analytics) uses the commonly cited but approximate energy content
  of body fat; it's labeled as an estimate, not a precise measurement.
- **No backup/restore beyond CSV export**: data can be exported but not
  re-imported from a backup file.
- **Not medical or financial advice**: calorie/BMI/budget outputs are
  informational, not clinical or professional guidance — the app says so
  directly where relevant (e.g. the aggressive-deficit warning).

## Future Improvements

- Adaptive maintenance estimate could incorporate more robust trend-fitting
  (e.g. linear regression over the weight series) instead of a two-point
  endpoint comparison.
- A study session heatmap/calendar view.
- Category-level budget rollover between months.
- Optional multi-user auth if this stops being a single-person tool.
