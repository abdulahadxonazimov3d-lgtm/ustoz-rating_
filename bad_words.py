BAD_WORDS = [
    "ahmoq", "tentak", "jinni", "it", "eshak", "savodsiz",
    "bezbet", "uyatsiz", "ablah", "iflos",
    "дурак", "идиот", "тупой", "безмозглый",
]

def has_bad_words(text: str) -> bool:
    if not text:
        return False
    low = text.lower()
    return any(word.lower() in low for word in BAD_WORDS)
