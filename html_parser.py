from html5lib.constants import EOF
import css_parser
import js_parser
import uri_parser
import contexts
import inspect
import library
import parser
import utils
import bs4.builder
from bs4 import BeautifulSoup
from bs4.builder import TreeBuilder
from bs4.builder._html5lib import AttrList
from bs4.builder._htmlparser import BeautifulSoupHTMLParser
from bs4.element import Comment
from bs4.element import ContentMetaAttributeValue
from bs4.element import CharsetMetaAttributeValue
from bs4.element import Doctype
from bs4.element import NavigableString
from bs4.element import Tag

URL_ATTRS = set([
    "href",
    "src",
    "dynsrc",
    "src",
    "action",
    "data",
    "codebase",
    "cite",
    "longdesc",
    "usemap",
    "classid",
    "formaction",
    "icon",
    "manifest",
    "poster",
])

class HtmlParserError(utils.ParserError):
    pass

def wrap_state(method, modus):
    def wrapper(self, *arg, **kwargs):
        current_state = self.state
        res = method(self, *arg, **kwargs)
        if self.state != current_state:
            self.currentToken["data"][-1][1] = utils.MyUnicode(self.currentToken["data"][-1][1], modus)
        return res
    return wrapper

def wrap_rearranger(method):
    def wrapper(self, tag_name, attrs):
        reg = {}
        for attr in attrs:
            if isinstance(attrs[attr], unicode) and attrs[attr] == '':
                attrs[attr] = utils.MyUnicode('', "DOUBLE")
            if hasattr(attrs[attr], "quoting"):
                reg[attr] = attrs[attr].quoting
            elif isinstance(attrs[attr], list):
                reg[attr] = attrs[attr][0].quoting
            else:
                raise HtmlParserError("Incorrect quoting of an HTML attribute in rearranger")
        res = method(self, tag_name, attrs)
        for attr in res:
            if isinstance(res[attr], list):
                new_list = []
                for item in res[attr]:
                    new_list.append(utils.MyUnicode(item, reg[attr]))
                res[attr] = new_list
        return res
    return wrapper

def wrap_setitem(method):
    def wrapper(self, name, value):
        if hasattr(value, "quoting"):
            quoting = value.quoting
        else:
            quoting = "NONE"
        method(self, name, value)
        self.element[name] = utils.MyUnicode(value, quoting)
    return wrapper

def patch_html5lib():
    try:
        from html5lib.tokenizer import HTMLTokenizer
    except ImportError:
        from html5lib._tokenizer import HTMLTokenizer
    HTMLTokenizer.attributeValueDoubleQuotedState = wrap_state(HTMLTokenizer.attributeValueDoubleQuotedState, "DOUBLE")
    HTMLTokenizer.attributeValueSingleQuotedState = wrap_state(HTMLTokenizer.attributeValueSingleQuotedState, "SINGLE")
    HTMLTokenizer.attributeValueUnQuotedState = wrap_state(HTMLTokenizer.attributeValueUnQuotedState, "NONE")
    TreeBuilder._replace_cdata_list_attribute_values = wrap_rearranger(TreeBuilder._replace_cdata_list_attribute_values)
    AttrList.__setitem__ = wrap_setitem(AttrList.__setitem__)

def parse_html(content):
    current_counts = {}
    for ph in library.REGISTRY:
        if ph in parser.DETECTION:
            current_counts[ph] = len(parser.DETECTION[ph])
        else:
            current_counts[ph] = 0
    soup = BeautifulSoup(content, 'html5lib')
    for element in soup:
        process_element(element)
    for ph in library.REGISTRY:
        if content.find(ph) != -1 and ph not in parser.DETECTION:
            parser.DETECTION[ph] = contexts.HTML_UNKNOWN
        elif content.find(ph) != -1 and len(parser.DETECTION[ph]) == current_counts[ph]:
            parser.DETECTION[ph] += contexts.HTML_UNKNOWN

def process_element(element):
    if isinstance(element, Comment):
        parser.process_content(unicode(element), contexts.HTML_COMMENT)
    elif isinstance(element, Doctype):
        parser.process_content(unicode(element), contexts.HTML_DOCTYPE)
    elif isinstance(element, NavigableString):
        if element.parent.name.lower() == "script":
            if "type" not in element.parent.attrs or element.parent.attrs["type"].lower().find("javascript") != -1:
                parser.process_content(unicode(element), contexts.HTML_JS_DATA)
                js_parser.parse_js(unicode(element))
            else:
                parser.process_content(unicode(element), contexts.HTML_UNKNOWN_SCRIPT)
        elif element.parent.name.lower() == "style":
            parser.process_content(unicode(element), contexts.HTML_CSS_DATA)
            css_parser.parse_css_stylesheet(unicode(element))
        else:
            parser.process_content(unicode(element), contexts.HTML_TEXT)
    elif isinstance(element, Tag):
        parser.process_content(element.name, contexts.HTML_TAGNAME)
        process_attributes(element)
        process_children(element)
    else:
        raise HtmlParserError("Unknown HTML element")


def process_attributes(tag):
    for attr in tag.attrs:
        parser.process_content(attr, contexts.HTML_ATTR_NAME)
        attr_value = tag.attrs[attr]
        if isinstance(attr_value, list):
            for value in attr_value:
                process_attr_value(attr, value)
        elif isinstance(attr_value, ContentMetaAttributeValue):
            if tag.attrs["http-equiv"].lower() == "refresh" and attr_value.lower().find("url=") != -1:
                process_meta_url_value(attr_value.original_value)
            else:
                process_attr_value(attr, attr_value.original_value)
        elif isinstance(attr_value, CharsetMetaAttributeValue):
            process_attr_value(attr, attr_value.original_value)
        else:
            process_attr_value(attr, attr_value)


def process_attr_value(name, value):
    if name.lower() in URL_ATTRS:
        if value.quoting == "DOUBLE":
            parser.process_content(value, contexts.HTML_QUOT_URI)
        elif value.quoting == "SINGLE":
            parser.process_content(value, contexts.HTML_APOS_URI)
        elif value.quoting == "NONE":
            parser.process_content(value, contexts.HTML_UNQUOT_URI)
        else:
            raise HtmlParserError("Wrong quoting of URI")
        uri_parser.parse_uri(value)
    elif name.lower()[0:2] == "on":
        if value.quoting == "DOUBLE":
            parser.process_content(value, contexts.HTML_QUOT_JS)
        elif value.quoting == "SINGLE":
            parser.process_content(value, contexts.HTML_APOS_JS)
        elif value.quoting == "NONE":
            parser.process_content(value, contexts.HTML_UNQUOT_JS)
        else:
            raise HtmlParserError("Wrong quoting of attr with JS")
        js_parser.parse_js(value)
    elif name.lower() == "style":
        if value.quoting == "DOUBLE":
            parser.process_content(value, contexts.HTML_QUOT_CSS)
        elif value.quoting == "SINGLE":
            parser.process_content(value, contexts.HTML_APOS_CSS)
        elif value.quoting == "NONE":
            parser.process_content(value, contexts.HTML_UNQUOT_CSS)
        else:
            raise HtmlParserError("Wrong quoting of attr with CSS")
        css_parser.parse_css_declaration_text(value)
    else:
        if value.quoting == "DOUBLE":
            parser.process_content(value, contexts.HTML_QUOT_ATTR)
        elif value.quoting == "SINGLE":
            parser.process_content(value, contexts.HTML_APOS_ATTR)
        elif value.quoting == "NONE":
            parser.process_content(value, contexts.HTML_UNQUOT_ATTR)
        else:
            raise HtmlParserError("Wrong quoting of generic HTML attr")


def process_children(tag):
    for child in tag.contents:
        process_element(child)


def process_meta_url_value(value):
    front = value[0:value.lower().find("url=")]
    back = value[value.lower().find("url=") + 4:]
    if value.quoting == "DOUBLE":
        parser.process_content(front, context.HTML_QUOT_ATTR)
        parser.process_content(back, context.HTML_QUOT_URI)
    elif value.quoting == "SINGLE":
        parser.process_content(front, context.HTML_APOS_ATTR)
        parser.process_content(back, context.HTML_APOS_URI)
    elif value.quoting == "NONE":
        parser.process_content(front, context.HTML_UNQUOT_ATTR)
        parser.process_content(back, context.HTML_UNQUOT_URI)
    else:
        raise HtmlParserError("Wrong quoting of meta refresh content")
    back = back.strip()
    back = back.strip(["'", '"'])
    uri_parser.parse_uri(back)
