#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import codecs
from tqdm import tqdm
from collections import defaultdict
import re
#from memory_profiler import profile


class Index:
    def __init__(self, docfile) -> None:
        with codecs.open(docfile, mode='r', encoding='utf-8') as docs:
            self._index = defaultdict(set)
            for index, item in tqdm(enumerate(docs), total=22285):
                base = item.strip('\n').strip().split('\t')[1:]
                for fragment in base:
                    for word in fragment.split():
                        self._index[word].add(index+1)

    def __getitem__(self, item):
        return self._index[item]


class QueryProcessor:
    OPERATORS = {' ': (2, lambda x, y: x & y), '|': (1, lambda x, y: x | y)}

    def __init__(self, query_idx, query):
        self.query = query

    def _parse(self, query, reversed_index):
        """
        Разобьем запрос на термины и операторы по отдельности
        """
        buf = ''
        for s in query:
            if s.isalpha() or s.isdigit():
                buf += s
            elif buf:
                yield reversed_index[buf]
                buf = ''
            if s in QueryProcessor.OPERATORS or s in "()":
                yield s
        if buf:
            yield reversed_index[buf]

    def _to_polish(self, parsed_formula):
        """
        Подаем элементы запроса в порядке польской нотации
        """
        stack = []
        for token in parsed_formula:
            if type(token) is set:
                yield token
                continue
            if token in QueryProcessor.OPERATORS:
                while stack and stack[-1] != "(" and QueryProcessor.OPERATORS[token][0] <= \
                        QueryProcessor.OPERATORS[stack[-1]][0]:
                    yield stack.pop()
                stack.append(token)
            elif token == ")":
                while stack:
                    x = stack.pop()
                    if x == "(":
                        break
                    yield x
            elif token == "(":
                stack.append(token)
        while stack:
            yield stack.pop()

    def _calc(self, polish):
        stack = []
        for token in polish:
            if type(token) is set:
                stack.append(token)
                continue
            if token in QueryProcessor.OPERATORS:
                y, x = stack.pop(), stack.pop()
                stack.append(QueryProcessor.OPERATORS[token][1](x, y))
        return stack[0]

    def process(self, reversed_index):
        return self._calc(self._to_polish(self._parse(self.query, reversed_index)))


class SearchResults:
    def __init__(self):
        self._query_to_result = dict()
    def add(self, qid, found):
        self._query_to_result[qid] = found


    def print_submission(self, objects_file, submission_file):
        with codecs.open(objects_file, mode='r', encoding='utf-8') as test_objects:
            with codecs.open(submission_file, mode='w', encoding='utf-8') as result:
                result.write('ObjectId,Relevance\n')
                for test_line in test_objects:
                    objectId, queryId, documentId = test_line.strip().split(',')
                    if not objectId.isdigit():
                        continue
                    documentId = int(re.search(r'\d+$', documentId).group())
                    result.write(f'{objectId},{1 if documentId in self._query_to_result[int(queryId)] else 0}\n')



#@profile
def main():
    # Command line arguments.
    parser = argparse.ArgumentParser(description='Homework: Boolean Search')
    parser.add_argument('--queries_file', default='queries.numerate.txt', help='queries.numerate.txt')
    parser.add_argument('--objects_file', default='objects.numerate.txt', help='objects.numerate.txt')
    parser.add_argument('--docs_file', default='docs.txt', help='docs.tsv')
    parser.add_argument('--submission_file', default='output.csv', help='output file with relevances')
    args = parser.parse_args()

    # Build index.
    index = Index(args.docs_file)

    # Process queries.
    search_results = SearchResults()
    with codecs.open(args.queries_file, mode='r', encoding='utf-8') as queries_fh:
        for line in queries_fh:
            fields = line.rstrip('\n').split('\t')
            qid = int(fields[0])
            query = fields[1]

            # Parse query.
            query_processor = QueryProcessor(qid, query)

            # Search and save results.
            search_results.add(qid, query_processor.process(index))

    # Generate submission file.
    search_results.print_submission(args.objects_file, args.submission_file)


if __name__ == "__main__":
    main()

