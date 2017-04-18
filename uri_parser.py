import contexts
import css_parser
import html_parser
import js_parser
import parser
import urllib
import library
from base64 import b64decode

def parse_uri(content):
    from datetime import datetime
    start = datetime.now()
    # javascript: scheme
    if content.lower().find('javascript:') == 0:
        parser.process_content(content[len('javascript:'):], contexts.URI_JS)
        content = urllib.unquote(content).decode("utf8")
        js_parser.parse_js(content)

    # data: scheme
    elif content.lower().find('data:') == 0:
        content = content[len('data:'):]

        # placeholder is in content type
        if content.find(",") == -1:
            # invalid format of data: scheme
            parser.process_content(content, contexts.URI_UNKNOWN_DATA)
            return
        parser.process_content(content[0:content.find(",")], contexts.URI_CONTENT_TYPE)

        # extracts content-type, encoding and charset
        # if encoding not found, uses urlencode
        # if encoding urlencode and charset not found, uses utf8
        enctype = "urlencode"
        if content.find(";") != -1 and content.find(",") > content.find(";"):
            content_type = content[0:content.find(";")]
            encoding = content[content.find(";")+1:content.find(",")]
            # placeholder is in encoding
            parser.process_content(encoding, contexts.URI_UNKNOWN_DATA)
            if encoding.tolower() == "base64":
                enctype = "base64"
            elif encoding.tolower().find("charset=") == 0:
                charset = encoding[0, encoding.tolower().find("charset=")]
            else:
                charset = "utf8"
        else:
            content_type = content[0:content.find(",")]
            charset = "utf8"

        # decode content
        content = content[content.find(",")]
        if enctype == "base64":
            content = b64decode(content)
        else:
            content = urllib.unquote(content).decode(charset)

        # subprocess content according to the content type
        if content_type.lower() == "text/html":
            parser.process_content(content, contexts.URI_HTML_DATA)
            html_parser.parse_html(content)
        elif content_type.lower() == "text/css":
            parser.process_content(content, contexts.URI_CSS_DATA)
            css_parser.parse_css_stylesheet(content)
        elif content_type.lower() == "text/javascript" or content_type.lower() == "application/x-javascript" or content_type.lower() == "application/javascript":
            parser.process_content(content, contexts.URI_JS_DATA)
            js_parser.parse_js(content)
        else:
            parser.process_content(content, contexts.URI_OTHER_DATA)

    # other schemes
    else:
        parser.process_content(content, contexts.URI_URL)
    end = datetime.now()
    library.uri_us += end - start
