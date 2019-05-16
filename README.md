Program to convert MARC Bibliographic  data fields using ysa, allars, musa and cilla thesaurus terms into using terms from YSO and SLM ontologies.

Fields with the old terms are removed (option).

Source data can be in MARC21 or MARCXML format. Resulting data is in MARCXML.

Input fields 385, 567, 648, 650, 651, 655. Output fields: 370, 385, 388, 567, 648, 650, 651, 653, 655, 884.

First version handles only text based records, not records of music recordings, notes, films nor videos.

Required Python libraries: pymarc, rdflib, unidecode. Use "pip install" to install them.

Usage: python yso_converter.py 
with command line arguments:
-f="marc21" (file format, possible values: "marc21" and "marcxml" 
-i="input.mrc" (input file path) 
-o="output.mrc" (output file path)