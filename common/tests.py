from common.templatetags.functional import zip_template_filter
from common.templatetags.language import lang_emoji_template_filter


def test_it_zips():
    a = [1, 2, 3]
    b = ["a", "b", "c"]
    result = zip_template_filter(a, b)
    assert list(result) == [(1, "a"), (2, "b"), (3, "c")]


def test_it_works_for_estonian():
    assert lang_emoji_template_filter("et") == "🇪🇪"


def test_it_works_for_english():
    assert lang_emoji_template_filter("en") == "🇬🇧"
