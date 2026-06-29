# machine AiAssessment

## context
| Field | Type | Default |
|---|---|---|
| document_id | string | |

## events
- ANALYZE
- ANALYZED
- REVISED
- FAIL

## state pending [initial]
> Verdict produced; awaiting AI assessment (skipped if no key / over budget).
- ignore: *

## state analyzing
> Generating the analysis — summary, aims, strengths, weaknesses, pitfalls, issues.
- ignore: *

## state revising
> Generating the redlined revision (chunked across the whole document).
- ignore: *

## state complete [final]
> Assessment + revision ready.

## state failed [final]
> AI assessment failed or was skipped.

## transitions
| Source | Event | Guard | Target | Action |
|---|---|---|---|---|
| pending | ANALYZE | | analyzing | |
| analyzing | ANALYZED | | revising | |
| analyzing | FAIL | | failed | |
| revising | REVISED | | complete | |
| revising | FAIL | | failed | |
