# apps/ai_insights/services.py

from django.conf import settings
from groq import Groq
from django.db.models import Sum
from collections import defaultdict
import datetime


def generate_insights(expenses, income: float = 0):
    """
    Generate AI financial insights.

    Args:
        expenses: QuerySet of Expense objects for the user
        income:   User's current monthly income in PKR (0 if not set)
    """
    client = Groq(api_key=settings.GROQ_API_KEY)

    # ── Totals ────────────────────────────────────────────────────
    total = float(expenses.aggregate(Sum("amount"))["amount__sum"] or 0)

    personal = float(
        expenses.filter(category="Personal")
        .aggregate(Sum("amount"))["amount__sum"] or 0
    )
    professional = float(
        expenses.filter(category="Professional")
        .aggregate(Sum("amount"))["amount__sum"] or 0
    )

    # ── Monthly breakdown ─────────────────────────────────────────
    monthly = defaultdict(float)
    monthly_dates = {}

    for e in expenses:
        key = e.date.strftime("%B %Y")
        monthly[key] += float(e.amount)
        monthly_dates[key] = datetime.date(e.date.year, e.date.month, 1)

    sorted_months = sorted(
        monthly.items(),
        key=lambda x: monthly_dates[x[0]]
    )

    # ── Trend & prediction ────────────────────────────────────────
    trend = "stable"
    predicted_next = 0

    if len(sorted_months) >= 2:
        last_month = sorted_months[-1][1]
        prev_month = sorted_months[-2][1]

        if last_month > prev_month * 1.15:
            trend = "increasing"
        elif last_month < prev_month * 0.85:
            trend = "decreasing"

        predicted_next = round(last_month + (last_month - prev_month) * 0.5, 2)
    elif sorted_months:
        predicted_next = sorted_months[-1][1]

    # ── Income-aware calculations ─────────────────────────────────
    current_month = datetime.date.today()
    month_expenses = float(
        expenses.filter(
            date__year=current_month.year,
            date__month=current_month.month
        ).aggregate(Sum("amount"))["amount__sum"] or 0
    )

    has_income = income > 0
    remaining_budget = round(income - month_expenses, 2) if has_income else None
    savings_rate = round(((income - month_expenses) / income) * 100, 1) if has_income and income > 0 else None
    savings_potential = round(income * 0.20, 2) if has_income else round(total * 0.15, 2)

    # Income-to-expense ratio context
    if has_income and month_expenses > 0:
        expense_ratio = round((month_expenses / income) * 100, 1)
    else:
        expense_ratio = None

    dominant_category = "Personal" if personal >= professional else "Professional"
    overspending = (
        personal > professional * 2 if professional > 0 else personal > total * 0.7
    )

    # ── Location analysis ─────────────────────────────────────────
    locations = defaultdict(float)
    for e in expenses:
        if e.where_spent:
            locations[e.where_spent] += float(e.amount)

    top_locations = sorted(locations.items(), key=lambda x: x[1], reverse=True)[:5]

    # ── Build prompt context strings ──────────────────────────────
    monthly_str = (
        "\n".join(f"  - {month}: Rs {amt:,.0f}" for month, amt in sorted_months)
        or "  - No monthly data available"
    )

    locations_str = (
        ", ".join(f"{loc} (Rs {amt:,.0f})" for loc, amt in top_locations)
        or "None recorded"
    )

    income_section = ""
    if has_income:
        income_section = f"""
Income & Budget (THIS MONTH):
  - Monthly Income: Rs {income:,.0f}
  - This Month's Expenses: Rs {month_expenses:,.0f}
  - Remaining Budget: Rs {remaining_budget:,.0f}
  - Savings Rate: {savings_rate}%
  - Expense-to-Income Ratio: {expense_ratio}%
  - Recommended Savings Target (20% rule): Rs {savings_potential:,.0f}
"""
    else:
        income_section = """
Income & Budget:
  - Income not set — analysis based on expense patterns only
  - Recommend user to set their monthly income for budget tracking
"""

    prompt = f"""
You are an elite Pakistani personal finance advisor AI integrated into SmartLedger,
a personal finance app used in Pakistan.

Analyze the user's complete financial data below and provide sharp, actionable insights.

STRICT RULES:
- Write EXACTLY 2 paragraphs. No more, no less.
- NO headings, NO bullet points, NO bold text, NO markdown.
- Be direct, specific, and brutally honest — do not sugarcoat bad habits.
- Use Pakistani context: mention Rs, local spending habits, Easypaisa/JazzCash if relevant.
- Reference real numbers from the data in your response.
- If income is set: comment specifically on savings rate, budget utilization, and whether they
  are on track or overspending relative to income.
- If income is NOT set: focus on expense patterns and strongly encourage setting income.
- Paragraph 1: Behavioral analysis — spending patterns, bad habits, category imbalances,
  location-based overspending, payment method patterns.
- Paragraph 2: Forward-looking — next month forecast, specific savings targets in Rs,
  2–3 concrete actions they can take immediately.

USER DATA:
{income_section}
All-Time Totals:
  - Total Spending: Rs {total:,.0f}
  - Personal Spending: Rs {personal:,.0f}
  - Professional Spending: Rs {professional:,.0f}
  - Dominant Category: {dominant_category}
  - Overspending Risk: {"Yes" if overspending else "No"}

Trend Analysis:
  - Spending Trend: {trend}
  - Predicted Next Month: Rs {predicted_next:,.0f}
  - Potential Monthly Savings: Rs {savings_potential:,.0f}

Monthly Breakdown:
{monthly_str}

Top Spending Locations:
  {locations_str}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a professional Pakistani financial advisor. "
                        "Provide realistic, concise, brutally honest, high-value insights. "
                        "Always respond in exactly 2 plain paragraphs with no formatting."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.35,
            max_tokens=500,
        )

        full_text = response.choices[0].message.content.strip()

        # Split into exactly 2 paragraphs
        paragraphs = [p.strip() for p in full_text.split("\n\n") if p.strip()]

        summary = paragraphs[0] if paragraphs else full_text
        forecast = paragraphs[1] if len(paragraphs) > 1 else ""

    except Exception:
        summary = (
            "Your spending data shows current financial activity, but AI insights are "
            "temporarily unavailable. Continue monitoring personal and professional expenses, "
            "reduce unnecessary discretionary purchases, and maintain a stable monthly budget "
            "for healthier savings growth."
        )
        forecast = (
            "If current patterns continue, your next month's expenses may remain similar. "
            "Focus on reducing avoidable personal spending, reviewing major expense locations, "
            "and targeting at least 15–20% monthly savings."
        )

    return {
        "total": round(total, 2),
        "personal": round(personal, 2),
        "professional": round(professional, 2),
        "trend": trend,
        "predicted_next": round(predicted_next, 2),
        "savings_potential": savings_potential,
        "income": income,
        "remaining_budget": remaining_budget,
        "savings_rate": savings_rate,
        "month_expenses": round(month_expenses, 2),
        "summary": summary,
        "forecast": forecast,
    }