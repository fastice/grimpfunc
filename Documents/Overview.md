# grimpfunc — Package Overview

grimpfunc provides utility classes for searching, authenticating against, and
working with [GrIMP](https://nsidc.org/data/measures/grimp) data hosted by
NASA NSIDC.  It is designed to work alongside **nisardev** — grimpfunc
handles discovery, authentication, and bounding-box selection; nisardev
handles the actual data I/O, subsetting, and analysis.

## Import convention

```python
import grimpfunc as grimp
```

## Modules

| Class / function | Description |
|-----------------|-------------|
| [`NASALogin`](NASALogin.md) | Panel widget for NASA EarthData authentication; validates credentials, writes `.netrc`, creates cookie file for GDAL |
| [`cmrUrls`](cmrUrls.md) | Search NSIDC CMR catalog and return COG/shapefile URLs |
| [`boxPicker`](boxPicker.md) | Interactive holoviews map for drawing a bounding box |
| [`Flowlines`](Flowlines.md) | Read glacier flowline shapefiles (Felikson format) and extract profiles |
| `get_urls` | Low-level CMR query function used internally by `cmrUrls` |
| `GrIMPSubsetter` | **Deprecated** — superseded by `nisardev` classes |
| `pointInspector` | Internal tool used by `nisardev.inspect()` — not a direct user API |

---

## Typical workflow

### 1 — Authenticate with NSIDC

```python
import grimpfunc as grimp
import os

# Point GDAL at the cookie file
env = dict(GDAL_HTTP_COOKIEFILE=os.path.expanduser('~/.grimp_download_cookiejar.txt'),
           GDAL_HTTP_COOKIEJAR =os.path.expanduser('~/.grimp_download_cookiejar.txt'))
os.environ.update(env)

# Create and display login widget (prints "Already logged in" if .netrc
# and cookie file already exist; otherwise shows credential entry widget)
myLogin = grimp.NASALogin()
myLogin.view()
```

### 2 — Search for data

```python
# mode='nisar'     → Sentinel velocity mosaics only (NSIDC-0725/0727/0731/0766)
# mode='image'     → SAR image mosaics (NSIDC-0723)
# mode='subsetter' → all products; for GrIMPSubsetter notebook
# mode='terminus'  → terminus positions (NSIDC-0642)
# mode='none'      → all products, cumulative results

myUrls = grimp.cmrUrls(mode='nisar')
myUrls.initialSearch()   # displays Panel search widget, runs default search

# Or supply parameters directly and suppress the widget:
myUrls.initialSearch(firstDate='2014-01-01', lastDate='2026-01-01', product='NSIDC-0725')
```

### 3 — Get COG file list for nisardev

```python
# For velocity series (wildcard replaces the band component; .tif suffix removed)
myCogs = myUrls.getCogs(replace='vv', removeTiff=True)

# For image series (no replace needed)
myCogs = myUrls.getCogs(removeTiff=True)
```

These lists are passed directly to `nisardev` read methods:

```python
import nisardev as nisar

myVelSeries = nisar.nisarVelSeries(numWorkers=4)
myVelSeries.readSeriesFromTiff(myCogs, url=True, readSpeed=False, useStack=True)
```

### 4 — (Optional) Pick a bounding box interactively

```python
# Start with a manually defined box (can then be refined interactively)
bbox = {'minx': -243500, 'miny': -2295000, 'maxx': -149000, 'maxy': -2255000}
myBox = grimp.boxPicker(bbox=bbox)
myBox.plotMap()        # displays interactive map with a box-select tool
bbox = myBox.boxBounds(decimals=-3)   # returns rounded bbox dict
myBox.saveBox('region.yaml')          # save for later reuse

# Reload a saved box
myBox2 = grimp.boxPicker(boxFile='region.yaml')
```

### 5 — (Optional) Work with flowlines

```python
import glob

myShapeFiles = glob.glob('./shpfiles/glacier*.shp')
# Build dict: {glacierID: Flowlines object}, truncated to 50 km from terminus
myFlowlines = {
    x[-8:-4]: grimp.Flowlines(shapefile=x, name=x[-8:-4], length=50e3)
    for x in myShapeFiles
}

# Collect all unique flowline IDs across glaciers
import numpy as np
flowlineIDs = np.unique([fl.flowlineIDs() for fl in myFlowlines.values()])

# Build a shared colour dict (spans all glaciers)
flowlineColors = list(myFlowlines.values())[0].genColorDict(flowlineIDs=flowlineIDs)

# Plot flowlines over a velocity map
import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(6, 12))
myVelSeries.displayVelForDate('2020-01-01', ax=ax, units='km')

for glacierId, fl in myFlowlines.items():
    fl.plotFlowlineLocations(ax=ax, units='km', colorDict=flowlineColors)
    fl.plotGlacierName(ax=ax, units='km', color='w', fontsize=12, first=False)

# Extract points 10 km along each flowline
points10km = myFlowlines['0001'].extractPoints(10, units='km')
# → {'03': (x, y), '06': (x, y), ...}

# Plot speed profile along a central flowline for each year
for myDate in myVelSeries.time:
    myVelSeries.plotProfile(
        *myFlowlines['0001'].xy(index='06', units='km'),
        date=myDate, label=myDate.year, units='km', ax=ax)
```

---

## Supported products

| NSIDC ID | Description |
|----------|-------------|
| NSIDC-0723 | Greenland SAR image mosaics (image, sigma0, gamma0) — 25 m |
| NSIDC-0725 | Annual velocity mosaics — 200 m |
| NSIDC-0727 | Quarterly velocity mosaics — 200 m |
| NSIDC-0731 | Monthly/6-day velocity mosaics — 200 m |
| NSIDC-0766 | 6/12-day velocity mosaics — 200 m |
| NSIDC-0481 | TSX individual glacier velocity (~50 km boxes) — 100 m |
| NSIDC-0646 | Optical individual glacier velocity (~50 km boxes) |
| NSIDC-0642 | Terminus positions (shapefiles) |

---

## Detailed class documentation

| File | Class |
|------|-------|
| [NASALogin.md](NASALogin.md) | EarthData authentication |
| [cmrUrls.md](cmrUrls.md) | NSIDC catalog search |
| [boxPicker.md](boxPicker.md) | Interactive bounding-box selection |
| [Flowlines.md](Flowlines.md) | Glacier flowline utilities |
