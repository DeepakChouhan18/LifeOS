"""Reusable Plotly chart builders, shared across modules."""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


def apply_chart_theme(fig):
    """
    Applies a clean, modern dark theme to Plotly figures.

    Legend is placed BELOW the plot (not above) — a legend anchored
    above the chart (y > 1) sits in the same vertical space as the
    chart's own title text and anything rendered above it in Streamlit,
    causing visible overlap/collision. Below-plot placement avoids that
    for every chart type (bar, line, pie/donut) without needing a
    per-chart special case.
    """
    if fig is None:
        return None
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", size=12, color="#94A3B8"),
        title=dict(y=0.97, yanchor="top"),
        margin=dict(l=20, r=20, t=60, b=70),
        legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="center", x=0.5),
    )
    return fig


def subject_minutes_bar(df):
    """Bar chart of total study minutes per subject."""
    if df.empty or df["total_minutes"].sum() == 0:
        return None
    fig = px.bar(
        df, x="subject_name", y="total_minutes",
        title="Study Time by Subject (minutes)",
        labels={"subject_name": "Subject", "total_minutes": "Minutes"},
        color="subject_name",
        color_discrete_sequence=["#38BDF8", "#818CF8", "#34D399", "#FBBF24", "#F87171"],
    )
    fig.update_layout(showlegend=False)
    return apply_chart_theme(fig)


def rolling_weekly_line(df):
    """Line chart of rolling 7-day study hours over time."""
    if df.empty:
        return None
    fig = px.line(
        df, x="session_date", y="rolling_7day_hours",
        title="Rolling 7-Day Study Hours",
        labels={"session_date": "Date", "rolling_7day_hours": "Hours (7-day total)"},
        markers=True,
    )
    fig.update_traces(line_color="#38BDF8", line_width=3)
    return apply_chart_theme(fig)


def weight_trend_line(df, target_weight=None):
    """Line chart of raw weight entries + smoothed rolling average + optional target line."""
    if df.empty:
        return None
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["log_date"], y=df["weight_kg"],
        mode="markers", name="Logged weight", marker=dict(size=6, color="#94A3B8", opacity=0.6),
    ))
    fig.add_trace(go.Scatter(
        x=df["log_date"], y=df["rolling_avg_weight"],
        mode="lines", name="7-entry rolling avg", line=dict(width=3, color="#38BDF8"),
    ))

    if target_weight:
        fig.add_hline(
            y=target_weight, line_dash="dash", line_color="#34D399",
            annotation_text=f"Target ({target_weight} kg)", annotation_position="top right"
        )

    fig.update_layout(title="Weight Trend (kg)", xaxis_title="Date", yaxis_title="Weight (kg)")
    return apply_chart_theme(fig)


def workout_consistency_bar(df):
    """Bar chart of workouts logged per week."""
    if df.empty:
        return None
    fig = px.bar(
        df, x="week", y="workout_count",
        title="Workouts per Week",
        labels={"week": "Week", "workout_count": "Workouts"},
        color_discrete_sequence=["#818CF8"],
    )
    return apply_chart_theme(fig)


def weekly_calories_line(df, calorie_target=None):
    """Line chart of average daily calories per week."""
    if df.empty:
        return None
    fig = px.line(
        df, x="week", y="avg_calories",
        title="Avg Daily Calories per Week",
        labels={"week": "Week", "avg_calories": "Avg Calories"},
        markers=True,
    )
    fig.update_traces(line_color="#FBBF24", line_width=3)
    if calorie_target:
        fig.add_hline(
            y=calorie_target, line_dash="dash", line_color="#F87171",
            annotation_text=f"Target ({calorie_target} kcal)", annotation_position="bottom right"
        )
    return apply_chart_theme(fig)


def category_spend_pie(df):
    """Donut chart of spend by category."""
    if df.empty or df["total_spent"].sum() == 0:
        return None
    fig = px.pie(
        df, names="category_name", values="total_spent",
        title="Spending by Category (This Month)",
        hole=0.45,
        color_discrete_sequence=["#38BDF8", "#34D399", "#818CF8", "#FBBF24", "#F87171", "#A78BFA", "#60A5FA"],
    )
    return apply_chart_theme(fig)


def budget_remaining_bar(df):
    """Bar chart of remaining budget per category, colored by over/under."""
    if df.empty:
        return None
    fig = px.bar(
        df, x="category_name", y="remaining",
        title="Budget Remaining by Category",
        labels={"category_name": "Category", "remaining": "Remaining (₹)"},
        color=df["remaining"] < 0,
        color_discrete_map={True: "#EF4444", False: "#10B981"},
    )
    fig.update_layout(showlegend=False)
    return apply_chart_theme(fig)


def spend_trend_line(df):
    """Line chart of rolling 7-day spend."""
    if df.empty:
        return None
    fig = px.line(
        df, x="expense_date", y="rolling_7day_spend",
        title="Rolling 7-Day Spend",
        labels={"expense_date": "Date", "rolling_7day_spend": "Spend (7-day total)"},
        markers=True,
    )
    fig.update_traces(line_color="#10B981", line_width=3)
    return apply_chart_theme(fig)


def macro_breakdown_donut(protein_g, carbs_g, fats_g):
    """Donut chart of macronutrient breakdown for today."""
    p_kcal = (protein_g or 0) * 4
    c_kcal = (carbs_g or 0) * 4
    f_kcal = (fats_g or 0) * 9
    total = p_kcal + c_kcal + f_kcal

    if total == 0:
        return None

    df = pd.DataFrame({
        "Macro": ["Protein", "Carbs", "Fats"],
        "Calories": [p_kcal, c_kcal, f_kcal],
    })

    fig = px.pie(
        df, names="Macro", values="Calories",
        title="Today's Macro Breakdown (kcal)",
        hole=0.45,
        color="Macro",
        color_discrete_map={"Protein": "#38BDF8", "Carbs": "#FBBF24", "Fats": "#F87171"},
    )
    return apply_chart_theme(fig)
