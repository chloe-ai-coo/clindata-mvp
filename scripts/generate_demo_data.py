"""生成临床试验模拟数据 — 用于 MVP 演示"""

import csv
import random
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "demo_data"
DATA_DIR.mkdir(exist_ok=True)

SUBJECTS = [f"SUB-{str(i).zfill(3)}" for i in range(1, 101)]
AE_TERMS = ["头痛", "恶心", "肝功能异常", "皮疹", "疲劳", "腹泻", "转氨酶升高", "血压升高"]
LB_TESTS = ["ALT", "AST", "BIL", "CREAT", "GLUC", "WBC"]
VS_PARAMS = ["SYSBP", "DIABP", "HR", "TEMP", "WEIGHT"]
CM_DRUGS = ["Metformin", "Lisinopril", "Atorvastatin", "Omeprazole", "Aspirin"]


def generate_dm():
    """DM — 受试者人口学"""
    rows = []
    for sub in SUBJECTS:
        rows.append({
            "SUBJECTID": sub,
            "SEX": random.choice(["M", "F"]),
            "AGE": random.randint(18, 75),
            "RACE": random.choice(["Asian", "White", "Black", "Other"]),
            "ARM": random.choice(["Treatment", "Placebo"]),
            "SITEID": f"SITE-{random.randint(1, 10):02d}",
        })
    return rows


def generate_ae():
    """AE — 不良事件"""
    rows = []
    for sub in random.sample(SUBJECTS, 60):
        n_ae = random.randint(1, 4)
        for _ in range(n_ae):
            start = f"2026-{random.randint(1,6):02d}-{random.randint(1,28):02d}"
            rows.append({
                "SUBJECTID": sub,
                "AETERM": random.choice(AE_TERMS),
                "AESEV": random.choice(["MILD", "MODERATE", "SEVERE"]),
                "AESTDTC": start,
                "AEOUT": random.choice(["RECOVERED", "RECOVERING", "NOT RECOVERED", "FATAL"]),
                "AESER": random.choice(["Y", "N"]),
            })
    return rows


def generate_lb():
    """LB — 实验室检查"""
    rows = []
    for sub in random.sample(SUBJECTS, 80):
        for test in LB_TESTS:
            for visit in ["V1", "V2", "V3", "V4"]:
                base = {"ALT": 25, "AST": 22, "BIL": 12, "CREAT": 0.9, "GLUC": 95, "WBC": 7.0}
                uln = {"ALT": 40, "AST": 40, "BIL": 21, "CREAT": 1.2, "GLUC": 110, "WBC": 11.0}
                val = base[test] * random.uniform(0.5, 2.5)
                if random.random() < 0.1:
                    val = uln[test] * random.uniform(3, 8)  # 异常值
                rows.append({
                    "SUBJECTID": sub,
                    "LBTEST": test,
                    "LBORRES": round(val, 2),
                    "LBORRESU": {"ALT": "U/L", "AST": "U/L", "BIL": "μmol/L",
                                 "CREAT": "mg/dL", "GLUC": "mg/dL", "WBC": "10^3/μL"}[test],
                    "LBULN": uln[test],
                    "VISIT": visit,
                    "LBDTC": f"2026-{random.randint(1,6):02d}-{random.randint(1,28):02d}",
                })
    return rows


def generate_vs():
    """VS — 生命体征"""
    rows = []
    for sub in random.sample(SUBJECTS, 80):
        for visit in ["V1", "V2", "V3"]:
            rows.append({
                "SUBJECTID": sub,
                "VSTEST": "SYSBP",
                "VSORRES": random.randint(100, 160),
                "VSORRESU": "mmHg",
                "VISIT": visit,
            })
            rows.append({
                "SUBJECTID": sub,
                "VSTEST": "DIABP",
                "VSORRES": random.randint(60, 100),
                "VSORRESU": "mmHg",
                "VISIT": visit,
            })
            rows.append({
                "SUBJECTID": sub,
                "VSTEST": "HR",
                "VSORRES": random.randint(55, 100),
                "VSORRESU": "bpm",
                "VISIT": visit,
            })
    return rows


def generate_cm():
    """CM — 合并用药"""
    rows = []
    for sub in random.sample(SUBJECTS, 50):
        n_drugs = random.randint(1, 3)
        for _ in range(n_drugs):
            rows.append({
                "SUBJECTID": sub,
                "CMTRT": random.choice(CM_DRUGS),
                "CMDOSE": f"{random.choice([5, 10, 20, 50, 100])} mg",
                "CMSTDTC": f"2026-{random.randint(1,3):02d}-{random.randint(1,28):02d}",
                "CMENDTC": f"2026-{random.randint(4,6):02d}-{random.randint(1,28):02d}",
            })
    return rows


def write_csv(data: list[dict], name: str):
    path = DATA_DIR / f"{name}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    print(f"  ✅ {name}.csv — {len(data)} rows")
    return path


if __name__ == "__main__":
    print("🧬 生成临床试验模拟数据...")
    write_csv(generate_dm(), "DM_人口学")
    write_csv(generate_ae(), "AE_不良事件")
    write_csv(generate_lb(), "LB_实验室检查")
    write_csv(generate_vs(), "VS_生命体征")
    write_csv(generate_cm(), "CM_合并用药")
    print(f"\n📁 数据已生成到: {DATA_DIR}")
