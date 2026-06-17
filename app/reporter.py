from collections import Counter
from operator import itemgetter
 
from .schemas import RequestResult
 
 
def generate_report(results: list[RequestResult]) -> str:
    total = len(results)
    errors = [r for r in results if r.llm_error]
    needs_clarification = [r for r in results if r.needs_clarification]
 
    category_counts = Counter(r.category.value for r in results)
    priority_counts = Counter(r.priority.value for r in results)
    department_counts = Counter(
        r.target_department for r in results if r.target_department
    )
 
    lines = [
        "# AI Request Classifier — Report",
        "",
        f"**Total requests processed:** {total}",
        f"**Successfully classified:** {total - len(errors)}",
        f"**Classification errors (fallback used):** {len(errors)}",
        f"**Needs clarification:** {len(needs_clarification)}",
        "",
        "---",
        "",
        "## By Category",
        "",
        "| Category | Count |",
        "|---|---|",
    ]
    for cat, count in sorted(category_counts.items(), key=itemgetter(1), reverse=True):
        lines.append(f"| {cat} | {count} |")
 
    lines += [
        "",
        "## By Priority",
        "",
        "| Priority | Count |",
        "|---|---|",
    ]
    for pri in ["high", "medium", "low"]:
        lines.append(f"| {pri} | {priority_counts.get(pri, 0)} |")
 
    lines += [
        "",
        "## By Department",
        "",
        "| Department | Count |",
        "|---|---|",
    ]
    if department_counts:
        for dept, count in sorted(department_counts.items(), key=itemgetter(1), reverse=True):
            lines.append(f"| {dept} | {count} |")
    else:
        lines.append("| — | No department data available |")
 
    lines += [
        "",
        "## Requests Needing Clarification",
        "",
    ]
    if needs_clarification:
        lines += [
            "| ID | Channel | Summary |",
            "|---|---|---|",
        ]
        for r in needs_clarification:
            lines.append(f"| {r.id} | {r.channel} | {r.short_summary} |")
    else:
        lines.append("_No requests need clarification._")
 
    if errors:
        lines += [
            "",
            "## Classification Errors",
            "",
            "| ID | Error |",
            "|---|---|",
        ]
        for r in errors:
            lines.append(f"| {r.id} | {r.llm_error} |")
 
    return "\n".join(lines)