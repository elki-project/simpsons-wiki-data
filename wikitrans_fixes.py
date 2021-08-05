### This is a utility library, and not executable by itself. ###
# Bug fixes for wikitrans
import wikitrans

# Fix for wikitrans 1.3, s/list/seq/
def _fixed_parse_ref(self):
    """Parse a reference block ([...])"""
    tok = self.getkn()
    if not (tok.type == 'TEXT' and self.refstart.match(tok.content)):
        return None

    seq = []
    (ref, sep, text) = tok.content.partition(' ')
    if text:
        seq.insert(0, self._new_node(type='TEXT', content=text))

    while True:
        tok = self.getkn()
        if tok.type == 'NIL':
            return None
        elif self.is_block_end(tok):
            return None
        elif tok.type == 'DELIM':
            if tok.content == ']':
                break
            else:
                tok = self.parse_inline_delim(tok)
                if tok:
                    seq.append(tok)
                else:
                    return None
        elif tok.type == 'OTAG':
            seq.append(self.parse_tag(tok))
        else:
            seq.append(tok)

    ret = self._new_node(type='REF', ref=ref,
                         content=self._new_node(type='SEQ', content=seq))
    return ret

# Also for wikitrans 1.3, but already fixed upstream:
# https://git.gnu.org.ua/wikitrans.git/commit/?id=c785e3ad767b12a13ae75a3513ec88a4d1144210
def _fixed_tagnode_format(self):
    if self.tag == 'code':
        self.parser.nested += 1
        s = self.content.format()
        self.parser.nested -= 1
        return '<pre><code>' + s + '</code></pre>' #FIXME
    elif self.tag == 'ref':
        n = self.idx+1
        return '<sup id="cite_ref-%d" class="reference"><a name="cite_ref-%d" href=#cite_note-%d">%d</a></sup>' % (n, n, n, n)
    elif self.tag == 'references':
        s = '<div class="references">\n'
        s += '<ol class="references">\n'
        n = 0
        for ref in self.parser.references:
            n += 1
            s += ('<li id="cite_note-%d">'
                  + '<span class="mw-cite-backlink">'
                  + '<b><a href="#cite_ref-%d">^</a></b>'
                  + '</span>'
                  + '<span class="reference-text">'
                  + '%s'
                  + '</span>'
                  + '</li>\n') % (n, n, ref.content.format())
        s += '</ol>\n</div>\n'
        return s
    else:
        s = '<' + self.tag
        if self.args:
            s += ' ' + str(self.args)
        s += '>'
        s += self.content.format()
        return s + '</' + self.tag + '>'


# Unfortunately, wikitrans currently does not provide version information.
# If the bugs are fixed upstream, you may want to remove these workarounds:
wikitrans.wikimarkup.WikiMarkupParser.parse_ref = _fixed_parse_ref
wikitrans.wiki2html.HtmlTagNode.format = _fixed_tagnode_format
