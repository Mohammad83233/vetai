
import tensorflow as tf
import cv2
import numpy as np
import pickle
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
model = tf.keras.models.load_model(os.path.join(BASE_DIR, "vet_densenet_model.keras"))

with open(os.path.join(BASE_DIR, "labels.pkl"), "rb") as f:
    label_map = pickle.load(f)
idx_to_class = {v: k for k, v in label_map.items()}

print(f"Model Loaded! Classes: {list(label_map.keys())}")

def predict_disease(image_path, top_k=3):
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Cannot read image: {image_path}")
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = cv2.resize(img, (224, 224))
    img = np.array(img, dtype=np.float32) / 255.0
    img_batch = np.expand_dims(img, axis=0)
    preds = model.predict(img_batch, verbose=0)[0]
    top_indices = np.argsort(preds)[::-1][:top_k]
    return [(idx_to_class[i], round(float(preds[i]) * 100, 2)) for i in top_indices]
