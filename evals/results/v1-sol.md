# eval-v0 · outputs/v1-sol

| client | C1_risk_warning | C2_fca_line | C3_no_leftover_slots | F1_accounts_in_scope | F2_sections | F5_only_approved_figures |
|---|---|---|---|---|---|---|
| client_01_clean | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| client_02_medium | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| client_03_hard | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| client_04_stretch | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **passed** | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 |

**Fails**


**Run cost** (from the Langfuse traces, same v1 prompts, gpt-4o-mini → gpt-6.1-sol)

| client | calls | tokens | cost | time |
|---|---|---|---|---|
| client_01_clean | 6 → 6 | 6,415 → 6,787 | $0.0011 → $0.0193 | 10.4s → 21.3s |
| client_02_medium | 7 → 7 | 9,551 → 9,912 | $0.0012 → $0.0272 | 16.0s → 27.3s |
| client_03_hard | 7 → 7 | 13,834 → 14,572 | $0.0019 → $0.0398 | 14.6s → 32.8s |
| client_04_stretch | 7 → 7 | 22,617 → 23,461 | $0.0027 → $0.0601 | 20.3s → 38.5s |
| **all four** | **27 → 27** | **52,417 → 54,732** | **$0.0069 → $0.1464 (~21x)** | **61.3s → 119.9s (~2x)** |

same calls and about the same tokens: the difference is the model's price per token and its
reasoning time. about 4p per report.
