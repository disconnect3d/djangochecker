import contexts
import css_parser
import html_parser
import js_parser
import library
import utils

DETECTION = {}

parsers_patched = False

class SequenceError(utils.ParserError):
    pass

def process_content(content, context):
    for ph in library.REGISTRY:
        if content.find(ph) != -1:
            if ph in DETECTION:
                DETECTION[ph] += context
            else:
                DETECTION[ph] = context


def patch_parsers():
    global parsers_patched
    if parsers_patched:
        return
    else:
        parsers_patched = True
        html_parser.patch_html5lib()
        css_parser.patch_cssutils()
        js_parser.patch_pyjsparser()


def parse(content):
    content = deduplicate(content)
    patch_parsers()
    html_parser.parse_html(content)
    return check_sequences(content)


def get_placeholders(content):
    result = []
    for ph in DETECTION:
        if content.find(ph) != -1:
            result.append(ph)
    return result


def deduplicate(content):
    newdict = {}
    for ph in library.REGISTRY:
        newdict[ph] = library.REGISTRY[ph]

    for ph in newdict:
        if content.find(ph) == -1:
            continue
        parts = content.split(ph)
        if len(parts) == 2:
            continue
        output = ''
        counter = 0
        for part in parts:
            if counter == 0:
                output += part
            elif counter == 1:
                output += ph
                output += part
            else:
                output += library.duplicate_placeholder(ph)
                output += part
            counter += 1
        content = output
    return content


def check_sequences(content):
    phs = get_placeholders(content)
    for placeholder in phs:
        detected = DETECTION[placeholder]
        sanitized = library.REGISTRY[placeholder]
        value = library.VALUES[placeholder]
        match(detected, sanitized, value)
    return phs


def match(detected, sanitized, value):
    if not contexts.is_valid_sequence(detected):
        raise SequenceError("Detected context sequence is invalid " + detected)

    result_set = set([])
    for seq in sanitized:
        if contexts.is_valid_sequence(seq):
            result_set.add(seq)
        else:
            for nl in contexts.NEUTRAL_LEAFS:
                if contexts.is_valid_sequence(seq + nl):
                    result_set.add(seq + nl)

    if len(result_set) == 0:
        raise SequenceError("Invalid stored sanitizer sequence " + sanitized)

    with open("/home/user/Desktop/djangochecker_results.txt", "a") as outfile:
        if detected not in sanitized:
            outfile.write("INCORRECT;;;;")
        else:
            outfile.write("Correct;;;;")
        outfile.write("Detected: " + detected + ";;;;")
        outfile.write("Sanitized: " + str(sanitized) + ";;;;")
        outfile.write("Position: ")
        outfile.write(value.encode('utf8'))
        outfile.write(";;;;")
        outfile.write("===============\n")

    with open("/home/user/Desktop/djangochecker_times.txt", "w") as outfile:
        outfile.write("Taint tracking: " + str(library.taint_us) + "\n")
        outfile.write("HTML parsing: " + str(library.parser_us - library.js_us - library.uri_us - library.css_us) + "\n")
        outfile.write("CSS parsing: " + str(library.css_us) + "\n")
        outfile.write("JavaScript parsing: " + str(library.js_us) + "\n")
        outfile.write("URI parsing: " + str(library.uri_us) + "\n")
