"""
Quick test: load the DenseNet121 disease model + labels, run inference
on a synthetic 224x224 image, and print the results.
"""
import os, sys, pickle
import numpy as np

MODEL_DIR = os.path.join(os.path.dirname(__file__), 'Antigravity_Package')
MODEL_PATH = os.path.join(MODEL_DIR, 'vet_densenet_model.keras')
LABELS_PATH = os.path.join(MODEL_DIR, 'labels.pkl')

print(f"Model path: {os.path.abspath(MODEL_PATH)}")
print(f"Labels path: {os.path.abspath(LABELS_PATH)}")
print(f"Model exists: {os.path.exists(MODEL_PATH)}")
print(f"Labels exists: {os.path.exists(LABELS_PATH)}")

# Load labels (dict[str, int]: name -> index)
with open(LABELS_PATH, 'rb') as f:
    raw_labels = pickle.load(f)

# Build idx_to_class mapping (same as inference.py)
idx_to_class = {v: k for k, v in raw_labels.items()}
num_classes = len(idx_to_class)

print(f"\n--- Labels (raw type: {type(raw_labels).__name__}) ---")
print(f"Number of classes: {num_classes}")
for i in range(num_classes):
    print(f"  [{i}] {idx_to_class.get(i, 'MISSING')}")

# Load model
print("\n--- Loading DenseNet121 model ---")
import tensorflow as tf

model = tf.keras.models.load_model(MODEL_PATH)
print(f"Input shape: {model.input_shape}")
print(f"Output shape: {model.output_shape}")

# Inference on synthetic image (224x224, /255.0 preprocessing)
print("\n--- Running inference on synthetic 224x224 image ---")
dummy_img = np.random.randint(0, 255, (1, 224, 224, 3), dtype=np.uint8).astype(np.float32) / 255.0
preds = model.predict(dummy_img, verbose=0)
print(f"Prediction shape: {preds.shape}")

# Verify output size matches labels
assert preds.shape[1] == num_classes, f"MISMATCH: model outputs {preds.shape[1]} classes but labels has {num_classes}"

# Top 5
sorted_idx = np.argsort(preds[0])[::-1]
print("\nTop 5 predictions:")
for rank, idx in enumerate(sorted_idx[:5], 1):
    print(f"  {rank}. {idx_to_class.get(idx, f'class_{idx}')}: {preds[0][idx]:.4f}")

print(f"\nAll predictions sum: {np.sum(preds[0]):.4f}")
print("\n=== DenseNet121 model loaded and inference works correctly! ===")
