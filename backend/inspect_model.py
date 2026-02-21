import joblib
import os
import json

model_dir = os.path.join(os.path.dirname(__file__), '..', 'trained_model')
output = []

files = ['animal_encoder.pkl', 'breed_encoder.pkl', 'disease_encoder.pkl', 
         'symptom_binarizer.pkl', 'vitals_scaler.pkl']

for fname in files:
    try:
        obj = joblib.load(os.path.join(model_dir, fname))
        name = fname.replace('.pkl', '')
        info = {"name": name, "type": type(obj).__name__}
        if hasattr(obj, 'classes_'):
            info["classes"] = [str(c) for c in obj.classes_]
        if hasattr(obj, 'n_features_in_'):
            info["n_features"] = int(obj.n_features_in_)
        if hasattr(obj, 'mean_'):
            info["mean"] = [float(m) for m in obj.mean_]
        if hasattr(obj, 'scale_'):
            info["scale"] = [float(s) for s in obj.scale_]
        if hasattr(obj, 'feature_names_in_'):
            info["feature_names"] = [str(f) for f in obj.feature_names_in_]
        output.append(info)
    except Exception as e:
        output.append({"name": fname, "error": str(e)})

# Model
try:
    import warnings
    warnings.filterwarnings('ignore')
    model = joblib.load(os.path.join(model_dir, 'vet_ai_model.pkl'))
    info = {"name": "vet_ai_model", "type": type(model).__name__}
    if hasattr(model, 'n_features_in_'):
        info["n_features"] = int(model.n_features_in_)
    if hasattr(model, 'feature_names_in_'):
        info["feature_names"] = [str(f) for f in model.feature_names_in_]
    output.append(info)
except Exception as e:
    output.append({"name": "vet_ai_model", "error": str(e)})

with open('model_inspection.json', 'w') as f:
    json.dump(output, f, indent=2)

print("Done! Output written to model_inspection.json")
