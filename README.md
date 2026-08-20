# LifeOS

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Streamlit%20Cloud-6366f1?style=for-the-badge&logo=streamlit&logoColor=white)](https://lifeos-ofnibiwxcpdemar5vwtswn.streamlit.app/)
[![Tests](https://img.shields.io/badge/Tests-109%20Passed-22c55e?style=for-the-badge&logo=pytest&logoColor=white)](./tests/)
[![Python](https://img.shields.io/badge/Python-3.13-3b82f6?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Database](https://img.shields.io/badge/Database-SQLite%20%2F%20PostgreSQL-f59e0b?style=for-the-badge&logo=postgresql&logoColor=white)](./database/)
[![ML](https://img.shields.io/badge/ML-Scikit--Learn-ec4899?style=for-the-badge&logo=scikit-learn&logoColor=white)](./ml/)

> **[Open Live Application](https://lifeos-ofnibiwxcpdemar5vwtswn.streamlit.app/)** — Explore demo data or create a private account.

LifeOS is an all-in-one personal analytics and habit tracking platform integrating **Study, Health, and Personal Finance** into a cohesive system. Built with modern dark-mode aesthetics, raw SQL query optimizations, machine learning forecasting, and secure multi-user data isolation.

---

## Overview

Tracking daily habits across separate apps creates friction and obscures cross-domain insights. LifeOS solves this by consolidating daily habit tracking, health metrics, and expense management under one unified dashboard powered by machine learning and database-backed analytics.

---

## Key Features

- **Personal Consistency Score**: A user-weighted formula dynamically combining Study, Health, and Finance consistency into a daily performance index.
- **Secure Multi-User Architecture**: Production authentication powered by `bcrypt` (work factor 12) with user data isolation across all CRUD queries and database models.
- **Modern Dark UI Design**: Glassmorphic dark design system with Plus Jakarta Sans typography, refined metric cards, and responsive sidebar navigation.
- **High-Performance Query Caching**: `@st.cache_data` query-level caching layer (`database/cache.py`) with targeted invalidations.
- **Study Module**:
  - Live study session timer using Streamlit fragments (`@st.fragment(run_every="1s")`) without page flicker.
  - Priority task manager with inline completion and status indicators.
  - Streak tracking with SQL gaps-and-islands queries.
- **Health Module**:
  - Dynamic calorie and macronutrient targets based on Mifflin-St Jeor BMR and TDEE formulas.
  - Fast food and water logging with recent food shortcuts.
  - Rolling weight trends and weekly workout consistency tracking.
- **Finance Module**:
  - Monthly budget tracking with progress indicators and status badges (On Track, Near Limit, Over Budget).
  - Categorized expense logging with month-over-month comparisons.
  - Weekly and weekday spending distribution analytics.
- **Machine Learning & Insights**:
  - **Supervised Forecasting**: Logistic Regression model predicting weekly study goal achievement with chronological data splitting and target leakage prevention.
  - **Unsupervised Clustering**: KMeans clustering identifying behavioral day types based on user activity.
- **Data Export & Management**: CSV data export for all modules and demo data seeding/resetting.

---

## Architecture

```
lifeos/
├── app.py                      # Application shell, authentication, and routing
├── config.py                    # Environment settings, DATABASE_URL resolution
├── database/
│   ├── models.py                # SQLAlchemy ORM models (indexed on user_id, Numeric currency)
│   ├── connection.py            # SQLite & PostgreSQL database session factory
│   ├── cache.py                 # Query-level caching & targeted invalidation
│   ├── init_db.py               # Table migrations & demo data seeding
│   └── raw_queries.py           # CTEs, window functions, and SQL aggregations
├── modules/
│   ├── dashboard/               # Unified overview and Consistency Score
│   ├── study/                   # Study timer, task list, streak analytics
│   ├── health/                  # Nutrition, workouts, body metrics, TDEE calculator
│   ├── finance/                 # Expense tracking, budget management, category insights
│   ├── insights/                # Cross-domain correlations and ML forecasting
│   └── settings/                # Profile setup, weight adjustment, CSV export, demo reset
├── ml/
│   ├── preprocessing.py         # Leakage-safe feature engineering & chronological splitting
│   ├── supervised_model.py      # Logistic Regression goal predictor
│   ├── unsupervised_model.py    # KMeans behavioral day clustering
│   ├── train.py                 # Training pipeline & metadata persistence
│   └── evaluate.py              # Confusion matrix and performance evaluation
├── utils/
│   ├── auth.py                  # Bcrypt password hashing & session management
│   ├── charts.py                # Plotly dark theme chart builders
│   ├── date_helpers.py          # Date parsing, week calculations, greeting helper
│   ├── export.py                # CSV export generator
│   ├── health_calc.py           # BMR, TDEE, BMI, and macro calculation formulas
│   ├── ui_components.py         # Custom CSS stylesheet and reusable UI components
│   └── validation.py            # Input validation and boundary checks
└── tests/                       # 109 automated tests (auth, SQL, ML, analytics, scoring)
```

---

## Tech Stack

- **Frontend & App Framework**: Streamlit (with custom CSS design system)
- **Backend & Data**: Python 3.13, Pandas, NumPy, Plotly
- **Database Layer**: SQLAlchemy, SQLite (local), PostgreSQL (production/Supabase/Neon), Raw SQL (CTEs, window functions)
- **Machine Learning**: Scikit-Learn (Logistic Regression, KMeans, StandardScaler)
- **Authentication & Security**: Bcrypt password hashing, session state token guards
- **Testing**: Pytest (109 unit & integration tests)

---

## Installation & Local Setup

### 1. Clone the repository
```bash
git clone https://github.com/DeepakChouhan18/LifeOS.git
cd LifeOS
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the application
```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## Database Configuration

LifeOS automatically resolves database connections in the following priority order:

1. `DATABASE_URL` environment variable.
2. `st.secrets["DATABASE_URL"]` (for Streamlit Community Cloud).
3. Local SQLite database fallback (`data/lifeos.db`).

### PostgreSQL Deployment (Recommended for Cloud Hosting)
For production deployment with persistent multi-user data:
1. Provision a PostgreSQL instance (e.g., [Supabase](https://supabase.com), [Neon](https://neon.tech), or [Railway](https://railway.app)).
2. In Streamlit Community Cloud settings under **Secrets**, configure:
```toml
DATABASE_URL = "postgresql://user:password@host:5432/dbname"
```

---

## Machine Learning Pipeline

### Supervised Learning
- **Task**: Forecast whether the user will achieve their weekly study goal.
- **Features**: Lagged (t-1) study minutes, average calories, workout duration, sleep hours, expenses, and task completion rate.
- **Split**: Strict **chronological split** (past data trains, future data tests) to prevent lookahead bias.
- **Metrics**: Accuracy, Precision, Recall, F1 Score, Confusion Matrix.

### Unsupervised Clustering
- **Task**: Discover behavioral patterns across lifestyle dimensions.
- **Algorithm**: KMeans with automatic $k$ selection ($k \in [2, 5]$) optimizing silhouette score.
- **Interpretability**: Cluster labels generated relative to the user's personal baseline standard deviations.

To retrain models from CLI:
```bash
python ml/train.py
```

---

## Running Tests

Run the complete test suite:
```bash
pytest
```

```text
======================= 109 passed, 14 warnings in 6.20s =======================
```

The test suite validates:
- Password hashing security & multi-tenant user data isolation
- SQL correctness (CTEs, calendar-day rolling averages, gap-and-island streaks)
- BMR/TDEE and macro formulas
- ML feature lag integrity & absence of target leakage
- Personal Consistency Score formula & weight boundaries

---

## License

MIT License. Feel free to use, modify, and build upon this project.
