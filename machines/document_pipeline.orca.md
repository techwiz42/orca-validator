# machine DocumentPipeline

## context
| Field | Type | Default |
|---|---|---|
| document_id | string | |

## events
- BEGIN
- INGESTED
- VALIDATED
- ASSESSED
- FAIL

## state received [initial]
> Document submitted; pipeline not yet started.
- ignore: *

## state ingesting
> Component: Ingestion (extract text from the upload/paste).
- ignore: *

## state validating
> Component: ContractValidation (the verified structural verdict).
- ignore: *

## state assessing
> Component: AiAssessment (analysis + redlined revision).
- ignore: *

## state complete [final]
> Verdict + assessment + revision delivered.

## state failed [final]
> Pipeline failed (extraction error).

## transitions
| Source | Event | Guard | Target | Action |
|---|---|---|---|---|
| received | BEGIN | | ingesting | |
| ingesting | INGESTED | | validating | |
| ingesting | FAIL | | failed | |
| validating | VALIDATED | | assessing | |
| validating | FAIL | | failed | |
| assessing | ASSESSED | | complete | |
| assessing | FAIL | | failed | |
