# Earth reference dataset conversion

`prepare-reference.py` promotes existing repository snapshots to attributed Earth
assets. It validates input bytes against the committed source-reference.json before
conversion. Originals remain at their legacy paths, preserving existing consumers.

Install requirements-reference.txt in an isolated environment, fetch the original
LFS assets, then run:

```sh
python earth/scripts/prepare-reference.py --source-root /path/to/deck.gl-data
```

Output defaults to this repository's earth directory. `--out` supports a separate
output root. Repeated runs exclude manifests and attribution from data inventories.
Conversion verifies Arrow/Parquet equality for every vector row and checks every
geoid raw pixel and scaled meter height. EGM2008 is processed in 120-row latitude
bands, with independent Parquet row groups and an index in the manifest.

Scientific data keeps its original license; scripts are MIT. Attribution, exact
source commit, legacy paths, checksums, changes and file inventories accompany each
dataset. STAC dates denote repository snapshot commits, not field observations.
