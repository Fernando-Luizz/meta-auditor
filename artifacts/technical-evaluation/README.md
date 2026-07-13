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

## From raw output to report

Both raw JSON files are preserved exactly as returned by the two APIs, before any transformation, so every number in the paper can be traced back to its source. From there, Meta-Auditor's deterministic pipeline runs end to end:

```text
lighthouse_raw.json + wave_raw.json
  -> normalization, consolidation, severity, Risk Score, priority
  -> *_meta_auditor_consolidado.json
  -> HTML report
  -> PDF report
```

The consolidated JSON is also the source used to render the HTML report; the PDF is a print of that same HTML.

## Related material

- Normalization mapping specification: [`../normalization/`](../normalization/README.md)
- Acceptance-evaluation reports (AP01-AP05): [`../acceptance-evaluation/`](../acceptance-evaluation/README.md)
- Full artifact index: [`../README.md`](../README.md)

