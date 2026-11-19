# World Ocean Atlas 2023 (WOA23)

Source: NOAA National Centers for Environmental Information (NCEI),
[World Ocean Atlas 2023](https://www.ncei.noaa.gov/products/world-ocean-atlas),
NCEI Accession 0270533. Annual, 1°, all-decades average (`decav`, 1955–2022).

Cite the product and the volume for each variable:

- Reagan, J.R., T.P. Boyer, H.E. García, R.A. Locarnini, O.K. Baranova, C. Bouchard,
  S.L. Cross, A.V. Mishonov, C.R. Paver, D. Seidov, Z. Wang and D. Dukhovskoy (2024).
  World Ocean Atlas 2023. NOAA National Centers for Environmental Information.
  Dataset: NCEI Accession 0270533.
- Locarnini, R.A., A.V. Mishonov, O.K. Baranova, J.R. Reagan, T.P. Boyer, D. Seidov,
  Z. Wang, H.E. Garcia, C. Bouchard, S.L. Cross, C.R. Paver and D. Dukhovskoy (2023).
  World Ocean Atlas 2023, Volume 1: Temperature. A. Mishonov, Technical Editor.
  NOAA Atlas NESDIS 89. https://doi.org/10.25923/54bh-1613
- Reagan, J.R., D. Seidov, Z. Wang, D. Dukhovskoy, T.P. Boyer, R.A. Locarnini,
  O.K. Baranova, A.V. Mishonov, H.E. Garcia, C. Bouchard, S.L. Cross and C.R. Paver
  (2023). World Ocean Atlas 2023, Volume 2: Salinity. A. Mishonov, Technical Editor.
  NOAA Atlas NESDIS 90. https://doi.org/10.25923/70qt-9574

License: the source files state "These data are openly available to the public.
Please acknowledge the use of these data with the text given in the acknowledgment
attribute." The NCEI product page states "WOA data are available free of charge."
No named license (such as CC0) applies, so the STAC Collection uses
`license: "other"` and links this evidence. See
[license-evidence.json](license-evidence.json). The repository MIT license applies
to the conversion scripts only.

Changes: `grids.parquet` keeps every cell, standard depth and statistic of the two
source files, with unchanged float32/int32 values and fill values as null. The
display preview (`preview.bin.gz`) is decimated (every second node) and quantized
(0.01 °C and 0.01 salinity units) at 33 of the 102 standard depths.
