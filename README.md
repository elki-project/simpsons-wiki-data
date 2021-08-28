Simpsons Wiki Data
==================

This script extracts text and category information from
the [Simpsons Fandom Wiki](https://simpsons.fandom.com/)
to use in natural language processing and text mining education.


Usage
-----

This was tested on a Debian linux system and on Ubuntu 21.04.

Install the required packages:
`apt install python3-lxml python3-wikitrans p7zip-full`

You then need to manually download a "Current pages" dump (no history)
from the Wiki via <https://simpsons.fandom.com/wiki/Special:Statistics>.

Run `python3 simpsons-extract.py` to generate the output files:

- `simpsonswiki.json.gz` containing the text and category information
- `occurrences.json.gz` containing the cooccurrence information

Example
-------

Records in the text data look as follows:

```
{
  "title": "Homer Simpson",
  "text": "Homer Jay Simpson (born May 12) is the ...",
  "categories": [ "Characters voiced by Dan Castellaneta", ...],
  "heuristic": "Characters"
}
```

Where `categories` is a full list of categories in the article, while
`heuristic` is a single class label chosen by certain error-prone heuristics.

Released Snapshots
------------------

We intend to host snapshots of the data as Github "releases":

<https://github.com/elki-project/simpsons-wiki-data/releases>


License
-------

Because the Simpsons Wiki is CC BY-SA 3.0 licensed, the extracted text
is also available under the same license.

* [license summary](https://creativecommons.org/licenses/by-sa/3.0/)
* [legal code](https://creativecommons.org/licenses/by-sa/3.0/legalcode)

Attribution
-----------

Please credit our work by citing the introductory paper

Erich Schubert, Gloria Feher  
D'Oh! Learn NLP with the Simpsons Wiki Data Set  
under review, 2021

