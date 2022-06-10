import codecs
import csv
from re import template
import time
import os
from bs4 import BeautifulSoup
import wikitextparser as wtp

PATH_WIKI_XML = '/Users/yamamotobikutorueiichi/codes/abstract-extractor/dump'
FILENAME_WIKI = 'harrypotter_pages_current.xml'
FILENAME_ABSTRACT = 'abstract.csv'
ENCODING = "utf-8"

pathWikiXML = os.path.join(PATH_WIKI_XML, FILENAME_WIKI)
pathAbstractCsv = os.path.join(PATH_WIKI_XML, FILENAME_ABSTRACT)

with open(pathWikiXML, 'r') as f:
    data = f.read()

Bs_data = BeautifulSoup(data, "xml")

b_pages = Bs_data.find_all('page')

with open(pathAbstractCsv, 'w') as f_write:
    writer = csv.writer(f_write)

    header_row = ('title', 'long_abstract', 'short_abstract')
    writer.writerow(header_row)

    for b_page in b_pages:
        b_title = b_page.find('title')

        b_wikitext = b_page.find('text')

        parsed_text = wtp.parse(b_wikitext.text)

        first_section = parsed_text.sections[0]

        long_text = BeautifulSoup(first_section.plain_text(), "lxml").get_text()
        long_text = long_text.lstrip()
        splited_lines = long_text.splitlines()
        if len(splited_lines) > 0:
            short_abstract = splited_lines[0]
        else:
            short_abstract = long_text[:200]

        writer.writerow((b_title.text, long_text, short_abstract))

f_write.close()