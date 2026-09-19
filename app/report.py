"""根因报告生成器"""
from typing import Dict
from app.models import RootCauseReport


def format_report_markdown(report: RootCauseReport) -> str:
    """将根因报告格式化为 Markdown 文本"""
    lines = [
        f"# 根因分析报告",
        f"",
        f"**生成时间**: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
        f"",
        f"## 根因节点",
        f"- **名称**: {report.root_node_name}",
        f"- **类型**: {report.root_node_type.value}",
        f"",
        f"## 诊断结论",
        f"{report.summary}",
        f"",
        f"## 影响范围",
        f"共影响 {len(report.impacted_resources)} 个资源:",
    ]
    for res in report.impacted_resources[:10]:
        lines.append(f"  - {res}")
    if len(report.impacted_resources) > 10:
        lines.append(f"  - ... 及其他 {len(report.impacted_resources) - 10} 个")

    lines.extend([
        f"",
        f"## 修复建议",
        f"{report.suggestion}",
        f"",
        f"## 相关告警",
    ])
    for alert in report.related_alerts[:5]:
        alertname = alert.get("labels", {}).get("alertname", "unknown")
        severity = alert.get("labels", {}).get("severity", "warning")
        lines.append(f"  - [{severity}] {alertname}")

    return "\n".join(lines)


def format_report_text(report: RootCauseReport) -> str:
    """将根因报告格式化为纯文本"""
    return (
        f"{'='*50}\n"
        f"  根因分析报告\n"
        f"{'='*50}\n"
        f"时间: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"根因: [{report.root_node_type.value}] {report.root_node_name}\n"
        f"\n"
        f"诊断: {report.summary}\n"
        f"影响: {len(report.impacted_resources)} 个资源\n"
        f"建议: {report.suggestion}\n"
        f"{'='*50}"
    )
