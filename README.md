# deck.gl-data

Large static data files used by the websites of various vis.gl repositories, to avoid bloating the code repositories.


## Contents

* `website` - large data files used by deck.gl examples
* `images` - images used by deck.gl docs
*   `images/whats-new` - small 150 pixel tall images and GIFS used in what's new pages
*   `images/docs` - Larger images and GIFs used inline in docs
* `luma.gl` - assets for luma.gl

## Instructions

### Compressing Images/GIFs

See [ImageMagick convert docx](https://www.imagemagick.org/script/convert.php)

```
convert input.gif --resize x300 output.gif
```

## Attributions / Licenses / Data Sources

### 3D Tiles

* `3d-tiles/RoyalExhibitionBuilding`

The Royal Exhibition Building World Heritage Site in Melbourne, Australia, captured with the Zebedee handheld mapping system.

- [Zebedee 3D Data Collection](https://data.csiro.au/dap/landingpage?list=SEA&pid=csiro:13281&sb=RELEVANCE&rn=5&rpp=25&p=1&tr=8&q=zebedee&dr=all)
- [PDF](https://data.csiro.au/dap/SupportingAttachment?collectionId=13281&fileId=790)
 - Zebdee offers the data publicly under the Creative Commons Attribution 3.0 Unported License.
- Tiling generously provided by Cesium ion / https://cesium.com/


### Images

[website/sf-districts.png](https://github.com/uber-common/deck.gl-data/blob/master/website/sf-districts.png) is modified (removed the sea from original image) from [San Francisco districts map.svg](https://commons.wikimedia.org/wiki/File:San_Francisco_districts_map.svg).

[examples/mesh/minicooper.obj](https://github.com/uber-common/deck.gl-data/blob/master/examples/mesh/minicooper.obj) is from John Burkardt's [data sample collection](https://people.sc.fsu.edu/~jburkardt/data/data.html)
