# Technical evaluation artifacts

Artifacts from the nine technical-evaluation cases (CP01-CP09) referenced in the paper.

## What's in each case folder

| File | Contents |
|---|---|
| `lighthouse_raw.json` | Raw response from the PageSpeed Insights API |
| `wave_raw.json` | Raw response from the WAVE API |
| `CPxx_..._meta_auditor_consolidado.json` | Consolidated result produced by Meta-Auditor |
| `CPxx_....html` | Generated HTML report |
| `CPxx_....pdf` | Generated PDF report |

## From raw API responses to generated reports

For each evaluated case, Meta-Auditor receives two independent inputs:
the Lighthouse response obtained through the PageSpeed Insights API and
the response returned by the WAVE API.

These responses are preserved as JSON files before Meta-Auditor performs
any normalization, consolidation, severity classification, Risk Score
calculation, or correction prioritization. The JSON files use standardized
formatting, while preserving the data returned by the APIs.

Meta-Auditor then executes its deterministic processing pipeline:

```text
lighthouse_raw.json + wave_raw.json
  -> normalization of tool-specific findings
  -> consolidation of equivalent findings
  -> origin classification and divergence identification
  -> severity classification
  -> Risk Score calculation
  -> P1, P2, or P3 correction prioritization
  -> *_meta_auditor_consolidado.json
  -> HTML report
  -> PDF report
```

The structured result produced by this pipeline is stored in the SQLite
audit record and exported as the consolidated Meta-Auditor JSON available
in each case directory. The same structured audit data is passed to the
HTML report template. The PDF report is produced by rendering that HTML.

This organization enables traceability from the preserved API responses
to the structured results and final reports discussed in the paper.

## Related material

- Normalization mapping specification: [`../normalization/`](../normalization/README.md)
- Acceptance-evaluation reports (AP01-AP05): [`../acceptance-evaluation/`](../acceptance-evaluation/README.md)
- Full artifact index: [`../README.md`](../README.md)

