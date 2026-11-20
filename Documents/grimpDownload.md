# grimpdownload: batch download and crop of GrIMP products (design draft)

Status: **prototype, 2026-11-19.** `grimpfunc/grimpDownload.py` runs (Kopah tested; NSIDC source
resolution and a 9-file NSIDC crop run tested); not yet wired to the viewer. Installed as the `grimpdownload` command (`[tool.poetry.scripts]`).

```
grimpdownload selection.grimp.yaml --outDir jakobshavn     # run
grimpdownload selection.grimp.yaml --dryRun                # show the plan
```

| Option | Default | Meaning |
|---|---|---|
| `--outDir` | `./grimpDownload` | output directory (also holds `grimpDownload.log` and `grimpDownload.state.json`) |
| `--source` | `auto` | `auto`: NSIDC when it holds the version, else Kopah; `nsidc`; `kopah` |
| `--nsidcGap` | 1 | seconds between NSIDC files (doubles on each refusal, up to 30 s) |
| `--kopahWorkers` | 4 | parallel Kopah reads |
| `--retryFailed` | off | retry files that failed in an earlier run |
| `--dryRun` | off | print the plan (source of each file) and stop |
| `--yes` | off | skip the prompt for downloads over 5 GB |
| `--plain` | off | one status line per second (automatic when not in a terminal) |

## Goal

Download many GrIMP products, whole or cropped to a box, from a list written by the
[GrIMP Polar Viewer](https://github.com/fastice/grimpPolarViewer), reading from **NSIDC when NSIDC
holds the same version** (so the download counts in NSIDC's metrics) and from the Kopah copies
otherwise, without overloading NSIDC.

Until the current versions are live at NSIDC (expected within weeks of 2026-11-19), the viewer keeps
its own downloads (direct files, in-browser crops, `wget` URL lists). This tool is the replacement for
the URL list and the large in-browser crop.

## 1. The download file (manifest)

YAML, written by the viewer's **Download selection**, one per request. Products are named, not
linked: the tool decides at run time where each file comes from, so a manifest written before NSIDC
releases a version switches to NSIDC by itself afterwards.

```yaml
grimpDownload: 1                  # manifest format version
created: '2026-11-19T23:59:00Z'
viewer: 2190633                   # viewer build that wrote it
collection: nsidc-0725-v6         # catalog collection id
nsidc: {shortName: NSIDC-0725, version: '6'}   # null for collections not at NSIDC (e.g. Amundsen Sea)
epsg: 3413
crop:                             # omit to download whole files
  bbox: [-230000, -2300000, -150000, -2250000]  # minx, miny, maxx, maxy in metres (epsg above)
  resolution: 200                 # metres; the overview level closest to this is read
assets: [vv, vx, vy, ex, ey]
items:
  - id: GL_vel_mosaic_Annual_01Dec24_30Nov25_v06.0
    start: '2024-12-01'
    end: '2025-11-30'
    kopah: https://s3.kopah.uw.edu/ianj-grimp/public/nsidc-0725/v06/GL_vel_mosaic_Annual_01Dec24_30Nov25_*_v06.0.tif
```

`*` in `kopah` is replaced by the asset key. The id is the NSIDC granule name for the same version.

## 2. Choosing the source

`--source auto` (default): one CMR granule search per manifest (short name, version, the items' date
span, paged with `CMR-Search-After`), mapped by granule name to NSIDC URLs. An item found at NSIDC is
read from NSIDC; the rest from Kopah. `--source nsidc` fails items that are not at NSIDC;
`--source kopah` never contacts NSIDC. The plan is printed before anything is read
(e.g. "312 from NSIDC, 4 from Kopah").

grimpfunc's own CMR search (`cmr.py`) still sends `&scroll=false`, which CMR now rejects; it needs the
one-line fix before `cmrUrls` works again. The downloader does its own search.

## 3. Reading

- **Crops** follow nisardev's template approach, one file at a time: the overview level for the
  requested resolution is chosen once per asset, the first file's grid is the template, and each file
  is a single windowed read of the box (the same window as nisardev's `_bbox_to_window`; checked:
  identical pixels to `nisarVel.readDataFromTiff` + `writeCloudOptGeo`). Reads go through nisardev's
  `_remoteRetry` (one range request at a time, short retries). It does not call `nisarVel` itself,
  because that always reads vx and vy together (and computes ev), which would triple the NSIDC reads
  for a speed-only download. Each crop is a tiled, deflate GeoTIFF with the source tags plus
  `grimpDownloadSource` and `grimpDownloadBbox`.
- A file on a different grid from the first (e.g. two TerraSAR-X sites) is an error, so a TSX
  manifest holds **one site box**; the viewer should write one manifest per site.
- **Whole files** are streamed with `requests` (Earthdata login from `~/.netrc` for NSIDC), with
  byte-level progress, written to a `.part` file and renamed when complete.
- GDAL settings for remote reads: `GDAL_DISABLE_READDIR_ON_OPEN=EMPTY_DIR`,
  `GDAL_HTTP_MERGE_CONSECUTIVE_RANGES=YES`, `GDAL_INGESTED_BYTES_AT_OPEN=65536` (header in one
  request), Earthdata cookie jar `~/.grimp_download_cookiejar.txt` + `GDAL_HTTP_NETRC=YES`.

## 4. Not overloading NSIDC

NSIDC refuses requests when too many arrive at once: rasterio reports
`... not recognized as a supported dataset name` (no HTTP error code) and the service stays unavailable
for a while. The tool therefore:

1. **Reads NSIDC one file at a time** (one worker, dask single-threaded). Kopah reads may use more
   (`--kopahWorkers`, default 4).
2. **Paces requests:** a minimum gap between NSIDC files (`--nsidcGap`, default 1 s).
3. **Backs off on refusal:** the refusal errors (not-recognized, 404/429/5xx, timeouts) pause NSIDC
   reads 30 s, then 60, 120, 240 ... up to 15 min, with a countdown on screen, then retry the same file.
   Each refusal also doubles the pacing gap (up to 30 s); 20 successes in a row halve it again.
   After 8 refusals in a row it stops cleanly and says how to resume.
4. **Stops on login errors** (401/403) with a message to run `grimpfunc.NASALogin`, instead of retrying.
5. **Resumes:** every output is written to a temporary name and renamed when complete;
   `<manifest>.state.json` records done and failed items, so a rerun skips finished files and
   `--retryFailed` retries only the failures.
6. **Previews first:** files, estimated MB and the source mix, with a prompt above 5 GB
   (`--yes` skips it).

**Measured 2026-11-19** (80 x 50 km Jakobshavn crop at 200 m, 3 annual windows x vv/vx/vy = 9 files,
one at a time): NSIDC (v5) 1.6 s per file with no gap (about 2.6 s with the default 1 s gap); Kopah
(v6) 0.12 s per file. No refusals in either run. About 6 s of each run is Python start-up (imports).

## 5. Display

Command line, using `rich` (in the base environment):

```
grimpdownload  nsidc-0725-v6.grimp.yaml  ->  ./grimpDownload
  316 files: 312 from NSIDC, 4 from Kopah · crop 80 x 50 km at 200 m · ~92 MB
  Files  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   121/316  38%  31 MB  0:02:10 left
  Now    NSIDC  GL_vel_mosaic_Monthly_01Mar20_31Mar20_v06.0  (vv vx vy ex ey)
  Status paused by NSIDC, retrying in 0:47 (gap now 2 s)
  done 118 · skipped 3 · failed 0
```

`--plain` prints one line per file for logs and non-terminal use. The engine reports through
callbacks, so a notebook or Panel front end can reuse it later; no GUI for now.

## 6. Output

`<outDir>/<name>.tif`: whole files keep their names; crops are
`<name>_crop_<x0>_<y0>_<res>m.tif` (as the viewer's crops). A `download.log` records every file,
its source and any refusals.

## 7. Viewer changes (when NSIDC is live)

- **Download selection** writes the manifest instead of the URL list (crop box and resolution
  included); the note says to run `grimpdownload <file>`.
- **Download this image** links to the NSIDC file when NSIDC holds the version (the browser handles
  the Earthdata login); otherwise Kopah, as now.

## Open questions

- Package home: `grimpfunc` (has NSIDC login and search, public) is assumed here.
- NetCDF stack output (nisardev series) in addition to per-file GeoTIFFs?
- Pacing defaults need a measured run against NSIDC.
