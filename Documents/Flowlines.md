# Flowlines — Glacier Flowline Utilities

Reads glacier flowline shapefiles (currently in the
[Felikson et al., 2020](https://agupubs.onlinelibrary.wiley.com/doi/10.1029/2020GL090112)
format) and provides utilities for extracting coordinates, computing
distances along flowlines, plotting, and integrating with nisardev velocity
data.

---

## Construction

```python
import grimpfunc as grimp

fl = grimp.Flowlines(shapefile='glacier0001.shp', name='0001', length=50e3)
```

**Parameters:**
- `shapefile` — path to a `.shp` file
- `name` — label used for plotting (e.g. the glacier ID)
- `length` — if given, truncate each flowline to the first `length` metres from the start.  Use a negative value to keep the *last* portion.
- `epsg` — EPSG code for the output projection (default: 3413 — Greenland polar stereographic)
- `shapeFormat` — parser to use (default: `'felikson'`; currently the only built-in format)
- `altParser` — callable `(self, shapeTable) -> dict` for custom shapefile formats

---

## Key attributes

| Attribute | Description |
|-----------|-------------|
| `flowlines` | Dict of `{flowlineID: {'x': array, 'y': array, 'd': array}}` |
| `bounds` | Bounding box dict `{'minx', 'miny', 'maxx', 'maxy'}` of all flowlines (with padding) |
| `name` | Glacier name/label |

The inner dict for each flowline:
- `'x'` — x coordinates (metres, EPSG:3413)
- `'y'` — y coordinates (metres)
- `'d'` — cumulative distance from the start (metres)

---

## Loading multiple glaciers

The typical pattern from the Flowlines notebook:

```python
import glob
import numpy as np

shapeFiles = glob.glob('./shpfiles/glacier*.shp')

# Build a dict keyed by glacier ID (last 4 chars of filename before .shp)
myFlowlines = {
    x[-8:-4]: grimp.Flowlines(shapefile=x, name=x[-8:-4], length=50e3)
    for x in shapeFiles
}
# e.g. myFlowlines['0001'], myFlowlines['0002'], ...
```

---

## Coordinate access

### `xy`

```python
x, y = fl.xy(index=None, units='m')
```

Return `(x, y)` arrays for a single flowline.

- `index` — flowline ID string (e.g. `'06'`); if `None`, uses the first flowline
- `units` — `'m'` (default) or `'km'`

**Typical use** — pass directly to nisardev `plotProfile`:

```python
myVelSeries.plotProfile(*fl.xy(index='06', units='km'),
                         date=myDate, units='km', ax=ax)
```

### `flowlineDistance`

```python
d = fl.flowlineDistance(index=None, units='m')
```

Return the cumulative distance array along a flowline.

---

## Point extraction

### `extractPoint`

```python
x, y = fl.extractPoint(distance=10, index='06', units='km')
```

Return the `(x, y)` coordinate of the point nearest to `distance` from the
start of the flowline.

### `extractPoints`

```python
points = fl.extractPoints(distance=10, indices=None, units='km')
# → {'03': (x, y), '06': (x, y), ...}
```

Return a dict of points at a given distance from the start for all (or
specified) flowlines.  `indices=None` uses all flowline IDs.

**Example — extract and plot points 10 km from terminus:**

```python
points10km = fl.extractPoints(10, units='km')
for key in points10km:
    ax.plot(*points10km[key], 'r.')
```

---

## Plotting

### `plotFlowlineLocations`

```python
fl.plotFlowlineLocations(ax=ax, units='km', indices=None, colorDict=None, **kwargs)
```

Plot all (or specified) flowlines on `ax`.

- `colorDict` — dict mapping flowline ID → colour (see `genColorDict` below)
- `indices` — list of flowline IDs to plot; `None` plots all
- `**kwargs` — passed to `ax.plot` (e.g. `linewidth`, `alpha`)

### `plotGlacierName`

```python
fl.plotGlacierName(ax=ax, units='km', index=None, first=False,
                   xShift=0, yShift=0, **kwargs)
```

Annotate the glacier name (`self.name`) on the map.

- `first` — `True` places the label at the start of the flowline; `False` at the end
- `xShift`, `yShift` — offset the label in map units
- `**kwargs` — passed to `ax.text` (e.g. `color='w'`, `fontsize=12`, `fontweight='bold'`)

---

## Colour maps

### `genColorDict`

```python
colorDict = fl.genColorDict(flowlineIDs=None)
```

Return a dict mapping flowline ID → colour from matplotlib's TABLEAU palette.
Pass an external `flowlineIDs` list to create a colour dict that spans
multiple glacier objects with consistent colouring.

**Example — consistent colours across all glaciers:**

```python
# Collect all unique IDs from every glacier
flowlineIDs = np.unique([fl.flowlineIDs() for fl in myFlowlines.values()])
# Build colour dict from any one instance
flowlineColors = list(myFlowlines.values())[0].genColorDict(flowlineIDs=flowlineIDs)
# Use when plotting each glacier
fl.plotFlowlineLocations(ax=ax, units='km', colorDict=flowlineColors)
```

---

## Bounding boxes

### `computeBounds`

```python
fl.computeBounds(pad=10e3)
```

Recompute `fl.bounds` from the current flowline coordinates with `pad` metres
of padding.  Called automatically after `readShape` and `truncate`.

### `mergeBounds`

```python
merged = fl.mergeBounds(bounds1, bounds2)
```

Return the union of two bounding box dicts.  Useful for computing the combined
extent across multiple glaciers:

```python
myBounds = {'minx': 1e9, 'miny': 1e9, 'maxx': -1e9, 'maxy': -1e9}
for fl in myFlowlines.values():
    myBounds = fl.mergeBounds(myBounds, fl.bounds)
```

---

## Other methods

| Method | Description |
|--------|-------------|
| `readShape(shapefile, ...)` | (Re-)read a shapefile; called automatically by `__init__`. |
| `truncate(indices, length, pad)` | Clip flowlines to `length` metres; `indices=None` truncates all. |
| `computeDistance(x, y)` | Compute cumulative distance along x/y arrays. |
| `flowlineIDs()` | Return list of flowline ID strings. |
| `checkUnits(units)` | Validate that `units` is `'m'` or `'km'`; prints a message and returns `False` if invalid. |

---

## Complete example (from Flowlines notebook)

```python
import grimpfunc as grimp
import nisardev as nisar
import numpy as np
import matplotlib.pyplot as plt
import glob

# Load flowlines (truncated to 50 km from terminus)
shapeFiles = glob.glob('./shpfiles/glacier*.shp')
myFlowlines = {x[-8:-4]: grimp.Flowlines(shapefile=x, name=x[-8:-4], length=50e3)
               for x in shapeFiles}

# Build combined bounding box
myBounds = {'minx': 1e9, 'miny': 1e9, 'maxx': -1e9, 'maxy': -1e9}
for fl in myFlowlines.values():
    myBounds = fl.mergeBounds(myBounds, fl.bounds)

# Load velocity data (auth + search done previously)
myVelSeries = nisar.nisarVelSeries(numWorkers=4)
myVelSeries.readSeriesFromTiff(myCogs, url=True, readSpeed=False, useStack=True)
myVelSeries.subsetVel(myBounds)
myVelSeries.loadRemote()

# Build shared colour dict
flowlineIDs = np.unique([fl.flowlineIDs() for fl in myFlowlines.values()])
flowlineColors = list(myFlowlines.values())[0].genColorDict(flowlineIDs=flowlineIDs)

# Velocity map with flowlines
fig, ax = plt.subplots(figsize=(6, 12))
myVelSeries.displayVelForDate('2020-01-01', ax=ax, units='km', vmin=0, vmax=2000)
for glacierId, fl in myFlowlines.items():
    fl.plotFlowlineLocations(ax=ax, units='km', colorDict=flowlineColors)
    fl.plotGlacierName(ax=ax, units='km', color='w', fontsize=12,
                       fontweight='bold', first=False)

# Speed profiles along the central flowline for each year
flowlineId = '06'
fig, axes = plt.subplots(2, 4, figsize=(18, 9))
for glacierId, ax in zip(myFlowlines, axes.flatten()):
    for myDate in myVelSeries.time:
        myVelSeries.plotProfile(
            *myFlowlines[glacierId].xy(index=flowlineId, units='km'),
            date=myDate, label=myDate.year, units='km', ax=ax)
    myVelSeries.labelProfilePlot(ax, title=f'Glacier {glacierId}')
    ax.legend(ncol=2, loc='upper right')
plt.tight_layout()
```
