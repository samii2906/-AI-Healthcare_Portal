import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import joblib, os

SAVE_DIR = os.path.join(os.path.dirname(__file__), "saved_models")
os.makedirs(SAVE_DIR, exist_ok=True)

np.random.seed(42)
N = 1000

def train_diabetes():
    data = pd.DataFrame({
        "age":         np.random.randint(20, 80, N),
        "bmi":         np.random.uniform(18, 45, N),
        "glucose":     np.random.uniform(70, 200, N),
        "blood_pressure": np.random.uniform(60, 120, N),
        "insulin":     np.random.uniform(0, 300, N),
        "cholesterol": np.random.uniform(150, 300, N),
    })
    data["target"] = ((data["glucose"] > 140) | (data["bmi"] > 30) | (data["age"] > 50)).astype(int)
    X, y = data.drop("target", axis=1), data["target"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
    model = RandomForestClassifier(n_estimators=100)
    model.fit(X_train, y_train)
    print(f"Diabetes model accuracy: {model.score(X_test, y_test):.2f}")
    joblib.dump(model, f"{SAVE_DIR}/diabetes_model.pkl")

def train_heart():
    data = pd.DataFrame({
        "age":         np.random.randint(30, 80, N),
        "cholesterol": np.random.uniform(150, 350, N),
        "blood_pressure": np.random.uniform(90, 180, N),
        "bmi":         np.random.uniform(18, 40, N),
        "smoking":     np.random.randint(0, 2, N),
        "diabetes":    np.random.randint(0, 2, N),
    })
    data["target"] = ((data["cholesterol"] > 240) | (data["blood_pressure"] > 140) | (data["smoking"] == 1)).astype(int)
    X, y = data.drop("target", axis=1), data["target"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
    model = RandomForestClassifier(n_estimators=100)
    model.fit(X_train, y_train)
    print(f"Heart disease model accuracy: {model.score(X_test, y_test):.2f}")
    joblib.dump(model, f"{SAVE_DIR}/heart_model.pkl")

def train_kidney():
    data = pd.DataFrame({
        "age":         np.random.randint(20, 80, N),
        "blood_pressure": np.random.uniform(60, 130, N),
        "glucose":     np.random.uniform(70, 200, N),
        "blood_urea":  np.random.uniform(10, 80, N),
        "creatinine":  np.random.uniform(0.5, 10, N),
        "hemoglobin":  np.random.uniform(7, 17, N),
    })
    data["target"] = ((data["creatinine"] > 4) | (data["blood_urea"] > 50) | (data["hemoglobin"] < 10)).astype(int)
    X, y = data.drop("target", axis=1), data["target"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
    model = RandomForestClassifier(n_estimators=100)
    model.fit(X_train, y_train)
    print(f"Kidney disease model accuracy: {model.score(X_test, y_test):.2f}")
    joblib.dump(model, f"{SAVE_DIR}/kidney_model.pkl")

def train_outcome():
    data = pd.DataFrame({
        "age":         np.random.randint(20, 90, N),
        "severity":    np.random.randint(1, 5, N),
        "comorbidities": np.random.randint(0, 5, N),
        "bmi":         np.random.uniform(15, 45, N),
        "blood_pressure": np.random.uniform(80, 200, N),
    })
    data["recovery"] = ((data["age"] < 60) & (data["severity"] < 3) & (data["comorbidities"] < 2)).astype(int)
    X, y = data.drop("recovery", axis=1), data["recovery"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
    model = RandomForestClassifier(n_estimators=100)
    model.fit(X_train, y_train)
    print(f"Outcome model accuracy: {model.score(X_test, y_test):.2f}")
    joblib.dump(model, f"{SAVE_DIR}/outcome_model.pkl")

if __name__ == "__main__":
    print("Training all ML models...")
    train_diabetes()
    train_heart()
    train_kidney()
    train_outcome()
    print("All models trained and saved!")