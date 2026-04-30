import argparse
import json
import sys
import traceback
from pathlib import Path

from PIL import Image, ImageOps


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


def detect_style(image_path: Path, model_dir: Path) -> str:
    import torch
    from transformers import CLIPModel, CLIPProcessor

    labels = [prompt for _style, prompt in STYLE_PROMPTS]
    device = "cuda" if torch.cuda.is_available() else "cpu"
    processor = CLIPProcessor.from_pretrained(str(model_dir), local_files_only=True)
    model = CLIPModel.from_pretrained(str(model_dir), local_files_only=True)
    model.to(device)
    model.eval()

    with Image.open(image_path) as img:
        image = ImageOps.exif_transpose(img).convert("RGB")

    inputs = processor(
        text=labels,
        images=image,
        return_tensors="pt",
        padding=True,
    )
    inputs = {key: value.to(device) for key, value in inputs.items()}

    with torch.no_grad():
        outputs = model(**inputs)
        probabilities = outputs.logits_per_image.softmax(dim=1)[0]
        best_index = int(probabilities.argmax().item())

    return STYLE_PROMPTS[best_index][0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--fallback-model", required=True)
    args = parser.parse_args()

    image_path = Path(args.image)
    model_dir = Path(args.model_dir)
    fallback_model = args.fallback_model

    try:
        style = detect_style(image_path, model_dir)
        model = "realesrgan-x4plus-anime" if style in ANIME_STYLE_LABELS else fallback_model
        print(json.dumps({"ok": True, "style": style, "model": model}, ensure_ascii=False))
        return 0
    except Exception:
        model = choose_model_by_filename(image_path, fallback_model)
        print(
            json.dumps(
                {
                    "ok": False,
                    "style": "",
                    "model": model,
                    "error": traceback.format_exc(),
                },
                ensure_ascii=False,
            )
        )
        return 0


if __name__ == "__main__":
    sys.exit(main())
