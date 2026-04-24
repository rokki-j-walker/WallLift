from pathlib import Path


class StyleAnalyzer:
    """
    Лёгкий автоанализ без отдельной тяжёлой нейросети.

    Сейчас анализирует имя файла. Позже сюда можно заменить логику на CLIP/ONNX.
    """

    def choose_model_for_image(self, image_path: Path, fallback_model: str) -> str:
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
