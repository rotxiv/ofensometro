"""
Limpieza de un comentario crudo: lo deja como texto en minúsculas sin ruido, y avisa de las
señales que encontró por el camino (gritos, ofuscación, emojis, risas).
Está pensado como una cadena de pasos pequeños; cada uno hace una sola cosa y se puede probar
por separado.
"""

import re
import unicodedata
from dataclasses import asdict, dataclass, field

import emoji

from src.nlp.lexicon import ABBREVIATIONS, DIGIT_FOR_LETTER, EMOJI_TOKEN

_LETTERS = "a-záéíóúüñ"

_URL = re.compile(r"https?://\S+|www\.\S+")
_MENTION = re.compile(r"(?<!\w)@\w+")                     # @usuario, pero no «tod@s»
_SKIN_TONE = re.compile("[\U0001F3FB-\U0001F3FF]")
_CENSORED = re.compile(r"(?<=\w)\*+(?=\w)")               # «p*ta» -> «pta»
_NUMBER = re.compile(r"\d+([.,/:]\d+)*%?")
_STRETCHED = re.compile(r"(\w)\1{2,}")                    # el español no repite una letra 3 veces
_NOT_TEXT = re.compile(rf"[^{_LETTERS}_\s]")
_MANY_SPACES = re.compile(r"\s+")
# Misma sílaba repetida («jajaja», «hahaha», «ajajaj»). «hijo» no cuenta: hi + jo son distintas.
_LAUGH = re.compile(r"\b(?:a?([jh][aeiou])\1+[jh]?)\b")
# Dígito (o grupo de dígitos) camuflado entre letras; «covid19» o «mp3» no califican.
_DIGIT_INSIDE_WORD = re.compile(rf"(?<=[{_LETTERS}])[013457]+(?=[{_LETTERS}])")
_LEET_DIGIT = re.compile(r"[013457]")
_AT_AFTER_LETTER = re.compile(rf"(?<=[{_LETTERS}])@")

SHOUT_MIN_LETTERS = 6
SHOUT_RATIO = 0.7

@dataclass
class Signals:
    """Rasgos del texto original que el modelo y la app pueden querer conocer."""
    mayusculas: bool = False
    ofuscadas: list = field(default_factory=list)
    emojis: list = field(default_factory=list)
    risas: bool = False

    def as_dict(self) -> dict:
        return asdict(self)

def strip_accents(text: str) -> str:
    """Quita tildes pero conserva la ñ («año» y «ano» son palabras distintas)."""
    shielded = text.replace("ñ", "\0")
    plain = "".join(ch for ch in unicodedata.normalize("NFD", shielded)
                    if unicodedata.category(ch) != "Mn")
    return plain.replace("\0", "ñ")

def is_shouting(text: str) -> bool:
    """Mayúsculas sostenidas («ERES UN INÚTIL»). Hay que medirlo antes de bajar a minúsculas."""
    letters = [ch for ch in text if ch.isalpha()]
    if len(letters) < SHOUT_MIN_LETTERS:
        return False
    return sum(ch.isupper() for ch in letters) / len(letters) >= SHOUT_RATIO

def _drop_social_noise(text: str) -> str:
    text = _URL.sub(" ", text)
    text = _MENTION.sub(" ", text)
    return text.replace("#", " ")


def _emojis_to_tokens(text: str, signals: Signals) -> str:
    text = _SKIN_TONE.sub("", text)
    signals.emojis = sorted({found["emoji"] for found in emoji.emoji_list(text)})

    def as_token(chars: str, _meta: dict) -> str:
        return f" {EMOJI_TOKEN.get(chars.replace(chr(0xFE0F), ''), '')} "

    return emoji.replace_emoji(text, replace=as_token)

def _undo_obfuscation(text: str, signals: Signals) -> str:
    """«1di0ta» -> «idiota», «put@» -> «puta». Anota cada palabra que corrigió."""
    restored = []
    for word in text.split(" "):
        fixed = word
        if _DIGIT_INSIDE_WORD.search(word):       # un dígito interior delata la ofuscación
            fixed = _LEET_DIGIT.sub(lambda m: DIGIT_FOR_LETTER[m.group()], word)
        fixed = _AT_AFTER_LETTER.sub("a", fixed)
        if fixed != word:
            signals.ofuscadas.append({"original": word, "normal": fixed})
        restored.append(fixed)
    return " ".join(restored)

def _laughter_to_token(text: str, signals: Signals) -> str:
    signals.risas = bool(_LAUGH.search(text))
    return _LAUGH.sub(" xxrisa ", text)

def _keep_only_words(text: str) -> str:
    text = _NUMBER.sub(" ", text)
    text = _STRETCHED.sub(r"\1", text)
    return _NOT_TEXT.sub(" ", text)

def normalize_with_signals(text: str) -> tuple[str, dict]:
    """Devuelve el texto normalizado y las señales detectadas.
    Las tildes se conservan: el lematizador las necesita."""
    signals = Signals(mayusculas=is_shouting(text))

    text = _drop_social_noise(text.lower())
    text = _emojis_to_tokens(text, signals)
    text = _CENSORED.sub("", text)
    text = _undo_obfuscation(text, signals)
    text = _laughter_to_token(text, signals)
    text = _keep_only_words(text)

    words = [ABBREVIATIONS.get(word, word) for word in text.split()]
    result = _MANY_SPACES.sub(" ", " ".join(words)).strip()
    if signals.mayusculas:
        result = f"xxmayus {result}".strip()
    return result, signals.as_dict()

def normalize(text: str) -> str:
    return normalize_with_signals(text)[0]
