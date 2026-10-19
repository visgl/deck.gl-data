# Upstream source audit checklist

**Status: no third-party paleogeographic archive approved or ingested.**

Record one entry per upstream dataset release before redistribution.

| Field | Required evidence |
| --- | --- |
| Dataset title and DOI | Permanent record identifying the exact release |
| Version and original download URL | Immutable source version or archived checksum |
| Rights holder and individual contributors | Dataset citation and embedded file notices |
| License | Explicit license covering the **specific archive and layers** |
| Third-party layers | Separate permissions for every redistributed component |
| Geometry semantics | Present-day evidence or reconstructed epoch, with source frame |
| Feature fields | Name, type, plate ID, age interval, and source-native IDs |
| Processing | Pinned converter version and complete transformation notes |
| Verification | Source/output SHA-256, row counts, geometry validity |
| STAC | Correct license, producer, snapshot time, source link, immutable asset URL |

EarthByte GPlates sample data are a **candidate**, not automatically an approved
redistribution source. Check the exact release's licensing and any third-party
data attribution before adding files. Macrostrat aggregates geological sources,
so rights may differ by component. Do not bulk-ingest PALEOMAP without permission.

The catalogue must not advertise a downloadable asset before that asset exists.
Do not infer ancient geometry by attaching present-day coordinates to an age.
