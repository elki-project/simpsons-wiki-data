#!/usr/bin/python3
import re, json, gzip, sys, subprocess
from lxml import etree, objectify, html
import wikitrans.wiki2text, wikitrans.wiki2html
import wikitrans_fixes # For version 1.3 currently

import os
if not os.path.exists("simpsons_pages_current.xml.7z"):
	print("You need to download a dump from https://simpsons.fandom.com/wiki/Special:Statistics", file=sys.stderr)
	sys.exit(1)

# XML namespaces - there must be some easy way of ignoring namespaces?
ns="{http://www.mediawiki.org/xml/export-0.10/}"
pagetag=ns+"page"
titletag=ns+"title"
nstag=ns+"ns"
redirtag=ns+"redirect"
revisiontag=ns+"revision"
texttag=ns+"text"
namespaces={"mw":ns}

# REs for additional WikiMarkup cleaning
reheadline = re.compile(r"^\s*=+\s*([^ =].*?)\s*=+\s*$", re.M)
regal = re.compile(r"<gallery[^<>]*?>[^<]*?</gallery>", re.S)
retab = re.compile(r"<tabber[^<>]*?>.*?</tabber>", re.S)
reref1 = re.compile(r"<ref[^<>]*?>[^<]*?</ref>")
reref2 = re.compile(r"<ref(erences)?( *[^<>]*?)?/>")
recom = re.compile(r"<!--.*?-->", re.S)
reimg = re.compile(r"^\[\[(File:[^\[\]\|]+)(?:\|[^\[\]\|]+)*\]\]$", re.M)
reslink = re.compile(r"^\[\[([^\[\]\|]+:[^\[\]\|]+)(?:\|[^\[\]\|]+)?\]\]$", re.M)
relink = re.compile(r"\[\[(?!Category:)([^\[\]\|]+)(?:\|[^\[\]\|]+)?\]\]")
retrailing = re.compile(r"(\r*\n*\[\[[A-Za-z]+:[^\[\]]+\]\]\r*\n*|\{\{[^\}]+\}\})+\r*\n*$", re.S)
rewlink = re.compile(r"\{\{[wW]\|(.*?(?:\|.*?)?)\}\}", re.S)
retempl = re.compile(r"\{\{[^{}]*?\}\}", re.S)
retempl2 = re.compile(r"\{\{[^{]*?\}\}", re.S) # more aggressive match
retable = re.compile(r"\{\|[^\{]*?\|\}", re.S)
rehtml = re.compile(r"</?([a-zA-Z]+)(?: [^>]*)?/?>")

# But: guest stars is a good example where we probably do not want this?
seeds = {
"Characters": "Characters", # including Animals!
"Guest stars": "Guest stars",
"Episodes": "Episodes",
"Merchandise": "Merchandise",
"Locations": "Locations",
"Organizations": "Locations", # often not clearly distringuishable
"Songs": "Songs",
"Gags": "Gags",
"Parodies": "Gags",
"Couch Gags": "Couch Gags",
"Vehicles": "Vehicles",
"Media": "Media", # including TV shows, books, films, magazines
"Products": "Products", # including food, toys; but could be Objects, too.
"Objects": "Objects",
"Events": "Events",
"Trivia": "Trivia",
"Catchphrases": "Trivia",
"Cultural References": "Trivia",
"References": "Trivia",
"Real World comics": "Real World comics",
"Cast and Crew": "Cast and Crew",
"Itchy & Scratchy": "Itchy & Scratchy", # circular
"Itchy & Scratchy Show episodes": "Itchy & Scratchy", # circular
}
badparts = [x.lower() for x in ["Production", "Citations", "References", "Broadcasting Information", "External Links", "Appearances", "See also", "Credits", "Gallery", "Parodies"]]
badcats = ["Disambiguation", "Stubs", "Lists", "Candidates for deletion"]

# Conserve memory when processing large XML documents:
def remove_subtree(element):
	element.clear() # Clear children
	while element.getprevious() is not None:
		element.getprevious().getparent().remove(element.getprevious())

############# Category processing
# Collect category hierarchy information in the first pass:
cathier = dict()
def load_categories(title, text):
	cat = title[9:] # Strip "Category:"
	# Extract category links:
	cats = []
	for link in reslink.finditer(text):
		c = link.group(1)
		# After a | there could be a sorting key
		if c.startswith("Category:"): cats.append(c[9:].split("|")[0].strip())
	if cats: cathier[cat] = cats

# Beware that there could be a circle in the categories, because this is a Wiki...
classmap = dict(seeds)
warned = set()
def process_categories():
	max_depth = max([len(y) for y in cathier.values()])
	for depth in range(0, max_depth):
		active = True
		while active:
			active = False
			for cat, parents in cathier.items():
				for pa in parents[:depth]:
					p = classmap.get(pa)
					if p is not None:
						if not cat in classmap:
							#print("Inferred:", cat, "->", p)
							classmap[cat] = p
							active = True
						elif cat in seeds and p == seeds.get(cat):
							if not cat in warned:
								print("Unnecessary seed or cycle?", cat, " -> ", p, " via ", pa, file=sys.stderr)
								warned.add(cat)
						break
		depth += 1

def analyzecats():
	dcat = None
	for c in cats:
		tmp = classmap.get(c)
		if tmp is not None:
			if dcat is None:
				dcat = tmp
			elif dcat != tmp:
				print(cat,"->", dcat, "or", tmp, "?")
	if dcat: print(cat, "->", dcat)

############# Cooccurrence processing
# Collect character cooccurrences
episodes=dict()
def load_cooccur(title, text):
	assert "/Appearances" in title
	episode = title.split("/")[0]
	appear = dict()
	if not text:
		print("No text", etree.tostring(element), file=sys.stderr)
		return
	text = retrailing.sub("", text)
	parts = reheadline.split(text)
	for i in range(1, len(parts), 2):
		kind = parts[i]
		m = relink.findall(parts[i+1])
		if len(m) > 0: appear[kind] = [x.strip() for x in m]
		#if not len(m): print(parts[i], parts[i+1])
	if appear: episodes[episode] = appear

############# Text processing
# Store the texts only in the first pass for later processing
texts = list()
def load_text(title, text):
	texts.append((title, text))

# Simple text content extraction from HTML, with extra newlines to separate block elements
_xpathstar = etree.XPath("*")
def text_content(n):
	buf = ""
	if n.tag in ["h1", "h2", "h3", "br", "li", "ol", "ul", "dl", "dt", "div", "p"]: buf += "\n"
	if n.text: buf += n.text
	for c in _xpathstar(n): buf += text_content(c)
	if n.tail: buf += n.tail
	return buf

# Treat "File:" as image namespace
from wikitrans.wikins import wiki_ns_re, wiki_ns
wiki_ns["en"]["File"] = "NS_IMAGE"
# Monkey patch bad serialization of delimiters (usually emph/bold) in wikitrans:
wikitrans.wiki2html.WikiDelimNode.__str__ = lambda self: ""
# Try to cleanup the markup mess obtained from wikitrans:
def cleanup(elt):
	if isinstance(elt, wikitrans.wiki2html.WikiContentNode):
		if isinstance(elt.content, list):
			elt.content = [x for x in map(cleanup, elt.content) if not x is None]
			tmp = [x.format() for x in elt.content]
			### UGLY hack for wikitrans failing to parse nested [[File:img|[[link]]]]
			while "[[" in tmp:
				start, end = tmp.index("[["), len(tmp) - 1
				for i in range(start+1, len(tmp)):
					if tmp[i] is not None and "]]" in tmp[i]:
						end = i
						break
				# print("Zapping:", *tmp[start:end+1])
				for i in range(start, end+1): tmp[i] = None
			elt.content = [a for a,b in zip(elt.content, tmp) if b is not None]
		else:
			elt.content = cleanup(elt.content)
	elif isinstance(elt, wikitrans.wiki2html.WikiMarkupParser):
		if isinstance(elt.tree, list):
			elt.tree = [x for x in map(cleanup, elt.tree) if not x is None]
			for b in elt.tree: b.format()
	return elt

from collections import defaultdict
ucats = defaultdict(list)
articles=list()
def process(title, text):
	tmp = text
	#tmp = reimg.sub(r"", tmp)
	tmp = rewlink.sub(r"[[\1]]", tmp)
	tmp = regal.sub("", tmp)
	tmp = retab.sub("", tmp)
	tmp = reref1.sub("", tmp)
	tmp = reref2.sub("", tmp)
	tmp = recom.sub("", tmp)
	tmp = re.sub(r"__TOC__", "", tmp)
	tmp = re.sub(r"<[bB][rR] */?>", "\n", tmp)
	tmp = re.sub("\u00a0", " ", tmp) # non-breaking space?
	tmp = retempl.sub("", tmp)
	tmp = retempl.sub("", tmp)
	tmp = retable.sub("", tmp) # remove wiki tables
	tmp = rehtml.sub("", tmp) # remove extra html (that wikitrans tends to escape then)
	tmp = retempl2.sub("", tmp)

	# Extract category links:
	lcats, scats = [], []
	for link in reslink.finditer(tmp):
		c = link.group(1)
		if c.startswith("Category:"):
			c = c[9:].split("|")[0].strip()
			if c in badcats: return
			lcats.append(c)
			if c in classmap: scats.append(classmap.get(c))
	# Selected categories
	scats = list(dict.fromkeys(scats)) # unique, but keep order
	# Count unhandled categories, to see if we want to extract more
	if len(scats) == 0:
		for c in lcats: ucats[c].append(title)
	# Remove trailing links, in particular categories from the text
	tmp = reslink.sub("", tmp)
	tmp = retrailing.sub("", tmp)

	## Split and re-assemble headlines, trying to ensure we have double spacing inbetween.
	parts = reheadline.split(tmp)
	buf = parts[0]
	for i in range(1, len(parts), 2):
		if parts[i].lower() in badparts: continue
		if len(parts[i+1]) < 5: continue
		buf += "=="+parts[i]+"==\n"
		buf += parts[i+1] + "\n\n"
	tmp = buf

	t = wikitrans.wiki2html.HtmlWikiMarkup(text=tmp.encode("utf-8"), lang="en", html_base="https://simpsons.fandom.com/wiki/")
	t.parse()
	if t.tree is None: return
	if len(scats) > 0 and not "Stubs" in lcats and not "Write the text of your article here" in tmp:
		buf = str(cleanup(t))
		tmp = html.document_fromstring("<html><body>%s</body></html>" % buf)
		#print(etree.tostring(tmp))
		tmp=text_content(tmp).replace("\n\n\n","\n\n").strip("\n")
		if "[[" in tmp:
			print(title, tmp)
			sys.exit(1)
		if len(tmp) >= 40:
			articles.append({"title":title, "text":tmp, "categories":lcats, "heuristic":scats[0]})


################ LOAD the data
with subprocess.Popen(["7z", "e", "-so", "simpsons_pages_current.xml.7z"], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=sys.stderr) as sevenzip:
	for event, element in etree.iterparse(sevenzip.stdout, ["end"], encoding="utf-8", recover=False, remove_blank_text=True):
		if element.tag != pagetag: continue
		title = element.find(titletag)
		if title is None:
			print("No title", etree.tostring(element), file=sys.stderr)
			remove_subtree(element)
			continue
		# Skip redirects
		if element.find(redirtag) is not None:
			remove_subtree(element)
			continue
		ns = element.find(nstag)
		# Ignore empty entries
		text = element.find(revisiontag).find(texttag)
		if text is None or not text.text:
			remove_subtree(element)
			continue
		# Handle categories. TODO: the namespace number 14 could change, theoretically
		if ns is not None and ns.text == "14":
			load_categories(title.text, text.text)
			remove_subtree(element)
			continue
		# Ignore everything except main namespace articles
		if ns is None or ns.text != "0":
			remove_subtree(element)
			continue
		# Store text for analysis
		if not "/" in title.text and not title.text.startswith("List of "):
			load_text(title.text, text.text)
		# Analyze character cooccurrences
		if episodes is not None and "/Appearances" in title.text:
			load_cooccur(title.text, text.text)
		remove_subtree(element)

print("Loaded", len(cathier), "categories, and", len(texts), "raw articles.")

# transitive closure of categories
process_categories()

# Analyze the texts (categories should now be good)
for title, text in texts:
	try:
		process(title, text)
	except Exception as e:
		print("Errors in:", text, "\t", e, file=sys.stderr)
		raise e

#### WRITE the occurence information
if episodes is not None:
	with gzip.open('occurrences.json.gz', 'wt', encoding="utf-8") as output:
		json.dump(episodes, output, indent=1)
#### WRITE the text and category jsons
if articles is not None:
	with gzip.open('simpsonswiki.json.gz', 'wt', encoding="utf-8") as output:
		json.dump(articles, output, indent=1)

#### show some basic statistics:
print(len(articles), "usable articles")
from collections import Counter
for k,v in Counter([x["heuristic"] for x in articles]).most_common(): print(k,v,sep="\t")

#### Print top unhandled categories
print("Top unhandled categories / articles:")
ucats = list(ucats.items())
ucats.sort(key=lambda x:-len(x[1]))
for uc, art in ucats[:30]:
	print(uc, len(art), art[:5], sep="\t")
