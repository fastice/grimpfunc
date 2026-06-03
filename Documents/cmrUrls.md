# cmrUrls — NSIDC Catalog Search

Searches the NASA Common Metadata Repository (CMR) for GrIMP products and
returns lists of COG/shapefile URLs.  The class wraps a Panel/param widget
that can display an interactive search panel, or can be driven
programmatically by passing parameters to `initialSearch()`.

---

## Construction

```python
import grimpfunc as grimp

myUrls = grimp.cmrUrls(mode='nisar')
```

**`mode`** controls which products can be searched and how results accumulate:

| Mode | Products available | Cumulative? | Typical use |
|------|--------------------|-------------|-------------|
| `'nisar'` | NSIDC-0725, 0727, 0731, 0766 | No | velocity notebooks |
| `'image'` | NSIDC-0723 | No | image notebooks |
| `'subsetter'` | all products (including 0481) | No | GrIMPSubsetter notebook |
| `'terminus'` | NSIDC-0642 | No | terminus positions |
| `'none'` | all products | Yes (searches accumulate) | custom workflows |

---

## Searching

### `initialSearch`

```python
myUrls.initialSearch(firstDate=None, lastDate=None, product=None, productFilter=None)
```

Run an initial search and display the Panel widget.  Parameters set the
initial widget state; the user can then refine the search interactively.

| Parameter | Description |
|-----------|-------------|
| `firstDate` | `'YYYY-MM-DD'` string; start of date range |
| `lastDate` | `'YYYY-MM-DD'` string; end of date range |
| `product` | NSIDC product ID (e.g. `'NSIDC-0725'`).  Must be valid for the current mode. |
| `productFilter` | Band/type filter (e.g. `'velocity'`, `'velocity+errors'`, `'image'`, `'sigma0'`, `'gamma0'`).  Depends on product. |

**Examples:**

```python
# Velocity mosaics (all Sentinel products), default search
myUrls = grimp.cmrUrls(mode='nisar')
myUrls.initialSearch()

# Restricted date range, suppress widget output
myUrls.initialSearch(firstDate='2014-01-01', lastDate='2026-01-01');

# Image mosaics, only 'image' band
myImageUrls = grimp.cmrUrls(mode='image')
myImageUrls.initialSearch(firstDate='2020-01-01', lastDate='2020-05-01',
                           productFilter='image')

# Sigma0 products
mySigma0Urls = grimp.cmrUrls(mode='image')
mySigma0Urls.initialSearch(firstDate='2020-01-01', lastDate='2020-05-01',
                            productFilter='sigma0');
```

### `productFilter` options by product

| Product | Valid filters |
|---------|--------------|
| NSIDC-0723 | `'image'`, `'gamma0'`, `'sigma0'` |
| NSIDC-0725/0727/0731/0766 | `'speed'`, `'velocity'`, `'velocity+errors'`, `'all'` |
| NSIDC-0481/0646 | `'speed'`, `'velocity'`, `'velocity+errors'`, `'all'` |
| NSIDC-0642 | `'termini'` |

---

## Getting results

### `getCogs`

```python
myCogs = myUrls.getCogs(replace=None, removeTiff=False)
```

Return a list of COG `.tif` URLs (or local paths) from the search results.

| Parameter | Description |
|-----------|-------------|
| `replace` | If given, replace this band token with `'*'` (e.g. `replace='vv'` turns `filename.vv.tif` → `filename.*.tif`). Used to create wildcard names for nisardev read methods. |
| `removeTiff` | Strip the `.tif` suffix if `True`. |

**Standard patterns for nisardev:**

```python
# Velocity series: wildcard replaces band, suffix removed
myCogs = myUrls.getCogs(replace='vv', removeTiff=True)
# → ['https://.../GL_vel_mosaic_Annual_01Dec14_30Nov15_*_v05.0', ...]

# Image series: no replace needed
myCogs = myUrls.getCogs(removeTiff=True)
```

### `getShapes`

```python
shapes = myUrls.getShapes()
```

Return a list of `.shp` shapefile URLs (for terminus products).

### `checkIDs`

```python
if myUrls.checkIDs(['NSIDC-0725', 'NSIDC-0727']):
    ...
```

Return `True` if any of the given product IDs appear in the current result
set.  Used in the subsetter notebook to branch on product type.

### `getIDs`

```python
ids = myUrls.getIDs()   # e.g. ['NSIDC-0725']
```

Return the unique set of NSIDC product IDs in the current result set.

### `findTSXBoxes`

```python
boxes = myUrls.findTSXBoxes()  # e.g. ['W69.10N', 'W70.55N']
```

Return the unique TSX/OPT box names present in the current COG list.
Returns `['']` when no box-named products are present.

---

## Interactive panel

`initialSearch()` returns a Panel layout that can be displayed in Jupyter.
The search panel contains:
- Product radio buttons
- Product filter dropdown
- Date pickers
- Search / Clear buttons
- Results table showing matching products and their dates

If the Panel widget is unresponsive (search button does nothing), re-run the
cell containing `initialSearch()`.

---

## Low-level search function

`get_urls` is the underlying CMR query function, exposed at the package level
for advanced use:

```python
urls = grimp.get_urls(short_name, version, time_start, time_end,
                      bounding_box, polygon, filename_filter, verbose=False)
```

It is not normally called directly — `cmrUrls` handles version auto-increment
and result filtering automatically.
