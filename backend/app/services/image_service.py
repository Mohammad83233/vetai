"""
Image analysis service using TensorFlow transfer learning + OpenCV.
Uses MobileNetV2 pre-trained on ImageNet for feature extraction,
with OpenCV-powered HSV color analysis, texture detection, and
custom mapping to veterinary conditions for skin and eye images.
"""

import os
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

# TensorFlow imports (lazy loaded to avoid startup delay)
_model = None
_preprocess_input = None

def _load_model():
    """Lazy load TensorFlow model to avoid startup delay."""
    global _model, _preprocess_input
    if _model is None:
        import tensorflow as tf
        from tensorflow.keras.applications import MobileNetV2
        from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
        
        # Load MobileNetV2 without top layers for feature extraction
        _model = MobileNetV2(
            weights='imagenet',
            include_top=False,
            pooling='avg',
            input_shape=(224, 224, 3)
        )
        _preprocess_input = preprocess_input
    return _model, _preprocess_input


# ─────────────────────────────────────────────────────────────────────
# Veterinary condition mappings
# ─────────────────────────────────────────────────────────────────────

SKIN_CONDITIONS = {
    "dermatitis": {
        "description": "Skin inflammation with redness and irritation",
        "species": ["dog", "cat", "rabbit", "horse", "cow", "goat", "sheep", "pig"],
        "signals": {
            "redness_pct": (0.12, 0.4),
            "edge_density": (0.10, 0.3),
            "texture_irregular": (True, 0.2),
            "high_saturation_pct": (0.10, 0.1)
        },
        "base_confidence": 0.15
    },
    "fungal_infection": {
        "description": "Circular scaly patches indicating ringworm or fungal growth",
        "species": ["dog", "cat", "rabbit", "horse", "cow", "goat"],
        "signals": {
            "edge_density": (0.12, 0.35),
            "texture_irregular": (True, 0.25),
            "low_saturation_pct": (0.15, 0.2),
            "redness_pct": (0.05, 0.2)
        },
        "base_confidence": 0.12
    },
    "hot_spots": {
        "description": "Moist, red, hairless lesions from acute dermatitis",
        "species": ["dog", "cat"],
        "signals": {
            "redness_pct": (0.20, 0.45),
            "high_saturation_pct": (0.15, 0.25),
            "brightness_mean": (0.45, 0.15),
            "edge_density": (0.08, 0.15)
        },
        "base_confidence": 0.18
    },
    "allergic_reaction": {
        "description": "Swollen areas with redness and raised bumps",
        "species": ["dog", "cat", "horse", "rabbit"],
        "signals": {
            "redness_pct": (0.15, 0.4),
            "high_saturation_pct": (0.12, 0.3),
            "brightness_mean": (0.40, 0.15),
            "texture_irregular": (True, 0.15)
        },
        "base_confidence": 0.14
    },
    "mange": {
        "description": "Hair loss with crusty, scaly skin caused by mites",
        "species": ["dog", "cat", "rabbit", "goat", "pig"],
        "signals": {
            "edge_density": (0.15, 0.35),
            "low_saturation_pct": (0.20, 0.3),
            "texture_irregular": (True, 0.2),
            "redness_pct": (0.05, 0.15)
        },
        "base_confidence": 0.16
    },
    "tumor_mass": {
        "description": "Elevated lump or growth with distinct boundary",
        "species": ["dog", "cat", "horse", "cow"],
        "signals": {
            "edge_concentration": (0.15, 0.4),
            "brightness_contrast": (0.20, 0.3),
            "edge_density": (0.10, 0.2),
            "cnn_elevated": (True, 0.1)
        },
        "base_confidence": 0.20
    }
}

EYE_CONDITIONS = {
    "conjunctivitis": {
        "description": "Red, swollen conjunctiva with possible discharge",
        "species": ["dog", "cat", "rabbit", "horse", "cow", "goat", "sheep"],
        "signals": {
            "redness_pct": (0.18, 0.45),
            "high_saturation_pct": (0.10, 0.25),
            "yellowish_pct": (0.03, 0.15),
            "edge_density": (0.05, 0.15)
        },
        "base_confidence": 0.17
    },
    "cataracts": {
        "description": "Cloudy, opaque lens reducing vision clarity",
        "species": ["dog", "cat", "horse", "rabbit"],
        "signals": {
            "whiteness_pct": (0.08, 0.35),
            "blur_score": (0.40, 0.30),
            "low_saturation_pct": (0.15, 0.20),
            "brightness_contrast": (0.15, 0.15)
        },
        "base_confidence": 0.22
    },
    "glaucoma": {
        "description": "Enlarged eye with corneal cloudiness and pain",
        "species": ["dog", "cat", "horse"],
        "signals": {
            "blur_score": (0.30, 0.30),
            "whiteness_pct": (0.05, 0.25),
            "brightness_mean": (0.35, 0.20),
            "edge_density": (0.05, 0.25)
        },
        "base_confidence": 0.19
    },
    "corneal_ulcer": {
        "description": "Painful erosion on the corneal surface",
        "species": ["dog", "cat", "horse", "cow"],
        "signals": {
            "edge_density": (0.12, 0.35),
            "texture_irregular": (True, 0.25),
            "whiteness_pct": (0.05, 0.20),
            "redness_pct": (0.08, 0.20)
        },
        "base_confidence": 0.21
    },
    "cherry_eye": {
        "description": "Prolapsed third eyelid gland appearing as red mass",
        "species": ["dog", "cat"],
        "signals": {
            "redness_pct": (0.25, 0.45),
            "high_saturation_pct": (0.15, 0.25),
            "edge_concentration": (0.10, 0.20),
            "brightness_contrast": (0.10, 0.10)
        },
        "base_confidence": 0.25
    },
    "dry_eye": {
        "description": "Insufficient tear production causing dull, irritated eyes",
        "species": ["dog", "cat"],
        "signals": {
            "low_saturation_pct": (0.20, 0.35),
            "yellowish_pct": (0.05, 0.25),
            "blur_score": (0.20, 0.20),
            "redness_pct": (0.05, 0.20)
        },
        "base_confidence": 0.15
    }
}


class ImageAnalyzer:
    """Analyzes veterinary clinical images using transfer learning + OpenCV."""
    
    UPLOAD_DIR = Path("uploads/images")
    ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    def __init__(self):
        self.upload_dir = self.UPLOAD_DIR
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    async def save_image(
        self, 
        file_content: bytes, 
        filename: str,
        image_type: str = "general"
    ) -> Dict[str, Any]:
        """Save uploaded image and return metadata."""
        # Validate file extension
        ext = Path(filename).suffix.lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            raise ValueError(f"Invalid file type. Allowed: {self.ALLOWED_EXTENSIONS}")
        
        # Validate file size
        if len(file_content) > self.MAX_FILE_SIZE:
            raise ValueError(f"File too large. Maximum size: {self.MAX_FILE_SIZE // (1024*1024)}MB")
        
        # Generate unique ID and paths
        image_id = str(uuid.uuid4())
        date_folder = datetime.now().strftime("%Y-%m-%d")
        save_dir = self.upload_dir / date_folder
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # Save original
        original_path = save_dir / f"{image_id}_original{ext}"
        with open(original_path, 'wb') as f:
            f.write(file_content)
        
        # Create thumbnail
        thumb_path = save_dir / f"{image_id}_thumb.jpg"
        self._create_thumbnail(original_path, thumb_path)
        
        # Get image dimensions
        with Image.open(original_path) as img:
            width, height = img.size
        
        return {
            "image_id": image_id,
            "original_path": str(original_path),
            "thumbnail_path": str(thumb_path),
            "image_type": image_type,
            "filename": filename,
            "file_size": len(file_content),
            "width": width,
            "height": height,
            "uploaded_at": datetime.utcnow().isoformat()
        }
    
    def _create_thumbnail(self, source_path: Path, thumb_path: Path, size: Tuple[int, int] = (200, 200)):
        """Create a thumbnail of the image."""
        with Image.open(source_path) as img:
            img.thumbnail(size, Image.Resampling.LANCZOS)
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            img.save(thumb_path, 'JPEG', quality=85)

    # ─────────────────────────────────────────────────────────────────
    # Core analysis pipeline
    # ─────────────────────────────────────────────────────────────────
    
    async def analyze_image(
        self, 
        image_path: str, 
        image_type: str = "general"
    ) -> Dict[str, Any]:
        """
        Analyze image using MobileNetV2 + OpenCV HSV/texture analysis.
        """
        # Load image with OpenCV for analysis
        cv_img = cv2.imread(image_path)
        if cv_img is None:
            raise ValueError(f"Could not read image: {image_path}")
        
        # Load and preprocess for CNN
        pil_img = self._load_and_preprocess(image_path)
        
        # Extract CNN features
        cnn_features = self._extract_cnn_features(pil_img)
        
        # Run OpenCV-based color analysis (HSV + center-region)
        color_analysis = self._analyze_colors(cv_img)
        
        # Run texture analysis (Laplacian + Sobel)
        texture_analysis = self._analyze_texture(cv_img)
        
        # CNN feature summary
        cnn_summary = self._summarize_cnn_features(cnn_features)
        
        # Merge all signals into a unified signal dict
        signals = self._build_signal_dict(color_analysis, texture_analysis, cnn_summary)
        
        # Detect conditions based on image type
        if image_type == "skin":
            detected_features, conditions = self._analyze_skin(signals)
        elif image_type == "eye":
            detected_features, conditions = self._analyze_eye(signals)
        else:
            detected_features, conditions = self._analyze_general(signals)
        
        return {
            "image_type": image_type,
            "detected_features": detected_features,
            "suggested_conditions": conditions,
            "color_analysis": color_analysis,
            "cnn_feature_summary": cnn_summary,
            "analyzed_at": datetime.utcnow().isoformat()
        }
    
    def _load_and_preprocess(self, image_path: str) -> np.ndarray:
        """Load image and preprocess for MobileNetV2."""
        img = Image.open(image_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        img = img.resize((224, 224), Image.Resampling.LANCZOS)
        return np.array(img)
    
    def _extract_cnn_features(self, img: np.ndarray) -> np.ndarray:
        """Extract features using MobileNetV2."""
        model, preprocess_input = _load_model()
        
        # Preprocess for MobileNetV2
        img_array = np.expand_dims(img, axis=0)
        img_array = preprocess_input(img_array.astype(np.float32))
        
        # Extract features
        features = model.predict(img_array, verbose=0)
        return features[0]

    # ─────────────────────────────────────────────────────────────────
    # OpenCV-powered color analysis
    # ─────────────────────────────────────────────────────────────────
    
    def _analyze_colors(self, cv_img: np.ndarray) -> Dict[str, Any]:
        """
        Analyze color distribution using HSV color space with center-region focus.
        """
        h, w = cv_img.shape[:2]
        
        # --- Center-region crop (60% of image) ---
        margin_h, margin_w = h // 5, w // 5
        center = cv_img[margin_h:h - margin_h, margin_w:w - margin_w]
        
        # Convert to HSV
        hsv_center = cv2.cvtColor(center, cv2.COLOR_BGR2HSV)
        total_pixels = hsv_center.shape[0] * hsv_center.shape[1]
        
        hue = hsv_center[:, :, 0].astype(float)
        sat = hsv_center[:, :, 1].astype(float)
        val = hsv_center[:, :, 2].astype(float)
        
        # Redness
        red_mask = ((hue <= 10) | (hue >= 170)) & (sat > 50) & (val > 40)
        redness_pct = float(np.sum(red_mask) / total_pixels)
        
        # Whiteness
        white_mask = (sat < 60) & (val > 160)
        whiteness_pct = float(np.sum(white_mask) / total_pixels)
        
        # Bluish
        blue_mask = (hue >= 90) & (hue <= 130) & (sat > 30) & (val > 40)
        bluish_pct = float(np.sum(blue_mask) / total_pixels)
        
        # Yellowish
        yellow_mask = (hue >= 15) & (hue <= 35) & (sat > 40) & (val > 60)
        yellowish_pct = float(np.sum(yellow_mask) / total_pixels)
        
        # High/Low saturation
        high_saturation_pct = float(np.sum(sat > 140) / total_pixels)
        low_saturation_pct = float(np.sum(sat < 50) / total_pixels)
        
        brightness_mean = float(np.mean(val) / 255.0)
        saturation_mean = float(np.mean(sat) / 255.0)
        
        return {
            'redness_pct': redness_pct,
            'whiteness_pct': whiteness_pct,
            'bluish_pct': bluish_pct,
            'yellowish_pct': yellowish_pct,
            'high_saturation_pct': high_saturation_pct,
            'low_saturation_pct': low_saturation_pct,
            'brightness_mean': brightness_mean,
            'saturation_mean': saturation_mean
        }

    # ─────────────────────────────────────────────────────────────────
    # OpenCV-powered texture analysis
    # ─────────────────────────────────────────────────────────────────
    
    def _analyze_texture(self, cv_img: np.ndarray) -> Dict[str, Any]:
        """
        Analyze texture using Laplacian and Sobel.
        """
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        
        # Blur score
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        lap_var = float(np.var(laplacian))
        blur_score = max(0.0, min(1.0, 1.0 - (lap_var / 2000.0)))
        
        # Edge density
        sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        edge_magnitude = np.sqrt(sobel_x**2 + sobel_y**2)
        edge_max = float(np.max(edge_magnitude)) if np.max(edge_magnitude) > 0 else 1.0
        edge_normalized = edge_magnitude / edge_max
        edge_threshold = 0.15
        edge_density = float(np.mean(edge_normalized > edge_threshold))
        
        # Edge concentration
        mid_h, mid_w = h // 2, w // 2
        quadrant_edges = [
            np.mean(edge_normalized[:mid_h, :mid_w] > edge_threshold),
            np.mean(edge_normalized[:mid_h, mid_w:] > edge_threshold),
            np.mean(edge_normalized[mid_h:, :mid_w] > edge_threshold),
            np.mean(edge_normalized[mid_h:, mid_w:] > edge_threshold)
        ]
        edge_concentration = float(np.std(quadrant_edges))
        
        # Brightness contrast
        margin_h, margin_w = h // 4, w // 4
        center = gray[margin_h:h - margin_h, margin_w:w - margin_w]
        brightness_contrast = abs(float(np.mean(center)) - float(np.mean(gray))) / 255.0
        
        # Texture irregularity
        local_std = cv2.blur(gray.astype(float), (15, 15))
        local_var = cv2.blur((gray.astype(float) - local_std)**2, (15, 15))
        texture_irregular = bool(float(np.mean(local_var)) > 800)
        
        return {
            'blur_score': round(blur_score, 4),
            'edge_density': round(edge_density, 4),
            'edge_concentration': round(edge_concentration, 4),
            'brightness_contrast': round(brightness_contrast, 4),
            'texture_irregular': texture_irregular
        }

    def _build_signal_dict(self, color, texture, cnn) -> Dict[str, Any]:
        """Merge signals for scoring."""
        return {
            'redness_pct': color.get('redness_pct', 0),
            'whiteness_pct': color.get('whiteness_pct', 0),
            'bluish_pct': color.get('bluish_pct', 0),
            'yellowish_pct': color.get('yellowish_pct', 0),
            'high_saturation_pct': color.get('high_saturation_pct', 0),
            'low_saturation_pct': color.get('low_saturation_pct', 0),
            'brightness_mean': color.get('brightness_mean', 0.5),
            'blur_score': texture.get('blur_score', 0),
            'edge_density': texture.get('edge_density', 0),
            'edge_concentration': texture.get('edge_concentration', 0),
            'brightness_contrast': texture.get('brightness_contrast', 0),
            'texture_irregular': texture.get('texture_irregular', False),
            'cnn_elevated': cnn.get('mean', 0) > 0.3
        }

    def _analyze_skin(self, signals) -> Tuple[List[str], List[Dict]]:
        detected_features = self._detect_features(signals, "skin")
        conditions = self._score_conditions(signals, SKIN_CONDITIONS, detected_features)
        return detected_features, conditions

    def _analyze_eye(self, signals) -> Tuple[List[str], List[Dict]]:
        detected_features = self._detect_features(signals, "eye")
        conditions = self._score_conditions(signals, EYE_CONDITIONS, detected_features)
        return detected_features, conditions

    def _analyze_general(self, signals) -> Tuple[List[str], List[Dict]]:
        detected_features = self._detect_features(signals, "general")
        skin_c = self._score_conditions(signals, SKIN_CONDITIONS, detected_features)
        eye_c = self._score_conditions(signals, EYE_CONDITIONS, detected_features)
        return detected_features, (skin_c + eye_c)[:5]

    def _detect_features(self, signals: Dict, context: str) -> List[str]:
        """Human-readable features."""
        features = []
        if signals['redness_pct'] > 0.08: features.append("redness_detected")
        if signals['whiteness_pct'] > 0.06: features.append("cloudiness_detected")
        if signals['yellowish_pct'] > 0.03: features.append("yellowish_discharge")
        if signals['high_saturation_pct'] > 0.10: features.append("vivid_coloration")
        if signals['low_saturation_pct'] > 0.25: features.append("washed_out_appearance")
        if signals['blur_score'] > 0.40: features.append("blurriness_or_cloudiness")
        if signals['edge_density'] > 0.12: features.append("detailed_texture")
        if signals['texture_irregular']: features.append("irregular_texture")
        if signals['edge_concentration'] > 0.08: features.append("focal_abnormality")
        if signals.get('cnn_elevated'): features.append("elevated_cnn_activation")
        return features
    
    def _score_conditions(self, signals, conditions_map, detected_features) -> List[Dict]:
        """Weighted scoring."""
        results = []
        for name, data in conditions_map.items():
            score = 0.0
            matched = []
            for sig, (thresh, weight) in data['signals'].items():
                val = signals.get(sig, 0)
                if isinstance(thresh, bool):
                    if val == thresh: 
                        score += weight
                        matched.append(sig)
                elif val >= thresh:
                    score += weight * min(val / thresh / 2, 1.0)
                    matched.append(f"{sig} ({val:.1%})")
            
            if score > 0.05:
                results.append({
                    "condition": name,
                    "matched_features": matched,
                    "confidence": round(min(0.95, data['base_confidence'] + score), 2)
                })
        results.sort(key=lambda x: x['confidence'], reverse=True)
        return results[:5]

    def _summarize_cnn_features(self, features: np.ndarray) -> Dict[str, float]:
        return {"mean": float(np.mean(features)), "std": float(np.std(features))}

    async def get_image(self, image_id: str) -> Optional[Dict[str, Any]]:
        from ..database import Database
        images = Database.get_collection("images")
        image = await images.find_one({"image_id": image_id})
        if image:
            image["_id"] = str(image["_id"])
            return image
        return None

    async def delete_image(self, image_id: str) -> bool:
        from ..database import Database
        images = Database.get_collection("images")
        image = await images.find_one({"image_id": image_id})
        if not image: return False
        for k in ['original_path', 'thumbnail_path']:
            try: os.remove(image[k])
            except: pass
        await images.delete_one({"image_id": image_id})
        return True

# Singleton instance
image_analyzer = ImageAnalyzer()
