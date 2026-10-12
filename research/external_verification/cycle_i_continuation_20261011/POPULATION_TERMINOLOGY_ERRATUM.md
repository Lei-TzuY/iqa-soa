# Population terminology correction

This additive correction applies to the new Cycle I benign-utility report and execution manifest first published at `61f1976188d2a94d554184cc07923627bab551ad`. It preserves those bytes and all historical evidence rather than silently replacing the report. Read this correction with the report and manifest.

The correct frozen populations are:

| Population | OFF/FULL pairs | Confirmatory observations |
|---|---:|---:|
| Entire original paired archive | **474** | **948** |
| Benign user tasks | **194** | **388** |
| All attacker goals | **280** | **560** |
| Frozen-eligible principal attacker population, a subset of the 280 | **168** | **336** |

Two new-artifact descriptions were incorrect:

1. The report's statistical-consequences paragraph calls the 474 total pairs “attack pairs.” Read that as **474 total original pairs**. Only 280 are attacker pairs; the principal attacker subset is 168.
2. The manifest field `attacker_checkpoint_unchanged.original_attack_pairs: 474` is misnamed. Its value refers to the **total** original paired population. The actual all-attacker count is **280**. The other primary/benign population fields are unchanged and correctly scoped.

Source: the unchanged [Cycle H report](../CYCLE_H_ADJUDICATION_2026-10-11.md), statistical-identifiability section, explicitly states 280 security pairs for the separate all-35-goal population; the unchanged [first Cycle I report](../CYCLE_I_HUMAN_GATE_2026-10-11.md) states 474 original pairs and 168 principal pairs. The benign audit retains the original 194 benign pairs. The partition checks are `194 + 280 = 474` and `388 + 560 = 948`. This is a terminology correction, not a record acquisition or new outcome analysis.

**No statistical result, record decision, eligibility, model weighting, clustering or testing gate changes.** The one confirmed benign false positive, 23/30 required-action classifications, seven unresolved benign observations, conditional sensitivities and unchanged H attacker bounds remain as reported. Pending owner decisions remain pending. No old report, manuscript or original result is modified.
