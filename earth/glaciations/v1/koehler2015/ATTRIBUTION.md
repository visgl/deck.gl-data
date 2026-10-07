# koehler2015

Source: Köhler, de Boer, von der Heydt, Stap and van de Wal (2015). [https://doi.pangaea.de/10.1594/PANGAEA.855449](https://doi.pangaea.de/10.1594/PANGAEA.855449).

Scientific data, source files, Parquet conversions and preview assets retain
[CC-BY-3.0](https://creativecommons.org/licenses/by/3.0/), separate from MIT conversion code.

Changes: original archive/NetCDF retained; Parquet changes storage and expresses
age as positive ka before present. No source spatial decimation or quantization
in Parquet. Preview assets use the math.gl display conversion documented in
README.md. Climate JSON is a 0–120 ka subset; its UI rebases temperature variant 1
to its 0 ka value. Parquet retains the original temperature reference and uncertainties.
