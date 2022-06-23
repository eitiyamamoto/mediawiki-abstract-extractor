import os
from bs4 import BeautifulSoup
import wikitextparser as wtp
from rdflib import Graph, URIRef, Namespace, Literal
from rdflib.namespace import RDFS
import glob
import sys
from multiprocessing import cpu_count, Pool
import gc
from urllib.parse import urlparse

PATH_WIKI_XML = '/Users/yamamotobikutorueiichi/codes/dumps/'
PATH_EXTRACTED_KG = '/Users/yamamotobikutorueiichi/codes/postProcessedWikisAbstract/'
FILENAME_WIKI = 'harrypotter_pages_current.xml'
FILENAME_ABSTRACT = 'abstract.csv'
ENCODING = "utf-8"
KNOWLEDGE_GRAPH_NAME = 'dbkwik.webdatacommons.org/'
ONTOLOGY_URI = 'http://dbkwik.webdatacommons.org/ontology/'
PREFIX = 'dbkwik'
ABSTRACT_FILE = '/abstracts.ttl'


invalid_url_char_set = set('<>" {}|\\^`')


def contain_invalid_url_character(url):
    """
    Check if the url contains invalid characters
    Arguments:
        url: string
    Returns:
        boolean. True if valid. False if url contains invalid characters.
    """
    common_list = list(set(url) & invalid_url_char_set)
    return len(common_list) > 0


def read_extracted_knowledge_graph(folder_name):
    """
    Read all turtle files (ttl) inside the folder and create graph
    Argument:
        folder_name: folder name containing ttl files
    Returns:
        rdflib Graph containing the knowledge graph in the folder
        path to extracted knowledge graph
    """
    extracted_kg_path = PATH_EXTRACTED_KG + folder_name

    #abstract_file_path = extracted_kg + ABSTRACT_FILE
    #abstract_files = glob.glob(abstract_file_path)
    #if len(abstract_files) > 0:
    #    return None, None

    ttl_files = extracted_kg_path + '/*.ttl'
    file_list = glob.glob(ttl_files)

    if len(file_list) < 0:
        print('Could not find folder: ' + ttl_files)
        sys.exit(0)

    extracted_kg = Graph()

    for file in file_list:
        extracted_kg.parse(file)

    return extracted_kg, extracted_kg_path


def generate_long_abstract_predicate(graph):
    """
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
    """
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
    """
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
    """
    Add triple to the graph
    Arguments:
        graph: Graph
        sub: subject object
        pred: predicate object
        obj: object
    """
    graph.add((sub, pred, obj))


def generate_abstract_graph(dump):
    """
    Generate abstract graph
    Arguments:
        dump: Dump file name
    Returns:
        Graph containing abstract with triple structure
    """
    with open(dump, 'r') as f:
        data = f.read()

    Bs_data = BeautifulSoup(data, "xml")

    # b_sitename = Bs_data.find_all('sitename')
    # sitename = ''
    # if len(b_sitename) > 0:
    #     sitename = b_sitename[0].text
    # else:
    #     return False
    # sitename = sitename.lower().replace(' wiki', '.').replace(' ', '-').replace(' wiki', '.')

    # b_dbname = Bs_data.find_all('dbname')
    # dbname = ''
    # if len(b_dbname) > 0:
    #     dbname = b_dbname[0].text
    # else:
    #     print('Could not found dbname')
    #     return

    b_base = Bs_data.find_all('base')
    base_url = ''
    if len(b_base) > 0:
        base_url = b_base[0].text
    else:
        return False
    parsed_url = urlparse(base_url)
    parsed_url_netloc = parsed_url.netloc
    graph_name = parsed_url_netloc.split('.')[0]

    graph = Graph()
    long_abstract_predicate = generate_long_abstract_predicate(graph)
    short_abstract_predicate = RDFS.comment

    folder_name = graph_name + '.'
    base_uri = 'http://' + KNOWLEDGE_GRAPH_NAME + graph_name + './resource/'

    extracted_kg, extracted_kg_path = read_extracted_knowledge_graph(folder_name)

    if not extracted_kg:
        return False

    b_pages = Bs_data.find_all('page')

    for b_page in b_pages:
        try:
            title = b_page.find('title').text
            page_uri = generate_subject(base_uri, title, extracted_kg)

            if not page_uri:
                continue

            b_wikitext = b_page.find('text')

            if not b_wikitext.text :
                continue

            first_section = wtp.parse(b_wikitext.text).sections[0]

            if not first_section:
                continue

            long_text = BeautifulSoup(
                first_section.plain_text(), "lxml").get_text()
            long_text = long_text.lstrip()
            short_abstract = extract_short_abstract(long_text)

            add_sentence(graph, page_uri, long_abstract_predicate, Literal(long_text))
            add_sentence(graph, page_uri, short_abstract_predicate, Literal(short_abstract))
        except Exception as e:
            print(e)

    
    del extracted_kg
    gc.collect()
    destination_path = extracted_kg_path + ABSTRACT_FILE
    graph.serialize(destination=destination_path)

    # Free memory
    del graph
    gc.collect()

    return True

def main2():
    pathWikiXML = os.path.join(PATH_WIKI_XML, FILENAME_WIKI)

    with open(pathWikiXML, 'r') as f:
        data = f.read()

    graph = generate_abstract_graph(data)

    if graph:
        destination_path = PATH_WIKI_XML + '/abstracts.ttl'
        graph.serialize(destination=destination_path)

def log_result(retval):
    results.append(retval)
    print('{:.0%} done'.format(len(results)/dump_size))
    if retval:
        success_result.append(retval)
        print('{:.0%} successfully done'.format(len(success_result)/dump_size))

def main():
    cpu_qtd = cpu_count()
    cpu_qtd = 5
    print(f'Creating {cpu_qtd} process')
    pool = Pool(cpu_qtd)

    dump_list = glob.glob(PATH_WIKI_XML + '/*.xml')
    global dump_size
    dump_size = len(dump_list)
    global results
    results = []
    global success_result
    success_result = []

    #for dump in dump_list:
    #    pool.apply_async(generate_abstract_graph, args=[dump], callback=log_result)
    #for result in pool.imap_unordered(generate_abstract_graph, dump_list, chunksize=20):
    #    log_result(result)
    #for dump in dump_list:
    #    result = generate_abstract_graph(dump)
    #    log_result(result)
    result = generate_abstract_graph(dump_list[0])

    pool.close()
    pool.join()
    print("finished process")

if __name__ == "__main__":
    main()
