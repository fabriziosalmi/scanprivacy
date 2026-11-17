"""What the scanned site chooses must stay text in every report.

A localStorage key can be any string. Finding ids, parameters, evidence, hosts, URLs and the
domain of an unknown vendor are built from names like that, and a report is read, shared and
rendered by other people's tools. A key that closes a code span and opens a link, or starts a heading
or a fence, would let the site write into the document that judges it.

Each payload is put in every field a site controls, one at a time, and the Markdown, the PDF's HTML,
the SARIF help text and the diagram are checked for what the payload would do if it were structure.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import re
from pathlib import Path

import pytest

markdown_lib = pytest.importorskip("markdown")

from scanprivacy.core.graph import to_mermaid  # noqa: E402
from scanprivacy.i18n.escaping import Trusted, md_code, md_escape  # noqa: E402
from scanprivacy.report.markdown import render  # noqa: E402
from scanprivacy.report.pdf import render_html  # noqa: E402
from scanprivacy.report.sarif import build_sarif  # noqa: E402

_spec = importlib.util.spec_from_file_location("i18n_helpers", Path(__file__).with_name("test_i18n.py"))
_helpers = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_helpers)

PAYLOADS = {
    "link": "x`](https://evil.example/LINK)[y`",
    "html": '<b>HTMLMARK</b><img src="x" onerror="1"><script>SCRIPTMARK</script>',
    "lines": "x\n# HEADMARK\n```\nFENCEMARK\n- LISTMARK",
    "pipe": "a | b | c",
    "url": "see https://evil.example/AUTOLINK now",
    "emphasis": "**BOLDMARK** _ITALMARK_ ~~DELMARK~~ ![IMGMARK](https://evil.example/img)",
}


def _result():
    return _helpers._synthetic_result()


def _poison(result, payload: str, group: str):
    """The same result with `payload` in every field of one group that a site controls."""
    r = copy.deepcopy(result)
    if group == "finding_ids":
        for f in r.findings:
            if "|" in f.id or ":" in f.id:
                f.id = f"{f.id.split('|')[0]}|{payload}"
    elif group == "finding_params":
        for f in r.findings:
            for key, value in list(f.params.items()):
                if isinstance(value, str):
                    f.params[key] = payload
    elif group == "evidence":
        for f in r.findings:
            for key, value in list(f.evidence.items()):
                if isinstance(value, str):
                    f.evidence[key] = payload
                elif isinstance(value, list) and value and isinstance(value[0], str):
                    f.evidence[key] = [payload, payload]
    elif group == "inventory":
        for entry in r.inventory:
            entry["product"] = payload
            entry["vendor"] = payload
            entry["jurisdiction"] = payload
            entry["hosts"] = [payload]
    elif group == "urls":
        r.final_url = payload
        r.url = payload
        r.site["domain"] = payload
        r.observation["page_plan"] = [
            {"url": payload, "kind": "entry", "why": "x"},
            {"url": payload, "kind": "other", "why": "x"},
        ]
    elif group == "record":
        r.record["vantage"] = {"source": "looked_up", "endpoint": payload, "country": payload, "org": payload}
        r.record.setdefault("posture", {})["user_agent"] = payload
        r.record["rerun_params"] = {"url": payload}
    elif group == "graph":
        for node in r.graph.nodes:
            node.label = payload
    return r


GROUPS = ["finding_ids", "finding_params", "evidence", "inventory", "urls", "record", "graph"]
CASES = [(p, g) for p in PAYLOADS for g in GROUPS]
IDS = [f"{p}-{g}" for p, g in CASES]

LIVE_LINK = re.compile(r"<a\s[^>]*evil\.example", re.I)


def _to_html(md: str) -> str:
    """The way the site renders a report: Markdown inside <details> is parsed, as GitHub does."""
    return markdown_lib.markdown(
        md.replace("<details>", '<details markdown="1">'), extensions=["tables", "fenced_code", "md_in_html"]
    )


def _unescaped_pipes(line: str) -> int:
    line = re.sub(r"\\.", "", line)  # an escaped character is not structure
    return len(re.findall(r"\|", re.sub(r"(`+)[^`]*?\1", "", line)))


def _table_widths(md: str) -> set[tuple[int, ...]]:
    blocks, current = [], []
    for line in md.splitlines():
        if line.startswith("|"):
            current.append(_unescaped_pipes(line))
        elif current:
            blocks.append(tuple(sorted(set(current))))
            current = []
    if current:
        blocks.append(tuple(sorted(set(current))))
    return set(blocks)


@pytest.mark.parametrize("payload,group", CASES, ids=IDS)
def test_nothing_a_site_chooses_becomes_markdown_structure(payload, group):
    base = _result()
    marker = PAYLOADS[payload]
    md = render(_poison(base, marker, group), "en")
    baseline = render(base, "en")

    html = _to_html(md)
    assert not LIVE_LINK.search(html), "a link to an address the site chose"
    assert not re.search(r"<img\b[^>]*(evil\.example|onerror|src=\"x\")", html), "an image the site chose"
    assert "<script" not in html and "<b>HTMLMARK" not in html, "markup the site chose"

    for line in md.splitlines():
        assert not line.lstrip().startswith(("# HEADMARK", "- LISTMARK", "FENCEMARK")), f"a line the site started: {line!r}"
    fences = [line for line in md.splitlines() if line.startswith("```")]
    assert len(fences) == len([line for line in baseline.splitlines() if line.startswith("```")]), "a fence the site opened or closed"
    assert _table_widths(md) <= _table_widths(baseline) | _table_widths(md), "table shape"
    for block in _table_widths(md) - _table_widths(baseline):
        assert len(block) == 1, f"a table row with a different number of cells: {block}"


@pytest.mark.parametrize("payload,group", CASES, ids=IDS)
def test_nothing_a_site_chooses_becomes_markup_in_the_pdf(payload, group):
    html = render_html(_poison(_result(), PAYLOADS[payload], group), "en")
    assert "<b>HTMLMARK" not in html and "SCRIPTMARK</script>" not in html and "<script>SCRIPT" not in html
    assert not re.search(r"<img\b[^>]*(onerror|src=\"x\")", html)
    assert not LIVE_LINK.search(html)


@pytest.mark.parametrize("payload", list(PAYLOADS))
def test_the_sarif_help_text_keeps_site_chosen_names_as_text(payload):
    sarif = build_sarif(_poison(_result(), PAYLOADS[payload], "finding_params"), "en", None, "README.md")
    help_markdown = "\n".join(rule["help"]["markdown"] for rule in sarif["runs"][0]["tool"]["driver"]["rules"])
    html = _to_html(help_markdown)
    assert not LIVE_LINK.search(html) and "<b>HTMLMARK" not in html and "<script" not in html
    assert not any(line.lstrip().startswith(("# HEADMARK", "FENCEMARK")) for line in help_markdown.splitlines())
    json.dumps(sarif)


def test_a_diagram_label_cannot_leave_its_quotes_or_the_fence():
    result = _poison(_result(), PAYLOADS["lines"] + '"`', "graph")
    diagram = to_mermaid(result.graph)
    assert "```" not in diagram and "\n# HEADMARK" not in diagram
    assert all(line.startswith(("graph", "  ")) for line in diagram.splitlines())


# --------------------------------------------------------------------------- the helpers


def test_the_code_span_helper_survives_backticks_and_newlines():
    for value in ["a`b", "``", "`", "x\ny", "`a", "b`", "``` x", "a``b`c"]:
        span = md_code(value)
        html = markdown_lib.markdown(span)
        assert html.startswith("<p><code>") and html.rstrip().endswith("</code></p>"), (value, span, html)
        assert "\n" not in span


def test_the_escape_helper_leaves_plain_names_readable_and_trusted_text_alone():
    assert md_escape("utm_source") == "utm_source", "an underscore inside a word is not emphasis"
    assert md_escape("www.example.org") == "www.example.org"
    assert md_escape("_ga") == "\\_ga"
    assert md_escape(7) == 7
    catalogue = Trusted("**bold** `code`")
    assert md_escape(catalogue) == catalogue, "our own text keeps its Markdown"
    assert "\n" not in md_escape("a\nb") and md_escape("a\nb") == "a b"
    assert ":\\/\\/" in md_escape("https://evil.example"), "a bare URL is not turned into a link"


def test_the_json_keeps_what_was_observed_byte_for_byte():
    """Escaping is for rendering. The evidence is what the browser saw."""
    result = _poison(_result(), PAYLOADS["link"], "evidence")
    before = json.dumps(result.to_dict(), default=str, sort_keys=True)
    render(result, "en")
    render_html(result, "en")
    assert json.dumps(result.to_dict(), default=str, sort_keys=True) == before


@pytest.mark.parametrize("payload", list(PAYLOADS))
def test_the_fleet_summary_keeps_every_site_chosen_name_as_text(payload):
    """Domains, vendor names for unknown hosts and example sites come from the scanned targets."""
    from scanprivacy.analyze.fleet import FleetSummary, RulePrevalence, TargetSummary, VendorPrevalence
    from scanprivacy.report.fleet_markdown import render_fleet

    marker = PAYLOADS[payload]
    summary = FleetSummary(
        targets=1, scanned=1, grades={"F": 1},
        clean_sites=[marker],
        by_rule=[RulePrevalence("PM-COK-01", 1, 1, "high", examples=[marker, marker])],
        by_vendor=[VendorPrevalence("x", marker, 1, 1, "non_eea", examples=[marker])],
        targets_detail=[TargetSummary(marker, marker, "F", 1, 0, 1, 1, 1, "ok")],
    )
    md = render_fleet(summary, "en")
    html = _to_html(md)
    assert not LIVE_LINK.search(html) and "<b>HTMLMARK" not in html and "<script" not in html
    assert not any(line.lstrip().startswith(("# HEADMARK", "FENCEMARK", "- LISTMARK")) for line in md.splitlines())
    assert len(_table_widths(md)) <= len(_table_widths(render_fleet(FleetSummary(targets=1, scanned=1, grades={"F": 1}), "en"))) + 4
