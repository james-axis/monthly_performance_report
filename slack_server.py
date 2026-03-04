"""
slack_server.py
Flask server that receives Slack slash commands and triggers report generation.

Slash command usage:
    /report john_rojas               → generates last month's report for John Rojas
    /report john_rojas feb 2026      → generates specific month
    /report all                      → generates all advisers (last month)
    /report list                     → lists all active advisers

Environment variables:
    SLACK_SIGNING_SECRET   — from Slack app settings (to verify requests)
    DB_USER, DB_PASS etc   — same as pipeline
    GOOGLE_SERVICE_ACCOUNT_JSON, GOOGLE_DRIVE_FOLDER_ID
"""

import os
import sys
import hmac
import hashlib
import time
import threading
import json
from datetime import datetime, timedelta
from flask import Flask, request, jsonify

sys.path.insert(0, os.path.dirname(__file__))

app = Flask(__name__)


# ═══════════════════════════════════════════════════
#  Slack request verification
# ═══════════════════════════════════════════════════

def verify_slack_request(req):
    """Verify the request actually came from Slack."""
    signing_secret = os.getenv("SLACK_SIGNING_SECRET", "")
    if not signing_secret:
        return True  # Skip verification if not configured (dev mode)

    slack_signature = req.headers.get("X-Slack-Signature", "")
    slack_timestamp = req.headers.get("X-Slack-Request-Timestamp", "")

    # Reject requests older than 5 minutes
    if abs(time.time() - int(slack_timestamp)) > 300:
        return False

    sig_basestring = f"v0:{slack_timestamp}:{req.get_data(as_text=True)}"
    my_signature = "v0=" + hmac.new(
        signing_secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(my_signature, slack_signature)


# ═══════════════════════════════════════════════════
#  Helper: parse adviser name from slug
# ═══════════════════════════════════════════════════

def find_adviser(conn, name_slug):
    """Find adviser user_id by partial name match."""
    from build_config import query
    name_parts = name_slug.replace("_", " ").replace("-", " ").strip()
    rows = query(conn, """
        SELECT DISTINCT u.id, u.first_name, u.last_name
        FROM auth_user u
        JOIN account_usergroup_users ugu ON ugu.user_id = u.id
        JOIN account_usergroup ug ON ug.id = ugu.usergroup_id
            AND ug.real = 1 AND ug.is_active = 1
        WHERE u.is_active = 1
          AND CONCAT(u.first_name, ' ', u.last_name) LIKE %s
        LIMIT 5
    """, (f"%{name_parts}%",))
    return rows


def get_previous_month():
    today = datetime.now()
    first = today.replace(day=1)
    last = first - timedelta(days=1)
    return last.month, last.year


def parse_month_year(tokens):
    """Parse optional month/year from tokens like ['feb', '2026']."""
    month_map = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
        'may': 5, 'jun': 6, 'jul': 7, 'aug': 8,
        'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
        'january': 1, 'february': 2, 'march': 3, 'april': 4,
        'june': 6, 'july': 7, 'august': 8, 'september': 9,
        'october': 10, 'november': 11, 'december': 12,
    }
    month, year = get_previous_month()
    for token in tokens:
        if token.lower() in month_map:
            month = month_map[token.lower()]
        elif token.isdigit() and len(token) == 4:
            year = int(token)
    return month, year


# ═══════════════════════════════════════════════════
#  Background report generation
# ═══════════════════════════════════════════════════

def run_report_background(user_id, adviser_name, month, year, response_url):
    """Run report generation in background thread, post result to Slack."""
    import requests as req_lib
    from run_pipeline import run_single
    from build_config import get_connection

    try:
        conn = get_connection()
        api_key = os.getenv("ANTHROPIC_API_KEY")
        result = run_single(user_id, month, year, conn=conn, api_key=api_key)
        conn.close()

        month_name = datetime(year, month, 1).strftime("%B")
        drive_link = ""
        if result.get("drive_result") and result["drive_result"].get("web_link"):
            drive_link = f"\n📁 <{result['drive_result']['web_link']}|View in Google Drive>"

        msg = f"✅ *{month_name} {year} — {adviser_name}* report generated successfully! ({result['size_kb']:.0f} KB){drive_link}"

    except Exception as e:
        msg = f"❌ Failed to generate report for *{adviser_name}*: {str(e)}"

    # Post back to Slack
    if response_url:
        req_lib.post(response_url, json={"text": msg, "response_type": "in_channel"})


def run_all_reports_background(month, year, response_url):
    """Run all reports in background thread."""
    import requests as req_lib
    from run_pipeline import run_all

    try:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        results = run_all(month, year, api_key=api_key)
        successes = [r for r in results if r.get("success")]
        failures = [r for r in results if not r.get("success")]
        month_name = datetime(year, month, 1).strftime("%B")
        msg = (
            f"✅ *{month_name} {year}* — All reports complete!\n"
            f"• Generated: {len(successes)}/{len(results)}\n"
            f"• Failed: {len(failures)}"
            + (f"\n• Failed advisers: {', '.join(str(r['user_id']) for r in failures)}" if failures else "")
            + f"\n📁 Check Google Drive for all reports"
        )
    except Exception as e:
        msg = f"❌ Failed to run all reports: {str(e)}"

    if response_url:
        req_lib.post(response_url, json={"text": msg, "response_type": "in_channel"})


# ═══════════════════════════════════════════════════
#  Slack slash command handler: /report
# ═══════════════════════════════════════════════════

@app.route("/slack/report", methods=["POST"])
def slack_report():
    if not verify_slack_request(request):
        return jsonify({"error": "Invalid signature"}), 403

    text = request.form.get("text", "").strip().lower()
    response_url = request.form.get("response_url", "")
    tokens = text.split()

    if not tokens:
        return jsonify({
            "response_type": "ephemeral",
            "text": (
                "📊 *Report Bot Usage:*\n"
                "• `/report john_rojas` — last month's report for John Rojas\n"
                "• `/report john_rojas feb 2026` — specific month\n"
                "• `/report all` — all advisers (last month)\n"
                "• `/report list` — list all active advisers"
            )
        })

    command = tokens[0]

    # /report list
    if command == "list":
        from build_config import get_connection, query
        conn = get_connection()
        rows = query(conn, """
            SELECT DISTINCT u.first_name, u.last_name, u.id
            FROM auth_user u
            JOIN account_usergroup_users ugu ON ugu.user_id = u.id
            JOIN account_usergroup ug ON ug.id = ugu.usergroup_id
                AND ug.real = 1 AND ug.is_active = 1
            WHERE u.is_active = 1
              AND u.id NOT IN (88, 118, 172)
            ORDER BY u.last_name
        """)
        conn.close()
        names = [f"• {r['first_name']} {r['last_name']} (ID: {r['id']})" for r in rows]
        return jsonify({
            "response_type": "ephemeral",
            "text": f"👥 *Active Advisers ({len(rows)}):*\n" + "\n".join(names)
        })

    # /report all [month] [year]
    if command == "all":
        month, year = parse_month_year(tokens[1:])
        month_name = datetime(year, month, 1).strftime("%B")
        thread = threading.Thread(
            target=run_all_reports_background,
            args=(month, year, response_url)
        )
        thread.daemon = True
        thread.start()
        return jsonify({
            "response_type": "in_channel",
            "text": f"🚀 Generating *all adviser reports* for *{month_name} {year}*... I'll post here when done!"
        })

    # /report <adviser_name> [month] [year]
    name_slug = tokens[0]
    month, year = parse_month_year(tokens[1:])
    month_name = datetime(year, month, 1).strftime("%B")

    from build_config import get_connection
    conn = get_connection()
    matches = find_adviser(conn, name_slug)
    conn.close()

    if not matches:
        return jsonify({
            "response_type": "ephemeral",
            "text": f"❌ No adviser found matching *{name_slug}*. Try `/report list` to see all advisers."
        })

    if len(matches) > 1:
        names = "\n".join([f"• {r['first_name']} {r['last_name']} — `/report {r['first_name'].lower()}_{r['last_name'].lower()}`" for r in matches])
        return jsonify({
            "response_type": "ephemeral",
            "text": f"⚠️ Multiple matches for *{name_slug}*:\n{names}\nPlease be more specific."
        })

    adviser = matches[0]
    adviser_name = f"{adviser['first_name']} {adviser['last_name']}"
    user_id = adviser['id']

    thread = threading.Thread(
        target=run_report_background,
        args=(user_id, adviser_name, month, year, response_url)
    )
    thread.daemon = True
    thread.start()

    return jsonify({
        "response_type": "in_channel",
        "text": f"🚀 Generating *{month_name} {year}* report for *{adviser_name}*... I'll post here when done!"
    })


# ═══════════════════════════════════════════════════
#  Health check
# ═══════════════════════════════════════════════════

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "adviser-report-bot"})


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    print(f"🤖 Report bot listening on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
