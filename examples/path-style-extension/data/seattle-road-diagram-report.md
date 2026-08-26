# Seattle road-diagram extraction report

Generated: 2026-08-25T23:06:11.278Z

Candidate: Dexter Avenue N and Thomas Street, Seattle, Washington

Display bounds: `-122.3431, 47.62025, -122.3415, 47.6215`

Extraction gate: **PASS**

## Source summary

| Layer | Features | Geometry | Multipart | Exact duplicates | Near duplicates |
| --- | ---: | --- | ---: | ---: | ---: |
| VerticalElements | 161 | LineString, MultiLineString | 138 | 0 | 46 |
| LaneWidth | 20 | Point | 0 | 0 | 0 |
| GENBKGRND | 4 | LineString | 0 | 0 | 0 |
| PanelMarkings | 320 | LineString, MultiLineString | 2 | 36 | 36 |
| Longitudinal_Markings | 174 | LineString | 0 | 0 | 0 |
| TransverseMarkings | 74 | LineString | 0 | 0 | 0 |
| Legend_and_Symbols | 17 | MultiLineString | 17 | 0 | 0 |
| Seattle Streets | 4 | LineString | 0 | 0 | 0 |
| Sidewalks | 14 | LineString | 0 | 0 | 0 |
| Marked Crosswalks | 2 | Point | 0 | 0 | 0 |
| Existing Bike Facilities | 4 | LineString | 0 | 0 | 0 |

## Gate criteria

| Criterion | Result |
| --- | --- |
| twoLongitudinalPatterns | pass |
| trueDashSkipPattern | pass |
| denseDashedPath | pass |
| bicyclePanel | pass |
| markedCrosswalk | pass |
| curbOrSeparator | pass |
| streetSurfaceWidth | pass |
| laneWidths | pass |
| sourceContext | pass |

## Key source values

- Longitudinal marking types: 10'/20' pattern, 2' dash, 4' skip, Solid
- Longitudinal colors: White, Yellow
- Longitudinal source widths: none in this CAD crop
- Lane-width annotations: 10, 12, 2, 3, 4, 42, 5, 6, 8, 9
- Lane-band spatial-join residuals: 1.42, 55.54 meters

The channelization records around Dexter and Thomas preserve authoritative geometry and dash class,
but most descriptive asset fields are null in this CAD-derived crop. The example reports those nulls
instead of inventing values. Longitudinal stroke widths therefore use an explicitly labeled
cartographic fallback while dash/skip lengths come directly from the source `Type` values.

## Transformations

- Requested a bounded EPSG:4326 snapshot and paged by sorted object ID.
- Preserved all returned source properties and geometry.
- Derived continuous pavement-symbol paths by joining source fragment endpoints within 0.002 meters; no source vertex was moved.
- Derived equal-width lane bands from official street centerlines plus the nearest 12-foot lane-width annotations.
- Derived two crosswalk guides from official in-service inventory points and official street surface widths; matched source stripe polygons remain pinned but are not double-painted.
- Did not simplify, manually redraw, or snap the pinned official channelization geometry.

## License and limitations

City of Seattle Department of Transportation data is used under PDDL 1.0. This visualization and
its derived cartographic constructions are for demonstrating deck.gl rendering. They are not for
engineering, construction, legal interpretation, or navigation.
