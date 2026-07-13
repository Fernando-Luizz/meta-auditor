# Technical Evaluation Artifacts

This directory contains the artifacts produced during the technical
evaluation of the Meta-Auditor. The evaluation includes nine cases,
identified as CP01–CP09.

## Artifact processing sequence

For each evaluated case, the Meta-Auditor receives two independent
inputs:

1. the raw JSON response returned by the Lighthouse audit through the
   PageSpeed Insights API;
2. the raw JSON response returned by the WAVE API.

These raw files are preserved before any transformation to maintain
traceability to the original outputs of both tools.

From these inputs, the Meta-Auditor executes its deterministic
processing pipeline:

- normalization of tool-specific identifiers;
- consolidation of equivalent findings;
- classification of finding origin;
- identification of convergences and divergences;
- assignment of severity;
- calculation of the aggregated Risk Score;
- assignment of correction priorities P1, P2, or P3.

The result of this processing is a consolidated JSON file containing
the structured audit data produced by the Meta-Auditor.

The consolidated result is also stored as part of the audit record in
SQLite and is used to generate the HTML report. The PDF report is then
produced by rendering the corresponding HTML report.

Therefore, the artifact sequence for each case is:

```text
Raw Lighthouse JSON
        +
Raw WAVE JSON
        ↓
Meta-Auditor normalization, consolidation, severity classification,
Risk Score calculation, and correction prioritization
        ↓
Consolidated Meta-Auditor JSON
        ↓
HTML report
        ↓
PDF report
```

## Files available for each case

Each CP01–CP09 directory contains:

- the raw Lighthouse JSON response;
- the raw WAVE JSON response;
- the consolidated Meta-Auditor JSON;
- the generated HTML report;
- the generated PDF report.

This organization enables the results presented in the article to be
traced from the original API responses to the final reports generated
by the Meta-Auditor.

## Additional artifacts

The normalization specification is available in the
`../normalization/` directory. It documents the 80 deterministic
mappings implemented by the Meta-Auditor:

- 42 Lighthouse mappings;
- 38 WAVE mappings;
- 71 distinct normalized barrier types.

The acceptance-evaluation materials are available separately in the
`../acceptance-evaluation/` directory. These materials contain the
pseudonymized reports evaluated by participants AP01–AP05.

The pseudonymized mapping of selected open-ended TAM responses is
available in the `../TAM mapping/` directory.
