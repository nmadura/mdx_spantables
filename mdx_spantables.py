"""
SpanTables Extension for Python-Markdown
========================================

This is a slightly modified version of the tables extension that comes with
python-markdown.

To span cells across multiple columns make sure the cells end with multiple
consecutive vertical bars. To span cells across rows fill the cell on the last
row with at least one underscore at the start or end of its content and no
other characters than spaces or underscores.

For example:

    | head1           | head2 |
    |-----------------|-------|
    | span two cols          ||
    | span two rows   |       |
    |_                |       |

See <https://pythonhosted.org/Markdown/extensions/tables.html>
for documentation of the original extension.

Original code Copyright 2009 [Waylan Limberg](http://achinghead.com)
SpanTables changes Copyright 2016 [Maurice van der Pot](griffon26@kfk4ever.com)
used AI to update to support markdown 3.0+ by [Nathaniel Madura](shogunjp@gmail.com)

License: [BSD](http://www.opensource.org/licenses/bsd-license.php)

"""


from __future__ import unicode_literals
from markdown.blockprocessors import BlockProcessor
from markdown.extensions import Extension
import xml.etree.ElementTree as etree
import re


class SpanTableProcessor(BlockProcessor):
    """ Process Tables. """

    SEPARATOR_RE = re.compile(r'^\s*:?-+:?\s*$')

    def test(self, parent, block):
        rows = block.split('\n')
        if len(rows) < 2:
            return False

        if '|' not in rows[0]:
            return False

        border = rows[0].strip().startswith('|')
        separator_index = self._find_separator_index(rows, border)
        return separator_index > 0

    def _is_separator_cell(self, cell):
        return bool(self.SEPARATOR_RE.match(cell))

    def _is_separator_row(self, row, border):
        cells = self._split_row(row.strip(), border)
        if not cells:
            return False
        return all(self._is_separator_cell(c) for c in cells)

    def _find_separator_index(self, rows, border):
        for index, row in enumerate(rows):
            if self._is_separator_row(row, border):
                return index
        return -1


    def is_end_of_rowspan(self, td):
        return ((td != None) and
                (td.text.startswith('_') or td.text.endswith('_')) and
                (td.text.strip('_ ') == ''))

    def apply_rowspans(self, tbody):
            table_cells = {}

            rows = tbody.findall('tr')
            max_cols = 0
            max_rows = len(rows)
            for y, tr in enumerate(rows):

                cols = [cell for cell in tr if cell.tag in ('td', 'th')]

                x = 0
                for td in cols:

                    colspan_str = td.get('colspan')
                    colspan = int(colspan_str) if colspan_str else 1

                    # Insert the td together with its parent
                    table_cells[(x, y)] = (tr, td)

                    x += colspan

                max_cols = max(max_cols, x)

            for x in range(max_cols):
                possible_cells_in_rowspan = 0
                current_colspan = None

                for y in range(max_rows):
                    _, td = table_cells.get((x, y), (None, None))

                    if td == None:
                        possible_cells_in_rowspan = 0

                    else:
                        colspan = td.get('colspan')
                        if colspan != current_colspan:
                            current_colspan = colspan
                            possible_cells_in_rowspan = 0

                        if not td.text:
                            possible_cells_in_rowspan += 1

                        elif self.is_end_of_rowspan(td):
                            td.text = ''
                            possible_cells_in_rowspan += 1
                            first_cell_of_rowspan_y = y - (possible_cells_in_rowspan - 1)
                            for del_y in range(y, first_cell_of_rowspan_y, -1):
                                tr, td = table_cells.get((x, del_y))
                                tr.remove(td)
                            _, first_cell = table_cells.get((x, first_cell_of_rowspan_y))
                            first_cell.set('rowspan', str(possible_cells_in_rowspan))

                            possible_cells_in_rowspan = 0

                        else:
                            possible_cells_in_rowspan = 1

    def run(self, parent, blocks):
        """ Parse a table block and build table. """
        block = blocks.pop(0).split('\n')
        if not block:
            return

        # Get format type (bordered by pipes or not)
        border = False
        if block[0].strip().startswith('|'):
            border = True

        separator_index = self._find_separator_index(block, border)
        if separator_index < 1:
            return

        headers = [row.strip() for row in block[:separator_index]]
        separator = block[separator_index].strip()
        rows = [] if len(block) <= separator_index + 1 else block[separator_index + 1:]

        # Get alignment of columns
        align = []
        for c in self._split_row(separator, border):
            c = c.strip()
            if c.startswith(':') and c.endswith(':'):
                align.append('center')
            elif c.startswith(':'):
                align.append('left')
            elif c.endswith(':'):
                align.append('right')
            else:
                align.append(None)
        # Build table
        table = etree.SubElement(parent, 'table')
        thead = etree.SubElement(table, 'thead')
        for header in headers:
            self._build_row(header, thead, align, border)

        self.apply_rowspans(thead)

        tbody = etree.SubElement(table, 'tbody')
        for row in rows:
            self._build_row(row.strip(), tbody, align, border)

        self.apply_rowspans(tbody)

    def _apply_cell_alignment(self, cell, alignments):
        non_empty_alignments = [a for a in alignments if a]
        if not non_empty_alignments:
            return

        unique_alignments = set(non_empty_alignments)
        if len(unique_alignments) == 1:
            cell.set('align', non_empty_alignments[0])
        else:
            cell.set('align', 'center')

    def _build_row(self, row, parent, align, border):
        """ Given a row of text, build table cells. """
        tr = etree.SubElement(parent, 'tr')
        tag = 'td'
        if parent.tag == 'thead':
            tag = 'th'
        cells = self._split_row(row, border)
        c = None
        c_alignments = []
        # We use align here rather than cells to ensure every row
        # contains the same number of columns.
        for i, a in enumerate(align):

            # After this None indicates that the cell before it should span
            # this column and '' indicates an cell without content
            try:
                text = cells[i]
                if text == '':
                    text = None
            except IndexError:  # pragma: no cover
                text = ''

            # No text after split indicates colspan
            if text == None:
                if c is not None:
                    colspan_str = c.get('colspan')
                    colspan = int(colspan_str) if colspan_str else 1
                    c.set('colspan', str(colspan + 1))
                    c_alignments.append(a)
                    self._apply_cell_alignment(c, c_alignments)
                else:
                    # if this is the first cell, then fall back to creating an empty cell
                    text = ''

            if text != None:
                c = etree.SubElement(tr, tag)
                c.text = text.strip()
                c_alignments = [a]
                self._apply_cell_alignment(c, c_alignments)

    def _split_row(self, row, border):
        """ split a row of text into list of cells. """
        if border:
            if row.startswith('|'):
                row = row[1:]
            if row.endswith('|'):
                row = row[:-1]
        return self._split(row, '|')

    def _split(self, row, marker):
        """ split a row of text with some code into a list of cells. """
        return row.split(marker)

    def _row_has_unpaired_backticks(self, row):
        count_total_backtick = row.count('`')
        count_escaped_backtick = row.count('\\`')
        count_backtick = count_total_backtick - count_escaped_backtick
        # odd number of backticks,
        # we won't be able to build correct code blocks
        return count_backtick & 1


class TableExtension(Extension):
    """ Add tables to Markdown. """

    def extendMarkdown(self, md):
        """ Add an instance of SpanTableProcessor to BlockParser. """
        if '|' not in md.ESCAPED_CHARS:
            md.ESCAPED_CHARS.append('|')
        md.parser.blockprocessors.register(
            SpanTableProcessor(md.parser),
            'spantable',
            76,
        )


def makeExtension(*args, **kwargs):
    return TableExtension(*args, **kwargs)
