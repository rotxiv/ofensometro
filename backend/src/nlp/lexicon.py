"""
Vocabulario propio del dominio: jerga, emojis y sustituciones de ofuscación.
Todo lo que es «datos» (y no lógica) vive aquí, para ampliarlo sin tocar el código que lo usa.
"""

SPECIAL_PREFIX = "xx"

# Escritura abreviada -> forma completa, para que «xq» y «porque» sean el mismo token.
ABBREVIATIONS = {
    "q": "que", "k": "que", "ke": "que", "x": "por", "xq": "porque", "pq": "porque",
    "pk": "porque", "tb": "también", "tmb": "también", "tbn": "también",
    "xfa": "por favor", "pa": "para", "mui": "muy", "bn": "bien",
}

# Token que reemplaza a cada grupo de emojis.
EMOJI_GROUPS = {
    "xxemojiofensivo": "🖕🤡💩🐷🐖🐀🤮🤢🤬",
    "xxemojinegativo": "😡😠👎😤😒🙄😞😢😭😫😔",
    "xxemojirisa": "😂🤣😆😹😝😜🤪",
    "xxemojipositivo": "❤😍🥰😘👍👏🙌💯🔥😊😀😃😄😁🤩💕👌🙏😎",
}

def _invert(groups: dict[str, str]) -> dict[str, str]:
    lookup = {}
    for token, members in groups.items():
        lookup.update(dict.fromkeys(members, token))
    return lookup

EMOJI_TOKEN = _invert(EMOJI_GROUPS)

# Dígitos usados para disfrazar letras: «m13rda», «p3ndejo».
DIGIT_FOR_LETTER = {"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t"}

# Nombre legible de cada token inventado (lo usa la API al mostrar términos).
TOKEN_DISPLAY = {
    "xxmayus": "(mayúsculas)",
    "xxrisa": "(risa)",
    "xxemojiofensivo": "(emoji ofensivo)",
    "xxemojinegativo": "(emoji negativo)",
    "xxemojirisa": "(emoji de risa)",
    "xxemojipositivo": "(emoji positivo)",
}
