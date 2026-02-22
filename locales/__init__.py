from .ru import RU
from .en import EN

LOCALES = {'ru': RU, 'en': EN}

def t(lang: str, key: str, **kwargs) -> str:
    locale = LOCALES.get(lang, RU)
    text = locale.get(key, RU.get(key, key))
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text