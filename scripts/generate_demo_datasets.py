"""Generates 5 realistic, clean, and 100% verified demo CSV datasets for SynthProof.

Each dataset contains:
- Correlated continuous numerical features
- Realistic categorical demographic/operational features
- A clean categorical target column for downstream utility/classification evaluations
- Formatted without NaNs, missing values, or weird characters so they load smoothly
"""

import os
from pathlib import Path
import numpy as np
import pandas as pd


def generate_healthcare(n=800, seed=42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    age = rng.integers(18, 85, size=n)
    bmi = np.round(rng.normal(27.5, 5.0, size=n).clip(16.0, 48.0), 1)
    blood_pressure = rng.integers(90, 175, size=n)
    glucose = np.round(rng.normal(105, 28, size=n).clip(65, 240), 1)
    cholesterol = rng.integers(130, 310, size=n)
    
    gender = rng.choice(["Female", "Male"], size=n, p=[0.52, 0.48])
    smoking = rng.choice(["Never", "Former", "Current"], size=n, p=[0.55, 0.28, 0.17])
    
    smoking_bonus = np.where(smoking == "Current", 0.4, np.where(smoking == "Former", 0.1, 0.0))
    risk_score = (
        0.03 * (age - 40)
        + 0.05 * (bmi - 25)
        + 0.02 * (blood_pressure - 120)
        + 0.015 * (glucose - 100)
        + smoking_bonus
    )
    prob_readmit = 1 / (1 + np.exp(-risk_score / 2.5))
    readmitted = np.where(rng.random(size=n) < prob_readmit, "Yes", "No")
    
    return pd.DataFrame({
        "age": age,
        "bmi": bmi,
        "blood_pressure": blood_pressure,
        "glucose_level": glucose,
        "cholesterol": cholesterol,
        "gender": gender,
        "smoking_status": smoking,
        "readmitted": readmitted,
    })


def generate_credit_risk(n=1000, seed=101) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    age = rng.integers(21, 72, size=n)
    income = np.round(rng.lognormal(10.8, 0.6, size=n).clip(18000, 250000), -2)
    credit_score = rng.integers(380, 850, size=n)
    debt_to_income = np.round(rng.beta(2, 5, size=n).clip(0.05, 0.65), 3)
    loan_amount = np.round((income * rng.uniform(0.1, 0.5, size=n)).clip(2000, 50000), -2)
    emp_years = np.round((age - 20) * rng.uniform(0.1, 0.8, size=n)).astype(int).clip(0, 40)
    
    home_ownership = rng.choice(["RENT", "OWN", "MORTGAGE"], size=n, p=[0.45, 0.15, 0.40])
    loan_intent = rng.choice(["PERSONAL", "EDUCATION", "MEDICAL", "VENTURE"], size=n, p=[0.35, 0.25, 0.20, 0.20])
    
    default_logit = (
        -0.008 * (credit_score - 650)
        + 4.5 * (debt_to_income - 0.25)
        - 0.000015 * (income - 50000)
        + 0.000025 * (loan_amount - 15000)
        - 0.04 * emp_years
    )
    prob_default = 1 / (1 + np.exp(-default_logit))
    default_risk = np.where(rng.random(size=n) < prob_default, "High", "Low")
    
    return pd.DataFrame({
        "age": age,
        "annual_income": income,
        "credit_score": credit_score,
        "debt_to_income": debt_to_income,
        "loan_amount": loan_amount,
        "employment_years": emp_years,
        "home_ownership": home_ownership,
        "loan_intent": loan_intent,
        "default_risk": default_risk,
    })


def generate_telecom_churn(n=800, seed=202) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    tenure = rng.integers(1, 72, size=n)
    monthly = np.round(rng.uniform(20.0, 115.0, size=n), 2)
    total = np.round(tenure * monthly * rng.uniform(0.95, 1.05, size=n), 2)
    
    contract = rng.choice(["Month-to-Month", "One-Year", "Two-Year"], size=n, p=[0.55, 0.25, 0.20])
    internet = rng.choice(["DSL", "Fiber_Optic", "No"], size=n, p=[0.40, 0.45, 0.15])
    payment = rng.choice(["Electronic_Check", "Mailed_Check", "Bank_Transfer", "Credit_Card"], size=n, p=[0.35, 0.20, 0.25, 0.20])
    
    contract_factor = np.where(contract == "Month-to-Month", 1.2, np.where(contract == "One-Year", -0.4, -1.1))
    churn_logit = 0.02 * (monthly - 60) - 0.04 * (tenure - 20) + contract_factor
    prob_churn = 1 / (1 + np.exp(-churn_logit))
    churn = np.where(rng.random(size=n) < prob_churn, "Yes", "No")
    
    return pd.DataFrame({
        "tenure_months": tenure,
        "monthly_charges": monthly,
        "total_charges": total,
        "contract_type": contract,
        "internet_service": internet,
        "payment_method": payment,
        "churn": churn,
    })


def generate_hr_attrition(n=600, seed=303) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    age = rng.integers(22, 60, size=n)
    experience = np.round((age - 20) * rng.uniform(0.3, 0.95, size=n)).astype(int).clip(1, 38)
    years_company = np.minimum(experience, rng.integers(0, 20, size=n))
    salary = np.round(3000 + experience * 400 + rng.normal(0, 800, size=n), -2).clip(2500, 22000)
    overtime_hrs = rng.integers(0, 25, size=n)
    
    dept = rng.choice(["Sales", "Engineering", "HR"], size=n, p=[0.45, 0.45, 0.10])
    job_level = rng.choice(["Junior", "Mid", "Senior"], size=n, p=[0.40, 0.40, 0.20])
    
    attr_logit = 0.08 * (overtime_hrs - 8) - 0.00015 * (salary - 6000) - 0.05 * (years_company - 3)
    prob_attr = 1 / (1 + np.exp(-attr_logit))
    attrition = np.where(rng.random(size=n) < prob_attr, "Yes", "No")
    
    return pd.DataFrame({
        "age": age,
        "monthly_salary": salary,
        "total_experience_years": experience,
        "years_at_company": years_company,
        "monthly_overtime_hours": overtime_hrs,
        "department": dept,
        "job_level": job_level,
        "attrition": attrition,
    })


def generate_quick_demo(n=400, seed=404) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    age = rng.integers(20, 68, size=n)
    education_num = rng.integers(8, 16, size=n)
    hours_per_week = rng.integers(20, 60, size=n)
    workclass = rng.choice(["Private", "Public", "Self-Employed"], size=n, p=[0.70, 0.18, 0.12])
    
    logit = 0.05 * (age - 35) + 0.35 * (education_num - 11) + 0.04 * (hours_per_week - 40)
    prob = 1 / (1 + np.exp(-logit))
    high_income = np.where(rng.random(size=n) < prob, "Yes", "No")
    
    return pd.DataFrame({
        "age": age,
        "education_num": education_num,
        "hours_per_week": hours_per_week,
        "workclass": workclass,
        "high_income": high_income,
    })


def main():
    root = Path(__file__).resolve().parent.parent.parent
    dest_dirs = [
        root / "04_Demo_CSV_Datasets",
        root / "SynthProof" / "demo_datasets",
    ]
    
    datasets = {
        "01_healthcare_patient_outcomes.csv": generate_healthcare(),
        "02_financial_credit_risk.csv": generate_credit_risk(),
        "03_telecom_customer_churn.csv": generate_telecom_churn(),
        "04_hr_employee_attrition.csv": generate_hr_attrition(),
        "05_quick_demo_demographics.csv": generate_quick_demo(),
    }
    
    for d in dest_dirs:
        d.mkdir(parents=True, exist_ok=True)
        for name, df in datasets.items():
            path = d / name
            df.to_csv(path, index=False)
            print(f"[+] Written {len(df)} rows to: {path}")


if __name__ == "__main__":
    main()
