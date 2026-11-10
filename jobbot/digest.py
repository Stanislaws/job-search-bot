"""Render the daily digest as an email-safe HTML page (inline styles only) plus a plain-text fallback."""
from __future__ import annotations

import html
from datetime import datetime, timezone

from .models import Job

COLORS = {"green": "#16a34a", "yellow": "#d97706", "red": "#dc2626"}
LIGHTS = {"green": "🟢", "yellow": "🟡", "red": "🔴"}
LABELS = {"green": "Looks legit", "yellow": "Check before applying", "red": "Likely scam"}
E = html.escape


def _ago(dt: datetime | None, now: datetime) -> str:
    if not dt:
        return "date unknown"
    d = (now - dt).days
    return "today" if d <= 0 else "yesterday" if d == 1 else f"{d} days ago"


def _bar(score: int, color: str) -> str:
    return (
        '<table cellpadding="0" cellspacing="0" style="display:inline-table;vertical-align:middle;width:90px;'
        'height:8px;background:#e5e7eb;border-radius:4px"><tr>'
        f'<td style="width:{max(score, 3)}%;background:{color};border-radius:4px;height:8px"></td>'
        f'<td style="width:{100 - max(score, 3)}%"></td></tr></table>'
    )


def _card(j: Job, now: datetime) -> str:
    c = COLORS[j.verdict]
    loc = "; ".join(j.locations[:3]) + (f" +{len(j.locations) - 3} more" if len(j.locations) > 3 else "")
    meta = " · ".join(
        filter(None, [E(loc or "Location not listed"), E(j.pay_label()), f"posted {_ago(j.posted_at, now)}", f"via {E(j.source)}"])
    )
    why = ", ".join(E(r) for r in j.fit_reasons[:6])
    legit = "; ".join(E(r) for r in j.legit_reasons[:3]) or "no red flags found"
    auth = ""
    if j.auth_status == "caution":
        auth = f'<div style="margin-top:6px;color:#92400e;font-size:13px">⚠️ {E(j.auth_note)}</div>'
    elif j.auth_status == "positive":
        auth = f'<div style="margin-top:6px;color:#166534;font-size:13px">✅ Work authorization: {E(j.auth_note)}</div>'
    also = f' <span style="color:#6b7280">(also on {E(", ".join(j.also_on))})</span>' if j.also_on else ""
    return f"""
<table width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 14px;border:1px solid #e5e7eb;border-left:5px solid {c};border-radius:8px;background:#ffffff">
<tr><td style="padding:14px 16px;font-family:Arial,Helvetica,sans-serif;color:#111827">
  <div style="font-size:16px;font-weight:bold;line-height:1.3"><a href="{E(j.url)}" style="color:#1d4ed8;text-decoration:none">{E(j.title)}</a></div>
  <div style="font-size:14px;margin-top:2px"><b>{E(j.company or "Unknown company")}</b>{also}</div>
  <div style="font-size:13px;color:#4b5563;margin-top:4px">{meta}</div>
  <table cellpadding="0" cellspacing="0" style="margin-top:10px;font-size:13px;font-family:Arial,Helvetica,sans-serif">
    <tr><td style="color:#6b7280;padding:2px 8px 2px 0;white-space:nowrap">Fit <b style="color:#111827">{j.fit_score}</b></td>
        <td style="padding:2px 18px 2px 0">{_bar(j.fit_score, "#2563eb")}</td>
        <td style="color:#6b7280;padding:2px 8px 2px 0;white-space:nowrap">Legit <b style="color:#111827">{j.legit_score}</b></td>
        <td style="padding:2px 8px 2px 0">{_bar(j.legit_score, c)}</td>
        <td style="white-space:nowrap">{LIGHTS[j.verdict]} <b style="color:{c}">{LABELS[j.verdict]}</b></td></tr>
  </table>
  <div style="font-size:13px;color:#4b5563;margin-top:6px"><b>Why it fits:</b> {why}</div>
  <div style="font-size:13px;color:#4b5563;margin-top:3px"><b>Legitimacy:</b> {legit}</div>
  {auth}
</td></tr></table>"""


def _flagged_row(j: Job) -> str:
    reasons = "; ".join(E(r) for r in j.legit_reasons if not r.startswith(("listed on", "applies through", "direct apply", "link matches")))
    return (
        f'<li style="margin-bottom:8px"><b>{E(j.title)}</b> — {E(j.company or "?")} '
        f'<span style="color:#6b7280">({E(j.source)}, score {j.legit_score})</span><br>'
        f'<span style="color:#b91c1c">{reasons}</span></li>'
    )


def _section(title: str, subtitle: str, jobs: list[Job], now: datetime) -> str:
    if not jobs:
        return ""
    cards = "".join(_card(j, now) for j in jobs)
    return (
        f'<h2 style="font-family:Arial,Helvetica,sans-serif;font-size:18px;margin:26px 0 4px;color:#111827">{title} '
        f'<span style="color:#6b7280;font-weight:normal">({len(jobs)})</span></h2>'
        f'<div style="font-family:Arial,Helvetica,sans-serif;font-size:13px;color:#6b7280;margin-bottom:12px">{subtitle}</div>{cards}'
    )


def render(sections: dict[str, list[Job]], stats: dict, now: datetime | None = None, repo_url: str = "") -> tuple[str, str]:
    now = now or datetime.now(timezone.utc)
    interns, entry, flagged = sections["internships"], sections["entry"], sections["flagged"]
    total = len(interns) + len(entry)
    date_str = stats.get("local_date", now.strftime("%A, %B %d"))

    src_rows = "".join(
        f'<tr><td style="padding:2px 10px 2px 0">{E(name)}</td><td style="color:{"#16a34a" if s["ok"] else "#6b7280"}">{E(s["note"])}</td></tr>'
        for name, s in stats["sources"].items()
    )
    funnel = (
        f'{stats["scanned"]:,} postings scanned → {stats["matched"]:,} matched your filters → '
        f'{stats["new"]:,} new since last email'
    )
    empty = (
        '<p style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#374151">No new matching jobs today. '
        "The bot ran fine — it'll check again tomorrow.</p>"
        if total == 0
        else ""
    )
    flagged_html = ""
    if flagged:
        flagged_html = (
            '<h2 style="font-family:Arial,Helvetica,sans-serif;font-size:18px;margin:26px 0 4px;color:#991b1b">🚩 Flagged as likely scams</h2>'
            '<div style="font-family:Arial,Helvetica,sans-serif;font-size:13px;color:#6b7280;margin-bottom:8px">'
            "Not links on purpose. Shown so you learn to recognise the patterns.</div>"
            f'<ul style="font-family:Arial,Helvetica,sans-serif;font-size:13px;padding-left:18px">{"".join(_flagged_row(j) for j in flagged)}</ul>'
        )
    tune = (
        f'<a href="{E(repo_url)}/edit/main/config.yaml" style="color:#1d4ed8">edit config.yaml</a>' if repo_url else "edit config.yaml"
    )
    page = f"""<!DOCTYPE html><html><body style="margin:0;background:#f3f4f6">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6"><tr><td align="center" style="padding:20px 10px">
<table width="680" cellpadding="0" cellspacing="0" style="max-width:680px;width:100%"><tr><td>
  <div style="background:#0f172a;border-radius:10px;padding:20px 22px;font-family:Arial,Helvetica,sans-serif;color:#f8fafc">
    <div style="font-size:13px;color:#94a3b8;letter-spacing:.5px">DAILY JOB DIGEST · {E(date_str)}</div>
    <div style="font-size:24px;font-weight:bold;margin-top:4px">{total} new data analyst job{"s" if total != 1 else ""}</div>
    <div style="font-size:14px;color:#cbd5e1;margin-top:6px">🎓 {len(interns)} internships · 💼 {len(entry)} entry-level/other · 🚩 {len(flagged)} flagged</div>
    <div style="font-size:12px;color:#94a3b8;margin-top:8px">{funnel}</div>
  </div>
  {empty}
  {_section("🎓 Internships", "Sorted by fit. Postings that need a closer look come after the clean ones.", interns, now)}
  {_section("💼 Entry-level & other analyst roles", "Full-time roles open to new grads or with no seniority requirement.", entry, now)}
  {flagged_html}
  <div style="font-family:Arial,Helvetica,sans-serif;font-size:12px;color:#6b7280;margin-top:28px;border-top:1px solid #e5e7eb;padding-top:12px">
    <b>Legend.</b> Fit = how well it matches what you're looking for. Legit = how real it looks.
    🟢 looks legit · 🟡 check before applying · 🔴 likely scam. ⚠️ = says no sponsorship (CPT may still work).<br><br>
    <b>Sources today</b><table style="font-size:12px;color:#374151;margin-top:4px">{src_rows}</table><br>
    Always apply on the company's own site, never pay for anything, and never send your SSN or bank details before a signed offer.
    To tune the bot, {tune}.
  </div>
</td></tr></table></td></tr></table></body></html>"""

    lines = [f"{total} new data analyst jobs — {date_str}", funnel, ""]
    for name, jobs in (("INTERNSHIPS", interns), ("ENTRY-LEVEL & OTHER", entry)):
        if jobs:
            lines.append(f"== {name} ==")
            for j in jobs:
                lines.append(f"[{j.verdict.upper()} {j.legit_score} | fit {j.fit_score}] {j.title} — {j.company}")
                lines.append(f"   {'; '.join(j.locations[:2])} · {j.pay_label()} · {j.url}")
                if j.auth_status == "caution":
                    lines.append(f"   ! {j.auth_note}")
            lines.append("")
    if flagged:
        lines.append("== FLAGGED AS LIKELY SCAMS ==")
        lines += [f"- {j.title} — {j.company}: {'; '.join(j.legit_reasons[:3])}" for j in flagged]
    return page, "\n".join(lines)
