# deck.gl-data

Large static data files used by the websites of various vis.gl repositories, to avoid bloating the code repositories.


## Contents

* `website` - large data files used by deck.gl examples
* `images` - images used by deck.gl docs
*   `images/whats-new` - small 150 pixel tall images and GIFS used in what's new pages
*   `images/docs` - Larger images and GIFs used inline in docs


## Compressing Images/GIFs

See [ImageMagick convert docx](https://www.imagemagick.org/script/convert.php)

```
convert input.gif --resize x300 output.gif
```


## Source 
[website/sf-districts.png](https://github.com/uber-common/deck.gl-data/blob/master/website/sf-districts.png) is modified (removed the sea from original image) from [San Francisco districts map.svg](https://commons.wikimedia.org/wiki/File:San_Francisco_districts_map.svg).
