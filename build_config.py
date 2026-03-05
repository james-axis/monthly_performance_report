"""
build_config.py
Queries the live database and generates a populated report_config.py
for any adviser + month/year combination.

Usage:
    python build_config.py --user_id 80 --month 2 --year 2026

Requires: mysql-connector-python, python-dotenv
"""

import argparse
import calendar
import json
import statistics
import os
from datetime import datetime, timedelta
from textwrap import dedent

import mysql.connector

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    pass


# ═══════════════════════════════════════════════════════════════════
#  DB CONNECTION
# ═══════════════════════════════════════════════════════════════════

def get_connection():
    """Connect to the reporting replica."""
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "prod-slife-crm-db-reporting.cjte8bbhwgp7.ap-southeast-2.rds.amazonaws.com"),
        user=os.getenv("DB_USER", ""),
        password=os.getenv("DB_PASSWORD", os.getenv("DB_PASS", "")),
        database=os.getenv("DB_NAME", "lifeinsurancepartners"),
        connect_timeout=30,
    )


def query(conn, sql, params=None):
    """Execute a query and return list of dicts."""
    cur = conn.cursor(dictionary=True)
    cur.execute(sql, params or ())
    rows = cur.fetchall()
    cur.close()
    return rows


# ═══════════════════════════════════════════════════════════════════
#  SECTION BUILDERS
# ═══════════════════════════════════════════════════════════════════

def build_identity(conn, user_id, month, year):
    """Section: Adviser name, practice name, report metadata."""
    row = query(conn, """
        SELECT u.first_name, u.last_name, ug.name AS practice_name
        FROM auth_user u
        JOIN account_usergroup_users ugu ON ugu.user_id = u.id
        JOIN account_usergroup ug ON ug.id = ugu.usergroup_id
        WHERE u.id = %s
        LIMIT 1
    """, (user_id,))[0]

    month_name = calendar.month_name[month]
    # Report date = last day of the month
    import calendar as cal
    last_day = cal.monthrange(year, month)[1]
    report_date = f"{last_day} {month_name} {year}"

    return {
        "ADVISER_NAME": f"{row['first_name']} {row['last_name']}",
        "PRACTICE_NAME": row["practice_name"],
        "REPORT_DATE": report_date,
        "REPORT_MONTH": month,
        "REPORT_YEAR": year,
        "REPORT_MONTH_NAME": month_name,
        "TOTAL_PAGES": 12,
        "HAS_PAGE6": True,
    }


def build_12month_performance(conn, user_id, month, year):
    """Sections 1 & 2: 12-month premium trend + KPI tiles."""
    # Calculate 12-month window ending at report month
    end_date = datetime(year, month, 1) + timedelta(days=32)
    end_date = end_date.replace(day=1)  # 1st of next month
    start_date = datetime(year - 1, month, 1) + timedelta(days=32)
    start_date = start_date.replace(day=1)  # 12 months back

    rows = query(conn, """
        SELECT YEAR(submitted) AS y, MONTH(submitted) AS m,
               COUNT(*) AS apps, ROUND(SUM(premium)) AS prem
        FROM applications_application
        WHERE adviser_id = %s
          AND submitted >= %s AND submitted < %s
        GROUP BY YEAR(submitted), MONTH(submitted)
        ORDER BY y, m
    """, (user_id, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")))

    months_data = [{"y": r["y"], "m": r["m"], "apps": r["apps"], "prem": int(r["prem"] or 0)} for r in rows]

    # Current month data
    current = next((m for m in months_data if m["y"] == year and m["m"] == month), None)
    if not current:
        current = {"y": year, "m": month, "apps": 0, "prem": 0}

    total_prem = current["prem"]
    total_apps = current["apps"]
    avg_prem = round(total_prem / total_apps) if total_apps > 0 else 0

    # Find historical best for comparison labels
    prior_months = [m for m in months_data if not (m["y"] == year and m["m"] == month)]
    best_prior_prem = max((m["prem"] for m in prior_months), default=0)
    best_prior_apps = max((m["apps"] for m in prior_months), default=0)

    # KPI labels
    prem_label = ""
    if total_prem > best_prior_prem and total_prem > 0:
        prem_label = "Personal best"
        if total_prem >= 100000:
            prem_label += " \u2013 $100K+ milestone"
    apps_label = "Highest volume month" if total_apps > best_prior_apps else ""
    avg_label = ""
    if total_apps > 0:
        prior_avgs = [m["prem"] / m["apps"] for m in prior_months if m["apps"] > 0]
        if prior_avgs and avg_prem > max(prior_avgs):
            avg_label = "Highest ever average"

    return {
        "MONTHS_DATA": months_data,
        "KPI_TOTAL_SUBMITTED": f"${total_prem:,}",
        "KPI_TOTAL_SUBMITTED_RAW": total_prem,
        "KPI_APPLICATIONS": total_apps,
        "KPI_AVG_PREMIUM": f"${avg_prem:,}",
        "KPI_AVG_PREMIUM_RAW": avg_prem,
        "KPI_TOTAL_SUB_LABEL": prem_label,
        "KPI_APPS_LABEL": apps_label,
        "KPI_AVG_LABEL": avg_label,
    }


def build_benchmarking(conn, user_id, month, year):
    """Section 3: Network benchmarking — 12-month total premium submitted across all practices."""
    # 12-month window ending at report month (same window as sections 1 & 2)
    end_dt = datetime(year, month, 1) + timedelta(days=32)
    end_dt = end_dt.replace(day=1)
    start_dt = datetime(year - 1, month, 1) + timedelta(days=32)
    start_dt = start_dt.replace(day=1)

    start_str = start_dt.strftime("%Y-%m-%d")
    end_str = end_dt.strftime("%Y-%m-%d")
    bench_period = f"{calendar.month_name[start_dt.month]} {start_dt.year} to {calendar.month_name[month]} {year}"

    # All active practices: 12-month total premium submitted
    all_practices = query(conn, """
        SELECT a.adviser_id AS user_id, ROUND(SUM(a.premium)) AS total_prem
        FROM applications_application a
        WHERE a.submitted >= %s AND a.submitted < %s
          AND a.adviser_id IN (
            SELECT DISTINCT ugu.user_id
            FROM account_usergroup_users ugu
            JOIN account_usergroup ug ON ug.id=ugu.usergroup_id AND ug.real=1 AND ug.is_active=1
            JOIN auth_user au ON au.id=ugu.user_id AND au.is_active=1
            WHERE ugu.user_id NOT IN (88, 118, 172)
          )
        GROUP BY a.adviser_id
        ORDER BY total_prem DESC
    """, (start_str, end_str))

    # Total active practices (including those with 0 submissions)
    total_row = query(conn, """
        SELECT COUNT(DISTINCT ugu.user_id) as total_practices
        FROM account_usergroup_users ugu
        JOIN account_usergroup ug ON ug.id=ugu.usergroup_id AND ug.real=1 AND ug.is_active=1
        JOIN auth_user au ON au.id=ugu.user_id AND au.is_active=1
        WHERE ugu.user_id NOT IN (88, 118, 172)
    """)[0]
    total_practices = total_row["total_practices"]

    premiums = []
    adviser_prem = 0
    for p in all_practices:
        prem = int(p["total_prem"] or 0)
        premiums.append(prem)
        if p["user_id"] == user_id:
            adviser_prem = prem

    # Add zero-premium practices
    zero_count = total_practices - len(premiums)
    premiums.extend([0] * max(zero_count, 0))
    premiums.sort(reverse=True)

    n = len(premiums)
    rank = sum(1 for p in premiums if p > adviser_prem) + 1
    percentile = round((1 - rank / n) * 100) if n > 0 else 0

    avg_prem = round(statistics.mean(premiums)) if premiums else 0
    med_prem = round(statistics.median(premiums)) if premiums else 0
    sorted_asc = sorted(premiums)
    top_q_prem = sorted_asc[int(n * 0.75)] if n > 0 else 0

    # Quartile thresholds for percentile bar labels ($)
    prem_q1 = sorted_asc[int(n * 0.25)] if n > 0 else 0
    prem_q2 = med_prem
    prem_q3 = top_q_prem

    # Histogram bins in $k ranges
    bin_edges_k = [(0, 50), (50, 100), (100, 150), (150, 200), (200, 250), (250, 300)]
    bin_labels = ["$0–50k", "$50–100k", "$100–150k", "$150–200k", "$200–250k", "$250–300k", "$300k+"]
    hist_data = {lbl: 0 for lbl in bin_labels}
    for p in premiums:
        p_k = p / 1000
        placed = False
        for (lo, hi), lbl in zip(bin_edges_k, bin_labels[:-1]):
            if lo <= p_k < hi:
                hist_data[lbl] += 1
                placed = True
                break
        if not placed:
            hist_data["$300k+"] += 1

    return {
        "ADVISER_PREMIUM_12M": adviser_prem,
        "ADVISER_RANK": rank,
        "TOTAL_PRACTICES": n,
        "PERCENTILE": percentile,
        "NETWORK_AVG_PREM": avg_prem,
        "MEDIAN_PREM": med_prem,
        "TOP_QUARTILE_PREM": top_q_prem,
        "PREM_Q1": prem_q1,
        "PREM_Q2": prem_q2,
        "PREM_Q3": prem_q3,
        "BENCH_PERIOD": bench_period,
        "HIST_DATA": hist_data,
    }


def build_referral_partners(conn, user_id, month, year):
    """Section 4: Referral partner performance (6-month window)."""
    end_dt = datetime(year, month, 1) + timedelta(days=32)
    end_dt = end_dt.replace(day=1)
    start_dt = datetime(year, month, 1)
    for _ in range(5):
        start_dt = (start_dt - timedelta(days=1)).replace(day=1)

    rows = query(conn, """
        SELECT
          ls.name as source_name,
          l.tags_cache as contact_tag,
          COUNT(DISTINCT l.id) as leads,
          COUNT(DISTINCT CASE WHEN a.id IS NOT NULL THEN l.id END) as apps,
          ROUND(SUM(CASE WHEN a.premium IS NOT NULL THEN a.premium ELSE 0 END)) as total_prem,
          ROUND(COUNT(DISTINCT CASE WHEN a.id IS NOT NULL THEN l.id END) /
            NULLIF(COUNT(DISTINCT l.id), 0) * 100) as conv
        FROM leads_lead l
        LEFT JOIN leads_leadsource ls ON ls.id = l.source_id
        LEFT JOIN applications_application a ON a.lead_id = l.id AND a.submitted IS NOT NULL
        WHERE l.user_id = %s
          AND l.created >= %s AND l.created < %s
        GROUP BY ls.name, l.tags_cache
        HAVING leads >= 2
        ORDER BY leads DESC
        LIMIT 25
    """, (user_id, start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d")))

    # First pass: count how often each potential group-prefix appears (to detect real groups)
    prefix_counts = {}
    for r in rows:
        tag = r["contact_tag"] or ""
        if " - " in tag:
            prefix = tag.split(" - ", 1)[0].strip()
            prefix_counts[prefix] = prefix_counts.get(prefix, 0) + 1

    partners = []   # individual rows for the breakdown table
    groups = {}     # group_name -> aggregated totals

    for r in rows:
        tag = r["contact_tag"] or ""
        source = r["source_name"] or "Other"
        leads = r["leads"]
        apps_count = int(r["apps"] or 0)
        prem = int(r["total_prem"] or 0)

        # Determine group and display name
        if " - " in tag:
            prefix = tag.split(" - ", 1)[0].strip()
            individual = tag.split(" - ", 1)[1].strip()
            # Only treat as a group if the prefix appears 2+ times
            if prefix_counts.get(prefix, 0) >= 2:
                group_name = prefix.title()
            else:
                # Treat whole tag as a standalone (e.g. "Referral from Sandra - Marlun Finance")
                group_name = tag.strip().title()
                individual = tag.strip()
        elif tag:
            group_name = tag.strip().title()
            individual = tag.strip()
        else:
            group_name = source.title()
            individual = source

        partners.append({
            "name": individual,
            "group": group_name,
            "leads": leads,
            "apps": apps_count,
            "prem": prem,
            "conv": int(r["conv"] or 0),
        })

        if group_name not in groups:
            groups[group_name] = {"name": group_name, "leads": 0, "apps": 0, "prem": 0}
        groups[group_name]["leads"] += leads
        groups[group_name]["apps"] += apps_count
        groups[group_name]["prem"] += prem

    # Build group list with calculated conversion
    group_list = []
    for g in groups.values():
        g["conv"] = round(g["apps"] / g["leads"] * 100) if g["leads"] > 0 else 0
        group_list.append(g)
    group_list.sort(key=lambda x: -x["leads"])
    partners.sort(key=lambda x: -x["leads"])

    return {"PARTNERS": partners, "PARTNER_GROUPS": group_list}


def build_insurers_and_submissions(conn, user_id, month, year):
    """Sections 5 & 6: Insurer diversification + full submissions table."""
    start_str = f"{year}-{month:02d}-01"
    end_dt = datetime(year, month, 1) + timedelta(days=32)
    end_str = end_dt.replace(day=1).strftime("%Y-%m-%d")

    apps_raw = query(conn, """
        SELECT
          a.customer_name, ROUND(a.premium) as premium, a.company_name as insurer,
          a.status, a.submitted, a.commenced,
          a.life, a.tpd, a.trauma, a.ip
        FROM applications_application a
        WHERE a.adviser_id = %s
          AND a.submitted >= %s AND a.submitted < %s
        ORDER BY a.premium DESC
    """, (user_id, start_str, end_str))

    # Status mapping: 0=In Progress, 4=Commenced, 5=Completed, 6=Cancelled
    status_map = {0: "In Progress", 4: "Commenced", 5: "Completed", 6: "Cancelled"}

    # Build insurer counts
    insurer_counts = {}
    apps_list = []
    for a in apps_raw:
        insurer = a["insurer"] or "Unknown"
        insurer_counts[insurer] = insurer_counts.get(insurer, 0) + 1

        # Product string
        products = []
        if a["life"]:
            products.append("Life")
        if a["tpd"]:
            products.append("TPD")
        if a["trauma"]:
            products.append("Trauma")
        if a["ip"]:
            products.append("IP")

        # Clean customer name (strip Mr/Mrs/Ms)
        name = (a["customer_name"] or "").strip()
        for prefix in ["Mr ", "Mrs ", "Ms ", "Miss ", "Dr "]:
            if name.startswith(prefix):
                name = name[len(prefix):]

        sub_date = a["submitted"]
        date_str = sub_date.strftime("%-d %b") if sub_date else ""

        status_code = a["status"] or 0
        status_text = status_map.get(status_code, f"Status {status_code}")

        prem_val = int(a["premium"]) if a["premium"] else "TBC"

        apps_list.append({
            "client": name,
            "prem": prem_val,
            "insurer": insurer,
            "status": status_text,
            "products": ", ".join(products),
            "date": date_str,
            "green": False,  # Could flag same-day submissions
        })

    # Sort insurers by count descending
    insurers = sorted(insurer_counts.items(), key=lambda x: -x[1])

    # Commenced vs In Progress tiles
    commenced_apps = [a for a in apps_list if a["status"] == "Commenced"]
    ip_apps = [a for a in apps_list if a["status"] == "In Progress"]
    commenced_prem = sum(a["prem"] for a in commenced_apps if isinstance(a["prem"], int))
    ip_prem = sum(a["prem"] for a in ip_apps if isinstance(a["prem"], int))

    return {
        "INSURERS": insurers,
        "APPS": apps_list,
        "SUBMISSIONS_FOOTNOTE": "",
        "_commenced_count": len(commenced_apps),
        "_commenced_prem": commenced_prem,
        "_ip_count": len(ip_apps),
        "_ip_prem": ip_prem,
    }


def build_speed_to_contact(conn, user_id, month, year):
    """Section 7: Call activity vs conversion rate (8-month window)."""
    end_dt = datetime(year, month, 1) + timedelta(days=32)
    end_dt = end_dt.replace(day=1)
    start_dt = datetime(year, month, 1)
    for _ in range(7):
        start_dt = (start_dt - timedelta(days=1)).replace(day=1)

    start_str = start_dt.strftime("%Y-%m-%d")
    end_str = end_dt.strftime("%Y-%m-%d")

    rows = query(conn, """
        SELECT
          CASE
            WHEN COALESCE(cc.consultant_calls, 0) = 0 THEN '0 calls'
            WHEN COALESCE(cc.consultant_calls, 0) = 1 THEN '1 call'
            WHEN COALESCE(cc.consultant_calls, 0) = 2 THEN '2 calls'
            ELSE '3+ calls'
          END as bucket,
          COUNT(DISTINCT l.id) as leads,
          COUNT(DISTINCT CASE WHEN l.status = 5 THEN l.id END) as converted,
          ROUND(AVG(CASE WHEN l.status = 5 THEN a.app_value END)) as avg_case
        FROM leads_lead l
        LEFT JOIN (
          SELECT la.object_id, COUNT(*) as consultant_calls
          FROM leads_leadaction la
          WHERE la.object_type = 'lead' AND la.action_type = 'call'
            AND la.deleted = 0
            AND la.user_id IN (
              SELECT user_id FROM account_userrole_users WHERE userrole_id = 2
            )
          GROUP BY la.object_id
        ) cc ON cc.object_id = l.id
        LEFT JOIN applications_application a ON a.lead_id = l.id
        WHERE l.user_id = %s
          AND l.created >= %s AND l.created < %s
        GROUP BY bucket
        ORDER BY FIELD(bucket, '0 calls', '1 call', '2 calls', '3+ calls')
    """, (user_id, start_str, end_str))

    buckets = ["0 calls", "1 call", "2 calls", "3+ calls"]
    conv_rates = []
    avg_values = []
    total_leads = 0
    bucket_lead_counts = []

    for b in buckets:
        row = next((r for r in rows if r["bucket"] == b), None)
        if row:
            leads = row["leads"]
            converted = row["converted"]
            rate = round(converted / leads * 100, 1) if leads > 0 else 0
            conv_rates.append(rate)
            avg_values.append(int(row["avg_case"] or 0))
            total_leads += leads
            bucket_lead_counts.append(leads)
        else:
            conv_rates.append(0)
            avg_values.append(0)
            bucket_lead_counts.append(0)

    # Detect face-to-face advisers: <5% of leads have any phone calls made by a consultant
    leads_with_calls = sum(bucket_lead_counts[1:])  # 1 call, 2 calls, 3+ calls
    is_face_to_face = (total_leads > 10 and leads_with_calls / total_leads < 0.05)

    # Quoted vs unquoted conversion
    quoted_row = query(conn, """
        SELECT
          ROUND(COUNT(DISTINCT CASE WHEN l.status = 5 AND lq.id IS NOT NULL THEN l.id END) /
                NULLIF(COUNT(DISTINCT CASE WHEN lq.id IS NOT NULL THEN l.id END), 0) * 100, 1) as quoted_conv,
          ROUND(COUNT(DISTINCT CASE WHEN l.status = 5 AND lq.id IS NULL THEN l.id END) /
                NULLIF(COUNT(DISTINCT CASE WHEN lq.id IS NULL THEN l.id END), 0) * 100, 1) as unquoted_conv
        FROM leads_lead l
        LEFT JOIN leads_leadquote lq ON lq.lead_id = l.id
        WHERE l.user_id = %s
          AND l.created >= %s AND l.created < %s
    """, (user_id, start_str, end_str))[0]

    return {
        "CALL_BUCKETS": buckets,
        "CONV_RATES": conv_rates,
        "AVG_CASE_VALUES": avg_values,
        "TOTAL_LEADS_STC": total_leads,
        "STC_PERIOD": "8 months",
        "QUOTED_CONV_RATE_STC": float(quoted_row["quoted_conv"] or 0),
        "UNQUOTED_CONV_RATE_STC": float(quoted_row["unquoted_conv"] or 0),
        "IS_FACE_TO_FACE": is_face_to_face,
    }


def build_completion_forecast(conn, user_id, month, year):
    """Section 8: Historical completion patterns and forecast."""
    # All-time completion data for this adviser
    all_apps = query(conn, """
        SELECT a.submitted, a.commenced, a.status
        FROM applications_application a
        WHERE a.adviser_id = %s AND a.submitted IS NOT NULL
    """, (user_id,))

    total_submitted = len(all_apps)
    total_completed = sum(1 for a in all_apps if a["commenced"] is not None)
    completion_rate = round(total_completed / total_submitted * 100) if total_submitted > 0 else 0

    # Calculate days-to-completion distribution
    week_buckets = {"Week 1": 0, "Week 2": 0, "Week 3": 0, "Week 4": 0, "Month 2": 0, "60+ days": 0}
    days_list = []
    for a in all_apps:
        if a["commenced"] and a["submitted"]:
            days = (a["commenced"] - a["submitted"]).days
            if days >= 0:  # exclude retroactive/data-entry anomalies
                days_list.append(days)
            if days <= 7:
                week_buckets["Week 1"] += 1
            elif days <= 14:
                week_buckets["Week 2"] += 1
            elif days <= 21:
                week_buckets["Week 3"] += 1
            elif days <= 28:
                week_buckets["Week 4"] += 1
            elif days <= 60:
                week_buckets["Month 2"] += 1
            else:
                week_buckets["60+ days"] += 1

    total_comp = sum(week_buckets.values())
    per_period = []
    cumulative = []
    running = 0
    for lbl in ["Week 1", "Week 2", "Week 3", "Week 4", "Month 2", "60+ days"]:
        pct = round(week_buckets[lbl] / total_comp * 100) if total_comp > 0 else 0
        per_period.append(pct)
        running += pct
        cumulative.append(min(running, 100))

    avg_days = round(statistics.mean(days_list)) if days_list else 0

    # Current month in-progress
    start_str = f"{year}-{month:02d}-01"
    end_dt = datetime(year, month, 1) + timedelta(days=32)
    end_str = end_dt.replace(day=1).strftime("%Y-%m-%d")

    ip_apps = query(conn, """
        SELECT COUNT(*) as cnt, ROUND(SUM(premium)) as prem
        FROM applications_application
        WHERE adviser_id = %s AND submitted >= %s AND submitted < %s
          AND commenced IS NULL AND status = 0
    """, (user_id, start_str, end_str))[0]

    comm_apps = query(conn, """
        SELECT ROUND(SUM(premium)) as prem
        FROM applications_application
        WHERE adviser_id = %s AND submitted >= %s AND submitted < %s
          AND commenced IS NOT NULL
    """, (user_id, start_str, end_str))[0]

    feb_ip = int(ip_apps["cnt"] or 0)
    feb_ip_prem = int(ip_apps["prem"] or 0)
    feb_comm_prem = int(comm_apps["prem"] or 0)
    expected_completions = round(feb_ip * completion_rate / 100)
    expected_prem = round(feb_ip_prem * completion_rate / 100 / 1000) * 1000

    return {
        "COMPLETION_BUCKETS": ["Week 1", "Week 2", "Week 3", "Week 4", "Month 2", "60+ days"],
        "PER_PERIOD_PCT": per_period,
        "CUMULATIVE_PCT": cumulative,
        "TOTAL_COMPLETED": total_comp,
        "TOTAL_SUBMITTED_HIST": total_submitted,
        "COMPLETION_RATE": completion_rate,
        "AVG_DAYS": avg_days,
        "FEB_IN_PROGRESS": feb_ip,
        "FEB_IP_PREMIUM": feb_ip_prem,
        "FEB_COMMENCED_PREM": feb_comm_prem,
        "EXPECTED_COMPLETIONS": expected_completions,
        "EXPECTED_PREM": expected_prem,
        "TOTAL_FORECAST": feb_comm_prem + expected_prem,
    }


def build_quoted_pipeline(conn, user_id):
    """Section 9: Currently quoted leads (status=3, no close reason)."""
    rows = query(conn, """
        SELECT
          CONCAT(l.first_name, ' ', l.last_name) as client,
          ROUND(COALESCE(lq.total_premium, 0)) as quoted,
          ls.name as source,
          CASE
            WHEN l.calls_made >= 3 THEN CONCAT(l.calls_made, ' calls made')
            WHEN l.calls_made = 1 THEN '1 call made'
            ELSE 'No calls yet'
          END as activity
        FROM leads_lead l
        LEFT JOIN (
          SELECT lead_id, SUM(premium) as total_premium
          FROM leads_leadquote
          GROUP BY lead_id
        ) lq ON lq.lead_id = l.id
        LEFT JOIN leads_leadsource ls ON ls.id = l.source_id
        WHERE l.user_id = %s AND l.status = 3 AND l.close_reason_id IS NULL
        ORDER BY lq.total_premium DESC
        LIMIT 9
    """, (user_id,))

    pipeline = []
    for r in rows:
        pipeline.append({
            "client": r["client"],
            "quoted": int(r["quoted"] or 0),
            "source": r["source"] or "Other",
            "status": r["activity"],
        })

    return {"PIPELINE": pipeline}


def build_conversion_drivers(conn, user_id, month, year):
    """Sections 10 & 11: What your data says works + pipeline segments."""
    # 12-month window
    end_dt = datetime(year, month, 1) + timedelta(days=32)
    end_dt = end_dt.replace(day=1)
    start_dt = datetime(year - 1, month, 1) + timedelta(days=32)
    start_dt = start_dt.replace(day=1)

    start_str = start_dt.strftime("%Y-%m-%d")
    end_str = end_dt.strftime("%Y-%m-%d")

    # Conversion by call count (12-month) — consultant-role calls only
    call_rows = query(conn, """
        SELECT
          CASE
            WHEN COALESCE(cc.consultant_calls, 0) = 0 THEN '0 calls'
            WHEN COALESCE(cc.consultant_calls, 0) = 1 THEN '1 call'
            WHEN COALESCE(cc.consultant_calls, 0) = 2 THEN '2 calls'
            ELSE '3+ calls'
          END as bucket,
          COUNT(DISTINCT l.id) as leads,
          COUNT(DISTINCT CASE WHEN l.status = 5 THEN l.id END) as converted,
          ROUND(AVG(CASE WHEN l.status = 5 THEN a.app_value END)) as avg_case
        FROM leads_lead l
        LEFT JOIN (
          SELECT la.object_id, COUNT(*) as consultant_calls
          FROM leads_leadaction la
          WHERE la.object_type = 'lead' AND la.action_type = 'call'
            AND la.deleted = 0
            AND la.user_id IN (
              SELECT user_id FROM account_userrole_users WHERE userrole_id = 2
            )
          GROUP BY la.object_id
        ) cc ON cc.object_id = l.id
        LEFT JOIN applications_application a ON a.lead_id = l.id
        WHERE l.user_id = %s AND l.created >= %s AND l.created < %s
        GROUP BY bucket
        ORDER BY FIELD(bucket, '0 calls', '1 call', '2 calls', '3+ calls')
    """, (user_id, start_str, end_str))

    total_leads_12m = sum(r["leads"] for r in call_rows)
    conv_by_calls = []
    avg_case_0 = 0
    avg_case_3 = 0
    table_data = []
    leads_0_calls = 0
    leads_3_plus = 0

    for r in call_rows:
        rate = round(r["converted"] / r["leads"] * 100, 1) if r["leads"] > 0 else 0
        conv_by_calls.append(rate)
        avg_c = int(r["avg_case"] or 0)

        # Current leads at this call level (for "Leads Currently Here" column)
        current = ""
        if r["bucket"] == "0 calls":
            avg_case_0 = avg_c
            leads_0_calls = r["leads"] - r["converted"]  # unconverted at this level
        elif r["bucket"] == "3+ calls":
            avg_case_3 = avg_c
            leads_3_plus = r["leads"] - r["converted"]

        table_data.append([r["bucket"], f"{rate}%", f"${avg_c:,}", current or "\u2014"])

    # Quoted vs unquoted (12-month)
    qv = query(conn, """
        SELECT
          ROUND(COUNT(DISTINCT CASE WHEN l.status = 5 AND lq.id IS NOT NULL THEN l.id END) /
                NULLIF(COUNT(DISTINCT CASE WHEN lq.id IS NOT NULL THEN l.id END), 0) * 100, 1) as q_conv,
          ROUND(COUNT(DISTINCT CASE WHEN l.status = 5 AND lq.id IS NULL THEN l.id END) /
                NULLIF(COUNT(DISTINCT CASE WHEN lq.id IS NULL THEN l.id END), 0) * 100, 1) as uq_conv
        FROM leads_lead l
        LEFT JOIN leads_leadquote lq ON lq.lead_id = l.id
        WHERE l.user_id = %s AND l.created >= %s AND l.created < %s
    """, (user_id, start_str, end_str))[0]

    quoted_conv = float(qv["q_conv"] or 0)
    unquoted_conv = float(qv["uq_conv"] or 0)

    call_mult = (f"{conv_by_calls[-1] / conv_by_calls[0]:.1f}x"
                 if conv_by_calls[0] > 0 and conv_by_calls[-1] > 0 else "N/A")
    quote_mult = f"{quoted_conv / unquoted_conv:.1f}x" if unquoted_conv > 0 else "N/A"

    # Current pipeline segments for section 11 — consultant-role calls only
    seg_0 = query(conn, """
        SELECT COUNT(*) as cnt FROM leads_lead l
        WHERE l.user_id = %s AND l.status NOT IN (5, 6, 7)
          AND l.close_reason_id IS NULL
          AND NOT EXISTS (
            SELECT 1 FROM leads_leadaction la
            WHERE la.object_id = l.id AND la.object_type = 'lead'
              AND la.action_type = 'call' AND la.deleted = 0
              AND la.user_id IN (
                SELECT user_id FROM account_userrole_users WHERE userrole_id = 2
              )
          )
    """, (user_id,))[0]["cnt"]

    seg_3plus = query(conn, """
        SELECT COUNT(*) as cnt FROM leads_lead l
        WHERE l.user_id = %s AND l.status NOT IN (5, 6, 7)
          AND l.close_reason_id IS NULL
          AND (
            SELECT COUNT(*) FROM leads_leadaction la
            WHERE la.object_id = l.id AND la.object_type = 'lead'
              AND la.action_type = 'call' AND la.deleted = 0
              AND la.user_id IN (
                SELECT user_id FROM account_userrole_users WHERE userrole_id = 2
              )
          ) >= 3
    """, (user_id,))[0]["cnt"]

    quoted_followed = query(conn, """
        SELECT COUNT(*) as cnt FROM leads_lead l
        WHERE l.user_id = %s AND l.status = 3 AND l.close_reason_id IS NULL
          AND EXISTS (
            SELECT 1 FROM leads_leadaction la
            WHERE la.object_id = l.id AND la.object_type = 'lead'
              AND la.action_type = 'call' AND la.deleted = 0
              AND la.user_id IN (
                SELECT user_id FROM account_userrole_users WHERE userrole_id = 2
              )
          )
    """, (user_id,))[0]["cnt"]

    # Quoted leads awaiting follow-up (status=3, stale > 5 days)
    stale_quoted = query(conn, """
        SELECT COUNT(*) as cnt FROM leads_lead l
        WHERE l.user_id = %s AND l.status = 3 AND l.close_reason_id IS NULL
          AND l.last_action_time < DATE_SUB(NOW(), INTERVAL 5 DAY)
    """, (user_id,))[0]["cnt"]

    # Estimated premium for stale quoted leads
    stale_prem_row = query(conn, """
        SELECT ROUND(SUM(lq.total_premium)) as est_prem
        FROM leads_lead l
        LEFT JOIN (
          SELECT lead_id, SUM(premium) as total_premium
          FROM leads_leadquote GROUP BY lead_id
        ) lq ON lq.lead_id = l.id
        WHERE l.user_id = %s AND l.status = 3 AND l.close_reason_id IS NULL
          AND l.last_action_time < DATE_SUB(NOW(), INTERVAL 5 DAY)
    """, (user_id,))[0]
    stale_est_prem = int(stale_prem_row["est_prem"] or 0)

    pipeline_segments = [
        (f"Leads with\n3+ calls", seg_3plus, f"{conv_by_calls[-1]}%",
         round(seg_3plus * conv_by_calls[-1] / 100) if conv_by_calls else 0),
        (f"Quoted leads\n(follow-up done)", quoted_followed, f"{quoted_conv}%",
         round(quoted_followed * quoted_conv / 100)),
        (f"Quoted leads\n(awaiting follow-up)", stale_quoted, f"{quoted_conv}%",
         round(stale_quoted * quoted_conv / 100)),
        (f"Leads with\n0 calls", seg_0, f"{conv_by_calls[0]}%" if conv_by_calls else "0%",
         round(seg_0 * conv_by_calls[0] / 100) if conv_by_calls else 0),
    ]

    return {
        "CONV_BY_CALLS_12M": conv_by_calls,
        "QUOTED_VS_UNQUOTED": [unquoted_conv, quoted_conv],
        "CALL_MULTIPLIER": call_mult,
        "QUOTE_MULTIPLIER": quote_mult,
        "TOTAL_LEADS_12M": total_leads_12m,
        "AVG_CASE_0_CALLS": avg_case_0,
        "AVG_CASE_3_PLUS": avg_case_3,
        "TABLE_DATA_10": table_data,
        "PIPELINE_SEGMENTS": pipeline_segments,
        "STALE_QUOTED_COUNT": stale_quoted,
        "STALE_EST_PREMIUM": stale_est_prem,
        "QUOTED_CONV": quoted_conv,
        "UNTOUCHED_LEADS": seg_0,
        "UNTOUCHED_CONV": f"{conv_by_calls[0]}%" if conv_by_calls else "0%",
        "STALE_QUOTES": stale_quoted,
        "STALE_QUOTES_CONV": f"{quoted_conv}%",
        "EST_PIPELINE_VALUE": f"${stale_est_prem:,}",
        "UNQUOTED_CONV": unquoted_conv,
    }


def build_summary(conn, user_id):
    """Section 12: CRM hygiene + closing summary."""
    # Stale appointments (scheduled > 7 days ago, not updated)
    stale_appts = query(conn, """
        SELECT COUNT(*) as cnt FROM leads_leadschedule ls
        JOIN leads_lead l ON l.id = ls.object_id AND ls.object_type = 'lead'
        WHERE l.user_id = %s
          AND ls.date < DATE_SUB(NOW(), INTERVAL 7 DAY)
          AND l.status NOT IN (5, 6, 7)
          AND l.close_reason_id IS NULL
    """, (user_id,))[0]["cnt"]

    return {
        "STALE_APPOINTMENTS": stale_appts,
    }


# ═══════════════════════════════════════════════════════════════════
#  MAIN: BUILD + WRITE CONFIG
# ═══════════════════════════════════════════════════════════════════

def build_all(user_id, month, year, conn=None, api_key=None):
    """Run all section queries and return combined config dict.

    Args:
        user_id: adviser user ID
        month: report month (1-12)
        year: report year
        conn: optional MySQL connection (will create one if None)
        api_key: optional Anthropic API key for narrative generation
    """
    own_conn = conn is None
    if own_conn:
        conn = get_connection()

    try:
        config = {}
        config.update(build_identity(conn, user_id, month, year))
        config.update(build_12month_performance(conn, user_id, month, year))
        config.update(build_benchmarking(conn, user_id, month, year))
        config.update(build_referral_partners(conn, user_id, month, year))

        insurer_data = build_insurers_and_submissions(conn, user_id, month, year)
        config["INSURERS"] = insurer_data["INSURERS"]
        config["APPS"] = insurer_data["APPS"]
        config["SUBMISSIONS_FOOTNOTE"] = insurer_data["SUBMISSIONS_FOOTNOTE"]

        config.update(build_speed_to_contact(conn, user_id, month, year))
        config.update(build_completion_forecast(conn, user_id, month, year))
        config.update(build_quoted_pipeline(conn, user_id))
        config.update(build_conversion_drivers(conn, user_id, month, year))
        config.update(build_summary(conn, user_id))

        has_page6 = len(config.get("APPS", [])) > 10
        config["HAS_PAGE6"] = has_page6
        config["TOTAL_PAGES"] = 12 if has_page6 else 11

        # Generate AI narratives (or leave as placeholders)
        from generate_narratives import enrich_config_with_narratives
        config = enrich_config_with_narratives(config, api_key=api_key)

        # Fallback: ensure all narrative keys exist even if API call failed
        narrative_defaults = {
            "EXEC_NARRATIVE": "", "EXEC_DRIVING": "",
            "STC_NARRATIVE": "", "WHAT_WORKS_INTRO": "",
            "WHAT_WORKS_NARRATIVE": "",
            "PREDICTOR_NARRATIVE_1": "", "PREDICTOR_NARRATIVE_2_TEMPLATE": "",
            "PREDICTOR_CLOSING": "", "CRM_NOTE": "", "FORMULA_TEXT": "",
            "HIGHLIGHTS": [], "SHOW_MILESTONE": False,
            "MILESTONE_TEXT": "", "MILESTONE_SUB": "",
        }
        for k, v in narrative_defaults.items():
            if k not in config or not config[k]:
                config[k] = v

        return config

    finally:
        if own_conn:
            conn.close()


def write_config(config, output_path="report_config.py"):
    """Write config dict as a valid Python module."""
    lines = [
        '"""',
        'report_config.py',
        
        
        'Auto-generated by build_config.py — DO NOT EDIT MANUALLY.',
        f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
        '"""',
        '',
        'from decimal import Decimal',
        '',
    ]

    # Group by section for readability
    sections = {
        "IDENTITY": ["ADVISER_NAME", "PRACTICE_NAME", "REPORT_DATE", "REPORT_MONTH",
                      "REPORT_YEAR", "REPORT_MONTH_NAME", "TOTAL_PAGES", "HAS_PAGE6"],
        "SECTION 1 & 2: 12-MONTH PERFORMANCE": [
            "MONTHS_DATA", "KPI_TOTAL_SUBMITTED", "KPI_TOTAL_SUBMITTED_RAW",
            "KPI_APPLICATIONS", "KPI_AVG_PREMIUM", "KPI_AVG_PREMIUM_RAW",
            "KPI_TOTAL_SUB_LABEL", "KPI_APPS_LABEL", "KPI_AVG_LABEL",
            "EXEC_NARRATIVE", "EXEC_DRIVING"],
        "SECTION 3: BENCHMARKING": [
            "ADVISER_PREMIUM_12M", "ADVISER_RANK", "TOTAL_PRACTICES",
            "PERCENTILE", "NETWORK_AVG_PREM", "MEDIAN_PREM", "TOP_QUARTILE_PREM",
            "PREM_Q1", "PREM_Q2", "PREM_Q3", "BENCH_PERIOD", "HIST_DATA"],
        "SECTION 4: REFERRAL PARTNERS": ["PARTNERS", "PARTNER_GROUPS"],
        "SECTION 5/6: INSURERS + SUBMISSIONS": [
            "INSURERS", "APPS", "SUBMISSIONS_FOOTNOTE"],
        "SECTION 7: SPEED-TO-CONTACT": [
            "CALL_BUCKETS", "CONV_RATES", "AVG_CASE_VALUES", "TOTAL_LEADS_STC",
            "STC_PERIOD", "QUOTED_CONV_RATE_STC", "UNQUOTED_CONV_RATE_STC",
            "STC_NARRATIVE", "IS_FACE_TO_FACE"],
        "SECTION 8: COMPLETION FORECAST": [
            "COMPLETION_BUCKETS", "PER_PERIOD_PCT", "CUMULATIVE_PCT",
            "TOTAL_COMPLETED", "TOTAL_SUBMITTED_HIST", "COMPLETION_RATE",
            "AVG_DAYS", "FEB_IN_PROGRESS", "FEB_IP_PREMIUM",
            "FEB_COMMENCED_PREM", "EXPECTED_COMPLETIONS", "EXPECTED_PREM",
            "TOTAL_FORECAST"],
        "SECTION 9: QUOTED PIPELINE": ["PIPELINE"],
        "SECTION 10: WHAT WORKS": [
            "CONV_BY_CALLS_12M", "QUOTED_VS_UNQUOTED", "CALL_MULTIPLIER",
            "QUOTE_MULTIPLIER", "TOTAL_LEADS_12M", "AVG_CASE_0_CALLS",
            "AVG_CASE_3_PLUS", "TABLE_DATA_10",
            "WHAT_WORKS_INTRO", "WHAT_WORKS_NARRATIVE"],
        "SECTION 11: STRONGEST PREDICTOR": [
            "PIPELINE_SEGMENTS", "STALE_QUOTED_COUNT", "STALE_EST_PREMIUM",
            "QUOTED_CONV", "UNQUOTED_CONV",
            "PREDICTOR_NARRATIVE_1", "PREDICTOR_NARRATIVE_2_TEMPLATE",
            "PREDICTOR_CLOSING"],
	"SECTION 12: SUMMARY + MILESTONE": [
            "STALE_APPOINTMENTS", "CRM_NOTE", "FORMULA_TEXT",
            "HIGHLIGHTS", "SHOW_MILESTONE", "MILESTONE_TEXT", "MILESTONE_SUB",
            "UNTOUCHED_LEADS", "UNTOUCHED_CONV", "STALE_QUOTES",
            "STALE_QUOTES_CONV", "EST_PIPELINE_VALUE"],
    }

    # Also add derived values that section files expect
    # (UNTOUCHED_LEADS, UNTOUCHED_CONV, etc. are derived from other fields)

    for section_name, keys in sections.items():
        lines.append(f"# {'═' * 47}")
        lines.append(f"#  {section_name}")
        lines.append(f"# {'═' * 47}")
        for k in keys:
            if k in config:
                lines.append(f"{k} = {repr(config[k])}")
        lines.append("")

    with open(output_path, "w") as f:
        f.write("\n".join(lines))

    print(f"\u2705 Config written to {output_path}")


# ═══════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build adviser report config from live DB")
    parser.add_argument("--user_id", type=int, required=True)
    parser.add_argument("--month", type=int, required=True)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--output", default="report_config.py")
    parser.add_argument("--api_key", default=None,
                        help="Anthropic API key (or set ANTHROPIC_API_KEY env var)")
    args = parser.parse_args()

    api_key = args.api_key or os.getenv("ANTHROPIC_API_KEY")
    config = build_all(args.user_id, args.month, args.year, api_key=api_key)
    write_config(config, args.output)
    print(f"  Adviser: {config['ADVISER_NAME']}")
    print(f"  Practice: {config['PRACTICE_NAME']}")
    print(f"  Period: {config['REPORT_MONTH_NAME']} {config['REPORT_YEAR']}")
    print(f"  Apps: {config['KPI_APPLICATIONS']}, Premium: {config['KPI_TOTAL_SUBMITTED']}")
