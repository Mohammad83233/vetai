# Antigravity Vet Disease Detection
## DenseNet121 | 14 Classes

## Supported Diseases
- bacterial_dermatosis
- cataract
- cherry_eye
- conjunctivitis
- flea_allergy
- foot-and-mouth
- fungal_infections
- glaucoma
- healthy
- hypersensitivity_allergic_dermatosis
- iris_atrophy
- lumpy
- ringworm
- scabies

## Setup
pip install -r requirements.txt

## Usage
python inference.py

## Preprocessing (MUST match exactly)
1. Read image with cv2
2. Convert BGR to RGB
3. Resize to 224x224
4. Scale to 0-1 by dividing by 255
5. Add batch dimension
