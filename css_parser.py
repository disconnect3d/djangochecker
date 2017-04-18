from cssutils import helper
from cssutils import util
from cssutils.css import CSSStyleDeclaration
from cssutils.css import CSSRule
from cssutils.css import CSSStyleSheet
from cssutils.css import SelectorList
from cssutils.css import Value

import contexts
import parser
import uri_parser
import utils
import library


class CssParserError(utils.ParserError):
    pass


def wrap_string_val(function):
    def wrapper(string):
        if string[0] == '"':
            quoting = "DOUBLE"
        else:
            quoting = "SINGLE"
        string = function(string)
        return utils.MyString(string, quoting)
    return wrapper


def wrap_uri_val(function):
    def wrapper(uri):
        if uri[-2] == '"':
            quoting = "DOUBLE"
        elif uri[-2] == "'":
            quoting = "SINGLE"
        else:
            quoting = "NONE"
        uri = function(uri)
        return utils.MyString(uri, quoting)
    return wrapper

def wrap_string_token(function):
    def wrapper(self, token):
        if token[1][0] == '"':
            quoting = "DOUBLE"
        else:
            quoting = "SINGLE"
        token = function(self, token)
        if token is not None:
            return utils.MyString(token, quoting)
        else:
            return None
    return wrapper

def wrap_uri_token(function):
    def wrapper(self, token):
        if token[1][-2] == '"':
            quoting = "DOUBLE"
        elif token[1][-2] == "'":
            quoting = "SINGLE"
        else:
            quoting = "NONE"
        token = function(self, token)
        if token is not None:
            return utils.MyString(token, quoting)
        else:
            return None
    return wrapper


def patch_cssutils():
    helper.stringvalue = wrap_string_val(helper.stringvalue)
    helper.urivalue = wrap_uri_val(helper.urivalue)
    util.Base._stringtokenvalue = wrap_string_token(util.Base._stringtokenvalue)
    util.Base._uritokenvalue = wrap_uri_token(util.Base._uritokenvalue)


def parse_css_stylesheet(content):
    from datetime import datetime
    start = datetime.now()
    sheet = CSSStyleSheet()
    try:
        sheet.cssText = content
    except Exception:
        # Parsing failed
        parser.process_content(content, contexts.CSS_UNKNOWN)
    for rule in sheet.cssRules:
        parse_css_rule(rule)
    end = datetime.now()
    library.css_us += end - start


def parse_css_rule(rule):
    if rule.type == CSSRule.UNKNOWN_RULE:
        parser.process_content(rule, contexts.CSS_UNKNOWN)
    elif rule.type == CSSRule.STYLE_RULE:
        for selector in rule.selectorList:
            parse_selector(selector)
        parse_css_declaration(rule.style)
    elif rule.type == CSSRule.PAGE_RULE:
        parse_css_declaration(rule.style)
        selectorList = SelectorList(selectorText=rule.selectorText)
        for selector in selectorList:
            parse_selector(selector)
    elif rule.type == CSSRule.CHARSET_RULE:
        parser.process_content(rule.encoding, contexts.CSS_CHARSET)
    elif rule.type == CSSRule.IMPORT_RULE:
        if rule.media is not None:
            parse_media_list(rule.media)
        if rule.href.quoting == "DOUBLE":
            parser.process_content(rule.href, contexts.CSS_QUOT_URI)
        elif rule.href.quoting == "SINGLE":
            parser.process_content(rule.href, contexts.CSS_APOS_URI)
        elif rule.href.quoting == "NONE":
            parser.process_content(rule.href, contexts.CSS_UNQUOT_URI)
        else:
            raise CssParserError("Incorrectly quoted CSS import URI")
        uri_parser.parse_uri(rule.href)
    elif rule.type == CSSRule.MEDIA_RULE:
        parse_media_list(rule.media)
        for inner in rule.cssRules:
            parse_css_rule(inner)
    elif rule.type == CSSRule.FONT_FACE_RULE:
        parse_css_declaration(rule.style)
    elif rule.type == CSSRule.NAMESPACE_RULE:
        if rule.prefix is not None:
            parser.process_content(rule.prefix, contexts.CSS_QUOT_STRING)
        if rule.namespaceURI is not None:
            if rule.namespaceURI.quoting == "DOUBLE":
                parser.process_content(rule.namespaceURI, contexts.CSS_QUOT_URI)
            elif rule.namespaceURI.quoting == "SINGLE":
                parser.process_content(rule.namespaceURI, contexts.CSS_APOS_URI)
            elif rule.namespaceURI.quoting == "NONE":
                parser.process_content(rule.namespaceURI, contexts.CSS_UNQUOT_URI)
            else:
                raise CssParserError("Incorrect quoting CSS namespace URI")
            uri_parser.parse_uri(rule.namespaceURI)
    elif rule.type == CSSRule.COMMENT:
        parser.process_content(unicode(rule), contexts.CSS_COMMENT)
    elif rule.type == CSSRule.VARIABLES_RULE:
        for var in rule.variables:
            parser.process_content(rule, contexts.CSS_ENTITY)
            parse_css_declaration(rule.variables[var])
        if rule.media is not None:
            parse_media_list(rule.media)
    elif rule.type == CSSRule.MARGIN_RULE:
        parse_css_declaration(rule.style)
    else:
        raise CssParserError("Wrong CSS Rule")


def parse_media_list(media_list):
    for medium in media_list:
        parser.process_content(medium.value, contexts.CSS_MEDIA_ITEM)


def parse_selector(selector):
    parser.process_content(selector.selectorText, contexts.CSS_ENTITY)


def parse_css_declaration_text(text):
    from datetime import datetime
    start = datetime.now()
    declaration = CSSStyleDeclaration()
    try:
        declaration.cssText = text
    except Exception:
        # Parsing failed
        parser.process_content(text, contexts.CSS_UNKNOWN)
    parse_css_declaration(declaration)
    end = datetime.now()
    library.css_us += end - start

def parse_css_declaration(declaration):
    for prop in declaration:
        parse_property(prop)

def parse_property(prop):
    parser.process_content(prop.name, contexts.CSS_PROPERTY_NAME)
    parser.process_content(prop.priority, contexts.CSS_ENTITY)
    for value in prop.propertyValue:
        parse_property_value(value)

def parse_property_value(value):
    if value.type == Value.IDENT:
        parser.process_content(value.value, contexts.CSS_PROPERTY_VALUE)
    elif value.type == Value.STRING:
        if value.value.quoting == "DOUBLE":
            parser.process_content(value.value, contexts.CSS_QUOT_STRING)
        elif value.value.quoting == "SINGLE":
            parser.process_content(value.value, contexts.CSS_APOS_STRING)
        else:
            raise CssParserError("Incorrect quoting of a CSS STRING")
    elif value.type == Value.UNICODE_RANGE:
        # Data type is tuple of two integers
        pass
    elif value.type == Value.URI:
        if value.value.quoting == "DOUBLE":
            parser.process_content(value.value, contexts.CSS_QUOT_URI)
        elif value.value.quoting == "SINGLE":
            parser.process_content(value.value, contexts.CSS_APOS_URI)
        elif value.value.quoting == "NONE":
            parser.process_content(value.value, contexts.CSS_UNQUOT_URI)
        else:
            raise CssParserError("Incorrect quoting of a CSS URI")
        uri_parser.parse_uri(value.value)
    elif value.type == Value.DIMENSION:
        parser.process_content(value.dimension, contexts.CSS_ENTITY)
    elif value.type == Value.NUMBER:
        # Data type is integer
        pass
    elif value.type == Value.PERCENTAGE:
        # Data type is integer
        pass
    elif value.type == Value.COLOR_VALUE:
        # Data type is tuple of three integers
        pass
    elif value.type == Value.HASH:
        parser.process_content(value.value, contexts.CSS_ENTITY)
    elif value.type == Value.FUNCTION:
        parser.process_content(value.value, contexts.CSS_ENTITY)
    elif value.type == Value.CALC:
        parser.process_content(value.value, contexts.CSS_ENTITY)
    elif value.type == Value.VARIABLE:
        parser.process_content(value.value, contexts.CSS_ENTITY)
    else:
        raise CssParserError("Wrong CSS Value")
