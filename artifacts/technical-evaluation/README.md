# Technical Evaluation Artifacts

This directory contains the artifacts used in the technical evaluation
of the nine cases CP01–CP09.

Each case directory contains:

- `lighthouse_raw.json`: original response returned by the PageSpeed
  Insights API;
- `wave_raw.json`: original response returned by the WAVE API;
- `*_meta_auditor_consolidado.json`: structured result produced after
  normalization, consolidation, severity classification, risk-score
  calculation and correction prioritization;
- `*.html`: HTML report generated from the audit data;
- `*.pdf`: PDF version rendered from the HTML report.

The data correspond to the collection performed on 2026-05-30.
Public URLs are retained because they define the technical cases
reported in the article.
