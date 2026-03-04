"""
generate_narratives.py
Uses the Claude API to generate personalised narrative commentary
for each adviser report from their data config.

Called after build_config.py produces the raw data, and before
generate_report.py renders the PDF.

Usage:
    from generate_narratives import enrich_config_with_narratives
    config = enrich_config_with_narratives(config)
"""

import json
import os
import anthropic


SYSTEM_PROMPT = """\
You are the analytics narrator for a life insurance distribution company's monthly adviser reports.
You write short, data-driven commentary for financial advisers — clear, specific, and encouraging
without being fluffy. Every claim must reference a number from the data provided.

STYLE RULES:
- Write in second person ("you", "your")
- Bold key numbers and standout insights using HTML: <b>bold</b>
- Keep sentences short and punchy — no filler
- Never invent numbers — only use what's in the data
- If performance is poor, frame it constructively (opportunity, not criticism)
- Use HTML tags for formatting: <b> for bold, <font color="#252B37"> for emphasis
- Do NOT use markdown — only HTML inline formatting
- Each narrative should be 2-4 sentences unless specified otherwise
"""


def build_narrative_prompt(config):
    """Build the prompt with all data the narrator needs."""
    # Extract the key data points for the prompt
    months = config.get("MONTHS_DATA", [])
    current_month = months[-1] if months else {}
    prev_months = months[:-1] if len(months) > 1 else []

    # Find best previous month
    best_prev = max(prev_months, key=lambda m: m.get("prem", 0)) if prev_months else {}

    # 12-month totals
    total_12m_premium = sum(m.get("prem", 0) for m in months)
    total_12m_apps = sum(m.get("apps", 0) for m in months)

    # Month labels
    import calendar as cal
    def month_label(m):
        return f"{cal.month_abbr[m.get('m', 1)]} {m.get('y', '')}"

    data_summary = {
        "adviser_name": config.get("ADVISER_NAME", ""),
        "report_month": config.get("REPORT_MONTH_NAME", ""),
        "report_year": config.get("REPORT_YEAR", ""),

        # Current month KPIs
        "current_month_premium": config.get("KPI_TOTAL_SUBMITTED_RAW", 0),
        "current_month_premium_formatted": config.get("KPI_TOTAL_SUBMITTED", ""),
        "current_month_apps": config.get("KPI_APPLICATIONS", 0),
        "current_month_avg_premium": config.get("KPI_AVG_PREMIUM_RAW", 0),

        # Historical context
        "best_previous_month": month_label(best_prev) if best_prev else "",
        "best_previous_premium": best_prev.get("prem", 0),
        "total_12m_premium": total_12m_premium,
        "total_12m_apps": total_12m_apps,
        "months_trend": [{"month": month_label(m), "premium": m.get("prem", 0),
                          "apps": m.get("apps", 0)} for m in months],

        # Benchmarking
        "conversion_rate": config.get("ADVISER_CONV", 0),
        "network_avg": config.get("NETWORK_AVG", 0),
        "median_conv": config.get("MEDIAN", 0),
        "rank": config.get("ADVISER_RANK", 0),
        "total_practices": config.get("TOTAL_PRACTICES", 0),
        "percentile": config.get("PERCENTILE", 0),
        "adviser_leads": config.get("ADVISER_LEADS", 0),

        # Speed to contact / conversion drivers
        "conv_by_calls": config.get("CONV_BY_CALLS_12M", {}),
        "quoted_vs_unquoted": config.get("QUOTED_VS_UNQUOTED", {}),
        "call_multiplier": config.get("CALL_MULTIPLIER", 0),
        "quote_multiplier": config.get("QUOTE_MULTIPLIER", 0),
        "total_leads_12m": config.get("TOTAL_LEADS_12M", 0),
        "avg_case_0_calls": config.get("AVG_CASE_0_CALLS", 0),
        "avg_case_3_plus": config.get("AVG_CASE_3_PLUS", 0),

        # Pipeline / strongest predictor
        "quoted_conv": config.get("QUOTED_CONV", 0),
        "unquoted_conv": config.get("UNQUOTED_CONV", 0),
        "stale_quoted_count": config.get("STALE_QUOTED_COUNT", 0),
        "stale_est_premium": config.get("STALE_EST_PREMIUM", 0),
        "pipeline_segments": config.get("PIPELINE_SEGMENTS", []),

        # CRM hygiene
        "stale_appointments": config.get("STALE_APPOINTMENTS", 0),

        # Completion forecast
        "completion_rate": config.get("COMPLETION_RATE", 0),
        "avg_days_to_complete": config.get("AVG_DAYS", 0),
        "feb_in_progress": config.get("FEB_IN_PROGRESS", 0),
        "expected_completions": config.get("EXPECTED_COMPLETIONS", 0),
        "expected_prem": config.get("EXPECTED_PREM", 0),
    }

    prompt = f"""Here is the data for this adviser's monthly report. Generate ALL narrative sections
in a single JSON response.

DATA:
{json.dumps(data_summary, indent=2, default=str)}

Generate a JSON object with these exact keys. Each value should be an HTML-formatted string
(using <b> for bold, no markdown). Follow the length and content guidance for each:

1. "EXEC_NARRATIVE" — 2-3 sentences summarising the month. Lead with the headline number
   (premium or apps), compare to previous best if it's a record, note any standout trend.
   
2. "EXEC_DRIVING" — 1 sentence on what's driving performance (volume, case size, or both).

3. "STC_NARRATIVE" — 2-3 sentences about speed-to-contact patterns. Reference the call
   multiplier and quote multiplier. State the quoted vs unquoted conversion rates.

4. "WHAT_WORKS_INTRO" — 1-2 sentences introducing the conversion analysis. Reference the
   adviser's rate vs network average if notably higher.

5. "WHAT_WORKS_NARRATIVE" — 3-4 sentences about conversion by call activity. Reference total
   leads analysed, the conversion rate at 0 calls vs 3+ calls, and the average case value
   difference. Bold the multiplier.

6. "PREDICTOR_NARRATIVE_1" — 2-3 sentences about quoted vs unquoted conversion. State both
   rates, the multiplier, and what it means practically.

7. "PREDICTOR_NARRATIVE_2_TEMPLATE" — 2 sentences about the stale quoted pipeline opportunity.
   MUST include the literal placeholders {{stale_count}} and ${{est_premium:,.0f}} (these get
   formatted later). Reference the quoted conversion rate as the basis.

8. "PREDICTOR_CLOSING" — 2 sentences closing the predictor section. Summarise the pattern
   (deep engagement → high conversion) and suggest applying it to lighter-touch segments.

9. "CRM_NOTE" — 2-3 sentences about CRM hygiene. Reference the stale appointment count.
   Frame as: accurate data = better reports = better decisions. Not accusatory.

10. "FORMULA_TEXT" — 1-2 sentences summarising the winning formula from the data.
    Bold the key drivers.

11. "HIGHLIGHTS" — A JSON array of 3-4 short strings (max 15 words each) for the summary
    page bullet points. Each should be a key takeaway from the month.

12. "SHOW_MILESTONE" — boolean: true if current month premium >= $100,000 or total 12-month
    premium >= $500,000, or current month apps >= 25. Otherwise false.

13. "MILESTONE_TEXT" — If SHOW_MILESTONE is true, a short celebration line (e.g., "$100K MONTH – ACHIEVED").
    If false, empty string.

14. "MILESTONE_SUB" — If SHOW_MILESTONE is true, a 1-sentence sub-line. If false, empty string.

RESPOND WITH ONLY THE JSON OBJECT. No preamble, no markdown fences, no explanation."""

    return prompt


def enrich_config_with_narratives(config, api_key=None):
    """Call Claude API to generate narratives and merge them into config.

    Args:
        config: dict from build_config.build_all()
        api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)

    Returns:
        config dict with narrative fields populated
    """
    if api_key is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("⚠️  No ANTHROPIC_API_KEY — narratives will be empty placeholders")
        return config

    client = anthropic.Anthropic(api_key=api_key)

    prompt = build_narrative_prompt(config)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract text response
        text = ""
        for block in response.content:
            if hasattr(block, "text"):
                text += block.text

        # Clean and parse JSON
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            text = text.rsplit("```", 1)[0]

        narratives = json.loads(text)

        # Merge into config
        narrative_keys = [
            "EXEC_NARRATIVE", "EXEC_DRIVING", "STC_NARRATIVE",
            "WHAT_WORKS_INTRO", "WHAT_WORKS_NARRATIVE",
            "PREDICTOR_NARRATIVE_1", "PREDICTOR_NARRATIVE_2_TEMPLATE",
            "PREDICTOR_CLOSING", "CRM_NOTE", "FORMULA_TEXT",
            "HIGHLIGHTS", "SHOW_MILESTONE", "MILESTONE_TEXT", "MILESTONE_SUB",
        ]
        for key in narrative_keys:
            if key in narratives:
                config[key] = narratives[key]

        print(f"✅ Narratives generated ({len([k for k in narrative_keys if k in narratives])} fields)")
        return config

    except json.JSONDecodeError as e:
        print(f"⚠️  Failed to parse narrative JSON: {e}")
        print(f"   Raw response: {text[:200]}...")
        return config
    except Exception as e:
        print(f"⚠️  Claude API error: {e}")
        return config


# ═══════════════════════════════════════════════════════════════════
#  CLI — standalone test
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import importlib
    import sys

    # Load existing static config for testing
    sys.path.insert(0, os.path.dirname(__file__))
    rc = importlib.import_module("report_config")

    # Build config dict from module attributes
    config = {k: getattr(rc, k) for k in dir(rc) if k.isupper() and not k.startswith("_")}

    enriched = enrich_config_with_narratives(config)

    # Print results
    for key in ["EXEC_NARRATIVE", "HIGHLIGHTS", "SHOW_MILESTONE"]:
        print(f"\n{key}:")
        print(f"  {enriched.get(key, '(empty)')}")
