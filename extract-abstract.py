import os
from bs4 import BeautifulSoup
import wikitextparser as wtp
from rdflib import Graph, URIRef, Namespace, Literal
from rdflib.namespace import RDFS
import glob
import sys

PATH_WIKI_XML = '/Users/yamamotobikutorueiichi/codes/abstract-extractor/dump'
PATH_EXTRACTED_KG = '/Users/yamamotobikutorueiichi/codes/postProcessedWikis/'
FILENAME_WIKI = 'harrypotter_pages_current.xml'
FILENAME_ABSTRACT = 'abstract.csv'
ENCODING = "utf-8"
KNOWLEDGE_GRAPH_NAME = 'dbkwik.webdatacommons.org/'
ONTOLOGY_URI = 'http://dbkwik.webdatacommons.org/ontology/'
PREFIX = 'dbkwik'


invalid_url_char_set = set('<>" {}|\\^`')


def contain_invalid_url_character(url):
    """"
    Check if the url contains invalid characters
    Arguments:
        url: string
    Returns:
        boolean. True if valid. False if url contains invalid characters.
    """
    common_list = list(set(url) & invalid_url_char_set)
    return len(common_list) > 0


def read_extracted_knowledge_graph(folder_name):
    """"
    Read all turtle files (ttl) inside the folder and create graph
    Argument:
        folder_name: folder name containing ttl files
    Returns:
        rdflib Graph containing the knowledge graph in the folder
    """
    extracted_kg_path = PATH_EXTRACTED_KG + folder_name + '/*.ttl'
    file_list = glob.glob(extracted_kg_path)

    if len(file_list) < 0:
        print('Could not find folder: ' + extracted_kg_path)
        sys.exit(0)

    extracted_kg = Graph()

    for file in file_list:
        extracted_kg.parse(file)

    return extracted_kg


def generate_long_abstract_predicate(graph):
    """"
    Generate the long abstract predicate
    Arguments:
        graph: graph that will be used to save the abstracts
    Returns:
        Predicate to be used with the long abstract
    """
    graph_namespace = graph.namespace_manager
    ontology_ns = Namespace(ONTOLOGY_URI)
    graph_namespace.bind(PREFIX, ontology_ns)
    return ontology_ns.abstract


def generate_subject(base_uri, title, extracted_kg):
    """"
    Generate subject
    Arguments:
        base_uri: URI used in all subjects
        title: title of the page that will be used to compose generated URI
        extracted_kg: Graph that contains the previously extracted knowledge graph
    Returns:
        String with generated URI or None if generate URI is not valid or not contained in the extracted knowledge graph
    """
    if not title:
        return

    # Replace characters
    title = title.replace(' ', '_')
    title = title.replace('"', "'")
    title = title.replace("`", "'")

    if contain_invalid_url_character(title):
        return

    page_uri = URIRef(base_uri + title)

    if not (page_uri, None, None) in extracted_kg:
        return

    return page_uri


def extract_short_abstract(long_abstract):
    """"
    Create short abstract using long abstract
    Argument:
        long_abstract: string
    Returns:
        String with the shorter version of the abstract
    """
    splited_lines = long_abstract.splitlines()
    if len(splited_lines) > 0:
        short_abstract = splited_lines[0]
    else:
        short_abstract = long_abstract[:200]

    return short_abstract


def add_sentence(graph, sub, pred, obj):
    """"
    Add triple to the graph
    Arguments:
        graph: Graph
        sub: subject object
        pred: predicate object
        obj: object
    """
    graph.add((sub, pred, obj))


def generate_abstract_graph(data):
    """"
    Generate abstract graph
    Arguments:
        data: string containing xml data to extract abstract
    Returns:
        Graph containing abstract with triple structure
    """
    Bs_data = BeautifulSoup(data, "xml")

    b_dbname = Bs_data.find_all('dbname')
    dbname = ''
    if len(b_dbname) > 0:
        dbname = b_dbname[0].text
    else:
        print('Could not found dbname')
        return

    graph = Graph()
    long_abstract_predicate = generate_long_abstract_predicate(graph)
    short_abstract_predicate = RDFS.comment

    folder_name = dbname + '.'
    base_uri = 'http://' + KNOWLEDGE_GRAPH_NAME + dbname + './resource/'

    extracted_kg = read_extracted_knowledge_graph(folder_name)

    b_pages = Bs_data.find_all('page')

    for b_page in b_pages:
        title = b_page.find('title').text
        page_uri = generate_subject(base_uri, title, extracted_kg)

        if not page_uri:
            continue

        b_wikitext = b_page.find('text')

        if not b_wikitext.text :
            continue

        first_section = wtp.parse(b_wikitext.text).sections[0]

        long_text = BeautifulSoup(
            first_section.plain_text(), "lxml").get_text()
        long_text = long_text.lstrip()
        short_abstract = extract_short_abstract(long_text)

        add_sentence(graph, page_uri, long_abstract_predicate, Literal(long_text))
        add_sentence(graph, page_uri, short_abstract_predicate, Literal(short_abstract))
    return graph

def main():
    pathWikiXML = os.path.join(PATH_WIKI_XML, FILENAME_WIKI)

    with open(pathWikiXML, 'r') as f:
        data = f.read()

    graph = generate_abstract_graph(data)

    if graph:
        destination_path = PATH_WIKI_XML + '/abstracts.ttl'
        graph.serialize(destination=destination_path)


if __name__ == "__main__":
    main()
