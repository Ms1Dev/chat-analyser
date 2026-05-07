import re
import mistune
import nh3
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

_ALLOWED_TAGS = {
    "p", "br",
    "strong", "em", "del", "s",
    "code", "pre",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li",
    "blockquote",
    "a", "img",
    "table", "thead", "tbody", "tr", "th", "td",
    "hr",
}

_ALLOWED_ATTRIBUTES = {
    "a": {"href", "title"},
    "img": {"src", "alt", "title"},
    "td": {"align"},
    "th": {"align"},
}

_markdown = mistune.create_markdown(
    escape=False,
    plugins=["strikethrough", "table"],
)


@register.filter()
def render_markdown(value):
    if not value:
        return ""
    html = _markdown(value)
    clean = nh3.clean(
        html,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRIBUTES,
        url_schemes={"http", "https", "mailto"},
    )
    return mark_safe(clean)
