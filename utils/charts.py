"""Reusable Plotly chart builders, shared across modules.

Every chart builder provides explicit human-readable titles, axis labels,
and legend formatting to ensure clean, professional visualization.
"""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


def apply_chart_theme(fig, title_text=None):
    """
    Applies a clean, modern dark theme to Plotly figures.
    - Explicit title positioning and typography
    - Prevents Plotly.js 'undefined' title bug by avoiding title=None
    - Legend placed below the plot area
    - Responsive padding and Inter font styling
    """
    if fig is None:
        return None

    # Check if fig already has a title string set
    if title_text is None and hasattr(fig, "layout") and fig.layout.title and fig.layout.title.text:
        title_text = fig.layout.title.text

    if title_text:
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, sans-serif", size=12, color="#94A3B8"),
            title=dict(
                text=title_text,
                font=dict(family="Inter, sans-serif", size=13.5, color="#F8FAFC"),
                x=0.01,
                y=0.96,
                xanchor="left",
                yanchor="top",
            ),
            margin=dict(l=24, r=24, t=44, b=50),
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.22,
                xanchor="center",
                x=0.5,
                font=dict(size=11),
                bgcolor="rgba(0,0,0,0)",
            ),
            xaxis=dict(
                gridcolor="#1e293b",
                linecolor="#334155",
                tickfont=dict(size=10.5),
            ),
            yaxis=dict(
                gridcolor="#1e293b",
                linecolor="#334155",
                tickfont=dict(size=10.5),
            ),
        )
    else:
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, sans-serif", size=12, color="#94A3B8"),
            title=dict(text=""),
            margin=dict(l=24, r=24, t=20, b=50),
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.22,
                xanchor="center",
                x=0.5,
                font=dict(size=11),
                bgcolor="rgba(0,0,0,0)",
            ),
            xaxis=dict(
                gridcolor="#1e293b",
                linecolor="#334155",
                tickfont=dict(size=10.5),
            ),
            yaxis=dict(
                gridcolor="#1e293b",
                linecolor="#334155",
                tickfont=dict(size=10.5),
            ),
        )
    return fig


def subject_minutes_bar(df):
    """Bar chart of total study minutes per subject."""
    if df.empty or df["total_minutes"].sum() == 0:
        return None
    fig = px.bar(
        df, x="subject_name", y="total_minutes",
        title="Study Time by Subject",
        labels={"subject_name": "Subject", "total_minutes": "Minutes"},
        color="subject_name",
        color_discrete_sequence=["#6366f1", "#38BDF8", "#34D399", "#FBBF24", "#F87171"],
    )
    fig.update_layout(showlegend=False)
    return apply_chart_theme(fig, "Study Time by Subject")


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
    fig.update_traces(line_color="#6366f1", line_width=2.5)
    return apply_chart_theme(fig, "Rolling 7-Day Study Hours")


def weight_trend_line(df, target_weight=None):
    """Line chart of raw weight entries + smoothed rolling average + optional target line."""
    if df.empty:
        return None
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["log_date"], y=df["weight_kg"],
        mode="markers", name="Logged Weight", marker=dict(size=5, color="#94A3B8", opacity=0.6),
    ))
    fig.add_trace(go.Scatter(
        x=df["log_date"], y=df["rolling_avg_weight"],
        mode="lines", name="7-Day Rolling Avg", line=dict(width=2.5, color="#38BDF8"),
    ))

    if target_weight:
        fig.add_hline(
            y=target_weight, line_dash="dash", line_color="#34D399",
            annotation_text=f"Target ({target_weight} kg)", annotation_position="top right",
        )

    fig.update_layout(xaxis_title="Date", yaxis_title="Weight (kg)")
    return apply_chart_theme(fig, "Weight Trend")


def workout_consistency_bar(df):
    """Bar chart of workouts logged per week."""
    if df.empty:
        return None
    fig = px.bar(
        df, x="week", y="workout_count",
        title="Workouts per Week",
        labels={"week": "Week", "workout_count": "Workouts Completed"},
        color_discrete_sequence=["#10b981"],
    )
    return apply_chart_theme(fig, "Workouts per Week")


def weekly_calories_line(df, calorie_target=None):
    """Line chart of average daily calories per week."""
    if df.empty:
        return None
    fig = px.line(
        df, x="week", y="avg_calories",
        title="Average Daily Calories",
        labels={"week": "Week", "avg_calories": "Daily Avg Calories (kcal)"},
        markers=True,
    )
    fig.update_traces(line_color="#f59e0b", line_width=2.5)
    if calorie_target:
        fig.add_hline(
            y=calorie_target, line_dash="dash", line_color="#F87171",
            annotation_text=f"Target ({calorie_target} kcal)", annotation_position="bottom right",
        )
    return apply_chart_theme(fig, "Average Daily Calories")


def category_spend_pie(df):
    """Donut chart of spend by category."""
    if df.empty or df["total_spent"].sum() == 0:
        return None
    fig = px.pie(
        df, names="category_name", values="total_spent",
        title="Spending by Category",
        hole=0.45,
        labels={"category_name": "Category", "total_spent": "Spend (₹)"},
        color_discrete_sequence=["#6366f1", "#38BDF8", "#34D399", "#f59e0b", "#F87171", "#A78BFA", "#60A5FA"],
    )
    fig.update_traces(textposition="outside", textinfo="percent+label")
    return apply_chart_theme(fig, "Spending by Category")


def budget_remaining_bar(df):
    """Bar chart of remaining budget per category, colored by over/under."""
    if df.empty:
        return None
    fig = px.bar(
        df, x="category_name", y="remaining",
        title="Budget Remaining by Category",
        labels={"category_name": "Category", "remaining": "Remaining Budget (₹)"},
        color=df["remaining"] < 0,
        color_discrete_map={True: "#EF4444", False: "#10B981"},
    )
    fig.update_layout(showlegend=False)
    return apply_chart_theme(fig, "Budget Remaining by Category")


def spend_trend_line(df):
    """Line chart of rolling 7-day spend."""
    if df.empty:
        return None
    fig = px.line(
        df, x="expense_date", y="rolling_7day_spend",
        title="Spend Trend",
        labels={"expense_date": "Date", "rolling_7day_spend": "7-Day Total Spend (₹)"},
        markers=True,
    )
    fig.update_traces(line_color="#f59e0b", line_width=2.5)
    return apply_chart_theme(fig, "Spend Trend")


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
        title="Today's Macro Breakdown",
        hole=0.48,
        labels={"Macro": "Macronutrient", "Calories": "Calories (kcal)"},
        color="Macro",
        color_discrete_map={"Protein": "#6366f1", "Carbs": "#f59e0b", "Fats": "#ef4444"},
    )
    fig.update_traces(textposition="inside", textinfo="percent")
    return apply_chart_theme(fig, "Today's Macro Breakdown")
