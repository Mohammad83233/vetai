"""
AI Disease Prediction Service using trained XGBoost model.
Loads the trained model and encoders from the trained_model directory
and provides disease predictions with symptom verification checklists.
"""

import os
import json
import warnings
import numpy as np
from typing import List, Dict, Any, Optional, Tuple

warnings.filterwarnings('ignore')

# Paths
MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'trained_model')

# Lazy-loaded globals
_model = None
_animal_encoder = None
_breed_encoder = None
_disease_encoder = None
_symptom_vectorizer = None
_vitals_scaler = None
_knowledge_base = None


def _load_artifacts():
    """Lazy-load all model artifacts once on first prediction."""
    global _model, _animal_encoder, _breed_encoder, _disease_encoder
    global _symptom_vectorizer, _vitals_scaler, _knowledge_base

    if _model is not None:
        return True

    try:
        import joblib

        print("Loading VetAI prediction model artifacts...")

        _animal_encoder = joblib.load(os.path.join(MODEL_DIR, 'animal_encoder.pkl'))
        _breed_encoder = joblib.load(os.path.join(MODEL_DIR, 'breed_encoder.pkl'))
        _disease_encoder = joblib.load(os.path.join(MODEL_DIR, 'disease_encoder.pkl'))
        _symptom_vectorizer = joblib.load(os.path.join(MODEL_DIR, 'symptom_binarizer.pkl'))
        _vitals_scaler = joblib.load(os.path.join(MODEL_DIR, 'vitals_scaler.pkl'))
        _model = joblib.load(os.path.join(MODEL_DIR, 'vet_ai_model.pkl'))

        # Load knowledge base (disease -> symptoms mapping)
        kb_path = os.path.join(MODEL_DIR, 'veterinary_knowledge.json')
        with open(kb_path, 'r') as f:
            kb_list = json.load(f)
        _knowledge_base = {
            entry['disease']: {
                'symptoms': entry['typical_symptoms'],
                'species': entry['species']
            }
            for entry in kb_list
        }

        print(f"SUCCESS: Model loaded: {len(_disease_encoder.classes_)} diseases, "
              f"{len(_knowledge_base)} knowledge entries")
        return True

    except Exception as e:
        print(f"ERROR: Failed to load prediction model: {e}")
        import traceback
        traceback.print_exc()
        _model = None
        return False


def _encode_species(species: str) -> int:
    """Encode species string to integer. Returns 0 if unknown."""
    # Map from app's species names to model's expected names
    species_map = {
        'dog': 'Dog', 'cat': 'Cat', 'horse': 'Horse', 'cow': 'Cow',
        'pig': 'Pig', 'rabbit': 'Rabbit', 'goat': 'Goat', 'sheep': 'Sheep'
    }
    mapped = species_map.get(species.lower(), species.title())
    try:
        return int(_animal_encoder.transform([mapped])[0])
    except (ValueError, KeyError):
        return 0


def _encode_breed(breed: str) -> int:
    """Encode breed string to integer. Returns 0 if unknown."""
    if not breed:
        return 0
    try:
        return int(_breed_encoder.transform([breed])[0])
    except (ValueError, KeyError):
        # Try title case
        try:
            return int(_breed_encoder.transform([breed.title()])[0])
        except (ValueError, KeyError):
            return 0


def _compute_vitals(
    temperature: Optional[float],
    heart_rate: Optional[float],
    duration_days: Optional[int],
    weight_kg: float,
    age_months: int,
    symptoms: List[str]
) -> np.ndarray:
    """
    Compute the 6 vitals features expected by the scaler:
    [Fever_Signal, HR_Signal, Severity_Idx, Duration_Days, Weight, Age]
    """
    # Fever_Signal: deviation from normal (around 38.5°C for most animals)
    fever_signal = (temperature - 38.5) if temperature else 0.0

    # HR_Signal: deviation from normal resting heart rate (~80 bpm avg)
    hr_signal = (heart_rate - 80.0) if heart_rate else 0.0

    # Severity_Idx: rough severity score based on number of symptoms
    severity_idx = min(len(symptoms) / 8.0, 1.0)

    # Duration_Days
    dur = float(duration_days) if duration_days else 3.0

    raw = np.array([[fever_signal, hr_signal, severity_idx, dur, weight_kg, float(age_months)]])
    return _vitals_scaler.transform(raw)


def predict_diseases(
    species: str,
    breed: Optional[str],
    symptoms: List[str],
    weight_kg: float = 10.0,
    age_months: int = 24,
    temperature: Optional[float] = None,
    heart_rate: Optional[float] = None,
    duration_days: Optional[int] = None,
    top_n: int = 3
) -> List[Dict[str, Any]]:
    """
    Predict top N diseases using KNOWLEDGE-BASE symptom matching as primary
    ranking, with optional XGBoost model boost as secondary signal.

    Strategy:
      1. Score ALL diseases in veterinary_knowledge.json by how many input
         symptoms match each disease's typical_symptoms (filtered by species).
      2. If the XGBoost model is loaded, fetch its probabilities and blend
         them as a secondary signal (20% weight).
      3. Return the top N diseases sorted by combined score.

    This ensures diseases with the most matching symptoms always surface,
    regardless of what the XGBoost model predicts.
    """
    _load_artifacts()

    # --- Ensure we have a knowledge base to work with ---
    kb = _knowledge_base
    if not kb:
        # Try loading directly
        kb_path = os.path.join(MODEL_DIR, 'veterinary_knowledge.json')
        try:
            with open(kb_path, 'r') as f:
                kb_list = json.load(f)
            kb = {
                entry['disease']: {
                    'symptoms': entry['typical_symptoms'],
                    'species': entry['species']
                }
                for entry in kb_list
            }
        except Exception:
            pass

    if not kb:
        return [{
            "disease_name": "Unable to predict - knowledge base unavailable",
            "probability": 0.0, "confidence": "low",
            "matched_symptoms": [], "verification_symptoms": [],
            "all_disease_symptoms": [], "common_symptoms": symptoms,
            "species": species, "urgency": "routine", "symptom_confidence": 0
        }]

    # --- Species mapping ---
    species_map = {
        'dog': 'Dog', 'cat': 'Cat', 'horse': 'Horse', 'cow': 'Cow',
        'pig': 'Pig', 'rabbit': 'Rabbit', 'goat': 'Goat', 'sheep': 'Sheep'
    }
    target_species = species_map.get(species.lower(), species.title())
    input_symptoms_lower = set(s.lower().strip() for s in symptoms)

    # ──────────────────────────────────────────────────────────────
    # STEP 1 — Score every disease in the knowledge base by symptom match
    # ──────────────────────────────────────────────────────────────
    kb_scores = []   # list of (disease_name, match_ratio, matched, verification, all_symptoms)

    for disease_name, info in kb.items():
        # Filter by species
        if info.get('species') != target_species:
            continue

        all_disease_symptoms = info.get('symptoms', [])
        matched = []
        verification = []
        for ds in all_disease_symptoms:
            ds_lower = ds.lower().strip()
            is_matched = any(
                ds_lower in inp or inp in ds_lower
                for inp in input_symptoms_lower
            )
            if is_matched:
                matched.append(ds)
            else:
                verification.append(ds)

        if len(matched) > 0:
            match_ratio = len(matched) / len(all_disease_symptoms) if all_disease_symptoms else 0.0
            kb_scores.append((disease_name, match_ratio, matched, verification, all_disease_symptoms))

    # ──────────────────────────────────────────────────────────────
    # STEP 2 — Optionally get XGBoost probabilities for blending
    # ──────────────────────────────────────────────────────────────
    model_probs = {}   # disease_name -> probability
    if _model is not None:
        try:
            species_encoded = _encode_species(species)
            breed_encoded = _encode_breed(breed or "")
            symptom_text = ', '.join(symptoms)
            symptom_features = _symptom_vectorizer.transform([symptom_text])
            vitals_scaled = _compute_vitals(
                temperature, heart_rate, duration_days,
                weight_kg, age_months, symptoms
            )
            from scipy.sparse import hstack, csr_matrix
            cat_features = csr_matrix(np.array([[species_encoded, breed_encoded]]))
            symptom_count = csr_matrix(np.array([[float(len(symptoms))]]))
            feature_vector = hstack([cat_features, symptom_features, symptom_count, csr_matrix(vitals_scaled)])

            probabilities = _model.predict_proba(feature_vector)[0]
            for i, prob in enumerate(probabilities):
                try:
                    dname = _disease_encoder.inverse_transform([i])[0]
                    model_probs[dname] = float(prob)
                except Exception:
                    pass
        except Exception as e:
            print(f"XGBoost boost skipped: {e}")

    # ──────────────────────────────────────────────────────────────
    # STEP 3 — Combine scores: KB match (80%) + model probability (20%)
    # ──────────────────────────────────────────────────────────────
    KB_WEIGHT = 0.80
    MODEL_WEIGHT = 0.20

    combined = []
    for disease_name, match_ratio, matched, verification, all_syms in kb_scores:
        model_prob = model_probs.get(disease_name, 0.0)
        combined_score = (match_ratio * KB_WEIGHT) + (model_prob * MODEL_WEIGHT)
        combined.append((disease_name, combined_score, match_ratio, matched, verification, all_syms))

    # Sort by combined score descending
    combined.sort(key=lambda x: x[1], reverse=True)

    # ──────────────────────────────────────────────────────────────
    # STEP 4 — Build top-N result dicts
    # ──────────────────────────────────────────────────────────────
    results = []
    for disease_name, combined_score, match_ratio, matched, verification, all_syms in combined[:top_n]:
        max_symptoms = len(all_syms) if all_syms else 8
        symptom_confidence = round((len(matched) / max_symptoms) * 100) if max_symptoms > 0 else 0

        # Confidence / urgency based on symptom match ratio
        if match_ratio >= 0.6:
            confidence = "high"
        elif match_ratio >= 0.3:
            confidence = "medium"
        else:
            confidence = "low"

        if match_ratio >= 0.7:
            urgency = "urgent"
        elif match_ratio >= 0.4:
            urgency = "soon"
        else:
            urgency = "routine"

        kb_entry = kb.get(disease_name, {})
        results.append({
            "disease_name": disease_name,
            "probability": max(0.0, min(1.0, round(combined_score, 4))),
            "confidence": confidence,
            "matched_symptoms": matched,
            "verification_symptoms": verification,
            "all_disease_symptoms": all_syms,
            "common_symptoms": all_syms,
            "species": kb_entry.get('species', species),
            "urgency": urgency,
            "symptom_confidence": symptom_confidence
        })

    # Normalize confidence scores relative to Top N
    total_prob = sum(r["probability"] for r in results)
    if total_prob > 0:
        for r in results:
            r["normalized_confidence"] = round(r["probability"] / total_prob, 4)
    else:
        for r in results:
            r["normalized_confidence"] = round(1.0 / len(results), 4) if results else 0.0

    # If no KB matches at all, fall back
    if not results:
        return _fallback_prediction(species, symptoms)

    return results


def get_followup_symptoms(predictions: List[Dict[str, Any]]) -> List[str]:
    """
    Collect remaining (unmatched) symptoms from the Top 3 predictions
    into a single deduplicated list for doctor follow-up.
    """
    seen = set()
    followup_list = []

    for pred in predictions[:3]:
        verification = pred.get("verification_symptoms", [])
        for symptom in verification:
            key = symptom.lower().strip()
            if key not in seen:
                seen.add(key)
                followup_list.append(symptom)

    return followup_list


def refine_predictions(
    predictions: List[Dict[str, Any]],
    selected_symptoms: List[str],
    symptom_weight: float = 5.0
) -> List[Dict[str, Any]]:
    """
    Refine predictions based on doctor-selected follow-up symptoms.

    For each prediction:
      matched = initial_matched_count + newly_selected_matches
      refined_score = (confidence_percentage) + (matched × symptom_weight)

    Returns updated predictions sorted by refined_score descending.
    """
    selected_lower = set(s.lower().strip() for s in selected_symptoms)
    refined = []

    for pred in predictions[:3]:
        pred_copy = dict(pred)

        all_disease_symptoms = pred_copy.get("all_disease_symptoms", [])
        initial_matched = pred_copy.get("matched_symptoms", [])
        initial_count = len(initial_matched)

        # Count newly matched symptoms from doctor selection
        new_matches = []
        for ds in all_disease_symptoms:
            ds_lower = ds.lower().strip()
            if ds_lower in selected_lower or any(
                ds_lower in sel or sel in ds_lower for sel in selected_lower
            ):
                # Only count if not already in initial matched
                if ds not in initial_matched:
                    new_matches.append(ds)

        total_matched = initial_count + len(new_matches)
        confidence_pct = pred_copy.get("probability", 0) * 100
        refined_score = confidence_pct + (total_matched * symptom_weight)

        pred_copy["refined_score"] = round(refined_score, 2)
        pred_copy["total_matched"] = total_matched
        pred_copy["new_matched_symptoms"] = new_matches
        
        max_symptoms = len(all_disease_symptoms) if all_disease_symptoms else 8
        pred_copy["symptom_confidence"] = round((total_matched / max_symptoms) * 100) if max_symptoms > 0 else 0

        # Update the matched/verification lists
        all_matched = list(initial_matched) + new_matches
        pred_copy["matched_symptoms"] = all_matched
        pred_copy["verification_symptoms"] = [
            s for s in all_disease_symptoms if s not in all_matched
        ]

        refined.append(pred_copy)

    # Sort by refined_score descending
    refined.sort(key=lambda x: x["refined_score"], reverse=True)
    return refined


def _fallback_prediction(species: str, symptoms: List[str]) -> List[Dict[str, Any]]:
    """Fallback using knowledge base matching when model fails to load."""
    if not _knowledge_base:
        # Load knowledge base directly
        kb_path = os.path.join(MODEL_DIR, 'veterinary_knowledge.json')
        try:
            with open(kb_path, 'r') as f:
                kb_list = json.load(f)
        except Exception:
            return [{
                "disease_name": "Unable to predict - model unavailable",
                "probability": 0.0,
                "confidence": "low",
                "matched_symptoms": [],
                "verification_symptoms": [],
                "all_disease_symptoms": [],
                "common_symptoms": symptoms,
                "species": species,
                "urgency": "routine",
                "symptom_confidence": 0
            }]
    else:
        kb_list = [
            {"disease": d, "typical_symptoms": v["symptoms"], "species": v["species"]}
            for d, v in _knowledge_base.items()
        ]

    # Species mapping for matching
    species_map = {
        'dog': 'Dog', 'cat': 'Cat', 'horse': 'Horse', 'cow': 'Cow',
        'pig': 'Pig', 'rabbit': 'Rabbit', 'goat': 'Goat', 'sheep': 'Sheep'
    }
    target_species = species_map.get(species.lower(), species.title())

    input_symptoms_lower = set(s.lower().strip() for s in symptoms)
    scored = []

    for entry in kb_list:
        # Optionally filter by species
        if entry['species'] != target_species:
            continue

        disease_symptoms = entry['typical_symptoms']
        matched = []
        verification = []
        for ds in disease_symptoms:
            ds_lower = ds.lower().strip()
            is_matched = any(
                ds_lower in inp or inp in ds_lower
                for inp in input_symptoms_lower
            )
            if is_matched:
                matched.append(ds)
            else:
                verification.append(ds)

        if len(matched) > 0:
            prob = len(matched) / len(disease_symptoms)
            scored.append({
                "disease_name": entry['disease'],
                "probability": round(prob, 4),
                "confidence": "high" if prob >= 0.6 else ("medium" if prob >= 0.3 else "low"),
                "matched_symptoms": matched,
                "verification_symptoms": verification,
                "all_disease_symptoms": disease_symptoms,
                "common_symptoms": disease_symptoms,
                "species": entry['species'],
                "urgency": "urgent" if prob >= 0.7 else ("soon" if prob >= 0.4 else "routine"),
                "symptom_confidence": round((len(matched) / (len(disease_symptoms) or 8)) * 100)
            })

    scored.sort(key=lambda x: x['probability'], reverse=True)
    return scored[:3] if scored else [{
        "disease_name": "No matching diseases found",
        "probability": 0.0,
        "confidence": "low",
        "matched_symptoms": [],
        "verification_symptoms": [],
        "all_disease_symptoms": [],
        "common_symptoms": symptoms,
        "species": species,
        "urgency": "routine"
    }]
