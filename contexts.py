# Context scopes
HTML = 1
CSS = 2
JS = 3
URI = 4

# HTML contexts
HTML_TEXT = 'a'
HTML_COMMENT = 'b'
HTML_DOCTYPE = 'c'
HTML_TAGNAME = 'd'
HTML_JS_DATA = 'e'
HTML_CSS_DATA = 'f'
HTML_ATTR_NAME = 'g'
HTML_QUOT_URI = 'h'
HTML_APOS_URI = 'i'
HTML_UNQUOT_URI = 'j'
HTML_QUOT_CSS = 'k'
HTML_APOS_CSS = 'l'
HTML_UNQUOT_CSS = 'm'
HTML_QUOT_JS = 'n'
HTML_APOS_JS = 'o'
HTML_UNQUOT_JS = 'p'
HTML_QUOT_ATTR = 'q'
HTML_APOS_ATTR = 'r'
HTML_UNQUOT_ATTR = 's'
HTML_UNKNOWN_SCRIPT = 't'
HTML_UNKNOWN = 'u'

# CSS contexts
CSS_CHARSET = 'v'
CSS_COMMENT = 'w'
CSS_ENTITY = 'x'
CSS_MEDIA_ITEM = 'y'
CSS_PROPERTY_NAME = 'z'
CSS_PROPERTY_VALUE = 'A'
CSS_QUOT_STRING = 'B'
CSS_APOS_STRING = 'C'
CSS_QUOT_URI = 'D'
CSS_APOS_URI = 'E'
CSS_UNQUOT_URI = 'F'
CSS_UNKNOWN = 'G'

# JS contexts
JS_QUOT = 'H'
JS_APOS = 'I'
JS_CODE = 'J'

# URI contexts
URI_CONTENT_TYPE = 'K'
URI_CSS_DATA = 'L'
URI_HTML_DATA = 'M'
URI_JS_DATA = 'N'
URI_OTHER_DATA = 'O'
URI_UNKNOWN_DATA = 'P'
URI_JS = 'Q'
URI_URL = 'R'

SCOPE_MAPPING = {
    HTML_TEXT: HTML,
    HTML_COMMENT: HTML,
    HTML_DOCTYPE: HTML,
    HTML_TAGNAME: HTML,
    HTML_JS_DATA: HTML,
    HTML_CSS_DATA: HTML,
    HTML_ATTR_NAME: HTML,
    HTML_QUOT_URI: HTML,
    HTML_APOS_URI: HTML,
    HTML_UNQUOT_URI: HTML,
    HTML_QUOT_CSS: HTML,
    HTML_APOS_CSS: HTML,
    HTML_UNQUOT_CSS: HTML,
    HTML_QUOT_JS: HTML,
    HTML_APOS_JS: HTML,
    HTML_UNQUOT_JS: HTML,
    HTML_QUOT_ATTR: HTML,
    HTML_APOS_ATTR: HTML,
    HTML_UNQUOT_ATTR: HTML,
    HTML_UNKNOWN_SCRIPT: HTML,
    HTML_UNKNOWN: HTML,
    CSS_CHARSET: CSS,
    CSS_COMMENT: CSS,
    CSS_ENTITY: CSS,
    CSS_MEDIA_ITEM: CSS,
    CSS_PROPERTY_NAME: CSS,
    CSS_PROPERTY_VALUE: CSS,
    CSS_QUOT_STRING: CSS,
    CSS_APOS_STRING: CSS,
    CSS_QUOT_URI: CSS,
    CSS_APOS_URI: CSS,
    CSS_UNQUOT_URI: CSS,
    CSS_UNKNOWN: CSS,
    JS_QUOT: JS,
    JS_APOS: JS,
    JS_CODE: JS,
    URI_CONTENT_TYPE: URI,
    URI_CSS_DATA: URI,
    URI_HTML_DATA: URI,
    URI_JS_DATA: URI,
    URI_OTHER_DATA: URI,
    URI_JS: URI,
    URI_URL: URI
}

SUCCESSIONS = {
    HTML_JS_DATA: JS,
    HTML_CSS_DATA: CSS,
    HTML_QUOT_URI: URI,
    HTML_APOS_URI: URI,
    HTML_UNQUOT_URI: URI,
    HTML_QUOT_CSS: CSS,
    HTML_APOS_CSS: CSS,
    HTML_UNQUOT_CSS: CSS,
    HTML_QUOT_JS: JS,
    HTML_APOS_JS: JS,
    HTML_UNQUOT_JS: JS,
    CSS_QUOT_URI: URI,
    CSS_APOS_URI: URI,
    URI_CSS_DATA: CSS,
    URI_HTML_DATA: HTML,
    URI_JS_DATA: JS,
    URI_JS: JS
}

NEUTRAL_LEAFS = [
    CSS_PROPERTY_VALUE,
    CSS_QUOT_STRING,
    CSS_APOS_STRING,
    JS_QUOT,
    JS_APOS,
    URI_URL
]

def can_be_root(context):
    return SCOPE_MAPPING.get(context) == HTML

def is_leaf(context):
    return SUCCESSIONS.get(context) == None

def is_valid_sequence(sequence):
    if sequence == '':
        return True
    if not can_be_root(sequence[0]):
        return False
    if not is_leaf(sequence[len(sequence) - 1]):
        return False

    for i in range(0, len(sequence) - 1):
        if sequence[i] not in SUCCESSIONS:
            return False
        if SUCCESSIONS[sequence[i]] != SCOPE_MAPPING[sequence[i + 1]]:
            return False

    return True
