# AUTHENTICA — Stage 3 Fraud Intent Engine

## 🎯 Engine Purpose & Philosophy

Traditional deepfake detection systems answer only one question:  
> *"Is this media synthetic or manipulated?"*

Authentica recognizes that **Media Manipulation Risk** and **Fraud Intent Risk** are **orthogonal dimensions**:

| Scenario | Media Manipulation | Fraud Intent | Recommended Action |
| :--- | :---: | :---: | :---: |
| **Parody / Creative Deepfake** (e.g. Morgan Freeman AI clone reciting poetry) | `HIGH` | `LOW` | `CAUTION` |
| **Genuine Video Extortion** (e.g. Real CEO video recycled with scam demands) | `NO_STRONG_EVIDENCE` | `HIGH` | `STOP_AND_VERIFY` |
| **Weaponized CEO Deepfake** (e.g. Synthetic executive demanding wire transfer) | `HIGH` | `HIGH` | `STOP_AND_VERIFY` |
| **Benign Authentic Dialogue** (e.g. Authentic interview discussing personal finances) | `NO_STRONG_EVIDENCE` | `LOW` | `NO_ACTION_FLAGGED` |

---

## 🔍 Linguistic Directive Extraction Engine

The Fraud Intent Engine operates on timestamped speech segments extracted by Faster-Whisper. It parses text using contextual pattern matchers and regex grammars to detect high-risk extraction directives.

### 1. High-Risk Action Directives (`requested_actions`)

| Directive Category | Trigger Patterns & Grammars | Severity |
| :--- | :--- | :---: |
| **OTP & Credential Theft** | `(share|send|tell|give|enter|provide) (the|your)? (otp|one time password|pin|verification code|2fa|code)` | `HIGH` |
| **Wire & Payment Directives** | `(transfer|send|wire|pay|deposit) (\d+|money|funds|dollars|rupees|crypto|bitcoin|eth|usdt) (to|into|immediately|now|this account)` | `HIGH` |
| **Remote Software Access** | `(download|install|open|run) (anydesk|teamviewer|quicksupport|ultraviewer|screen share|remote)` | `HIGH` |
| **Urgent Secrecy Demand** | `(do not tell|keep this (secret|confidential)|do not contact|between us|keep quiet)` | `HIGH` |

### 2. Social-Engineering Tactics Taxonomy (`categories`)

1. **`DIRECT_FINANCIAL_REQUEST`**: Demands for wire transfers, bank deposits, or cryptocurrency transactions.
2. **`CREDENTIAL_EXTRACTION`**: Solicitations for 2FA tokens, passwords, or OTP codes.
3. **`REMOTE_ACCESS_EXPLOITATION`**: Instructions to download or execute remote management software.
4. **`URGENCY_AND_COERCION`**: Artificial deadlines, threats of arrest, account suspension, or immediate asset freezing.
5. **`AUTHORITY_IMPERSONATION`**: Claims of being law enforcement, bank fraud investigation teams, tax officials, or corporate executives.

---

## ⚖️ Calibration: Subjective Statements vs. Extortion Directives

To prevent false positives on conversational speech (e.g. *"I need money for groceries"*, *"He asked if I had money"*), the engine differentiates between **subjective statements of state** and **imperative extraction directives**:

- ❌ **Non-Threatening Subjective Statements (Evaluated as `LOW` Fraud Risk):**
  - *"I really need some money right now."*
  - *"Money is tight this month."*
  - *"We are discussing corporate wire transfers."*
- ✅ **Imperative Directives (Evaluated as `HIGH` Fraud Risk):**
  - *"Transfer 50,000 rupees to this account immediately."*
  - *"Send me the OTP you just received."*
  - *"Install AnyDesk so I can resolve your frozen account."*

---

## 🛡️ Scam Awareness & News Context Filter

When media discusses scams in an **educational, journalistic, or reporting context**, naive keyword matching would incorrectly trigger high fraud alarms.

Authentica includes an active context filter:
- **Awareness Markers:**
  - *"police have warned against"*
  - *"fraudsters are using"*
  - *"be aware of this scam"*
  - *"scam alert"*
  - *"cybercrime department advises"*
- **Action:** When awareness markers are detected without coercive user-directed commands, the engine sets `news_context_downgrade = true` and caps fraud severity at `LOW` or `MEDIUM` with an explanation tag.

---

## 🚦 Final Recommendation Decision Matrix

```
                          ┌─────────────────────────────┐
                          │     Evidence Evaluation     │
                          └──────────────┬──────────────┘
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 ▼                                               ▼
         [ Fraud Level == HIGH ]                       [ Fraud Level <= MEDIUM ]
                 │                                               │
                 ▼                                               │
     ┌────────────────────────┐                                  │
     │    STOP_AND_VERIFY     │                                  │
     │ (Immediate Block & 2FA)│                                  │
     └────────────────────────┘                                  │
                                                                 │
                 ┌───────────────────────────────────────────────┘
                 │
                 ├───────────────────────────────┬───────────────────────────────┐
                 ▼                               ▼                               ▼
       [ Media == LIKELY_MANIP ]      [ Media == SUSPICIOUS ]         [ Media == NO_STRONG_EVID ]
                 │                               │                               │
                 ▼                               ▼                               ▼
        ┌─────────────────┐             ┌─────────────────┐             ┌─────────────────┐
        │     CAUTION     │             │     VERIFY      │             │NO_ACTION_FLAGGED│
        │(Synthetic Media)│             │(Degraded Quality│             │(Safe / Standard)│
        └─────────────────┘             └─────────────────┘             └─────────────────┘
```
