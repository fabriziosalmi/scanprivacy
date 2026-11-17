# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [SemVer](https://semver.org/).

## [Unreleased]

## [0.1.4]

- Security: reports no longer let the scanned site write into them. Names a site chooses (cookie and storage key names, hosts, URLs, titles of documents, the domain of an unknown vendor) reach the Markdown report, the SARIF help text and the PDF through finding identifiers, parameters and evidence. A key such as ``_ga`  [text](https://example/)  ` `` closed a code span and put a clickable link in the Markdown report, and the PDF's "quick wins" sentence passed identifiers through as HTML. Such values are now escaped where they meet the report text (Markdown, SARIF help, fleet summary, diagram labels) and in the PDF, and links in the PDF are written only for `http` and `https` addresses. The JSON still holds what was observed, byte for byte. Checked with 42 payload and field combinations against the renderer GitHub uses: 38 of 84 renders let a payload act as structure before, none after. No file disclosure was possible: the PDF already refused any resource outside its templates.
- CI runs the suite on Python 3.13 as well, and the package declares it. A fleet PDF test looked for a placeholder in the compressed PDF bytes, where the same three bytes occur by chance in about 0.25% of runs; it now checks the HTML.

## [0.1.3]

- `scanprivacy scan --repeat N` (2 to 10) loads the page N times and reports how many loads showed each finding. The grade reported is that of the worst completed load; a load that did not finish is not counted as an absence; the other loads are kept in full and `scanprivacy verify` checks them. See "Repeating a scan" in the quickstart.

## [0.1.2]

- `scanprivacy install-browser` installs the Chromium build with the interpreter that runs scanprivacy, so an install with pipx or `uv tool` needs no second tool. The missing-browser message, the quickstart and the report's reproduction steps name it.
- The README and the quickstart start from `pipx install scanprivacy`; the PyPI page of 0.1.1 still shows the steps from a clone.

## [0.1.1]

First release published on PyPI.

- Reports: one design system for the PDF and the site, with bundled fonts. A page that never loaded is no longer summarised as one with no third parties and no cookies. How a document was found is shown in words in the English report, not as catalogue keys.
- Art. 13: the element detectors are measured on 21 labelled public notices (precision 0.93, recall 0.90; 0.98 and 0.89 on six held out while tuning), and six were widened to wordings the corpus showed they missed. Method and limits in `docs/art13-measurement.md`.
- Hosting platforms that cannot close a header finding: eleven measured, with sources, in `docs/platforms.md`.
- GitHub Action: run in CI against this project's own site, weekly and when it changes. The example workflow no longer says the action is unpublished.
- Site: content and referrer policy, preview image, sitemap, mobile layout, and a link to the shared privacy notice.
- Release: a version tag publishes to PyPI by trusted publisher, after checks on the tag and the built files.

## [0.1.0]

First public release. Passive observation engine with 27 passive rules and 4 refusal-pass rules, findings graph, verdict, EN/IT reports (Markdown, PDF), JSON evidence with verifiable digests, diff, SARIF, badge, signed attestation, HTTP API, GitHub Action. See "Known limits (v0.1)" in the README.
