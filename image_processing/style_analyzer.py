from pathlib import Path
import sys

from PIL import Image, ImageOps

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai_assets import is_clip_model_available
from app_config import get_clip_model_dir


class StyleAnalyzer:
    """
    CLIP-based zero-shot classifier for choosing a Real-ESRGAN model.

    The model is loaded lazily from the app settings folder. If the model is not
    available or inference fails, the analyzer falls back to the selected model.
    """

    STYLE_PROMPTS = [
        ("photo", "a realistic photo"),
        ("photo", "a photograph of a real scene"),
        ("anime", "an anime image"),
        ("anime", "a manga or anime illustration"),
        ("illustration", "a digital illustration"),
        ("illustration", "a drawing or painting"),
        ("render", "a 3d render"),
    ]

    ANIME_STYLE_LABELS = {"anime", "illustration"}

    def __init__(self):
        self.model = None
        self.processor = None
        self.device = None
        self.failed = False
        self.cache: dict[Path, str] = {}

    def choose_model_for_image(self, image_path: Path, fallback_model: str) -> str:
        image_path = Path(image_path)

        if image_path in self.cache:
            return self.cache[image_path]

        model = fallback_model

        try:
            style = self.detect_style(image_path)
            if style in self.ANIME_STYLE_LABELS:
                model = "realesrgan-x4plus-anime"
        except Exception:
            model = self.choose_model_by_filename(image_path, fallback_model)

        self.cache[image_path] = model
        return model

    def detect_style(self, image_path: Path) -> str:
        self.ensure_loaded()

        import torch

        labels = [prompt for _style, prompt in self.STYLE_PROMPTS]

        with Image.open(image_path) as img:
            image = ImageOps.exif_transpose(img).convert("RGB")

        inputs = self.processor(
            text=labels,
            images=image,
            return_tensors="pt",
            padding=True,
        )
        inputs = {key: value.to(self.device) for key, value in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)
            probabilities = outputs.logits_per_image.softmax(dim=1)[0]
            best_index = int(probabilities.argmax().item())

        return self.STYLE_PROMPTS[best_index][0]

    def ensure_loaded(self):
        if self.model is not None and self.processor is not None:
            return

        if self.failed or not is_clip_model_available():
            raise RuntimeError("CLIP model is not available")

        try:
            import torch
            from transformers import CLIPModel, CLIPProcessor

            model_dir = str(get_clip_model_dir())
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.processor = CLIPProcessor.from_pretrained(model_dir, local_files_only=True)
            self.model = CLIPModel.from_pretrained(model_dir, local_files_only=True)
            self.model.to(self.device)
            self.model.eval()
        except Exception:
            self.failed = True
            self.model = None
            self.processor = None
            raise

    @staticmethod
    def choose_model_by_filename(image_path: Path, fallback_model: str) -> str:
        name = image_path.name.lower()
        anime_words = [
            "anime",
            "manga",
            "chibi",
            "waifu",
            "girl",
            "art",
            "illustration",
            "drawing",
        ]

        if any(word in name for word in anime_words):
            return "realesrgan-x4plus-anime"

        return fallback_model
