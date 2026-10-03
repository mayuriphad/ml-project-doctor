"""Render a :class:`~ml_project_doctor.models.Report` as JSON, HTML or plain text."""

from __future__ import annotations

import html
import json

from .models import CATEGORIES, Finding, Report

_CSS = """
:root {
  --bg: #f7f7f5; --fg: #1d1d1b; --muted: #6b6b66; --card: #ffffff; --line: #e2e2dd;
  --good: #1f7a4d; --warn: #b26a00; --bad: #b3261e;
  --info-bg: #e8f0fb; --warn-bg: #fdf1dc; --bad-bg: #fbe3e1;
}
:root[data-theme="dark"] {
  --bg: #161614; --fg: #ececE6; --muted: #9a9a93; --card: #20201e; --line: #34342f;
  --good: #5fd39a; --warn: #f0b15a; --bad: #ff8a80;
  --info-bg: #1d2a3d; --warn-bg: #3a2c14; --bad-bg: #3d1f1d;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #161614; --fg: #ececE6; --muted: #9a9a93; --card: #20201e; --line: #34342f;
    --good: #5fd39a; --warn: #f0b15a; --bad: #ff8a80;
    --info-bg: #1d2a3d; --warn-bg: #3a2c14; --bad-bg: #3d1f1d;
  }
}
body { background: var(--bg); color: var(--fg); margin: 0; padding: 16px;
  font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width: 960px; margin: 0 auto; }
h1 { font-size: 1.6rem; margin: 0 0 4px; }
h2 { font-size: 1.15rem; margin: 32px 0 12px; border-bottom: 1px solid var(--line); padding-bottom: 6px; }
.muted { color: var(--muted); font-size: 0.9rem; word-break: break-all; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-top: 16px; }
.card { background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 12px 14px; }
.label { color: var(--muted); font-size: 0.8rem; text-transform: capitalize; }
.value { font-size: 1.6rem; font-weight: 600; }
.good { color: var(--good); } .warn { color: var(--warn); } .bad { color: var(--bad); }
table { width: 100%; border-collapse: collapse; background: var(--card); border-radius: 10px; overflow: hidden; }
th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--line); font-size: 0.9rem; vertical-align: top; }
th { color: var(--muted); font-weight: 500; }
.status-passed { color: var(--good); } .status-failed { color: var(--warn); } .status-error { color: var(--bad); }
ul.findings { list-style: none; padding: 0; margin: 0; }
ul.findings li { background: var(--card); border: 1px solid var(--line); border-left-width: 4px;
  border-radius: 8px; padding: 10px 12px; margin-bottom: 10px; }
li.sev-error { border-left-color: var(--bad); } li.sev-warning { border-left-color: var(--warn); }
li.sev-info { border-left-color: #4a7bd0; }
.badge { display: inline-block; font-size: 0.72rem; text-transform: uppercase; letter-spacing: .04em;
  padding: 1px 7px; border-radius: 999px; margin-right: 6px; }
li.sev-error .badge { background: var(--bad-bg); color: var(--bad); }
li.sev-warning .badge { background: var(--warn-bg); color: var(--warn); }
li.sev-info .badge { background: var(--info-bg); color: #4a7bd0; }
li p { margin: 6px 0 0; } li .rec { color: var(--muted); font-size: 0.9rem; }
code { font-family: ui-monospace, Consolas, monospace; font-size: 0.85em; }
.empty { color: var(--muted); font-style: italic; }
@media (max-width: 600px) { th:nth-child(2), td:nth-child(2) { display: none; } }
"""


def to_json(report: Report) -> str:
    return json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n"


def to_text(report: Report) -> str:
    counts = report.severity_counts()
    lines = [
        f"ML Project Doctor {report.tool_version}",
        f"Project: {report.project_path}",
        f"Score:   {report.score}/100",
        "",
        "Categories:",
    ]
    lines += [f"  {name:<16} {score:>3}/100" for name, score in report.category_scores.items()]
    lines += [
        "",
        f"Findings: {counts['error']} error, {counts['warning']} warning, {counts['info']} info",
    ]
    if not report.findings:
        lines.append("  No issues found.")
    for finding in _sorted(report.findings):
        location = f" [{finding.path}]" if finding.path else ""
        lines.append(f"  {finding.severity.value.upper():<8} {finding.check_id}{location}: {finding.message}")
        if finding.recommendation:
            lines.append(f"           -> {finding.recommendation}")
    return "\n".join(lines) + "\n"


def to_html(report: Report) -> str:
    e = html.escape
    counts = report.severity_counts()
    cards = "".join(
        f'<div class="card"><div class="label">{e(name.replace("_", " "))}</div>'
        f'<div class="value {_band(score)}">{score}</div></div>'
        for name, score in report.category_scores.items()
    )
    check_rows = "".join(
        f"<tr><td><code>{e(c.check_id)}</code></td><td>{e(c.category)}</td><td>{e(c.title)}</td>"
        f'<td class="status-{e(c.status)}">{e(c.status)}</td><td>{c.finding_count}</td></tr>'
        for c in report.checks
    )
    sections = []
    for category in CATEGORIES:
        if category not in report.category_scores:
            continue
        items = [f for f in _sorted(report.findings) if f.category == category]
        body = (
            f'<ul class="findings">{"".join(_finding_html(f) for f in items)}</ul>'
            if items
            else '<p class="empty">No issues.</p>'
        )
        sections.append(f"<h2>{e(category.capitalize())}</h2>{body}")

    return (
        "<!doctype html>\n"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>ML Project Doctor report: {e(report.project_path)}</title>"
        f"<style>{_CSS}</style></head><body><main>"
        "<h1>ML Project Doctor report</h1>"
        f'<div class="muted">{e(report.project_path)}<br>'
        f"Generated {e(report.generated_at.strftime('%Y-%m-%d %H:%M UTC'))} "
        f"by ml-project-doctor {e(report.tool_version)}</div>"
        '<div class="grid">'
        f'<div class="card"><div class="label">overall score</div>'
        f'<div class="value {_band(report.score)}">{report.score}</div></div>'
        f'<div class="card"><div class="label">errors</div><div class="value bad">{counts["error"]}</div></div>'
        f'<div class="card"><div class="label">warnings</div><div class="value warn">{counts["warning"]}</div></div>'
        f'<div class="card"><div class="label">info</div><div class="value">{counts["info"]}</div></div>'
        "</div>"
        f'<h2>Category scores</h2><div class="grid">{cards}</div>'
        "<h2>Checks</h2>"
        "<table><thead><tr><th>ID</th><th>Category</th><th>Check</th><th>Status</th><th>Findings</th>"
        f"</tr></thead><tbody>{check_rows}</tbody></table>"
        "<h2>Findings</h2>" + "".join(sections) + "</main></body></html>\n"
    )


def _sorted(findings: list[Finding]) -> list[Finding]:
    return sorted(findings, key=lambda f: (-f.severity.rank, f.category, f.check_id, f.path or ""))


def _band(score: int) -> str:
    if score >= 80:
        return "good"
    if score >= 50:
        return "warn"
    return "bad"


def _finding_html(finding: Finding) -> str:
    e = html.escape
    location = f" <code>{e(finding.path)}</code>" if finding.path else ""
    recommendation = f'<p class="rec">{e(finding.recommendation)}</p>' if finding.recommendation else ""
    return (
        f'<li class="sev-{finding.severity.value}">'
        f'<span class="badge">{finding.severity.value}</span>'
        f"<strong>{e(finding.check_id)}</strong> {e(finding.title)}{location}"
        f"<p>{e(finding.message)}</p>{recommendation}</li>"
    )
