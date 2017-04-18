#!/usr/bin/env python
import contexts
import importlib
import inspect
import random
import parser
from django.http import HttpResponse
from django.template import defaultfilters
from django.template.base import Variable
from django.template.base import VariableDoesNotExist
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe

# Roles
TAINT_SOURCE = 1
TAINT_SANITIZER = 2
TAINT_SINK = 3
PARSER = 4
RESOLVER = 5

# Registry of context sequences
REGISTRY = {}
VALUES = {}

def translate_function(function):
    def wrapper(*args, **kwargs):
        result = function(*args, **kwargs)
        seqs = set()
        for arg in args:
            append_sequences(seqs, arg)
        for arg in kwargs.keys():
            append_sequences(seqs, arg)
        for arg in kwargs.values():
            append_sequences(seqs, arg)

        if seqs:
            result = translate(result, seqs)

        return result
    return wrapper


ord = translate_function(ord)
chr = translate_function(chr)

# Harmless methods
TAINT_FREE_METHODS = set([
    '__cmp__',
    '__eq__',
    '__float__',
    '__getattr__',
    '__getattribute__',
    '__init__',
    '__int__',
    '__new__',
    '__nonzero__',
    '__reduce__',
    '__reduce_ex__',
    '__str__',
    '__unicode__',
])


def get_methods_to_patch(prototype):
    methods = set(prototype.__dict__.keys())
    return methods - TAINT_FREE_METHODS


def translate_method(method):
    def wrapper(self, *args, **kwargs):
        result = method(self, *args, **kwargs)
        seqs = set()
        for arg in args:
            append_sequences(seqs, arg)
        for arg in kwargs.keys():
            append_sequences(seqs, arg)
        for arg in kwargs.values():
            append_sequences(seqs, arg)

        seqs.update(self.sequences)
        return translate(result, seqs)
    return wrapper


def is_tainted(obj):
    if not hasattr(obj, 'sequences'):
        return False
    return bool(obj.sequences)


def create_extension(prototype):
    if hasattr(prototype, "sequences"):
        return prototype

    methods = get_methods_to_patch(prototype)
    class result(prototype):
        def __new__(cl, *args, **kwargs):
            self = super(result, cl).__new__(cl, *args, **kwargs)
            self.sequences = set()

            for arg in args:
                append_sequences(self.sequences, arg)
            for arg in kwargs.keys():
                append_sequences(self.sequences, arg)
            for arg in kwargs.values():
                append_sequences(self.sequences, arg)

            return self

        def __reduce__(self):
            return (prototype, (prototype(self), ))


    for name, value in [(m, prototype.__dict__[m]) for m in methods]:
        if inspect.ismethod(value) or inspect.ismethoddescriptor(value):
            setattr(result, name, translate_method(value))

    #unicode
    if prototype == unicode:
        setattr(result, '__rmod__', lambda self, other: result.__mod__(result(other), self))

    #string
    if '__add__' in methods and '__radd__' not in methods:
        setattr(result, '__radd__', lambda self, other: result.__add__(result(other), self))

    return result


def extend(obj, sequences):
    current_type = type(obj)
    superclass = create_extension(current_type)
    res = superclass(obj)
    res.sequences.update(sequences)
    return res


def translate(obj, sequences):
    if isinstance(obj, list) or isinstance(obj, tuple) or isinstance(obj, set):
        prototype = type(obj)
        return prototype(translate(k, sequences) for k in obj)
    elif isinstance(obj, dict):
        prototype = type(obj)
        return prototype((translate(k, sequences), translate(v, sequences)) for k, v in obj.iteritems())
    elif isinstance(obj, bool):
        return obj
    elif isinstance(obj, str) or isinstance(obj, unicode) or isinstance(obj, int) or isinstance(obj, float):
        return extend(obj, sequences)
    else:
        return obj


def create_placeholder(arg, position):
    seqs = get_sequences(arg)
    if not seqs:
        return ""
    result = str()
    for i in range(0, 16):
        result += chr(random.randint(97, 122))
    REGISTRY[result] = seqs
    VALUES[result] = position
    return result


def duplicate_placeholder(val):
    result = str()
    for i in range(0, 16):
        result += chr(random.randint(97, 122))
    REGISTRY[result] = REGISTRY[val]
    VALUES[result] = VALUES[val]
    return result


def make_source(obj):
    return translate(obj, set(['']))


def sanitize(obj, sequences, contexts):
    if not sequences:
        return obj
    newseqs = set()
    for seq in sequences:
        for ctx in contexts:
            newseqs.add(seq + ctx)
    return translate(obj, newseqs)


def append_sequences(dst, src):
    if not hasattr(src, 'sequences'):
        return
    dst.update(src.sequences)


def get_sequences(*args, **kwargs):
    seqs = set()
    for arg in args:
        append_sequences(seqs, arg)
    for arg in kwargs.keys():
        append_sequences(seqs, arg)
    for arg in kwargs.values():
        append_sequences(seqs, arg)
    return seqs


def resolve(self, context, ignore_failures=False):
    if isinstance(self.var, Variable):
        try:
            from datetime import datetime
            start = datetime.now()
            obj = self.var.resolve(context)
            end = datetime.now()
            return end - start
        except VariableDoesNotExist:
            if str(self.var).find('request.GET') == 0:
                with open("/home/user/Desktop/get_args.txt", "a") as outfile:
                    outfile.write(str(self.var)[len("request.GET."):] + "\n")


from datetime import timedelta
parser_us = timedelta(seconds=0)
taint_us = timedelta(seconds=0)
js_us = timedelta(seconds=0)
css_us = timedelta(seconds=0)
uri_us = timedelta(seconds=0)


def get_wrapper(function, role, contexts=None):
    def wrapper(*args, **kwargs):
        from datetime import datetime
        start = datetime.now()
        subtraction = None
        if role == TAINT_SANITIZER:
            backup_seqs = get_sequences(*args, **kwargs)
        elif role == RESOLVER:
            subtraction = resolve(*args, **kwargs)
        elif role == TAINT_SINK:
            if str(type(args[0])) == "<class 'django.template.debug.DebugVariableNode'>" or str(type(args[0])) == "<class 'django.template.base.VariableNode'>":
                position = unicode(args[0].origin) + '@' + unicode(args[0].lineno) + '@' + unicode(args[0].order) + '@' + unicode(args[0].filter_expression)
            else:
                import traceback
                position = ''
                for line in traceback.format_stack():
                    position += line.strip()
                    position = position.replace("\n", "")
        end = datetime.now()
        diff = end - start
        if subtraction is not None:
            diff -= subtraction
        res = function(*args, **kwargs)
        start = datetime.now()
        if role == TAINT_SOURCE:
            ret = make_source(res)
        elif role == TAINT_SANITIZER:
            ret = sanitize(res, backup_seqs, contexts)
        elif role == TAINT_SINK:
            if position.find("runtime/env/lib/python2.7/site-packages/django/template/base.py") == -1:
                ret = create_placeholder(res, position) + unicode(res)
            else:
                ret = res
        elif role == PARSER:
            ret = library_handler(res)
        elif role == RESOLVER:
            ret = res
        end = datetime.now()
        diff += end - start
        if role == PARSER:
            global parser_us
            parser_us += diff
        else:
            global taint_us
            taint_us += diff
        return ret
    return wrapper


def patch(function_name, role, contexts=None):
    source, func_name = find_function(function_name)
    function = getattr(source, func_name)
    wrapper = get_wrapper(function, role, contexts)
    setattr(source, func_name, wrapper)


def find_function(function_name):
    pieces = function_name.split('.')
    try:
        for i in range(0, len(pieces)):
            subarr = pieces[0:i+1]
            module_name = '.'.join(subarr)
            mod = importlib.import_module(module_name)
            func_name = '.'.join(pieces[i+1:])
    except ImportError:
        pass

    if func_name.find('.') == -1:
        return mod, func_name
    else:
        class_obj = getattr(mod, func_name[0:func_name.find('.')])
        return class_obj, func_name[func_name.find('.')+1:]


def cleanup_placeholders(placeholders, content):
    remove = []
    for ph in placeholders:
        new_value = content.replace(ph, '')
        if new_value != content:
            remove.append(ph)
        content = new_value
    for ph in remove:
        del parser.DETECTION[ph]
        del REGISTRY[ph]
        del VALUES[ph]
    return content


def library_handler(response):
    if hasattr(response, 'content'):
        placeholders = parser.parse(response.content)
        response.content = cleanup_placeholders(placeholders, response.content)
    return response

def safe(text):
    seqs = get_sequences(text)
    if seqs:
        return translate(mark_safe(text), seqs)
    else:
        return mark_safe(text)


def patchdjango():
    patch('django.http.request.QueryDict.get', TAINT_SOURCE)
    patch('django.http.request.QueryDict.__getitem__', TAINT_SOURCE)
    patch('django.db.models.sql.compiler.SQLCompiler.patch', TAINT_SOURCE)
    patch(
        'django.utils.html.escape',
        TAINT_SANITIZER,
        set([contexts.HTML_TEXT, contexts.HTML_QUOT_ATTR, contexts.HTML_APOS_ATTR])
    )
    patch(
        'django.utils.html.escapejs',
        TAINT_SANITIZER,
        set([contexts.HTML_JS_DATA, contexts.HTML_QUOT_JS, contexts.HTML_APOS_JS])
    )
    patch(
        'urllib.urlencode',
        TAINT_SANITIZER,
        set([contexts.HTML_QUOT_URI, contexts.HTML_APOS_URI, contexts.CSS_QUOT_URI, contexts.CSS_APOS_URI])
    )
    patch(
        'django.utils.six.moves.urllib.parse.urlencode',
        TAINT_SANITIZER,
        set([contexts.HTML_QUOT_URI, contexts.HTML_APOS_URI, contexts.CSS_QUOT_URI, contexts.CSS_APOS_URI])
    )
    patch(
        'django.utils.html.conditional_escape',
        TAINT_SINK
    )
    defaultfilters.register.filter(name='safe', filter_func=stringfilter(safe), is_safe=True)
    patch(
        'django.template.debug.DebugVariableNode.render',
        TAINT_SINK
    )
    patch(
        'django.core.handlers.base.BaseHandler.get_response',
        PARSER
    )
    patch(
        'django.template.base.FilterExpression.resolve',
        RESOLVER
    )
    patch(
        'django.template.base.VariableNode.render',
        TAINT_SINK
    )
