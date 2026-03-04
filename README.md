# Monthly Performance Report Pipeline

Automated generation of personalised monthly performance reports for life insurance advisers.

## Architecture

```
run_pipeline.py (orchestrator)
  → build_config.py      (DB queries → data config per adviser)
    → generate_narratives.py  (Claude API → personalised commentary)
      → generate_report.py    (ReportLab → 12-page PDF)
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Single adviser report
python run_pipeline.py --user_id 80 --month 2 --year 2026

# All advisers (production)
python run_pipeline.py --all --month 2 --year 2026

# Auto-detect previous month (cron mode)
python run_pipeline.py --all
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DB_HOST` | Yes | MySQL reporting replica host |
| `DB_USER` | Yes | Database username |
| `DB_PASSWORD` | Yes | Database password |
| `DB_NAME` | Yes | Database name (`lifeinsurancepartners`) |
| `ANTHROPIC_API_KEY` | Yes | Claude API key for narrative generation |

## Report Sections

1. **Executive Summary** — KPI tiles + 12-month trend chart
2. **12-Month Performance Table** — monthly breakdown with premium and apps
3. **Licensee Benchmarking** — "New Lead to Completed" rate vs network (histogram + percentile)
4. **Referral Partner Performance** — volume/conversion by source
5. **Insurer Diversification** — donut chart + summary cards
6. **February Submissions** — full detail table of applications
7. **Speed-to-Contact** — conversion by call activity + quote status
8. **Completion Forecast** — historical completion timeline applied to current pipeline
9. **Quoted Pipeline** — remaining quoted leads detail table
10. **What Your Data Says Works** — conversion drivers analysis
11. **Strongest Predictor** — pipeline by engagement level with estimated premium
12. **Summary + Milestone** — highlights, CRM note, and milestone celebration

## Conversion Formula (Validated)

```
New Lead to Completed = leads with ≥1 application / (total leads − fake/dup/deleted)
```

Where fake/dup/deleted = `close_reason_id IN (70, 80, 98)`.

## Deployment (Railway)

Configured for Railway cron deployment. See `railway.toml` for schedule (1st of each month, 6AM AEST).

## Project Structure

```
├── run_pipeline.py          # Production orchestrator (CLI + cron entry point)
├── build_config.py          # DB query layer → generates report_config.py
├── generate_narratives.py   # Claude API → personalised narrative text
├── generate_report.py       # PDF assembly (merges section PDFs)
├── chart_builder.py         # Matplotlib chart generation
├── template.html            # HTML report template (alternative renderer)
├── test_section[1-12].py    # Individual section PDF renderers (ReportLab)
├── requirements.txt
├── Dockerfile
├── railway.toml
└── .gitignore
```
