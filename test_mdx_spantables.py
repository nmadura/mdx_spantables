"""
Tests for SpanTables Extension
==============================

These tests are used to check the functionality of the spantables extension,
allowing me to more easily upgrade to a later version of the tables extension
it was based on without accidentally breaking functionality.

Run them like this: python -m unittest discover

Copyright 2018 [Maurice van der Pot](griffon26@kfk4ever.com)

License: [BSD](http://www.opensource.org/licenses/bsd-license.php)

"""

import unittest

import xml.etree.ElementTree as etree

import mdx_spantables


class FakeMarkdown():
    def __init__(self):
        self.tab_length = None

class FakeParser():
    def __init__(self):
        self.markdown = FakeMarkdown()
        self.md = self.markdown


class TestSpanTableProcessor(unittest.TestCase):

    def setUp(self):
        self.proc = mdx_spantables.SpanTableProcessor(FakeParser())

    def cell_to_text(self, cell):
        colspan_str = cell.get('colspan')
        colspan = int(colspan_str) if colspan_str else 1

        rowspan_str = cell.get('rowspan')
        rowspan = int(rowspan_str) if rowspan_str else 1

        output = '%dx%d' % (colspan, rowspan)
        return output

    def element_to_table(self, element):
        output = ''

        children = list(element)
        self.assertEqual(len(children), 1)

        table = children[0]
        self.assertEqual(table.tag, 'table')

        table_children = list(table)
        self.assertEqual(len(table_children), 2)
        table_head, table_body = table_children

        self.assertEqual(table_head.tag, 'thead')
        self.assertEqual(table_body.tag, 'tbody')

        for tr in table_head:
            if len(tr) > 0:
                output += ' '.join('%s' % self.cell_to_text(th) for th in tr)
                output += '\n'

        for tr in table_body:
            if len(tr) > 0:
                output += ' '.join('%s' % self.cell_to_text(td) for td in tr)
                output += '\n'

        return output


    def test_test(self):
        self.assertTrue(self.proc.test(None, '| bla | nogwat |\n'
                                             '|-----|--------|\n'))

    def test_test_with_multiple_header_rows(self):
        self.assertTrue(self.proc.test(None, '| Sensing | Warning and interventions | 2026-2027 ||\n'
                                             '|_ |_ | All passenger seats | Rear seats only |\n'
                                             '| --- | --- | --- | --- |\n'))


    def test_run_table_without_col_or_rowspan(self):
        parent = etree.Element('parent')
        self.proc.run(parent, [
            '| header1 | header2 |\n'
            '|---------|---------|\n'
            '| content1| content2|'
        ])
        actual = self.element_to_table(parent)
        expected = (
            '1x1 1x1\n'
            '1x1 1x1\n'
        )
        self.assertMultiLineEqual(actual, expected)

    def test_run_table_with_multiple_header_rows(self):
        parent = etree.Element('parent')
        self.proc.run(parent, [
            '| Sensing | Warning and interventions | 2026-2027 ||\n'
            '|_ |_ | All passenger seats | Rear seats only |\n'
            '| --- | --- | --- | --- |\n'
            '| Indirect Sensing | Initial warning | 2 | 1 |'
        ])
        actual = self.element_to_table(parent)
        expected = (
            '1x2 1x2 2x1\n'
            '1x1 1x1\n'
            '1x1 1x1 1x1 1x1\n'
        )
        self.assertMultiLineEqual(actual, expected)

    def test_run_table_with_single_rowspan_in_first_column(self):
        parent = etree.Element('parent')
        self.proc.run(parent, [
            '| header1 | header2 |\n'
            '|---------|---------|\n'
            '| content1| content2|\n'
            '|_        | content2|'
        ])
        actual = self.element_to_table(parent)
        expected = (
            '1x1 1x1\n'
            '1x2 1x1\n'
            '1x1\n'
        )
        self.assertMultiLineEqual(actual, expected)

    def test_run_table_with_single_rowspan_in_later_column(self):
        parent = etree.Element('parent')
        self.proc.run(parent, [
            '| header1 | header2 |\n'
            '|---------|---------|\n'
            '| content1| content2|\n'
            '| content2|_        |'
        ])
        actual = self.element_to_table(parent)
        expected = (
            '1x1 1x1\n'
            '1x1 1x2\n'
            '1x1\n'
        )
        self.assertMultiLineEqual(actual, expected)

    def test_run_table_with_single_rowspan_at_last_character(self):
        parent = etree.Element('parent')
        self.proc.run(parent, [
            '| header1 | header2 |\n'
            '|---------|---------|\n'
            '| content1| content2|\n'
            '| content2|        _|'
        ])
        actual = self.element_to_table(parent)
        expected = (
            '1x1 1x1\n'
            '1x1 1x2\n'
            '1x1\n'
        )
        self.assertMultiLineEqual(actual, expected)

    def test_run_table_with_single_colspan_in_first_column(self):
        parent = etree.Element('parent')
        self.proc.run(parent, [
            '| header1 | header2 |\n'
            '|---------|---------|\n'
            '| content1         ||'
        ])
        actual = self.element_to_table(parent)
        expected = (
            '1x1 1x1\n'
            '2x1\n'
        )
        self.assertMultiLineEqual(actual, expected)

    def test_run_table_with_single_colspan_in_later_column(self):
        parent = etree.Element('parent')
        self.proc.run(parent, [
            '| header1 | header2 | header3 |\n'
            '|---------|---------|---------|\n'
            '| content1| content2         ||'
        ])
        actual = self.element_to_table(parent)
        expected = (
            '1x1 1x1 1x1\n'
            '1x1 2x1\n'
        )
        self.assertMultiLineEqual(actual, expected)

    def test_run_table_with_combined_row_and_colspan(self):
        parent = etree.Element('parent')
        self.proc.run(parent, [
            '| header1 | header2 |\n'
            '|---------|---------|\n'
            '| content1         ||\n'
            '|_                 ||'
        ])
        actual = self.element_to_table(parent)
        expected = (
            '1x1 1x1\n'
            '2x2\n'
        )
        self.assertMultiLineEqual(actual, expected)

    def test_run_table_with_rowspan_stops_at_first_nonempty_cell(self):
        parent = etree.Element('parent')
        self.proc.run(parent, [
            '| head         |\n'
            '| ------------ |\n'
            '| regular cell |\n'
            '| span 2 rows  |\n'
            '|_             |'
        ])
        actual = self.element_to_table(parent)
        expected = (
            '1x1\n'
            '1x1\n'
            '1x2\n'
        )
        self.assertMultiLineEqual(actual, expected)

    def test_run_table_with_rowspan_limited_by_end_of_previous_rowspan(self):
        parent = etree.Element('parent')
        self.proc.run(parent, [
            '| head        |\n'
            '| ----------- |\n'
            '| span 2 rows |\n'
            '|_            |\n'
            '|             |\n'
            '|_            |'
        ])
        actual = self.element_to_table(parent)
        expected = (
            '1x1\n'
            '1x2\n'
            '1x2\n'
        )
        self.assertMultiLineEqual(actual, expected)

    def test_run_table_with_rowspan_limited_by_row_with_other_colspan(self):
        parent = etree.Element('parent')
        self.proc.run(parent, [
            '|             |            |\n'
            '| ----------- | ---------- |\n'
            '| not included in rowspan ||\n'
            '| span 2 rows |            |\n'
            '|_            |            |'
        ])
        actual = self.element_to_table(parent)
        expected = (
            '1x1 1x1\n'
            '2x1\n'
            '1x2 1x1\n'
            '1x1\n'
        )
        self.assertMultiLineEqual(actual, expected)

    def test_run_table_with_alignment_and_separator_padding(self):
        parent = etree.Element('parent')
        self.proc.run(parent, [
            '| head1 | head2 |\n'
            '| :----- | -----: |\n'
            '| a | b |'
        ])

        table = list(parent)[0]
        thead = table.find('thead')
        tbody = table.find('tbody')

        header_row = thead.findall('tr')[0]
        body_row = tbody.findall('tr')[0]

        self.assertEqual(header_row.findall('th')[0].get('align'), 'left')
        self.assertEqual(header_row.findall('th')[1].get('align'), 'right')
        self.assertEqual(body_row.findall('td')[0].get('align'), 'left')
        self.assertEqual(body_row.findall('td')[1].get('align'), 'right')

    def test_run_table_with_colspan_header_mixed_alignment_centers_cell(self):
        parent = etree.Element('parent')
        self.proc.run(parent, [
            '| span 2 hdr rows | span 2 hdr cols   ||\n'
            '|_                | subhead | subhead2  |\n'
            '| --------------- |:------- | --------:|\n'
            '| span 2 rows     |   2     |   1      |\n'
            '|_                |   3     |   4      |'
        ])

        table = list(parent)[0]
        thead = table.find('thead')

        first_header_row = thead.findall('tr')[0]
        second_header_row = thead.findall('tr')[1]

        top_left = first_header_row.findall('th')[0]
        top_span = first_header_row.findall('th')[1]
        lower_left = second_header_row.findall('th')[0]
        lower_right = second_header_row.findall('th')[1]

        self.assertEqual(top_left.get('rowspan'), '2')
        self.assertEqual(top_span.get('colspan'), '2')
        self.assertEqual(top_span.get('align'), 'center')
        self.assertEqual(lower_left.get('align'), 'left')
        self.assertEqual(lower_right.get('align'), 'right')


