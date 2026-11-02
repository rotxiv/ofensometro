"""
Traduce lo que ve el modelo (raíces) a lo que lee la persona (sus propias palabras).
"""

from src.nlp.lexicon import TOKEN_DISPLAY

def surface_forms(steps: dict) -> dict[str, str]:
    """raíz sin tildes -> primera palabra del usuario que la produjo."""
    forms: dict[str, str] = {}
    for word, root in zip(steps["without_stopwords"], steps["final"]):
        forms.setdefault(root, word)
    return forms

def readable(term: str, forms: dict[str, str]) -> str:
    """
    «idiot» -> «idiota»;
    «xxemojiofensivo» -> «(emoji ofensivo)»;
    los pares se traducen por partes.
    """
    return " ".join(TOKEN_DISPLAY.get(part) or forms.get(part, part) for part in term.split(" "))

def with_words(raw_terms: dict, forms: dict[str, str]) -> dict:
    """Agrega la palabra que produjo cada raíz, para que la persona lo entienda."""
    return {side: [{**item, "palabra": readable(item["termino"], forms)} for item in items]
            for side, items in raw_terms.items()}
