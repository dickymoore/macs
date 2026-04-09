# Evidence Templates Index

These templates define the minimum human-readable evidence pack for Epic 7 and Epic 8 execution. They are intentionally lightweight, but they are strict enough to support setup validation, adapter qualification, failure drills, dogfooding, and later release-gate reporting.

## Use This Folder For

- Epic 7.2 setup and validation evidence
- Epic 7.4 contributor-facing adapter qualification runs
- Epic 8.2 mandatory failure-drill reporting
- Epic 8.3 four-worker dogfood evidence
- Epic 8.4 release review inputs

## Template Set

| Template | Primary Epic/Story | Use when | Output style |
| --- | --- | --- | --- |
| [`setup-validation-template.md`](./setup-validation-template.md) | Epic 7.2 | validating a repo-local mixed-runtime installation and safe-ready state | one report per repo/setup run |
| [`adapter-qualification-template.md`](./adapter-qualification-template.md) | Epic 7.4, Epic 8.1 | qualifying a runtime adapter for first-class status or documenting gaps | one report per adapter/version |
| [`failure-drill-report-template.md`](./failure-drill-report-template.md) | Epic 8.2 | recording one mandatory failure-class drill or integration run | one report per failure class per run |
| [`dogfood-evidence-template.md`](./dogfood-evidence-template.md) | Epic 8.3 | proving the four-worker reference scenario in the MACS repo | one report per dogfood run |

## Working Rules

- Keep controller facts, adapter signals, and untrusted claims separate.
- Link machine-readable artifacts instead of pasting large logs.
- Record exact commands, fixture inputs, and runtime versions.
- Use explicit `PASS`, `FAIL`, `PARTIAL`, or `BLOCKED` outcomes.
- Capture event IDs, state snapshots, and timing where the story requires them.
- If evidence is missing, mark it as `UNAVAILABLE` or `NOT EXPOSED`; do not infer.

## Suggested Naming

- `setup-validation-YYYY-MM-DD-<repo>.md`
- `adapter-qualification-<adapter>-<version>-YYYY-MM-DD.md`
- `failure-drill-<failure-class>-YYYY-MM-DD-<run-id>.md`
- `dogfood-4-worker-YYYY-MM-DD-<run-id>.md`

## Release-Gate Fit

Together, these templates cover the evidence gaps called out in the implementation readiness report:

- documented setup validation
- first-class adapter qualification
- mandatory failure-mode proof
- repeatable dogfood artifacts

They are designed to feed a later Epic 8.4 release-gate command and human-readable readiness report without reformatting.
