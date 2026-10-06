---
name: robust-data-cleaning-and-output
description: Use when processing tabular data, cleaning records, and formatting JSON and CSV outputs.
---
- Convert monetary values into integer cents before writing output data structures.
- Construct the required metadata block containing source filename, total input rows including duplicates, and valid rows used.
- Normalize categorical fields, parse dates to UTC, filter out invalid records, and write the cleaned records to the designated CSV file.
