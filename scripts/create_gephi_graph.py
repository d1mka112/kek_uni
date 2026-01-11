#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Создает граф для Gephi из структуры файлов ГОД_АВТОР_НАЗВАНИЕ.txt
"""

import re
from pathlib import Path
from collections import defaultdict
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

def parse_filename(filename):
    """Парсит имя файла в формате ГОД_АВТОР_НАЗВАНИЕ.txt"""
    # Убираем расширение
    name = filename.replace('.txt', '')
    
    # Разделяем по первому и второму подчеркиванию
    parts = name.split('_', 2)
    
    if len(parts) < 3:
        return None
    
    year = parts[0]
    author = parts[1]
    title = parts[2]
    
    return {
        'year': year,
        'author': author,
        'title': title,
        'filename': filename
    }

def create_gephi_graph(texts_dir, output_file):
    """Создает GEXF файл для Gephi"""
    
    # Собираем все произведения
    works = []
    authors_to_works = defaultdict(list)
    
    txt_files = sorted(texts_dir.glob('*.txt'))
    
    for txt_file in txt_files:
        parsed = parse_filename(txt_file.name)
        if parsed:
            works.append(parsed)
            authors_to_works[parsed['author']].append(parsed)
    
    print(f"Found {len(works)} works by {len(authors_to_works)} authors")
    
    # Создаем XML структуру для GEXF
    gexf = Element('gexf')
    gexf.set('xmlns', 'http://www.gexf.net/1.2draft')
    gexf.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
    gexf.set('xsi:schemaLocation', 'http://www.gexf.net/1.2draft http://www.gexf.net/1.2draft/gexf.xsd')
    gexf.set('version', '1.2')
    
    # Meta информация
    meta = SubElement(gexf, 'meta')
    meta.set('lastmodifieddate', '2026-01-11')
    creator = SubElement(meta, 'creator')
    creator.text = 'create_gephi_graph.py'
    
    # Граф
    graph = SubElement(gexf, 'graph')
    graph.set('defaultedgetype', 'undirected')
    graph.set('mode', 'static')
    graph.set('name', 'Russian Science Fiction Works')
    
    # Атрибуты узлов
    attributes = SubElement(graph, 'attributes')
    attributes.set('mode', 'static')
    attributes.set('class', 'node')
    
    attr_year = SubElement(attributes, 'attribute')
    attr_year.set('id', '0')
    attr_year.set('title', 'year')
    attr_year.set('type', 'integer')
    
    attr_author = SubElement(attributes, 'attribute')
    attr_author.set('id', '1')
    attr_author.set('title', 'author')
    attr_author.set('type', 'string')
    
    attr_title = SubElement(attributes, 'attribute')
    attr_title.set('id', '2')
    attr_title.set('title', 'title')
    attr_title.set('type', 'string')
    
    attr_filename = SubElement(attributes, 'attribute')
    attr_filename.set('id', '3')
    attr_filename.set('title', 'filename')
    attr_filename.set('type', 'string')
    
    # Атрибуты рёбер
    edge_attributes = SubElement(graph, 'attributes')
    edge_attributes.set('mode', 'static')
    edge_attributes.set('class', 'edge')
    
    edge_weight = SubElement(edge_attributes, 'attribute')
    edge_weight.set('id', '0')
    edge_weight.set('title', 'weight')
    edge_weight.set('type', 'double')
    
    # Узлы
    nodes = SubElement(graph, 'nodes')
    node_map = {}  # filename -> node_id
    
    for idx, work in enumerate(works):
        node = SubElement(nodes, 'node')
        node_id = str(idx)
        node.set('id', node_id)
        node.set('label', work['title'])
        node_map[work['filename']] = node_id
        
        attvalues = SubElement(node, 'attvalues')
        
        attv_year = SubElement(attvalues, 'attvalue')
        attv_year.set('for', '0')
        attv_year.set('value', work['year'])
        
        attv_author = SubElement(attvalues, 'attvalue')
        attv_author.set('for', '1')
        attv_author.set('value', work['author'])
        
        attv_title = SubElement(attvalues, 'attvalue')
        attv_title.set('for', '2')
        attv_title.set('value', work['title'])
        
        attv_filename = SubElement(attvalues, 'attvalue')
        attv_filename.set('for', '3')
        attv_filename.set('value', work['filename'])
    
    # Рёбра - связываем произведения одного автора
    edges = SubElement(graph, 'edges')
    edge_id = 0
    edge_set = set()  # Чтобы избежать дубликатов
    
    for author, author_works in authors_to_works.items():
        # Создаем связи между всеми произведениями одного автора
        for i, work1 in enumerate(author_works):
            for j, work2 in enumerate(author_works):
                if i < j:  # Избегаем дубликатов и петель
                    node1_id = node_map[work1['filename']]
                    node2_id = node_map[work2['filename']]
                    
                    # Создаем уникальный ключ для ребра
                    edge_key = tuple(sorted([node1_id, node2_id]))
                    if edge_key not in edge_set:
                        edge_set.add(edge_key)
                        
                        edge = SubElement(edges, 'edge')
                        edge.set('id', str(edge_id))
                        edge.set('source', node1_id)
                        edge.set('target', node2_id)
                        edge.set('weight', '1.0')
                        
                        # Атрибуты ребра
                        edge_attvalues = SubElement(edge, 'attvalues')
                        edge_attv = SubElement(edge_attvalues, 'attvalue')
                        edge_attv.set('for', '0')
                        edge_attv.set('value', '1.0')
                        
                        edge_id += 1
    
    print(f"Created {len(works)} nodes and {edge_id} edges")
    
    # Форматируем и сохраняем XML
    xml_str = minidom.parseString(tostring(gexf)).toprettyxml(indent="  ", encoding='utf-8')
    
    with open(output_file, 'wb') as f:
        f.write(xml_str)
    
    print(f"Graph saved to {output_file}")

def main():
    script_dir = Path(__file__).parent
    texts_dir = script_dir.parent / 'texts'
    output_file = script_dir.parent / 'russian_sf_graph.gexf'
    
    if not texts_dir.exists():
        print(f"Error: Directory {texts_dir} does not exist")
        return
    
    create_gephi_graph(texts_dir, output_file)
    print(f"\nDone! You can now open {output_file} in Gephi")

if __name__ == '__main__':
    main()

