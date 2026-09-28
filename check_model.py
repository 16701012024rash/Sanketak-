import joblib, warnings
warnings.simplefilter("always")
tests = [
    "Worker reported gas leak near valve station, high pressure reading, no immediate evacuation",
    "Worker was welding near a chemical tank without wearing PPE",
    "Minor cut on finger, first aid only",
]
old = joblib.load("/app/app/ml_models/sif_classifier.joblib")
print("OLD type:", type(old), "classes:", getattr(old, "classes_", "n/a"))
print(old.predict_proba(tests))

try:
    b = joblib.load("/tmp/new_model.joblib")
    print("NEW type:", type(b))
    if isinstance(b, dict):
        print("bundle keys:", list(b.keys()))
        m = b["model"]
    else:
        m = b
    print("NEW classes:", getattr(m, "classes_", "n/a"))
    print(m.predict_proba(tests))
except Exception as e:
    print("NEW FAILED:", repr(e))
