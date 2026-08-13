# CLAUDE.md — grimpfunc

Public-facing utility package for discovering, authenticating against, and accessing [GrIMP](https://nsidc.org/data/measures/grimp) data products hosted at NASA NSIDC. Designed for notebook users; see the [packages CLAUDE.md](../CLAUDE.md) for pipeline context. Companion to `nisardev` — grimpfunc handles discovery/auth/bbox selection, `nisardev` handles data I/O and analysis.

This package has its own detailed docs in `Documents/` (Overview, NASALogin, cmrUrls, boxPicker, Flowlines) — read those for full detail. This file is a quick-orientation summary.

## Import convention

```python
import grimpfunc as grimp
```

## Modules / Classes

| Module | Class / function | Purpose |
|---|---|---|
| `NASALogin.py` | `NASALogin` | NASA EarthData auth: validates credentials, writes `~/.netrc`, creates cookie jar for GDAL |
| `cmrUrls.py` | `cmrUrls` | Search NSIDC CMR catalog (Panel widget or programmatic); returns COG/shapefile URL lists |
| `cmr.py` | `get_urls`, `cmr_filter_urls` | Low-level CMR query helpers used internally by `cmrUrls` |
| `cmrUrls.py` | `cmrUrls` | — |
| `boxPicker.py` | `boxPicker` | Interactive holoviews/Panel map for drawing/saving a bounding box |
| `Flowlines.py` | `Flowlines` | Read Felikson-format glacier flowline shapefiles; profile extraction & plotting |
| `GrIMPSubsetter.py` | `GrIMPSubsetter` | **Deprecated** — superseded by `nisardev` |
| `pointInspector.py` | `pointInspector` | Internal helper used by `nisardev.inspect()`; not a direct user API |

## Typical workflow

```python
import grimpfunc as grimp
import os

# 1. Auth — point GDAL at the cookie file, then login
env = dict(GDAL_HTTP_COOKIEFILE=os.path.expanduser('~/.grimp_download_cookiejar.txt'),
           GDAL_HTTP_COOKIEJAR =os.path.expanduser('~/.grimp_download_cookiejar.txt'))
os.environ.update(env)
myLogin = grimp.NASALogin()
myLogin.view()   # prints "Already logged in" if .netrc + cookie file exist

# 2. Search CMR
myUrls = grimp.cmrUrls(mode='nisar')   # 'nisar','image','subsetter','terminus','none'
myUrls.initialSearch(firstDate='2014-01-01', lastDate='2026-01-01', product='NSIDC-0725')

# 3. Get COG list for nisardev
myCogs = myUrls.getCogs(replace='vv', removeTiff=True)

# 4. (optional) interactive bbox
myBox = grimp.boxPicker(bbox={'minx': -243500, 'miny': -2295000,
                               'maxx': -149000, 'maxy': -2255000})
myBox.plotMap()
bbox = myBox.boxBounds(decimals=-3)
myBox.saveBox('region.yaml')

# 5. (optional) flowlines
fl = grimp.Flowlines(shapefile='glacier0001.shp', name='0001', length=50e3)
x, y = fl.xy(index='06', units='km')
```

## `cmrUrls` modes and product filters

| `mode` | Products | Cumulative |
|---|---|---|
| `'nisar'` | NSIDC-0725, 0727, 0731, 0766 (velocity) | No |
| `'image'` | NSIDC-0723 (SAR image mosaics) | No |
| `'subsetter'` | all (incl. 0481) | No |
| `'terminus'` | NSIDC-0642 (termini) | No |
| `'none'` | all | Yes — searches accumulate |

Key methods: `initialSearch(firstDate, lastDate, product, productFilter)`, `getCogs(replace=None, removeTiff=False)`, `getShapes()`, `checkIDs(ids)`, `getIDs()`, `findTSXBoxes()`.

## Supported NSIDC products

| ID | Description |
|---|---|
| NSIDC-0723 | Greenland SAR image mosaics (image/sigma0/gamma0), 25 m |
| NSIDC-0725/0727/0731/0766 | Annual/Quarterly/Monthly/6-12-day velocity mosaics, 200 m |
| NSIDC-0481 | TSX individual glacier velocity (~50 km boxes), 100 m |
| NSIDC-0646 | Optical individual glacier velocity |
| NSIDC-0642 | Terminus positions (shapefiles) |

## Notes

- **Auth/credential requirement**: `NASALogin` requires a NASA EarthData account (https://urs.earthdata.nasa.gov). It writes plaintext credentials to `~/.netrc` (mode `0600`) and an empty cookie jar at `~/.grimp_download_cookiejar.txt`; GDAL completes the OAuth2 flow on first remote COG access. Both `GDAL_HTTP_COOKIEFILE` and `GDAL_HTTP_COOKIEJAR` env vars must be set before any remote data access (also needed in QGIS via `Settings → Options → System → Environment`).
- If the cookie jar is stale/corrupted: `myLogin.resetCookie()` then `myLogin.view()`.
- `GrIMPSubsetter` and `pointInspector` are legacy/internal — do not build new code on them; prefer `nisardev` classes.
- This package is standalone (no dependency on `utilities`/`sarfunc`/GIT64 binaries) — it is the entry point for end-user/notebook workflows, distinct from the production pipeline packages (`mosaicworkflow`, `nisargrimpworkflow`).
- For full usage examples (multi-glacier flowline plotting, profile extraction, etc.) see `Documents/Flowlines.md` and the notebooks at https://github.com/fastice/GrIMPNotebooks.
