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
    LIST_ITEM_RE = re.compile(r'^\s*(?:[-+*]|\d+[.)])\s+')

    def __init__(self, parser, config=None):
        self.config = config or {}
        self.allow_blocks_in_table = self._coerce_bool(
            self.config.get('allow_blocks_in_table', False)
        )
        self.parse_error_marker = self._coerce_bool(
            self.config.get('parse_error_marker', False)
        )
        self.parse_error_marker_text = str(
            self.config.get('parse_error_marker_text', 'TABLE ERROR') or 'TABLE ERROR'
        )
        self._parse_errors = []
        super().__init__(parser)

    def _coerce_bool(self, value):
        if isinstance(value, str):
            return value.strip().lower() in ('1', 'true', 'yes', 'on')
        return bool(value)

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
                (len(td) == 0) and
                bool(td.text) and
                (td.text.startswith('_') or td.text.endswith('_')) and
                (td.text.strip('_ ') == ''))

    def _cell_has_content(self, td):
        return bool((td.text and td.text.strip()) or len(td) > 0)

    def _is_table_row_candidate(self, row, border, expected_columns=None):
        stripped = row.strip()
        if not stripped or '|' not in stripped:
            return False
        cells = self._split_row(stripped, border)
        if expected_columns is not None:
            if (
                self.allow_blocks_in_table
                and expected_columns == 1
                and border
                and not stripped.endswith('|')
            ):
                return False
            return len(cells) == expected_columns
        return len(cells) > 1

    def _is_list_continuation_line(self, row):
        return bool(self.LIST_ITEM_RE.match(row))

    def _is_incomplete_table_row_start(self, row, border, expected_columns=None):
        stripped = str(row or '').strip()
        if not stripped:
            return False
        if border and not stripped.startswith('|'):
            return False
        if self._is_table_row_candidate(stripped, border, expected_columns=expected_columns):
            return False
        return '|' in stripped

    def _append_continuation_to_cells(self, cells, continuation_text, *, starts_list, border, separator=None):
        if not cells:
            return

        cell_index = len(cells) - 1
        while cell_index > 0 and not str(cells[cell_index] or '').strip():
            cell_index -= 1

        existing = str(cells[cell_index] or '').rstrip()
        continuation = str(continuation_text or '').rstrip()
        if border and continuation.endswith('|'):
            continuation = continuation[:-1].rstrip()
        if not continuation:
            return

        if not existing:
            cells[cell_index] = continuation
            return

        joiner = separator if separator is not None else ('\n\n' if starts_list else '\n')
        cells[cell_index] = existing + joiner + continuation

    def _append_block_to_last_row(self, normalized_rows, block_text, *, border):
        if not normalized_rows:
            return False

        last_row = normalized_rows[-1]
        if not isinstance(last_row, list):
            return False

        continuation = str(block_text or '').strip('\n')
        if not continuation.strip():
            return False

        self._append_continuation_to_cells(
            last_row,
            continuation,
            starts_list=self._is_list_continuation_line(continuation),
            border=border,
            separator='\n\n',
        )
        return True

    def _normalize_cell_block_text(self, text):
        lines = str(text or '').split('\n')
        normalized_lines = []

        for line in lines:
            if (
                normalized_lines
                and self._is_list_continuation_line(line)
                and normalized_lines[-1].strip()
                and not self._is_list_continuation_line(normalized_lines[-1])
            ):
                normalized_lines.append('')
            normalized_lines.append(line)

        return '\n'.join(normalized_lines)

    def _record_parse_error(self, detail=None):
        if not self.parse_error_marker:
            return

        message = str(detail or '').strip()
        self._parse_errors.append(message or self.parse_error_marker_text)

    def _append_parse_error_marker(self, parent):
        if not self.parse_error_marker or not self._parse_errors:
            return

        marker = etree.SubElement(parent, 'p')
        marker.set('class', 'markdown-table-error')
        marker.set('data-table-error-count', str(len(self._parse_errors)))

        details = [detail for detail in self._parse_errors if detail]
        if details:
            marker.set('title', ' | '.join(details))

        marker.text = self.parse_error_marker_text

    def _block_is_table_rows(self, block_text, border, expected_columns=None):
        rows = [row.strip() for row in str(block_text or '').split('\n') if row.strip()]
        if not rows:
            return False
        return all(self._is_table_row_candidate(row, border, expected_columns=expected_columns) for row in rows)

    def _block_starts_new_table(self, block_text, border):
        rows = [row for row in str(block_text or '').split('\n') if row.strip()]
        if len(rows) < 2:
            return False
        separator_index = self._find_separator_index(rows, border)
        return separator_index > 0

    def _split_mixed_block(self, block_text, border, expected_columns=None):
        lines = str(block_text or '').split('\n')
        non_empty_indexes = [index for index, line in enumerate(lines) if line.strip()]
        if not non_empty_indexes:
            return None

        for start_index in non_empty_indexes:
            valid_end_index = start_index
            found_table_rows = False

            for index in range(start_index, len(lines)):
                line = lines[index]
                if not line.strip():
                    if found_table_rows:
                        break
                    continue

                if self._is_table_row_candidate(line, border, expected_columns=expected_columns):
                    valid_end_index = index + 1
                    found_table_rows = True
                    continue

                if found_table_rows:
                    break

                valid_end_index = start_index
                break

            if not found_table_rows:
                continue

            prefix = '\n'.join(lines[:start_index]).strip('\n')
            if not prefix.strip():
                return None

            row_lines = lines[start_index:valid_end_index]
            suffix_lines = lines[valid_end_index:]
            return prefix, row_lines, suffix_lines

        return None

    def _last_row_allows_block_continuation(self, entries, border):
        if not border:
            return False

        for entry in reversed(list(entries or [])):
            if isinstance(entry, tuple) and len(entry) == 2 and entry[0] == 'block':
                text = str(entry[1] or '').rstrip()
                if not text.strip():
                    continue
                return not text.endswith('|')

            if isinstance(entry, list):
                return False

            text = str(entry or '').rstrip()
            if not text.strip():
                continue
            return not text.endswith('|')

        return False

    def _collect_body_entries(self, rows, blocks, border, expected_columns=None):
        entries = list(rows or [])
        if not self.allow_blocks_in_table:
            return entries

        while blocks:
            next_block = str(blocks[0] or '')
            if self._block_starts_new_table(next_block, border):
                break

            if self._block_is_table_rows(next_block, border, expected_columns=expected_columns):
                entries.extend(next_block.split('\n'))
                blocks.pop(0)
                continue

            mixed_block = self._split_mixed_block(next_block, border, expected_columns=expected_columns)
            if mixed_block is not None:
                prefix_text, table_rows, trailing_lines = mixed_block
                entries.append(('block', prefix_text))
                entries.extend(table_rows)
                entries.extend(trailing_lines)
                blocks.pop(0)
                continue

            if self._last_row_allows_block_continuation(entries, border):
                entries.append(('block', blocks.pop(0)))
                continue

            if entries and any(
                self._block_is_table_rows(candidate, border, expected_columns=expected_columns)
                for candidate in blocks[1:]
            ):
                entries.append(('block', blocks.pop(0)))
                continue

            break

        return entries

    def _normalize_body_rows(self, rows, border, expected_columns=None):
        if not self.allow_blocks_in_table:
            return [row.strip() for row in rows]

        normalized_rows = []
        list_continuation_active = False
        pending_row_lines = []

        def append_pending_block_text(block_text):
            nonlocal pending_row_lines

            block_lines = str(block_text or '').strip('\n').split('\n')
            if not block_lines or not any(line.strip() for line in block_lines):
                return

            if pending_row_lines and pending_row_lines[-1].strip():
                pending_row_lines.append('')

            pending_row_lines.extend(block_lines)

            if pending_row_lines and pending_row_lines[-1].strip():
                pending_row_lines.append('')

        def flush_pending_row():
            nonlocal pending_row_lines
            if not pending_row_lines:
                return
            self._record_parse_error('Unclosed table row content was normalized with a fallback path.')
            normalized_rows.append('\n'.join(pending_row_lines).strip())
            pending_row_lines = []

        for raw_row in rows:
            if isinstance(raw_row, tuple) and len(raw_row) == 2 and raw_row[0] == 'block':
                if pending_row_lines:
                    append_pending_block_text(raw_row[1])
                    list_continuation_active = False
                    continue
                flush_pending_row()
                if not self._append_block_to_last_row(normalized_rows, raw_row[1], border=border):
                    self._record_parse_error('Dropped detached block continuation while normalizing a table.')
                list_continuation_active = False
                continue

            raw_text = str(raw_row or '')
            if pending_row_lines:
                candidate_row = '\n'.join(pending_row_lines + [raw_text.rstrip()])
                if self._is_table_row_candidate(candidate_row, border, expected_columns=expected_columns):
                    normalized_rows.append(self._split_row(candidate_row, border))
                    pending_row_lines = []
                    list_continuation_active = False
                    continue
                pending_row_lines.append(raw_text.rstrip())
                list_continuation_active = False
                continue

            stripped_row = raw_row.strip()

            if self._is_table_row_candidate(stripped_row, border, expected_columns=expected_columns):
                normalized_rows.append(self._split_row(stripped_row, border))
                list_continuation_active = False
                continue

            if self._is_incomplete_table_row_start(raw_text, border, expected_columns=expected_columns):
                pending_row_lines = [raw_text.rstrip()]
                list_continuation_active = False
                continue

            if normalized_rows and (self._is_list_continuation_line(raw_row) or list_continuation_active):
                self._append_continuation_to_cells(
                    normalized_rows[-1],
                    raw_row.rstrip(),
                    starts_list=(not list_continuation_active),
                    border=border,
                )
                list_continuation_active = True
                continue

            normalized_rows.append(stripped_row)
            list_continuation_active = False

        flush_pending_row()
        return normalized_rows

    def _render_cell_content(self, cell, text):
        stripped_text = text.strip()
        if self.allow_blocks_in_table and '\n' in stripped_text:
            self.parser.parseChunk(cell, self._normalize_cell_block_text(stripped_text))
            return
        cell.text = stripped_text

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

                        if not self._cell_has_content(td):
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
        self._parse_errors = []
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
        expected_columns = len(self._split_row(separator, border))
        rows = self._collect_body_entries(rows, blocks, border, expected_columns=expected_columns)

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
        for row in self._normalize_body_rows(rows, border, expected_columns=expected_columns):
            self._build_row(row, tbody, align, border)

        self.apply_rowspans(tbody)
        self._append_parse_error_marker(parent)

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
        if isinstance(row, (list, tuple)):
            cells = list(row)
        else:
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
                self._render_cell_content(c, text)
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

    def __init__(self, *args, **kwargs):
        self.config = {
            'allow_blocks_in_table': [False, 'Allow block continuation content inside table cells'],
            'parse_error_marker': [False, 'Render a marker when table content falls back due to malformed rows'],
            'parse_error_marker_text': ['TABLE ERROR', 'Marker text to render when table parsing falls back'],
        }
        super().__init__(*args, **kwargs)

    def extendMarkdown(self, md):
        """ Add an instance of SpanTableProcessor to BlockParser. """
        if '|' not in md.ESCAPED_CHARS:
            md.ESCAPED_CHARS.append('|')
        md.parser.blockprocessors.register(
            SpanTableProcessor(md.parser, self.getConfigs()),
            'spantable',
            76,
        )


def makeExtension(*args, **kwargs):
    return TableExtension(*args, **kwargs)
