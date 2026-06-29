# machine ContractValidation

## context
| Field | Type | Default |
|---|---|---|
| document_id | string | |
| owner | string | |
| missing_count | int | 0 |
| has_parties | int | 0 |
| has_effective_date | int | 0 |
| has_term | int | 0 |
| has_signatures | int | 0 |
| has_governing_law | int | 0 |

## events
- EXTRACTED
- EVALUATE
- EXTRACTION_FAILED
- TIMEOUT

## state received [initial]
> Document received; awaiting OCR and field extraction.

## state validating
> Extracted fields are being checked against the contract requirements.

## state valid [final]
> Contract satisfied all required-field checks.

## state invalid [final]
> Contract failed one or more required-field checks.

## state error [final]
> Extraction or processing failed; no verdict could be produced.

## transitions
| Source | Event | Guard | Target | Action |
|---|---|---|---|---|
| received | EXTRACTED | | validating | record_extracted |
| received | EVALUATE | | received | |
| received | EXTRACTION_FAILED | | error | record_error |
| received | TIMEOUT | | error | record_error |
| validating | EXTRACTED | | validating | |
| validating | EVALUATE | all_required_present | valid | record_valid |
| validating | EVALUATE | missing_required | invalid | record_invalid |
| validating | EXTRACTION_FAILED | | error | record_error |
| validating | TIMEOUT | | error | record_error |

## guards
| Name | Expression |
|---|---|
| all_required_present | `ctx.missing_count == 0` |
| missing_required | `ctx.missing_count > 0` |

## actions
| Name | Signature |
|---|---|
| record_extracted | (context, payload) -> context |
| record_valid | (context, payload) -> context |
| record_invalid | (context, payload) -> context |
| record_error | (context, payload) -> context |
