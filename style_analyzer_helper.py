import argparse
import json
import queue
import sys
import threading
import traceback
from pathlib import Path

import customtkinter as ctk
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
    parser.add_argument("--output")
    args = parser.parse_args()

    image_path = Path(args.image)
    model_dir = Path(args.model_dir)
    fallback_model = args.fallback_model
    output_path = Path(args.output) if args.output else None

    result = run_with_progress_window(image_path, model_dir, fallback_model)
    result_json = json.dumps(result, ensure_ascii=False)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(result_json, encoding="utf-8")
    else:
        print(result_json)

    return 0


def analyze_image(image_path: Path, model_dir: Path, fallback_model: str) -> dict:
    try:
        style = detect_style(image_path, model_dir)
        model = "realesrgan-x4plus-anime" if style in ANIME_STYLE_LABELS else fallback_model
        return {"ok": True, "style": style, "model": model}
    except Exception:
        model = choose_model_by_filename(image_path, fallback_model)
        return {
            "ok": False,
            "style": "",
            "model": model,
            "error": traceback.format_exc(),
        }


def run_with_progress_window(image_path: Path, model_dir: Path, fallback_model: str) -> dict:
    results: queue.Queue[dict] = queue.Queue(maxsize=1)

    def worker():
        results.put(analyze_image(image_path, model_dir, fallback_model))

    ctk.set_appearance_mode("system")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("WallLift")
    root.resizable(False, False)

    width = 520
    height = 190
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = max(0, int((screen_width - width) / 2))
    y = max(0, int((screen_height - height) / 2))
    root.geometry(f"{width}x{height}+{x}+{y}")

    frame = ctk.CTkFrame(root, corner_radius=10)
    frame.pack(fill="both", expand=True, padx=18, pady=18)

    title = ctk.CTkLabel(
        frame,
        text="Идет анализ файла",
        font=ctk.CTkFont(size=18, weight="bold"),
        anchor="w",
    )
    title.pack(fill="x", padx=18, pady=(18, 4))

    filename = ctk.CTkLabel(
        frame,
        text=image_path.name,
        anchor="w",
        justify="left",
        wraplength=450,
    )
    filename.pack(fill="x", padx=18, pady=(0, 16))

    progress = ctk.CTkProgressBar(frame, mode="indeterminate")
    progress.pack(fill="x", padx=18, pady=(0, 12))
    progress.start()

    status = ctk.CTkLabel(frame, text="Подбираем модель изображения...", anchor="w")
    status.pack(fill="x", padx=18, pady=(0, 18))

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    def poll_result():
        try:
            result = results.get_nowait()
        except queue.Empty:
            root.after(120, poll_result)
            return

        root.result = result
        progress.stop()
        root.destroy()

    root.after(120, poll_result)
    root.mainloop()

    return getattr(root, "result", choose_model_by_filename_payload(image_path, fallback_model))


def choose_model_by_filename_payload(image_path: Path, fallback_model: str) -> dict:
    return {
        "ok": False,
        "style": "",
        "model": choose_model_by_filename(image_path, fallback_model),
        "error": "Style analysis window was closed before completion.",
    }


if __name__ == "__main__":
    sys.exit(main())
