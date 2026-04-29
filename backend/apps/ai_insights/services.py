# backend/apps/ai_insights/services.py


from django.conf import settings
from groq import Groq
from django.db.models import Sum
from collections import defaultdict
import datetime



def generate_insights(expenses):

    client = Groq(api_key=settings.GROQ_API_KEY)

    # ── STATS ─────────────────────────────────────────────────────
    total = float(expenses.aggregate(Sum("amount"))["amount__sum"] or 0)
    personal = float(expenses.filter(category="Personal").aggregate(Sum("amount"))["amount__sum"] or 0)
    professional = float(expenses.filter(category="Professional").aggregate(Sum("amount"))["amount__sum"] or 0)

    # Monthly breakdown
    monthly = defaultdict(float)
    for e in expenses:
        key = e.date.strftime("%B %Y")
        monthly[key] += float(e.amount)

    monthly_str = "\n".join(
        f"  - {month}: Rs {amount:,.0f}"
        for month, amount in sorted(monthly.items())
    ) or "  - No data yet"

    # Top locations
    locations = defaultdict(float)
    for e in expenses:
        locations[e.where_spent] += float(e.amount)

    top_locations = sorted(locations.items(), key=lambda x: x[1], reverse=True)[:3]
    locations_str = ", ".join(
        f"{loc} (Rs {amt:,.0f})" for loc, amt in top_locations
    ) or "None"

    current_month = datetime.date.today().strftime("%B %Y")

    # ── PROMPT ────────────────────────────────────────────────────
    prompt = f"""
You are a smart personal finance assistant for a Pakistani user.
Analyze this expense data and respond with TWO short paragraphs only:

1. SUMMARY: 2-3 sentences summarizing their spending habits.
2. FORECAST: 1-2 sentences predicting next month based on trends.

Be friendly, specific, mention actual Rs amounts. No bullet points, no headers.

--- DATA ---
Total spent: Rs {total:,.0f}
Personal: Rs {personal:,.0f}
Professional: Rs {professional:,.0f}
Current month: {current_month}
Monthly breakdown:
{monthly_str}
Top locations: {locations_str}
------------

Write SUMMARY paragraph, blank line, then FORECAST paragraph. Nothing else.
"""

    # ── CALL GROQ ─────────────────────────────────────────────────
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are a concise financial assistant. Respond in exactly 2 paragraphs."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=300,
        )

        full_text = response.choices[0].message.content.strip()
        paragraphs = [p.strip() for p in full_text.split("\n\n") if p.strip()]
        summary = paragraphs[0] if paragraphs else full_text
        forecast = paragraphs[1] if len(paragraphs) > 1 else ""

    except Exception as e:
        summary = f"Could not generate insights: {str(e)}"
        forecast = ""

    return {
        "total": round(total, 2),
        "personal": round(personal, 2),
        "professional": round(professional, 2),
        "summary": summary,
        "forecast": forecast,
    }