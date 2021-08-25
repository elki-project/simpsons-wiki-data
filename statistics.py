#!/usr/bin/python3
import gzip, json, re
from collections import Counter

data = json.load(gzip.open("simpsonswiki.json.gz"))

cats=Counter([x for y in data for x in y["categories"]])

N = len(data)

print("Number of articles:", N, sep="\t")
print("Number of heuristic labels:", len(set([x["heuristic"] for x in data])), sep="\t")
tmp = [len(y["categories"]) for y in data]
print("Number of category assignments:", sum(cats.values()), sum(cats.values())/N, sorted(tmp)[len(tmp)//2], sep="\t")
print("Number of overlapping categories:", len(cats), sep="\t")
print("Number of singleton categories:", len([x for x,y in cats.items() if y == 1]), sep="\t")

parsplit = re.compile(r"\s*\n\n+\s*", re.U)
sensplit = re.compile(r"(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s", re.U)
wordsplit = re.compile(r"[\w']+", re.U)

chars, paragraphs, sentences, tokens = [],[],[],[]
for x in data:
	title, text = x["title"], x["text"]
	text = title  + "\n\n" + text # prepend title
	chars.append(len(text))
	pars = [x for x in parsplit.split(text) if not x == ""]
	paragraphs.append(len(pars))
	sent = [x for par in pars for x in sensplit.split(par)]
	sentences.append(len(sent))
	words = [x for s in sent for x in wordsplit.findall(s)]
	tokens.append(len(words))

paragraphs.sort()
sentences.sort()
tokens.sort()
chars.sort()

print("Number of paragraphs:", sum(paragraphs), sum(paragraphs) / N, paragraphs[len(paragraphs)//2], sep="\t")
print("Number of sentences:", sum(sentences), sum(sentences) / N, sentences[len(sentences)//2], sep="\t")
print("Number of words:", sum(tokens), sum(tokens) / N, tokens[len(tokens)//2], sep="\t")
print("Number of characters:", sum(chars), sum(chars) / N, chars[len(chars)//2], sep="\t")
