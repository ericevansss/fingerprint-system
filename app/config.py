"""Application configuration constants."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEIGHTS_DIR = PROJECT_ROOT / "weights"
FINGERNET_WEIGHTS_PATH = WEIGHTS_DIR / "fingernet.pth"
RESNET_WEIGHTS_PATH = WEIGHTS_DIR / "resnet18_fingerprint.pth"

# Model input size (width, height)
IMAGE_SIZE = (256, 256)

DEVICE_PREFERENCE = "cuda"  # will fall back to CPU if CUDA is unavailable

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}

# Model output classes in index order
FINGERNET_CLASSES = ["arch", "left_loop", "right_loop", "whorl"]

# FingerNet orientation bins (0-180 degrees)
ORIENTATION_BINS = 12

# Minutiae detection configuration
MINUTIAE_THRESHOLD = 0.35
MINUTIAE_NMS_RADIUS = 6

# Preprocessing configuration
CLAHE_CLIP_LIMIT = 2.0
CLAHE_TILE_GRID_SIZE = (8, 8)
GABOR_KERNEL_SIZE = 15
GABOR_SIGMA = 4.0
GABOR_LAMBDA = 10.0
GABOR_GAMMA = 0.5
