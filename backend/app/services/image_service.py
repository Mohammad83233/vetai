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
        "signals": {
            "redness_pct": (0.12, 0.4),    # min, weight
            "edge_density": (0.10, 0.3),
            "texture_irregular": (True, 0.2),
            "high_saturation_pct": (0.10, 0.1)
        },
        "base_confidence": 0.15
    },
    "fungal_infection": {
        "description": "Circular scaly patches on skin",
        "signals": {
            "edge_density": (0.12, 0.35),
            "texture_irregular": (True, 0.25),
            "low_saturation_pct": (0.15, 0.2),
            "redness_pct": (0.05, 0.2)
        },
        "base_confidence": 0.12
    },
    "hot_spots": {
        "description": "Moist, red, hairless lesions",
        "signals": {
            "redness_pct": (0.20, 0.45),
            "high_saturation_pct": (0.15, 0.25),
            "brightness_mean": (0.45, 0.15),
            "edge_density": (0.08, 0.15)
        },
        "base_confidence": 0.18
    },
    "allergic_reaction": {
        "description": "Swollen areas with redness and bumps",
        "signals": {
            "redness_pct": (0.15, 0.4),
            "high_saturation_pct": (0.12, 0.3),
            "brightness_mean": (0.40, 0.15),
            "texture_irregular": (True, 0.15)
        },
        "base_confidence": 0.14
    },
    "mange": {
        "description": "Hair loss with crusty, scaly skin",
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
        Returns detected features and suggested conditions.
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
    # OpenCV-powered color analysis (replaces old RGB-only approach)
    # ─────────────────────────────────────────────────────────────────
    
    def _analyze_colors(self, cv_img: np.ndarray) -> Dict[str, Any]:
        """
        Analyze color distribution using HSV color space with center-region focus.
        
        Returns color metrics including redness, whiteness, bluish, yellowish
        percentages, saturation stats, and brightness stats.
        """
        h, w = cv_img.shape[:2]
        
        # --- Center-region crop (60% of image) ---
        margin_h, margin_w = h // 5, w // 5
        center = cv_img[margin_h:h - margin_h, margin_w:w - margin_w]
        
        # Convert to HSV
        hsv_full = cv2.cvtColor(cv_img, cv2.COLOR_BGR2HSV)
        hsv_center = cv2.cvtColor(center, cv2.COLOR_BGR2HSV)
        
        total_pixels = hsv_center.shape[0] * hsv_center.shape[1]
        
        hue = hsv_center[:, :, 0].astype(float)       # 0-179 in OpenCV
        sat = hsv_center[:, :, 1].astype(float)       # 0-255
        val = hsv_center[:, :, 2].astype(float)       # 0-255
        
        # --- Color zone detection (center region) ---
        
        # Redness: hue 0-10 or 170-179, decent saturation
        red_mask = ((hue <= 10) | (hue >= 170)) & (sat > 50) & (val > 40)
        redness_pct = float(np.sum(red_mask) / total_pixels)
        
        # Whiteness/cloudiness: low saturation + high value
        white_mask = (sat < 60) & (val > 160)
        whiteness_pct = float(np.sum(white_mask) / total_pixels)
        
        # Bluish (can indicate certain eye conditions): hue 90-130
        blue_mask = (hue >= 90) & (hue <= 130) & (sat > 30) & (val > 40)
        bluish_pct = float(np.sum(blue_mask) / total_pixels)
        
        # Yellowish (discharge): hue 15-35
        yellow_mask = (hue >= 15) & (hue <= 35) & (sat > 40) & (val > 60)
        yellowish_pct = float(np.sum(yellow_mask) / total_pixels)
        
        # High saturation areas (vivid colors — inflammation, masses)
        high_sat_mask = sat > 140
        high_saturation_pct = float(np.sum(high_sat_mask) / total_pixels)
        
        # Low saturation areas (washed out — scarring, cloudiness)
        low_sat_mask = sat < 50
        low_saturation_pct = float(np.sum(low_sat_mask) / total_pixels)
        
        # --- Overall stats ---
        brightness_mean = float(np.mean(val) / 255.0)
        saturation_mean = float(np.mean(sat) / 255.0)
        
        # RGB channel stats (kept for backward compatibility)
        rgb = cv2.cvtColor(center, cv2.COLOR_BGR2RGB)
        channel_stats = {}
        for i, name in enumerate(['red', 'green', 'blue']):
            ch = rgb[:, :, i].astype(float)
            channel_stats[name] = {
                'mean': float(np.mean(ch)),
                'std': float(np.std(ch)),
                'max': float(np.max(ch))
            }
        
        total_brightness = sum(channel_stats[c]['mean'] for c in ['red', 'green', 'blue'])
        red_ratio = channel_stats['red']['mean'] / max(total_brightness, 1)
        
        means = [channel_stats[c]['mean'] for c in ['red', 'green', 'blue']]
        dominant_color = ['red', 'green', 'blue'][int(np.argmax(means))]
        
        return {
            # New HSV-based metrics
            'redness_pct': redness_pct,
            'whiteness_pct': whiteness_pct,
            'bluish_pct': bluish_pct,
            'yellowish_pct': yellowish_pct,
            'high_saturation_pct': high_saturation_pct,
            'low_saturation_pct': low_saturation_pct,
            'brightness_mean': brightness_mean,
            'saturation_mean': saturation_mean,
            # Legacy RGB fields (backward compat)
            'channel_stats': channel_stats,
            'red_ratio': red_ratio,
            'dominant_color': dominant_color,
            'overall_brightness': total_brightness / 3 / 255,
            'high_red_ratio': red_ratio > 0.4 or redness_pct > 0.12,
            'is_dark': total_brightness / 3 < 80,
            'is_bright': total_brightness / 3 > 200
        }

    # ─────────────────────────────────────────────────────────────────
    # OpenCV-powered texture analysis (new)
    # ─────────────────────────────────────────────────────────────────
    
    def _analyze_texture(self, cv_img: np.ndarray) -> Dict[str, Any]:
        """
        Analyze texture using Laplacian (blur) and Sobel (edges).
        
        Returns:
          - blur_score: 0-1 (higher = more blur/cloudiness)
          - edge_density: 0-1 (higher = more edges/detail)
          - edge_concentration: 0-1 (are edges concentrated in one area?)
          - brightness_contrast: 0-1 (difference between bright and dark regions)
        """
        # Convert to grayscale
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        
        # --- Blur / Cloudiness score (Laplacian variance) ---
        # Low variance = blurry/cloudy, high variance = sharp
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        lap_var = float(np.var(laplacian))
        # Normalize: <100 is very blurry, >2000 is very sharp
        blur_score = max(0.0, min(1.0, 1.0 - (lap_var / 2000.0)))
        
        # --- Edge density (Sobel) ---
        sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        edge_magnitude = np.sqrt(sobel_x**2 + sobel_y**2)
        
        # Normalize edge magnitude
        edge_max = float(np.max(edge_magnitude)) if np.max(edge_magnitude) > 0 else 1.0
        edge_normalized = edge_magnitude / edge_max
        
        # Edge density: fraction of pixels with significant edges
        edge_threshold = 0.15
        edge_density = float(np.mean(edge_normalized > edge_threshold))
        
        # --- Edge concentration ---
        # Split into quadrants and check if edges are concentrated
        mid_h, mid_w = h // 2, w // 2
        quadrant_edges = [
            np.mean(edge_normalized[:mid_h, :mid_w] > edge_threshold),
            np.mean(edge_normalized[:mid_h, mid_w:] > edge_threshold),
            np.mean(edge_normalized[mid_h:, :mid_w] > edge_threshold),
            np.mean(edge_normalized[mid_h:, mid_w:] > edge_threshold)
        ]
        edge_concentration = float(np.std(quadrant_edges))
        
        # --- Brightness contrast ---
        # Difference between center and peripheral brightness
        margin_h, margin_w = h // 4, w // 4
        center = gray[margin_h:h - margin_h, margin_w:w - margin_w]
        periphery_mean = float(np.mean(gray))
        center_mean = float(np.mean(center))
        brightness_contrast = abs(center_mean - periphery_mean) / 255.0
        
        # --- Texture irregularity ---
        # High local variance indicates irregular texture
        local_std = cv2.blur(gray.astype(float), (15, 15))
        local_var = cv2.blur((gray.astype(float) - local_std)**2, (15, 15))
        texture_irregular = bool(float(np.mean(local_var)) > 800)
        
        return {
            'blur_score': round(blur_score, 4),
            'edge_density': round(edge_density, 4),
            'edge_concentration': round(edge_concentration, 4),
            'brightness_contrast': round(brightness_contrast, 4),
            'texture_irregular': texture_irregular,
            'laplacian_variance': round(lap_var, 2)
        }

    # ─────────────────────────────────────────────────────────────────
    # Unified signal dict
    # ─────────────────────────────────────────────────────────────────
    
    def _build_signal_dict(
        self,
        color: Dict[str, Any],
        texture: Dict[str, Any],
        cnn: Dict[str, float]
    ) -> Dict[str, Any]:
        """Merge color, texture, and CNN signals into one dict for scoring."""
        return {
            # Color signals
            'redness_pct': color.get('redness_pct', 0),
            'whiteness_pct': color.get('whiteness_pct', 0),
            'bluish_pct': color.get('bluish_pct', 0),
            'yellowish_pct': color.get('yellowish_pct', 0),
            'high_saturation_pct': color.get('high_saturation_pct', 0),
            'low_saturation_pct': color.get('low_saturation_pct', 0),
            'brightness_mean': color.get('brightness_mean', 0.5),
            # Texture signals
            'blur_score': texture.get('blur_score', 0),
            'edge_density': texture.get('edge_density', 0),
            'edge_concentration': texture.get('edge_concentration', 0),
            'brightness_contrast': texture.get('brightness_contrast', 0),
            'texture_irregular': texture.get('texture_irregular', False),
            # CNN signals
            'cnn_mean': cnn.get('mean', 0),
            'cnn_std': cnn.get('std', 0),
            'cnn_elevated': cnn.get('mean', 0) > 0.3,
        }

    # ─────────────────────────────────────────────────────────────────
    # Condition analysis (skin)
    # ─────────────────────────────────────────────────────────────────
    
    def _analyze_skin(
        self,
        signals: Dict[str, Any]
    ) -> Tuple[List[str], List[Dict]]:
        """Analyze skin image using HSV + texture signals."""
        detected_features = self._detect_features(signals, context="skin")
        conditions = self._score_conditions(signals, SKIN_CONDITIONS, detected_features)
        return detected_features, conditions

    # ─────────────────────────────────────────────────────────────────
    # Condition analysis (eye)
    # ─────────────────────────────────────────────────────────────────
    
    def _analyze_eye(
        self,
        signals: Dict[str, Any]
    ) -> Tuple[List[str], List[Dict]]:
        """Analyze eye image using HSV + texture signals."""
        detected_features = self._detect_features(signals, context="eye")
        conditions = self._score_conditions(signals, EYE_CONDITIONS, detected_features)
        return detected_features, conditions

    # ─────────────────────────────────────────────────────────────────
    # Condition analysis (general)
    # ─────────────────────────────────────────────────────────────────
    
    def _analyze_general(
        self,
        signals: Dict[str, Any]
    ) -> Tuple[List[str], List[Dict]]:
        """General image analysis without specific condition mapping."""
        detected_features = self._detect_features(signals, context="general")
        
        # Score against both condition sets and merge
        skin_conditions = self._score_conditions(signals, SKIN_CONDITIONS, detected_features)
        eye_conditions = self._score_conditions(signals, EYE_CONDITIONS, detected_features)
        
        all_conditions = skin_conditions + eye_conditions
        all_conditions.sort(key=lambda x: x['confidence'], reverse=True)
        
        return detected_features, all_conditions[:5]

    # ─────────────────────────────────────────────────────────────────
    # Feature detection (human-readable features from signals)
    # ─────────────────────────────────────────────────────────────────
    
    def _detect_features(self, signals: Dict, context: str) -> List[str]:
        """Convert numeric signals into human-readable detected features."""
        features = []
        
        # Color features
        if signals['redness_pct'] > 0.08:
            features.append("redness_detected")
            if context == "eye":
                features.append("red_sclera")
        
        if signals['whiteness_pct'] > 0.06:
            features.append("cloudiness_detected")
            if context == "eye":
                features.append("lens_opacity")
                features.append("reduced_clarity")
        
        if signals['bluish_pct'] > 0.05:
            features.append("bluish_discoloration")
        
        if signals['yellowish_pct'] > 0.03:
            features.append("yellowish_discharge")
            if context == "eye":
                features.append("discharge_present")
        
        if signals['high_saturation_pct'] > 0.10:
            features.append("vivid_coloration")
        
        if signals['low_saturation_pct'] > 0.25:
            features.append("washed_out_appearance")
        
        # Texture features
        if signals['blur_score'] > 0.40:
            features.append("blurriness_or_cloudiness")
            if context == "eye":
                features.append("corneal_haze")
        
        if signals['edge_density'] > 0.12:
            features.append("detailed_texture")
            if context == "skin":
                features.append("lesion_boundaries")
        
        if signals['texture_irregular']:
            features.append("irregular_texture")
        
        if signals['edge_concentration'] > 0.08:
            features.append("focal_abnormality")
            if context == "skin":
                features.append("distinct_boundary")
        
        if signals['brightness_contrast'] > 0.12:
            features.append("contrast_variation")
        
        # CNN features
        if signals.get('cnn_elevated'):
            features.append("elevated_cnn_activation")
        
        return features
    
    # ─────────────────────────────────────────────────────────────────
    # Weighted multi-signal scoring
    # ─────────────────────────────────────────────────────────────────
    
    def _score_conditions(
        self,
        signals: Dict[str, Any],
        conditions_map: Dict[str, Dict],
        detected_features: List[str]
    ) -> List[Dict]:
        """
        Score each condition using weighted multi-signal approach.
        
        For each condition, iterate over its required signals:
          - If the signal exceeds the threshold, add (weight) to the score
          - Partial credit for signals that are close to the threshold
        
        Final confidence = base_confidence + weighted_score (capped at 0.95)
        """
        results = []
        
        for condition_name, condition_data in conditions_map.items():
            total_score = 0.0
            matched_features = []
            total_weight = 0.0
            
            for signal_name, (threshold, weight) in condition_data['signals'].items():
                total_weight += weight
                signal_value = signals.get(signal_name, 0)
                
                if isinstance(threshold, bool):
                    # Boolean signal
                    if signal_value == threshold:
                        total_score += weight
                        matched_features.append(signal_name)
                else:
                    # Numeric signal with threshold
                    if signal_value >= threshold:
                        # Full credit + bonus for exceeding threshold
                        ratio = min(signal_value / threshold, 3.0)  # cap at 3x
                        total_score += weight * min(ratio / 2, 1.0)
                        matched_features.append(f"{signal_name} ({signal_value:.1%})")
                    elif signal_value >= threshold * 0.5:
                        # Partial credit (50-100% of threshold)
                        partial = (signal_value / threshold) * 0.5
                        total_score += weight * partial
            
            if total_score > 0.05:  # Minimum threshold to report
                confidence = min(0.95, condition_data['base_confidence'] + total_score)
                
                results.append({
                    "condition": condition_name,
                    "confidence": round(confidence, 3),
                    "matched_features": matched_features,
                    "description": condition_data.get('description', ''),
                    "category": "skin" if condition_name in SKIN_CONDITIONS else "eye"
                })
        
        # Sort by confidence descending
        results.sort(key=lambda x: x['confidence'], reverse=True)
        return results[:5]
    
    def _summarize_cnn_features(self, features: np.ndarray) -> Dict[str, float]:
        """Summarize CNN feature vector statistics."""
        return {
            "mean": float(np.mean(features)),
            "std": float(np.std(features)),
            "max": float(np.max(features)),
            "min": float(np.min(features)),
            "nonzero_ratio": float(np.count_nonzero(features) / len(features))
        }
    
    async def get_image(self, image_id: str) -> Optional[Dict[str, Any]]:
        """Get image metadata by ID (searches in database)."""
        from ..database import Database
        
        images = Database.get_collection("images")
        image = await images.find_one({"image_id": image_id})
        
        if image:
            image["_id"] = str(image["_id"])
            return image
        return None
    
    async def delete_image(self, image_id: str) -> bool:
        """Delete image files and database record."""
        from ..database import Database
        
        images = Database.get_collection("images")
        image = await images.find_one({"image_id": image_id})
        
        if not image:
            return False
        
        # Delete files
        for path_key in ['original_path', 'thumbnail_path']:
            if path_key in image:
                try:
                    os.remove(image[path_key])
                except OSError:
                    pass
        
        # Delete database record
        await images.delete_one({"image_id": image_id})
        return True


# Singleton instance
image_analyzer = ImageAnalyzer()
