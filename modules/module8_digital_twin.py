import json
import random
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import os

# ── Path to the real dataset ──
DATASET_PATH = "data/ai4i2020.csv"

def load_real_dataset():
    """Load the real Kaggle industrial sensor dataset."""
    if not os.path.exists(DATASET_PATH):
        raise FileNotFoundError(
            f"Dataset not found at {DATASET_PATH}. "
            "Run: curl -L 'https://archive.ics.uci.edu/static/public/601/ai4i+2020+predictive+maintenance+dataset.zip' -o dataset.zip && unzip dataset.zip -d data/"
        )
    
    df = pd.read_csv(DATASET_PATH)
    print(f"[M8] Dataset loaded: {len(df)} rows, columns: {list(df.columns)}")
    return df

def prepare_features(df):
    """Extract the sensor columns we care about."""
    # These are the real sensor columns in the dataset
    feature_cols = [
        "Air temperature [K]",
        "Process temperature [K]", 
        "Rotational speed [rpm]",
        "Torque [Nm]",
        "Tool wear [min]"
    ]
    
    # Keep only normal operation rows for training
    # Machine failure = 0 means the machine was OK
    normal_df = df[df["Machine failure"] == 0][feature_cols]
    failed_df = df[df["Machine failure"] == 1][feature_cols]
    
    print(f"[M8] Normal readings: {len(normal_df)}")
    print(f"[M8] Failure readings: {len(failed_df)}")
    
    return normal_df, failed_df, feature_cols

def run_module8(state: dict) -> dict:
    print("[M8] Building digital twin with REAL sensor data...")

    specs     = state.get("specs") or {}
    num_valves = min(specs.get("quantity", 200), 20)  # cap at 20 for demo

    # ── Step 1: Load real dataset ──
    try:
        df = load_real_dataset()
        normal_data, failed_data, feature_cols = prepare_features(df)
        using_real_data = True
    except FileNotFoundError as e:
        print(f"[M8] WARNING: {e}")
        print("[M8] Falling back to synthetic data...")
        using_real_data = False

    # ── Step 2: Train IsolationForest on REAL normal readings ──
    if using_real_data:
        scaler = StandardScaler()
        X_train = scaler.fit_transform(normal_data)
        
        model = IsolationForest(
            n_estimators=100,
            contamination=0.05,  # expect 5% anomalies
            random_state=42
        )
        model.fit(X_train)
        print(f"[M8] Model trained on {len(X_train)} real sensor readings")

    else:
        # Fallback synthetic training
        np.random.seed(42)
        synthetic = np.random.normal(0, 1, (500, 5))
        scaler = StandardScaler()
        X_train = scaler.fit_transform(synthetic)
        model = IsolationForest(contamination=0.05, random_state=42)
        model.fit(X_train)

    # ── Step 3: Simulate current valve readings ──
    # We sample from the real dataset to simulate our valves
    valves = []

    for i in range(num_valves):
        if using_real_data:
            # 85% chance: sample a normal reading from real data
            # 15% chance: sample a failure reading from real data
            if random.random() < 0.85 and len(normal_data) > 0:
                row = normal_data.sample(1).iloc[0]
                is_known_failure = False
            else:
                row = failed_data.sample(1).iloc[0] if len(failed_data) > 0 else normal_data.sample(1).iloc[0]
                is_known_failure = True

            air_temp    = round(row["Air temperature [K]"] - 273.15, 1)  # K to C
            process_temp= round(row["Process temperature [K]"] - 273.15, 1)
            rpm         = int(row["Rotational speed [rpm]"])
            torque      = round(row["Torque [Nm]"], 1)
            tool_wear   = int(row["Tool wear [min]"])

            # Ask the model
            reading_scaled = scaler.transform(pd.DataFrame([[
             row["Air temperature [K]"],
             row["Process temperature [K]"],
             row["Rotational speed [rpm]"],
             row["Torque [Nm]"],
             row["Tool wear [min]"]
             ]], columns=feature_cols))
        else:
            # Fallback synthetic reading
            air_temp     = round(random.uniform(15, 35), 1)
            process_temp = round(random.uniform(35, 55), 1)
            rpm          = random.randint(1200, 2900)
            torque       = round(random.uniform(3, 65), 1)
            tool_wear    = random.randint(0, 250)
            is_known_failure = random.random() < 0.15

            reading_scaled = scaler.transform([[
                air_temp + 273.15,
                process_temp + 273.15,
                rpm, torque, tool_wear
            ]])

        prediction = model.predict(reading_scaled)[0]   # 1=normal, -1=anomaly
        score      = round(model.score_samples(reading_scaled)[0], 4)

        # Determine status
        if prediction == -1 or is_known_failure:
            status           = "CRITICAL"
            action           = "Immediate inspection required"
            days_to_failure  = random.randint(3, 15)
        elif tool_wear > 200 or torque > 60:
            status           = "WARNING"
            action           = "Schedule inspection within 30 days"
            days_to_failure  = random.randint(20, 60)
        else:
            status           = "OK"
            action           = "Normal operation"
            days_to_failure  = random.randint(200, 500)

        valves.append({
            "valve_id":               f"V-{i+1:03d}",
            "air_temp_c":             air_temp,
            "process_temp_c":         process_temp,
            "rpm":                    rpm,
            "torque_nm":              torque,
            "tool_wear_min":          tool_wear,
            "anomaly_score":          score,
            "data_source":            "real_kaggle" if using_real_data else "synthetic",
            "status":                 status,
            "recommended_action":     action,
            "predicted_failure_days": days_to_failure
        })

    # ── Step 4: Summary ──
    critical  = [v for v in valves if v["status"] == "CRITICAL"]
    warnings  = [v for v in valves if v["status"] == "WARNING"]
    ok_valves = [v for v in valves if v["status"] == "OK"]

    twin = {
        "data_source":     "AI4I 2020 Kaggle Dataset" if using_real_data else "Synthetic",
        "model":           "IsolationForest (sklearn)",
        "trained_on":      len(X_train),
        "total_monitored": len(valves),
        "status_summary": {
            "ok":       len(ok_valves),
            "warning":  len(warnings),
            "critical": len(critical)
        },
        "overall_health": "CRITICAL" if critical else "WARNING" if warnings else "GOOD",
        "valves": valves,
        "maintenance_schedule": [
            {
                "valve_id": v["valve_id"],
                "priority": "HIGH" if v["status"] == "CRITICAL" else "MEDIUM",
                "action":   v["recommended_action"],
                "due_in_days": v["predicted_failure_days"]
            }
            for v in valves if v["status"] != "OK"
        ]
    }

    # ── Step 5: Save ──
    os.makedirs("outputs", exist_ok=True)
    with open("outputs/digital_twin.json", "w") as f:
        json.dump(twin, f, indent=2)

    print(f"[M8] Done → {len(critical)} critical, {len(warnings)} warnings, {len(ok_valves)} ok")
    print(f"[M8] Data source: {twin['data_source']}")
    return {**state, "digital_twin": twin}