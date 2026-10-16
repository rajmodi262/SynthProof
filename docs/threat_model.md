# SynthProof — Threat Model & Scope Specification

---

## 1. Adversary Model

- **Adversary Goal:** Determine whether a specific target individual $x^*$ was present in the sensitive training dataset $D_{\text{train}}$ (Membership Inference Attack) or reconstruct sensitive attributes of $x^*$ given partial background knowledge (Attribute Reconstruction Attack).
- **Adversary Capabilities:**
  - **Black-Box Access:** The adversary receives the released synthetic dataset $D_{\text{synth}}$ and the signed Privacy Data Sheet certificate.
  - **Auxiliary Knowledge:** The adversary possesses background knowledge of the population distribution and partial attribute values for target records.
  - **Held-out Reference Set:** The adversary has access to an independent held-out reference dataset $D_{\text{holdout}}$ from the same population distribution.

---

## 2. Unit of Privacy

- **Record-Level Differential Privacy:** SynthProof guarantees $(\epsilon, \delta)$-Differential Privacy at the single-record level. Addition or removal of any individual record $x$ alters the probability of output synthetic datasets by at most $e^\epsilon$.

---

## 2a. Disclosure risks measured

The EDPB's anonymisation criteria — operationalised by Anonymeter (Giomi et al., PoPETs 2023)
— treat three risks as distinct. All three are now measured on every release:

| Risk | Question | Implementation |
|---|---|---|
| **Singling out** | Can one record be isolated? | `attacks/exact_match_risk.py` |
| **Linkability** | Can two pieces of information be shown to concern the same person? | `attacks/linkability.py` |
| **Inference** | Can an attribute value be deduced? | `attacks/attribute_inference.py` |

**These are our own approximations, not Anonymeter.** Integrating the reference toolkit was
attempted on 2026-08-23 and is not possible here: `anonymeter` pins `numpy < 2` while
`jax`/`jaxlib` — and therefore `mbi`, private-PGM and real AIM — require `numpy >= 2`.
Installing it downgraded numpy and broke AIM outright. The trade is not worth making, and
naming our approximations after Anonymeter's concepts without saying so would breach standing
rule 4.

Each carries its own control, because a raw rate is uninterpretable: linkability reports
agreement in excess of a **row-shuffled release** (marginals preserved, row correspondence
destroyed), and attribute inference scores against a **conditional** baseline rather than a
marginal one. Linkability is reported **not applicable** on tables with fewer than four
columns, which cannot be split into two disjoint halves.

---

## 2b. Threats to the service, the keys and the record — and the evidence for each mitigation

The adversary above attacks the **release**. These attack the **system that makes it**: the API,
the signing key, the ledger, the build. Each row names the test that fails if the mitigation is
removed; "argument" marks the one row that rests on code inspection alone. Added 2026-10-16 (W7).

| # | Threat | Mitigation | Evidence |
|---|---|---|---|
| T1 | A remote caller reaches an unauthenticated service and uploads data, spends budget or reads the ledger | With no API key, data and budget endpoints answer only the trusted network (loopback; `private` in the image); Compose publishes on 127.0.0.1 | `tests/test_security.py::test_an_open_service_refuses_a_remote_caller`, `::test_the_container_setting_admits_the_docker_bridge_but_not_the_internet` |
| T2 | One principal exhausts the privacy budget | `SYNTHPROOF_BUDGETS` caps each principal; an over-cap release is refused before it runs and charges nothing | `tests/test_security.py::test_a_release_past_the_principals_cap_is_refused_before_it_runs` |
| T3 | Flooding releases or uploads | Per-principal rate limit (429 + Retry-After), on by default for a durable ledger | `tests/test_security.py::test_releases_beyond_the_rate_limit_get_429`, `::test_the_rate_limiter_windows_per_key` |
| T4 | Script injection or clickjacking in the console | CSP without inline script, `frame-ancestors 'none'`, `nosniff`, `X-Frame-Options: DENY` | `tests/test_security.py::test_the_console_gets_a_content_security_policy_without_inline_scripts`; the Playwright suite runs the console under the CSP (`web/e2e/console.spec.ts`) |
| T5 | Theft of the signing key from disk | Encrypted at rest with `SYNTHPROOF_KEY_PASSPHRASE` (or `_FILE`); owner-only permissions | `tests/test_key_custody.py::test_with_a_passphrase_the_key_on_disk_is_encrypted`, `::test_an_encrypted_key_will_not_load_without_its_passphrase` |
| T6 | A compromised or ageing key | `synthproof keygen --rotate`: old public key retained, old private key destroyed, rotation logged | `tests/test_key_custody.py::test_rotation_keeps_old_signatures_verifiable_and_destroys_the_old_private_key` |
| T7 | Rotation used to launder a tampered ledger | The chain must verify under the current key before it is re-signed | `tests/test_key_custody.py::test_rotation_refuses_to_launder_a_tampered_ledger` |
| T8 | Editing, replaying or forging ledger entries | Hash chain, per-entry Ed25519 signatures | `tests/test_ledger_adversarial.py::test_editing_a_field_and_recomputing_the_stored_hash_is_still_detected`, `::test_replaying_a_signed_entry_under_a_new_id_is_detected`, `::test_appending_a_forged_entry_and_rewriting_the_head_is_detected` |
| T9 | Truncating the ledger | A signed head commits to the entry count | `tests/test_ledger_adversarial.py::test_truncating_the_tail_is_detected`, `::test_deleting_the_head_row_does_not_launder_a_truncation` |
| T10 | Editing a released Privacy Data Sheet | Ed25519 signature over the canonical sheet | `tests/test_meaning.py::test_changing_any_reported_number_breaks_the_signature` |
| T11 | Recovering an API key by timing | Every configured key compared with `hmac.compare_digest`, with no early exit | argument (`synthproof/api/context.py::require_api_key`) |
| T12 | Malformed or hostile requests and sheets | Strict validation (422, never 500); the boundary auditor never crashes | `tests/test_fuzz.py` |
| T13 | Replaying a release from its seed | The seed is secret and never written to any artefact | `tests/test_release_boundary.py::test_no_artefact_carries_the_seed`, `::test_a_published_seed_would_decide_membership` |
| T14 | Exhausting memory with uploads | Size and row caps, chunked reads, a bounded FIFO store, nothing written to disk | `tests/test_api.py::test_upload_store_is_bounded`, `::test_uploads_never_touch_the_filesystem` |
| T15 | A browser page abusing an open CORS policy | CORS narrows once any key is configured | `tests/test_api_auth.py::test_cors_stops_being_a_wildcard_once_a_key_is_set`, `tests/test_app_factory.py::test_named_keys_also_narrow_cors` |
| T16 | A vulnerable dependency or a committed secret | `pip-audit`, `npm audit --omit=dev`, `bandit`, `gitleaks` in CI; Dependabot | CI `security` and `console` jobs |
| T17 | A compromised process writing to the image | Non-root user, read-only root filesystem, `no-new-privileges` | CI `docker` job: "Runs with a read-only root filesystem" |

**What none of this covers**, stated so it is not assumed: there is no TLS termination (put a
reverse proxy in front), no per-key expiry or SSO, and a holder of the signing key can still
rewrite and re-sign the ledger — the chain is tamper-evident, not tamper-proof.

---

## 3. Out-of-Scope Attacks

- **Hardware Side-Channels:** Physical power, electromagnetic, or CPU cache timing side-channels during execution.
- **Upstream Data Corruption:** Adversarial poisoning of raw database extracts before ingestion by SynthProof.
