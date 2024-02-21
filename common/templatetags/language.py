from django import template

register = template.Library()


@register.filter(name="lang_emoji")
def lang_emoji_template_filter(lang_code: str):
    lang_emoji = {
        "en": "🇬🇧",
        "et": "🇪🇪",
    }
    return lang_emoji.get(lang_code, lang_code)
