from pyjsparser import PyJsParser, JsSyntaxError

import contexts
import parser
import utils
import library

class JsParserError(utils.ParserError):
    pass


def wrap_literal(function):
    def wrapper(self):
        quote = self.source[self.index]
        res = function(self)
        res["value"] = quote + res["value"] + quote
        return res
    return wrapper


def wrap_state(function):
    def wrapper(self):
        self.state['inFunctionBody'] = True
        return function(self)
    return wrapper


def patch_pyjsparser():
    PyJsParser.scanStringLiteral = wrap_literal(PyJsParser.scanStringLiteral)
    PyJsParser.parseProgram = wrap_state(PyJsParser.parseProgram)


def parse_js(content):
    from datetime import datetime
    start = datetime.now()
    js_parser = PyJsParser()
    try:
        tree = js_parser.parse(content)
        for expr in tree["body"]:
            parse_expr(expr)
    except JsSyntaxError:
         parser.process_content(content, contexts.JS_CODE)
    end = datetime.now()
    library.js_us += end - start


def parse_expr(expr):
    if isinstance(expr, dict):
        if "type" in expr and expr["type"] == "Literal":
            parse_literal(expr)
        else:
            for key in expr:
                parse_expr(key)
                parse_expr(expr[key])
    elif isinstance(expr, list) or isinstance(expr, set) or isinstance(expr, tuple):
        for item in expr:
            parse_expr(item)
    elif isinstance(expr, str) or isinstance(expr, unicode):
        parser.process_content(expr, contexts.JS_CODE)


def parse_literal(literal):
    if isinstance(literal["value"], str) or isinstance(literal["value"], unicode):
        if literal["value"][0] == '"':
            parser.process_content(literal["value"], contexts.JS_QUOT)
        elif literal["value"][0] == "'":
            parser.process_content(literal["value"], contexts.JS_APOS)
        else:
            raise JsParserError("Incorrect quoting of literal")
