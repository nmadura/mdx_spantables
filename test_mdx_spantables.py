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
import sys
from pathlib import Path

import markdown
import re
import xml.etree.ElementTree as etree

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

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


class TestSpanTableMarkdownIntegration(unittest.TestCase):

    def render(self, text, **config):
        extension_configs = {}
        if config:
            extension_configs['mdx_spantables'] = config
        return markdown.markdown(
            text,
            extensions=['md_in_html', 'mdx_spantables'],
            extension_configs=extension_configs,
        )

    def test_blocks_in_table_are_disabled_by_default(self):
        html = self.render(
            '| head 1 | head 2 |\n'
            '| :---- | :---- |\n'
            '| Legs | Driver paragraph\n'
            '- item 1\n'
            '- item 2 |'
        )

        self.assertNotIn('<ul>', html)
        self.assertEqual(html.count('<tr>'), 4)
        self.assertIn('- item 1', html)

    def test_blank_line_continuation_is_not_absorbed_by_default(self):
        html = self.render(
            '| Excursion line | Description |\n'
            '| :--- | :--- |\n'
            '| Red - Maximum intrusion | This line is marking the maximum post-test intruding point.  \n\n'
            'Peak intrusion values will be compared. |\n\n'
            '| Orange - Excursion limit | Struck side seat centreline, pre-test, without intrusion. |',
        )

        self.assertEqual(html.count('<tr>'), 2)
        self.assertIn('<p>Peak intrusion values will be compared. |</p>', html)
        self.assertIn('<p>| Orange - Excursion limit | Struck side seat centreline, pre-test, without intrusion. |</p>', html)

    def test_blocks_in_table_can_be_enabled_for_list_content(self):
        html = self.render(
            '| head 1 | head 2 |\n'
            '| :---- | :---- |\n'
            '| Legs | **Driver -** Driver paragraph\n'
            '- item 1\n'
            '- item 2 |',
            allow_blocks_in_table=True,
        )

        self.assertIn('<strong>Driver -</strong>', html)
        self.assertIn('<ul>', html)
        self.assertIn('<li>item 1</li>', html)
        self.assertIn('<li>item 2</li>', html)
        self.assertEqual(html.count('<tr>'), 2)

    def test_blocks_in_table_can_render_multiple_paragraphs_inside_one_cell(self):
        html = self.render(
            '| Excursion line | Description |\n'
            '| :--- | :--- |\n'
            '| Red - Maximum intrusion | This line is marking the maximum post-test intruding point of the interior door panel from AE-MDB (60km/h) and 75º pole impacts respectively. The method to determine the maximum deformation is detailed in [CP 004](/documents/translation/61/).  \n\n'
            'Peak intrusion values will be compared to those observed in the official tests. The OEM shall provide details of the measurement point used for establishing the intrusion lines. Where the red line is further inboard than any of the other excursion lines, those lines will not be marked on the BIW. |\n'
            '| Orange - Excursion limit | Struck side seat centreline, pre-test, without intrusion. |\n'
            '| Yellow - Excursion limit | 125mm inboard of the struck side seat centreline. |\n'
            '| Green - Occupant interaction limit | 250mm inboard from the struck side seat centreline |\n'
            '| Blue - Vehicle centreline | Y=0 |',
            allow_blocks_in_table=True,
        )

        self.assertEqual(html.count('<tr>'), 6)
        self.assertIn('<thead>', html)
        self.assertIn('<tbody>', html)
        self.assertRegex(
            html,
            r'<td[^>]*>\s*<p>This line is marking.*?</p>\s*<p>Peak intrusion values will be compared',
        )
        self.assertIn('>Orange - Excursion limit</td>', html)
        self.assertIn('>Yellow - Excursion limit</td>', html)
        self.assertIn('>Green - Occupant interaction limit</td>', html)
        self.assertIn('>Blue - Vehicle centreline</td>', html)

    def test_blocks_in_table_can_render_list_inside_multiline_first_cell(self):
        html = self.render(
            '| Criterion || WorldSID 50th ||\n'
            '|_          || HPL - LPL | Capping |\n'
            '| :--- | --- | --- | --- |\n'
            '| HIC~15~ | - | 500 - 700 | 700 |\n'
            '| A~res~-3ms | g | 72 - 80 | 80 |\n'
            '| A~res~-3ms \n'
            '- Direct contact with pole\n'
            '- O2O Head contact | g | - | 80 |',
            allow_blocks_in_table=True,
        )

        self.assertEqual(html.count('<table>'), 1)
        self.assertEqual(html.count('<tr>'), 5)
        self.assertIn('<ul>', html)
        self.assertIn('<li>Direct contact with pole</li>', html)
        self.assertIn('<li>O2O Head contact</li>', html)

    def test_blocks_in_table_does_not_merge_following_different_table(self):
        html = self.render(
            '| Load case |  |  | Head Excursion | Total points |\n'
            '| :--- | :--- | --- | --- | --- |\n'
            '| Far side | Main load cases | AE-MDB | 2.0 | 4 |\n'
            '|     |_ | Pole | 2.0 |_ |\n'
            '|     | Robustness | AE-MDB | 2.0 | 4 |\n'
            '|_    |_          | Pole | 2.0 |_ |\n\n'
            '| Front Occupant | Head | Total points |\n'
            '| :--- | --- | --- |\n'
            '| Occupant to occupant interaction[^1] | 2.00 | 2 |\n\n'
            '[^1]: Footnote',
            allow_blocks_in_table=True,
        )

        self.assertEqual(html.count('<table>'), 2)
        self.assertIn('<th align="left">Load case</th>', html)
        self.assertIn('<th align="left">Front Occupant</th>', html)
        self.assertRegex(html, r'</table>\s*<table>')

    def test_blocks_in_table_can_continue_open_last_cell_across_blank_lines(self):
        html = self.render(
            '| Rollover ||\n'
            '| :--- | :--- |\n'
            '| Triggering of HPD | The vehicle manufacturer must provide evidence showing that the vehicle can both sense rollover and that the side curtain HPD is deployed as a result. Functionality of rollover triggering shall be demonstrated with a full scale rollover dynamic test which may be selected by the OEM. |\n'
            '| HPD inflation | During the HPD measurements, after airbag deployment, detailed in [Section 4.1.3](#s:4.1.3), the laboratory will check that the deployed curtain airbag remains inflated and maintains sufficient pressure for at least 6 seconds to provide head impact protection.\n\n'
            'Where the laboratory check cannot be performed or there are doubts regarding inflation, functionality of rollover countermeasures shall be demonstrated with one of the following: \n\n'
            '- HPD internal pressure retention of 50% for a minimum of 6 seconds - C-NCAP 2024. Data must include pressure vs time output. \n'
            '- Compliance with FMVSS 226. |',
            allow_blocks_in_table=True,
        )

        self.assertEqual(html.count('<table>'), 1)
        self.assertEqual(html.count('<tr>'), 3)
        self.assertRegex(html, r'<td[^>]*>\s*<p>During the HPD measurements.*?</p>\s*<p>Where the laboratory check cannot be performed',)
        self.assertIn('<ul>', html)
        self.assertIn('<li>Compliance with FMVSS 226.</li>', html)

    def test_blocks_in_table_does_not_absorb_paragraph_after_closed_last_cell(self):
        html = self.render(
            '| Rollover ||\n'
            '| :--- | :--- |\n'
            '| Triggering of HPD | The vehicle manufacturer must provide evidence showing that the vehicle can both sense rollover and that the side curtain HPD is deployed as a result. Functionality of rollover triggering shall be demonstrated with a full scale rollover dynamic test which may be selected by the OEM. |\n'
            '| HPD inflation | During the HPD measurements, after airbag deployment, detailed in [Section 4.1.3](#s:4.1.3), the laboratory will check that the deployed curtain airbag remains inflated and maintains sufficient pressure for at least 6 seconds to provide head impact protection.\n\n'
            'Where the laboratory check cannot be performed or there are doubts regarding inflation, functionality of rollover countermeasures shall be demonstrated with one of the following: \n\n'
            '- HPD internal pressure retention of 50% for a minimum of 6 seconds - C-NCAP 2024. Data must include pressure vs time output. \n'
            '- Compliance with FMVSS 226. |\n\n'
            'Both of the above requirements must be met in order to receive rewards for rollover protection, no partial',
            allow_blocks_in_table=True,
        )

        self.assertEqual(html.count('<table>'), 1)
        self.assertEqual(html.count('<tr>'), 3)
        self.assertRegex(html, r'</table>\s*<p>Both of the above requirements must be met')

    def test_blocks_in_table_does_not_merge_following_full_table_block(self):
        html = self.render(
            '| Front Occupant | Modifiers | Criterion | Modifier score |\n'
            '| :--- | :--- | :--- | --- |\n'
            '| Head & neck | Direct contact with pole | Inspection | capping |\n'
            '|     | DAMAGE | DAMAGE >= 0.47 | monitoring |\n'
            '|_    | Incorrect airbag deployment | Inspection | -20% |\n'
            '| Chest | Shoulder load | >= 3.0kN | -100% |\n'
            '|     | Viscous Criterion | >= 1.0m/s | -100% |\n'
            '|_    | Incorrect airbag deployment | Inspection | -20% | | Abdomen | Viscous Criterion | >= 1.0m/s | -100% |\n'
            '|_    | Incorrect airbag deployment | Inspection | -20% | | Pelvis | Incorrect airbag deployment | Inspection | -20% |\n\n'
            '| Rear child occupants | Modifiers | Criterion | Modifier score |\n'
            '| --- | --- | --- | --- |\n'
            '| Head | Restraint | Inspection | -100% |\n'
            '| Q dummy test score | CRS to vehicle attachment | Inspection | -50% |',
            allow_blocks_in_table=True,
        )

        self.assertEqual(html.count('<table>'), 2)
        self.assertIn('<th align="left">Front Occupant</th>', html)
        self.assertIn('<th>Rear child occupants</th>', html)
        self.assertRegex(html, r'</table>\s*<table>')

    def test_blocks_in_table_does_not_merge_fenced_caption_block_into_last_cell(self):
        html = self.render(
            '|  | 2026 | 2027 | 2028 | 2029 |\n'
            '|----|----|----|----|----|\n'
            '| Stand-alone optional | 50% | 60% | 70% | 80% |\n'
            '| Percentage of Total Sales | 70% | 80% | 90%  | 100% |\n'
            '\n'
            '/// caption | <\n'
            'AEB Car to Car (C2C)\n'
            '///\n\n'
            '|  | 2026 | 2027 | 2028 | 2029 |\n'
            '|----|----|----|----|----|\n'
            '| Stand-alone optional | 50% | 60% | 70% | 80% |\n'
            '| Percentage of Total Sales | 70% | 80% | 90%  | 100% |\n'
            '\n'
            '/// caption | <\n'
            'AEB Vulnerable Road Users (VRU)\n'
            '///',
            allow_blocks_in_table=True,
        )

        self.assertEqual(html.count('<table>'), 2)
        self.assertIn('<td>100%</td>', html)
        self.assertRegex(
            html,
            r'</table>\s*<p>/// caption \| &lt;\s*AEB Car to Car \(C2C\)\s*///</p>\s*<table>',
        )
        self.assertRegex(
            html,
            re.compile(
                r'</table>\s*<p>/// caption \| &lt;\s*AEB Car to Car \(C2C\)\s*///</p>\s*<table>.*?<p>/// caption \| &lt;\s*AEB Vulnerable Road Users \(VRU\)\s*///</p>',
                re.S,
            ),
        )


