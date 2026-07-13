# Supplementary Artifacts

This directory contains the supplementary artifacts associated with
the Meta-Auditor evaluation.

## Normalization

The `normalization/` directory contains the specification of the
80 deterministic mappings used by the Meta-Auditor:

- 42 Lighthouse mappings;
- 38 WAVE mappings;
- 71 distinct normalized barrier types.

## Technical evaluation

The `technical-evaluation/` directory contains the artifacts for the
nine evaluated cases, identified as CP01–CP09.

Each case contains:

1. the raw Lighthouse JSON;
2. the raw WAVE JSON;
3. the consolidated JSON produced by the Meta-Auditor;
4. the HTML report;
5. the PDF report.

The processing sequence is:

Lighthouse raw JSON + WAVE raw JSON
→ Meta-Auditor consolidated JSON
→ HTML report
→ PDF report

## Artifact traceability

For each technical-evaluation case, the repository preserves the
complete sequence from the original tool outputs to the final report:

```text
Raw Lighthouse JSON + Raw WAVE JSON
→ Consolidated Meta-Auditor JSON
→ HTML report
→ PDF report
```

The consolidated JSON contains the structured result produced after
normalization, consolidation, severity classification, Risk Score
calculation, and correction prioritization. This organization supports
traceability from the original API responses to the results reported
in the article.

## Acceptance evaluation

The `acceptance-evaluation/` directory contains the public,
pseudonymized versions of the five reports used in the acceptance
evaluation, identified as AP01–AP05.

Primary identifiers, collection dates and internal audit identifiers
were removed. Visual and semantic evidence produced by the
Meta-Auditor was preserved, following the evaluation protocol, and
may contain fragments of the original portal content.

## Article figures

The `Article images/` directory contains the figures used to illustrate
the architecture, normalization, consolidation, reports and evaluation
results presented in the associated article.

## TAM qualitative mapping

The `TAM mapping/` directory contains the pseudonymized mapping of
selected open-ended responses used to support the qualitative analysis
reported in the article.

Participants are identified only by the codes AP01–AP05.
