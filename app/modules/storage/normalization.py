import re
import unicodedata


_QUANTITY_PATTERN = re.compile(
    r"\b\d+([.,]\d+)?\s*(кг|kg|г|g|гр|ml|мл|l|л|шт|pcs|pack|уп|упак)\b",
    re.IGNORECASE,
)
_PUNCTUATION_PATTERN = re.compile(r"[^\w\s-]", re.UNICODE)
_SPACES_PATTERN = re.compile(r"\s+")
_STOP_WORDS = {
    "свежий", "свежая", "свежее", "свежие", "домашний",
    "домашняя", "домашнее", "домашние", "красный", "красная",
    "зеленый", "зеленая", "желтый", "желтая", "белый", "белая",
    "черный", "черная", "fresh", "organic", "bio",
}


def normalize_storage_name(value: str) -> str:
    text = unicodedata.normalize("NFKC", value).lower().replace("ё", "е")
    text = _QUANTITY_PATTERN.sub(" ", text)
    text = _PUNCTUATION_PATTERN.sub(" ", text)
    text = text.replace("-", " ")
    words = [word for word in _SPACES_PATTERN.split(text.strip()) if word and word not in _STOP_WORDS]
    return " ".join(words)
