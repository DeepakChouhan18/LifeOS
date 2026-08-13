"""
Dashboard aggregator — powers the Overview page.

Two responsibilities:
1. Personal Consistency Score — a simple, transparent, user-configurable
   weighted average (NOT presented as an objective "life score"; weights
   live on the user's own profile and can be changed in Settings).
2. Real, data-driven insights, including cross-domain patterns (e.g.
   study vs. workout). These are described as "observed patterns", never
   as causation — the SQL only reports correlation-shaped facts, and the
   wording here is written to match that.
"""

from modules.study import analytics as study_analytics
from modules.health import analytics as health_analytics
from modules.finance import analytics as finance_analytics
from modules.settings import crud as settings_crud
from database import raw_queries as rq
from config import DEFAULT_SCORE_WEIGHTS


def _study_score(summary: dict) -> float:
    completion_component = summary.get("completion_pct", 0.0)
    current_streak = summary.get("current_streak", 0)
    streak_component = min(current_streak / 7.0, 1.0) * 100.0
    return round((completion_component * 0.6) + (streak_component * 0.4), 1)


def _health_score(summary: dict) -> float:
    workouts = summary.get("workouts_this_week", 0)
    workout_component = min(workouts / 4.0, 1.0) * 100.0

    calorie_diff = summary.get("calorie_diff") or 0
    calorie_component = max(0.0, 100.0 - (abs(calorie_diff) / 10.0))
    calorie_component = min(calorie_component, 100.0)

    return round((workout_component * 0.5) + (calorie_component * 0.5), 1)


def _finance_score(summary: dict) -> float:
    budget = summary.get("total_budget_this_month", 0)
    remaining = summary.get("budget_remaining", 0)

    if not budget or float(budget) == 0:
        return 50.0

    pct_remaining = (float(remaining) / float(budget)) * 100.0
    return round(max(0.0, min(100.0, 100.0 + pct_remaining if pct_remaining < 0 else 100.0)), 1)


def get_score_weights(session, user_id: int) -> dict:
    """User-configurable weights from their profile, falling back to defaults."""
    profile = settings_crud.get_user_profile(session, user_id)
    if profile and profile.score_weight_study is not None:
        return {
            "study": profile.score_weight_study,
            "health": profile.score_weight_health,
            "finance": profile.score_weight_finance,
        }
    return DEFAULT_SCORE_WEIGHTS


def generate_insights(session, user_id: int) -> list:
    """
    Generates plain-language insights strictly from real stored data.
    Cross-domain relationships are phrased as "observed patterns", never
    as causal claims (e.g. never "X causes Y").
    """
    insights = []
    comparison = rq.get_weekly_comparison(session, user_id)

    if len(comparison) >= 2:
        last_week, this_week = comparison[0], comparison[1]

        s1, s2 = last_week["study_minutes"], this_week["study_minutes"]
        if s1 > 0:
            diff_pct = round(((s2 - s1) / s1) * 100.0, 1)
            if diff_pct > 5:
                insights.append(f"Your study time is {diff_pct}% higher than last week.")
            elif diff_pct < -5:
                insights.append(f"Your study time is {abs(diff_pct)}% lower than last week.")

        sp1, sp2 = float(last_week["total_spend"]), float(this_week["total_spend"])
        if sp1 > 0:
            sp_diff = round(((sp2 - sp1) / sp1) * 100.0, 1)
            if sp_diff > 10:
                insights.append(f"Your spending is {sp_diff}% higher than last week.")
            elif sp_diff < -10:
                insights.append(f"Your spending is {abs(sp_diff)}% lower than last week.")

    # Protein consistency insight (uses real 7-day consistency, not just today)
    consistency = health_analytics.get_target_consistency(session, user_id, days=7)
    if consistency["days_logged"] >= 4 and consistency["protein_consistency_pct"] is not None:
        days_hit = round(consistency["protein_consistency_pct"] / 100 * consistency["days_logged"])
        insights.append(
            f"Protein target achieved {days_hit} of the last {consistency['days_logged']} logged days."
        )

    # Cross-domain: study vs workout (observed pattern only, no causation claim)
    cross = rq.get_cross_study_workout(session, user_id)
    if len(cross) >= 3:
        weeks_with_workout = [w for w in cross if w["workout_count"] > 0]
        weeks_without = [w for w in cross if w["workout_count"] == 0]
        if weeks_with_workout and weeks_without:
            avg_study_with = sum(w["study_hours"] for w in weeks_with_workout) / len(weeks_with_workout)
            avg_study_without = sum(w["study_hours"] for w in weeks_without) / len(weeks_without)
            if avg_study_with > avg_study_without * 1.15:
                insights.append(
                    "Observed pattern: your study hours tend to be higher in weeks "
                    "with at least one workout logged."
                )

    study_sum = study_analytics.get_full_summary(session, user_id)
    if study_sum["current_streak"] >= 3:
        insights.append(f"You're on a {study_sum['current_streak']}-day study streak.")

    if not insights:
        insights.append("Log a few days of study, health, and expenses to start seeing personalized insights here.")

    return insights[:5]


def get_todays_priorities(session, user_id: int) -> list:
    """
    Builds a real "today's priorities" checklist from actual incomplete
    items — never a hardcoded list.
    """
    from modules.study import crud as study_crud
    priorities = []

    pending_tasks = study_crud.list_tasks(session, user_id, include_completed=False)
    high_priority = [t for t in pending_tasks if t.priority == "high"]
    for task in high_priority[:2]:
        priorities.append({"label": task.title, "done": False})

    health_summary = health_analytics.get_full_summary(session, user_id)
    if not health_summary["workout_completed_today"]:
        priorities.append({"label": "Workout", "done": False})
    else:
        priorities.append({"label": "Workout", "done": True})

    if health_summary["calorie_target"] and health_summary["calories_today"] <= health_summary["calorie_target"]:
        priorities.append({"label": "Stay within calorie target", "done": True})
    elif health_summary["calorie_target"]:
        priorities.append({"label": "Stay within calorie target", "done": False})

    return priorities[:5]


def get_combined_summary(session, user_id: int) -> dict:
    study_summary = study_analytics.get_full_summary(session, user_id)
    health_summary = health_analytics.get_full_summary(session, user_id)
    finance_summary = finance_analytics.get_full_summary(session, user_id)

    weights = get_score_weights(session, user_id)

    study_score = _study_score(study_summary)
    health_score = _health_score(health_summary)
    finance_score = _finance_score(finance_summary)

    consistency_score = round(
        study_score * weights["study"] + health_score * weights["health"] + finance_score * weights["finance"], 1,
    )

    return {
        "study": study_summary, "health": health_summary, "finance": finance_summary,
        "scores": {
            "study": study_score, "health": health_score, "finance": finance_score,
            "overall": consistency_score,
        },
        "weights": weights,
        "insights": generate_insights(session, user_id),
        "priorities": get_todays_priorities(session, user_id),
    }
