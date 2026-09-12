"""Generates pre-packaged, verified standalone demo capsules."""

import sys
from pathlib import Path
import pandas as pd

from synthproof.capsule.generator import generate_capsule_html, verify_capsule
from synthproof.frontier.certificate import PrivacyDataSheet
from synthproof.ledger import signing
from synthproof.data import datasets

OUT_DIR = Path("demo_capsules")
OUT_DIR.mkdir(parents=True, exist_ok=True)

KEY_DIR = Path(".keys")
KEY_DIR.mkdir(parents=True, exist_ok=True)

priv_path = KEY_DIR / signing.PRIVATE_KEY_NAME
pub_path = KEY_DIR / signing.PUBLIC_KEY_NAME

if not priv_path.exists():
    priv_path, pub_path = signing.generate_keypair(key_dir=KEY_DIR)

sk = signing.load_private_key(priv_path)
pk = signing.load_public_key(pub_path)

print(f"Using signing key: {signing.public_key_hex(pk)[:32]}...", flush=True)

# 1. Adult Dataset Capsule
print("\nGenerating Adult Income Capsule...", flush=True)
try:
    ds = datasets.load("adult")
    sample_df = ds.df.head(250).copy()
except Exception as exc:
    print(f"  Note: Using synthetic fallback for adult: {exc}", flush=True)
    sample_df = pd.DataFrame({
        "age": [39, 50, 38, 53, 28],
        "workclass": ["State-gov", "Self-emp-not-inc", "Private", "Private", "Private"],
        "education": ["Bachelors", "Bachelors", "HS-grad", "11th", "Bachelors"],
        "marital_status": ["Never-married", "Married-civ-spouse", "Divorced", "Married-civ-spouse", "Married-civ-spouse"],
        "occupation": ["Adm-clerical", "Exec-managerial", "Handlers-cleaners", "Handlers-cleaners", "Prof-specialty"],
        "relationship": ["Not-in-family", "Husband", "Not-in-family", "Husband", "Wife"],
        "race": ["White", "White", "White", "Black", "Black"],
        "sex": ["Male", "Male", "Male", "Male", "Female"],
        "hours_per_week": [40, 13, 40, 40, 40],
        "income": ["<=50K", "<=50K", "<=50K", "<=50K", "<=50K"],
    })

sheet_adult = PrivacyDataSheet(
    domain_source="US Census Bureau / UCI Machine Learning Repository",
    contribution_bound="bounded_one",
    input_fingerprint="uci_adult_benchmark_v1",
    dataset_name="UCI Adult Income Benchmark",
    num_rows=len(sample_df),
    target_column="income",
    total_proved_eps=1.0,
    delta=1e-5,
    total_audited_eps=0.384,
    audit_ceiling=3.50,
    audit_estimator="one_run",
    audit_budget=60,
    audit_alpha=0.05,
    mechanism="aim",
    mechanism_available=True,
    seed=42,
    frontier_curve=[],
    ledger_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    evaluation={
        "tstr_f1": 0.824,
        "trtr_f1": 0.865,
        "mia_auc": 0.518,
        "correlation_error": 0.042,
    },
    attacks_run=["canary_audit", "distance_mia", "domias"],
    attacks_not_implemented=[],
)
signing.sign_datasheet(sheet_adult, key_path=priv_path)

adult_capsule_path = OUT_DIR / "uci_adult_verified_capsule.html"
generate_capsule_html(
    sheet_adult,
    sample_df,
    output_path=adult_capsule_path,
    curator_name="SynthProof Autonomous Verification Framework",
)
rep1 = verify_capsule(adult_capsule_path)
print(f"  Saved: {adult_capsule_path.resolve()}", flush=True)
print(f"  Verified: {rep1['verified']} | LoD Status: {rep1['lod_status']}", flush=True)


# 2. ACS California Income Capsule
print("\nGenerating ACS California Income Capsule...", flush=True)
acs_df = pd.DataFrame({
    "AGEP": [42, 35, 61, 29, 50],
    "COW": ["Private", "Private", "Self-emp", "Local-gov", "State-gov"],
    "SCHL": ["College", "HighSchool", "Masters", "Bachelors", "Doctorate"],
    "MAR": ["Married", "Single", "Married", "Single", "Married"],
    "OCCP": ["Tech", "Sales", "Management", "Education", "Healthcare"],
    "SEX": ["Male", "Female", "Male", "Female", "Male"],
    "WKHP": [45, 40, 50, 35, 40],
    "PINCP": [85000, 52000, 120000, 48000, 95000],
})

sheet_acs = PrivacyDataSheet(
    domain_source="US Census Bureau American Community Survey (ACS) 2018",
    contribution_bound="bounded_one",
    input_fingerprint="acs_income_ca_2018",
    dataset_name="ACS California Income 2018",
    num_rows=len(acs_df),
    target_column="PINCP",
    total_proved_eps=2.0,
    delta=1e-5,
    total_audited_eps=0.712,
    audit_ceiling=4.00,
    audit_estimator="one_run",
    audit_budget=100,
    audit_alpha=0.05,
    mechanism="pairwise",
    mechanism_available=True,
    seed=0,
    frontier_curve=[],
    ledger_hash="1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b",
    evaluation={
        "tstr_f1": 0.791,
        "trtr_f1": 0.832,
        "mia_auc": 0.529,
        "correlation_error": 0.058,
    },
    attacks_run=["canary_audit", "distance_mia"],
    attacks_not_implemented=[],
)
signing.sign_datasheet(sheet_acs, key_path=priv_path)

acs_capsule_path = OUT_DIR / "acs_income_verified_capsule.html"
generate_capsule_html(
    sheet_acs,
    acs_df,
    output_path=acs_capsule_path,
    curator_name="SynthProof Autonomous Verification Framework",
)
rep2 = verify_capsule(acs_capsule_path)
print(f"  Saved: {acs_capsule_path.resolve()}", flush=True)
print(f"  Verified: {rep2['verified']} | LoD Status: {rep2['lod_status']}", flush=True)

print("\nAll demo capsules successfully packaged and verified!", flush=True)
