# boxPicker — Interactive Bounding-Box Selection

Displays a SAR image basemap (loaded from NSIDC) in a holoviews/Panel
widget.  The user draws a rectangle on the map with the box-select tool;
the resulting bounding box can then be passed to nisardev subset methods
or saved to a YAML file for later reuse.

---

## Construction

```python
import grimpfunc as grimp

# Start with a manually defined box (metres, EPSG:3413)
bbox = {'minx': -243500, 'miny': -2295000, 'maxx': -149000, 'maxy': -2255000}
myBox = grimp.boxPicker(bbox=bbox)

# Start from a previously saved YAML file
myBox = grimp.boxPicker(boxFile='region.yaml')

# Default box (Jakobshavn area)
myBox = grimp.boxPicker()
```

**Parameters:**
- `bbox` — initial bounding box dict `{'minx', 'miny', 'maxx', 'maxy'}` in metres
- `boxFile` — YAML file path to load a previously saved box (overrides `bbox`)
- `mapUrl` — NSIDC URL for the basemap image (default: auto-fetched 2020 image mosaic)
- `numWorkers` — dask worker threads for loading the basemap (default: 2)

---

## Methods

### `plotMap`

```python
mapview = myBox.plotMap(show=True)
```

Display the SAR image basemap with the current box outlined in red.
Users can redraw the box using the box-select tool in the plot toolbar.

- `show` — `True` (default) renders the map widget; `False` skips rendering
  (used in the subsetter notebook when TSX products are selected, since those
  don't need spatial subsetting)

### `boxBounds`

```python
bbox = myBox.boxBounds(decimals=-3)
```

Return the current bounding box as a dict `{'minx', 'miny', 'maxx', 'maxy'}`.

- `decimals` — rounding argument passed to `numpy.around` (default: `-3`,
  which rounds to the nearest 1 km).  Use `-2` for 100 m rounding.

Pass the result directly to nisardev subset methods:

```python
myVelSeries.subsetVel(myBox.boxBounds(decimals=-3))
```

### `saveBox`

```python
myBox.saveBox('region.yaml')
```

Write the current bounding box to a YAML file.  The `.yaml` extension is
added automatically if not already present.

### `readBox`

```python
bbox = myBox.readBox('region.yaml')
```

Load a bounding box dict from a YAML file.  Returns the default
(Jakobshavn) box and prints a warning if the file does not exist.

---

## Typical workflow in the subsetter notebook

```python
import grimpfunc as grimp

# 1 — create with a starting box
bbox = {'minx': -243500, 'miny': -2295000, 'maxx': -149000, 'maxy': -2255000}
myBox = grimp.boxPicker(bbox=bbox)

# 2 — show interactive map (user adjusts box with box-select tool)
myBox.plotMap()

# 3 — retrieve the (possibly adjusted) box, rounded to 1 km
bbox = myBox.boxBounds(decimals=-3)

# 4 — apply to nisardev object
myVelSeries.subsetVel(bbox)
myVelSeries.loadRemote()

# 5 — save for future reuse
myBox.saveBox('GlacierSubset.yaml')

# — later: reload the box —
myBox2 = grimp.boxPicker(boxFile='GlacierSubset.yaml')
```
