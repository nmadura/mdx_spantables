# mdx_spantables

Extension for python-markdown allowing cells in tables to span multiple rows or columns

This is a slightly modified version of the tables extension that comes with
[python-markdown](https://github.com/Python-Markdown/markdown).

## Requirements

- Markdown>=3.10.2
- pymdown-extensions>=10.0

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

The pretty layout of the above table is only for readability. The next table is
equivalent to the above one:

    |head1|head2|
    |-|-|
    |span two cols||
    |span two rows| |
    |_| |

Note that the single spaces in the right cell of the last two rows are
significant. Without them the left cells would not only span over two rows, but
also over two columns.

Row spanning will create a single cell from the cell with the underscore upto
and including the first non-empty cell above it:

    | head         |
    | ------------ |
    | regular cell |
    | span 2 rows  |
    |_             |

However, if the first non-empty cell above it is the end of an earlier span of
rows, then it will be excluded. The table below would have two cells that each
span two rows:

    | head        |
    | ----------- |
    | span 2 rows |
    |_            |
    |             |
    |_            |

Row spanning also only includes cells that span the same set of columns.

    |             |            |
    | ----------- | ---------- |
    | not included in rowspan ||
    | span 2 rows |            |
    |_            |            |

    |             |            |
    | ----------- | ---------- |
    | span 2 columns and rows ||
    |_                        ||

6 Mar 2026: Added the ability to have multiple header rows

    | span 2 hdr rows | span 2 hdr cols   ||
    |_                | subhead | subhead  |
    | --------------- | ------- | -------- |
    | span 2 rows     |   2     |   1      |
    |_                |   3     |   4      |

Added support for setting column alignment using the typical ':' :

    |  centered span  | span 2 hdr cols   ||
    |_                | subhead | subhead  |
    |:---------------:|:------- | --------:|
    |  centered span  | LH      |       RH |
    |_                | LH      |       RH |
