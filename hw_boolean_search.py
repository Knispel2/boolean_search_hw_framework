#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import codecs
from collections import defaultdict
import re
#from memory_profiler import profile


class my_set:
    def __init__(self, iter_=None):
        if iter_ is None:
            self.base = []
        else:
            self.base = iter_

    def add(self, obj):
        if self.base and self.base[-1] == obj:
            return self
        self.base.append(obj)
        return self

    def __and__(self, other):
        result = []
        left, right = 0, 0
        while left < len(self.base) and right < len(other.base):
            if self.base[left] < other.base[right]:
                left += 1
            elif self.base[left] > other.base[right]:
                right += 1
            else:
                result.append(self.base[left])
                left += 1
                right += 1
        return my_set(result)

    def __or__(self, other):
        result = []
        left, right = 0, 0
        while left < len(self.base) and right < len(other.base):
            if self.base[left] < other.base[right]:
                result.append(self.base[left])
                left += 1
            elif self.base[left] > other.base[right]:
                result.append(other.base[right])
                right += 1
            else:
                result.append(self.base[left])
                left += 1
                right += 1
        while left < len(self.base):
            result.append(self.base[left])
            left += 1
        while right < len(other.base):
            result.append(other.base[right])
            right += 1
        return my_set(result)

    def __contains__(self, item):
        # TODO: вставить сюда бинарный поиск
        return item in self.base



class Index:
    def __init__(self, docfile) -> None:
        with codecs.open(docfile, mode='r', encoding='utf-8') as docs:
            self._index = defaultdict(set)
            for index, item in enumerate(docs):
                base = item.strip('\n').strip().split('\t')[1:]
                for fragment in base:
                    for word in fragment.split():
                        self._index[word].add(index+1)

    def __getitem__(self, item):
        return self._index[item]


class QueryProcessor:
    OPERATORS = {' ': (2, lambda x, y: x and y), '|': (1, lambda x, y: x or y)}

    def separate(self, query):
        result = []
        left = 0
        bra_counter = 0
        for i in range(1, len(query)):
            if query[i] == '(':
                bra_counter += 1
                continue
            if query[i] == ')':
                bra_counter -= 1
                continue
            if bra_counter > 0:
                continue
            if query[i] == ' ':
                result.append(query[left:i])
                left = i+1
            else:
                continue
        return result


    def __init__(self, query):
        self.query = self.separate(query)

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
        return [self._calc(self._to_polish(self._parse(obj, reversed_index))) for obj in self.query]


class SearchResults:
    def __init__(self):
        self._query_to_result = dict()
    def add(self, qid, found):
        self._query_to_result[qid] = found

    def soft_search(self, documentId, queryId, tau=0.2):
        count = sum(1 if documentId in obj else 0 for obj in self._query_to_result[int(queryId)])
        if count == 0:
            return 0
        return count / len(self._query_to_result[int(queryId)]) > tau

    def print_submission(self, objects_file, submission_file):
        with codecs.open(objects_file, mode='r', encoding='utf-8') as test_objects:
            with codecs.open(submission_file, mode='w', encoding='utf-8') as result:
                result.write('ObjectId,Relevance\n')
                for test_line in test_objects:
                    objectId, queryId, documentId = test_line.strip().split(',')
                    if not objectId.isdigit():
                        continue
                    documentId = int(re.search(r'\d+$', documentId).group())
                    result.write(f'{objectId},{1 if self.soft_search(documentId, queryId) else 0}\n')



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
            query_processor = QueryProcessor(query)

            # Search and save results.
            search_results.add(qid, query_processor.process(index))

    # Generate submission file.
    search_results.print_submission(args.objects_file, args.submission_file)


if __name__ == "__main__":
    main()

