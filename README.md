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
convert --resize x300 input.gif
