# eval-v0 · outputs/baseline

| client | C1_risk_warning | C2_fca_line | C3_no_leftover_slots | F1_accounts_in_scope | F2_sections | F5_only_approved_figures |
|---|---|---|---|---|---|---|
| client_01_clean | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| client_02_medium | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| client_03_hard | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
| client_04_stretch | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
| **passed** | 4/4 | 4/4 | 4/4 | 1/4 | 4/4 | 1/4 |

**Fails**

- client_01_clean · F1_accounts_in_scope: table 1: missing [], repeated [], 1 other rows
- client_02_medium · F5_only_approved_figures: not approved: ['£5,000', '£12,300']
- client_03_hard · F1_accounts_in_scope: table 1: missing [], repeated [], 1 other rows
- client_03_hard · F5_only_approved_figures: not approved: ['£150,000', '£20,000', '£110,000', '£25,000', '£5,000', '£12,300']
- client_04_stretch · F1_accounts_in_scope: table 1: missing [], repeated [], 3 other rows; table 2: missing [], repeated [], 2 other rows; table 3: missing [], repeated [], 3 other rows
- client_04_stretch · F5_only_approved_figures: not approved: ['£30,000', '£15,000', '£6,000', '£9,000', '10%', '£900', '£1,800', '£0']
