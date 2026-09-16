# Empirical In-The-Wild Measurement Study: Release Boundary Side Channels in Public Datasets

> **Audit Date:** 2026-09-15  
> **Target Platform:** Hugging Face Hub (Public Datasets API)  
> **Total Datasets Audited:** 73  

## 1. Executive Summary Table

| Vulnerability Category | Severity | Flagged Datasets | Percentage of Corpus |
|---|---|:---:|:---:|
| **Exposed PRNG Seed (`random_state`)** | **FATAL** | 22 | **30.14%** |
| **Exact Sample Count Side Channel** | **HIGH** | 38 | **52.05%** |
| **Unkeyed Table Hash (`SHA-256`)** | **HIGH** | 0 | 0.0% |
| **Unlabelled Evaluation Split** | **MEDIUM** | 11 | 15.07% |
| **At Least One Fatal Side Channel** | **FATAL** | **22** | **30.14%** |

## 2. Exemplar Vulnerable Repositories

Below are real-world repositories from the audit that published fatal side channels:

### `airesearch/wangchanx-seed-free-synthetic-instruct-thai-120k` (Downloads: 51)
- **[HIGH] EXACT_COUNT_SIDE_CHANNEL:** Exact sample count published without DP count mechanism: 636862793

### `pacozaa/seed-free-synthetic-instruct-thai-v1-chatml` (Downloads: 7)
- **[HIGH] EXACT_COUNT_SIDE_CHANNEL:** Exact sample count published without DP count mechanism: 33188707

### `sacrificialpancakes/synthetic_demographics_seed` (Downloads: 20)
- **[FATAL] EXPOSED_PRNG_SEED:** Found random seeds published: ['in repo title']

### `ostapeno/med_wrap1666058_seed_4.72e07_synthetic_5.71e07` (Downloads: 19)
- **[FATAL] EXPOSED_PRNG_SEED:** Found random seeds published: ['4.72e07', '4']

### `ostapeno/med_wrap1666058_seed_1.89e08_synthetic_2.27e08` (Downloads: 14)
- **[FATAL] EXPOSED_PRNG_SEED:** Found random seeds published: ['1', '1.89e08']

### `lhpku20010120/AAIR_synthetic_seed` (Downloads: 15)
- **[FATAL] EXPOSED_PRNG_SEED:** Found random seeds published: ['in repo title']
- **[MEDIUM] UNLABELLED_EVALUATION_SPLIT:** No clear train/test/holdout split specified in metadata card

### `davidberenstein1957/uplimit-synthetic-data-week-1-with-seed` (Downloads: 8)
- **[FATAL] EXPOSED_PRNG_SEED:** Found random seeds published: ['with-seed']

### `uplimit/uplimit-synthetic-data-week-1-with-seed` (Downloads: 49)
- **[FATAL] EXPOSED_PRNG_SEED:** Found random seeds published: ['with-seed']
- **[HIGH] EXACT_COUNT_SIDE_CHANNEL:** Exact sample count published without DP count mechanism: 11067

### `uplimit/uplimit-synthetic-data-week-1-with-seed-evol` (Downloads: 21)
- **[FATAL] EXPOSED_PRNG_SEED:** Found random seeds published: ['with-seed']
- **[HIGH] EXACT_COUNT_SIDE_CHANNEL:** Exact sample count published without DP count mechanism: 11087

### `uonyeka/uplimit-synthetic-data-week-1-with-seed` (Downloads: 31)
- **[FATAL] EXPOSED_PRNG_SEED:** Found random seeds published: ['with-seed']
- **[HIGH] EXACT_COUNT_SIDE_CHANNEL:** Exact sample count published without DP count mechanism: 11095

### `marotosg/uplimit-synthetic-data-week-1-with-seed` (Downloads: 19)
- **[FATAL] EXPOSED_PRNG_SEED:** Found random seeds published: ['with-seed']
- **[HIGH] EXACT_COUNT_SIDE_CHANNEL:** Exact sample count published without DP count mechanism: 11101

### `85danf/uplimit-synthetic-data-week-1-with-seed` (Downloads: 14)
- **[FATAL] EXPOSED_PRNG_SEED:** Found random seeds published: ['with-seed']
- **[HIGH] EXACT_COUNT_SIDE_CHANNEL:** Exact sample count published without DP count mechanism: 10993

### `jsimon-pfpt/uplimit-synthetic-data-week-1-with-seed` (Downloads: 16)
- **[FATAL] EXPOSED_PRNG_SEED:** Found random seeds published: ['with-seed']
- **[HIGH] EXACT_COUNT_SIDE_CHANNEL:** Exact sample count published without DP count mechanism: 11093

### `landedmover/uplimit-synthetic-data-week-1-with-seed` (Downloads: 5)
- **[FATAL] EXPOSED_PRNG_SEED:** Found random seeds published: ['with-seed']
- **[HIGH] EXACT_COUNT_SIDE_CHANNEL:** Exact sample count published without DP count mechanism: 11109

### `Tiamz/uplimit-synthetic-data-week-1-with-seed` (Downloads: 25)
- **[FATAL] EXPOSED_PRNG_SEED:** Found random seeds published: ['with-seed']
- **[HIGH] EXACT_COUNT_SIDE_CHANNEL:** Exact sample count published without DP count mechanism: 11193

### `isabei/uplimit-synthetic-data-week-1-with-seed` (Downloads: 18)
- **[FATAL] EXPOSED_PRNG_SEED:** Found random seeds published: ['with-seed']
- **[HIGH] EXACT_COUNT_SIDE_CHANNEL:** Exact sample count published without DP count mechanism: 11239

### `sooney/uplimit-synthetic-data-week-1-with-seed` (Downloads: 4)
- **[FATAL] EXPOSED_PRNG_SEED:** Found random seeds published: ['with-seed']
- **[HIGH] EXACT_COUNT_SIDE_CHANNEL:** Exact sample count published without DP count mechanism: 11121

### `akattamuri/uplimit-synthetic-data-week-1-with-seed` (Downloads: 9)
- **[FATAL] EXPOSED_PRNG_SEED:** Found random seeds published: ['with-seed']
- **[HIGH] EXACT_COUNT_SIDE_CHANNEL:** Exact sample count published without DP count mechanism: 11117

### `ndhananj/uplimit-synthetic-data-week-1-with-seed` (Downloads: 19)
- **[FATAL] EXPOSED_PRNG_SEED:** Found random seeds published: ['with-seed']
- **[HIGH] EXACT_COUNT_SIDE_CHANNEL:** Exact sample count published without DP count mechanism: 2097767

### `eliasprost/uplimit-synthetic-data-week-1-with-seed` (Downloads: 33)
- **[FATAL] EXPOSED_PRNG_SEED:** Found random seeds published: ['with-seed']
- **[HIGH] EXACT_COUNT_SIDE_CHANNEL:** Exact sample count published without DP count mechanism: 1685014

### `johnmccabe/uplimit-synthetic-data-week-1-with-seed` (Downloads: 10)
- **[FATAL] EXPOSED_PRNG_SEED:** Found random seeds published: ['with-seed']
- **[HIGH] EXACT_COUNT_SIDE_CHANNEL:** Exact sample count published without DP count mechanism: 11137

### `rutvima/uplimit-synthetic-data-week-1-with-seed` (Downloads: 11)
- **[FATAL] EXPOSED_PRNG_SEED:** Found random seeds published: ['with-seed']
- **[HIGH] EXACT_COUNT_SIDE_CHANNEL:** Exact sample count published without DP count mechanism: 116833

### `mimartin1234/uplimit-synthetic-data-week-1-with-seed` (Downloads: 4)
- **[FATAL] EXPOSED_PRNG_SEED:** Found random seeds published: ['with-seed']
- **[HIGH] EXACT_COUNT_SIDE_CHANNEL:** Exact sample count published without DP count mechanism: 56132

### `6StringNinja/synthetic-incidents-seed` (Downloads: 3)
- **[FATAL] EXPOSED_PRNG_SEED:** Found random seeds published: ['in repo title']

### `umairafzal92/tabular-synthetic-data` (Downloads: 9)
- **[MEDIUM] UNLABELLED_EVALUATION_SPLIT:** No clear train/test/holdout split specified in metadata card

### `ESHMO-AI-2047/machinelearninglm-scm-synthetic-tabularml` (Downloads: 3)
- **[MEDIUM] UNLABELLED_EVALUATION_SPLIT:** No clear train/test/holdout split specified in metadata card

### `deprem-private/intent_test_v13_anonymized` (Downloads: 16)
- **[HIGH] EXACT_COUNT_SIDE_CHANNEL:** Exact sample count published without DP count mechanism: 588460

### `deprem-private/intent_train_v13_anonymized` (Downloads: 19)
- **[HIGH] EXACT_COUNT_SIDE_CHANNEL:** Exact sample count published without DP count mechanism: 2367324

### `uplimit/uplimit-synthetic-data-week-1-basic` (Downloads: 7)
- **[HIGH] EXACT_COUNT_SIDE_CHANNEL:** Exact sample count published without DP count mechanism: 1526

### `uplimit/uplimit-synthetic-data-week-1-with-multi-turn` (Downloads: 13)
- **[HIGH] EXACT_COUNT_SIDE_CHANNEL:** Exact sample count published without DP count mechanism: 2489

### `uonyeka/uplimit-synthetic-data-week-1-basic` (Downloads: 20)
- **[HIGH] EXACT_COUNT_SIDE_CHANNEL:** Exact sample count published without DP count mechanism: 1574

### `uonyeka/uplimit-synthetic-data-week-1-with-evol` (Downloads: 19)
- **[HIGH] EXACT_COUNT_SIDE_CHANNEL:** Exact sample count published without DP count mechanism: 10751

### `uonyeka/uplimit-synthetic-data-week-1-with-multi-turn` (Downloads: 19)
- **[HIGH] EXACT_COUNT_SIDE_CHANNEL:** Exact sample count published without DP count mechanism: 2280

### `marotosg/uplimit-synthetic-data-week-1-basic` (Downloads: 11)
- **[HIGH] EXACT_COUNT_SIDE_CHANNEL:** Exact sample count published without DP count mechanism: 2784

### `marotosg/uplimit-synthetic-data-week-1-with-evol` (Downloads: 15)
- **[HIGH] EXACT_COUNT_SIDE_CHANNEL:** Exact sample count published without DP count mechanism: 11147

### `ssavchev/uplimit-synthetic-data-week-1-basic` (Downloads: 4)
- **[HIGH] EXACT_COUNT_SIDE_CHANNEL:** Exact sample count published without DP count mechanism: 2076

### `ssavchev/uplimit-synthetic-data-week-1-with-evol` (Downloads: 29)
- **[HIGH] EXACT_COUNT_SIDE_CHANNEL:** Exact sample count published without DP count mechanism: 44131

### `85danf/uplimit-synthetic-data-week-1-basic` (Downloads: 12)
- **[HIGH] EXACT_COUNT_SIDE_CHANNEL:** Exact sample count published without DP count mechanism: 1680

### `85danf/uplimit-synthetic-data-week-1-with-evol` (Downloads: 22)
- **[HIGH] EXACT_COUNT_SIDE_CHANNEL:** Exact sample count published without DP count mechanism: 11091

### `85danf/uplimit-synthetic-data-week-1-with-multi-turn` (Downloads: 7)
- **[HIGH] EXACT_COUNT_SIDE_CHANNEL:** Exact sample count published without DP count mechanism: 2461

### `jsimon-pfpt/uplimit-synthetic-data-week-1-basic` (Downloads: 15)
- **[HIGH] EXACT_COUNT_SIDE_CHANNEL:** Exact sample count published without DP count mechanism: 8504

### `jsimon-pfpt/uplimit-synthetic-data-week-1-with-evol` (Downloads: 11)
- **[HIGH] EXACT_COUNT_SIDE_CHANNEL:** Exact sample count published without DP count mechanism: 11017

### `boleeproofpoint/uplimit-week-1-synthetic-spam-email-data-filtered-quality` (Downloads: 9)
- **[HIGH] EXACT_COUNT_SIDE_CHANNEL:** Exact sample count published without DP count mechanism: 1864057

### `Ezi/Synthetic_medical` (Downloads: 5)
- **[MEDIUM] UNLABELLED_EVALUATION_SPLIT:** No clear train/test/holdout split specified in metadata card

### `Ezi/medical_and_legislators_synthetic` (Downloads: 3)
- **[MEDIUM] UNLABELLED_EVALUATION_SPLIT:** No clear train/test/holdout split specified in metadata card

### `cp500/synthetic_hebrew_medical_text` (Downloads: 25)
- **[HIGH] EXACT_COUNT_SIDE_CHANNEL:** Exact sample count published without DP count mechanism: 12496549

### `ayrus08/medicalcoding-synthetic` (Downloads: 14)
- **[MEDIUM] UNLABELLED_EVALUATION_SPLIT:** No clear train/test/holdout split specified in metadata card

### `thesven/SyntheticMedicalQA-4336` (Downloads: 25)
- **[HIGH] EXACT_COUNT_SIDE_CHANNEL:** Exact sample count published without DP count mechanism: 8535196

### `batuhanaktas/turkish_synthetic_medical_multiple_choice_QA` (Downloads: 20)
- **[MEDIUM] UNLABELLED_EVALUATION_SPLIT:** No clear train/test/holdout split specified in metadata card

### `wasiqnauman/medical-diagnosis-synthetic` (Downloads: 39)
- **[MEDIUM] UNLABELLED_EVALUATION_SPLIT:** No clear train/test/holdout split specified in metadata card

### `MaziyarPanahi/synthetic-medical-conversations-deepseek-v3-chat` (Downloads: 589)
- **[HIGH] EXACT_COUNT_SIDE_CHANNEL:** Exact sample count published without DP count mechanism: 17283575

### `II-Vietnam/Medical-MedMCQA-Synthetic` (Downloads: 12)
- **[MEDIUM] UNLABELLED_EVALUATION_SPLIT:** No clear train/test/holdout split specified in metadata card

### `II-Vietnam/Medical-MedQA-Synthetic` (Downloads: 18)
- **[MEDIUM] UNLABELLED_EVALUATION_SPLIT:** No clear train/test/holdout split specified in metadata card

### `aaarsas/synthetic_medical_data` (Downloads: 7)
- **[MEDIUM] UNLABELLED_EVALUATION_SPLIT:** No clear train/test/holdout split specified in metadata card

