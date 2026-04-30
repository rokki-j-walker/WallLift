import json
import subprocess
from pathlib import Path

from ai_assets import is_clip_model_available, is_style_analyzer_available
from app_config import get_clip_model_dir, get_downloaded_style_analyzer_exe


class StyleAnalyzer:
    """
    Chooses a Real-ESRGAN model through an optional external CLIP helper.

    The main WallLift build does not bundle PyTorch or Transformers. When style
    analysis is enabled, WallLift downloads a separate helper executable and
    calls it only for the images that need automatic model selection.
    """

    def __init__(self):
        self.failed = False
        self.cache: dict[Path, str] = {}

    def choose_model_for_image(self, image_path: Path, fallback_model: str) -> str:
        image_path = Path(image_path)

        if image_path in self.cache:
            return self.cache[image_path]

        try:
            model = self.detect_model(image_path, fallback_model)
        except Exception:
            model = self.choose_model_by_filename(image_path, fallback_model)

        self.cache[image_path] = model
        return model

    def detect_model(self, image_path: Path, fallback_model: str) -> str:
        if self.failed or not is_clip_model_available() or not is_style_analyzer_available():
            raise RuntimeError("Style analyzer helper or CLIP model is not available")

        helper_exe = get_downloaded_style_analyzer_exe()
        cmd = [
            str(helper_exe),
            "--image",
            str(image_path),
            "--model-dir",
            str(get_clip_model_dir()),
            "--fallback-model",
            fallback_model,
        ]

        completed = subprocess.run(
            cmd,
            cwd=str(helper_exe.parent),
            capture_output=True,
            text=True,
            shell=False,
            timeout=180,
            check=False,
        )

        if completed.returncode != 0:
            self.failed = True
            raise RuntimeError(completed.stderr or completed.stdout or "Style analyzer helper failed")

        try:
            payload = json.loads(completed.stdout.strip())
        except json.JSONDecodeError as exc:
            self.failed = True
            raise RuntimeError(f"Style analyzer helper returned invalid JSON: {completed.stdout}") from exc

        model = str(payload.get("model") or fallback_model)
        return model

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
