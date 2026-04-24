import json
from dataclasses import dataclass
from pathlib import Path

from app_config import BASE_DIR


LANG_DIR = BASE_DIR / "lang"
DEFAULT_LANGUAGE = "en"


@dataclass(frozen=True)
class LanguageInfo:
    code: str
    name: str
    path: Path


class Translator:
    def __init__(self, language_code: str):
        self.language_code = language_code
        self.messages = load_language_messages(language_code)

    def t(self, key: str, **kwargs) -> str:
        text = str(self.messages.get(key, key))
        if not kwargs:
            return text

        try:
            return text.format(**kwargs)
        except Exception:
            return text


def list_languages() -> list[LanguageInfo]:
    LANG_DIR.mkdir(exist_ok=True)
    result: list[LanguageInfo] = []

    for path in sorted(LANG_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue

        code = str(data.get("language.code") or path.stem).strip()
        name = str(data.get("language.name") or code).strip()

        if code:
            result.append(LanguageInfo(code=code, name=name, path=path))

    return result


def get_available_language_codes() -> set[str]:
    return {language.code for language in list_languages()}


def normalize_language_code(language_code: str | None) -> str:
    codes = get_available_language_codes()

    if language_code in codes:
        return str(language_code)

    if DEFAULT_LANGUAGE in codes:
        return DEFAULT_LANGUAGE

    if codes:
        return sorted(codes)[0]

    return DEFAULT_LANGUAGE


def load_language_messages(language_code: str) -> dict:
    language_code = normalize_language_code(language_code)
    path = LANG_DIR / f"{language_code}.json"

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}
