# grimpfunc

Is a small python package with utility classes and functions to work with [GrIMP](https://nsidc.org/data/measures/grimp) data hosted by NASA NSIDC: ([NSIDC-0723](https://nsidc.org/data/nsidc-0723)) and velocity ([NSIDC-481](https://nsidc.org/data/nsidc-0481), [0725](https://nsidc.org/data/nsidc-0725), [0727](https://nsidc.org/data/nsidc-0727), [0731](https://nsidc.org/data/nsidc-0731)).

For examples of how this library is used refer to notebooks in https://github.com/fastice/GrIMPNotebooks

## Installation

grimpfunc has dependencies that are best installed as a `conda` package and not via `pip`. You can either:

1. Install grimpfunc in a stand-alone reproducible virtual environment managed by [pixi](https://pixi.sh/latest/)
```
gh repo clone fastice/grimpfunc
pixi run notebooks
```

2. Install as a conda-package into an exiting conda/mamba environment
```
conda activate myenv
conda install --channel https://repo.prefix.dev/uw-cryo grimpfunc
```

## Release Notes

0.0.6  2025-08-20  Updated to fix issues with NSIDC migration of data sets to cloud

## Building a new package version

Be sure to bump package versions in pyproject.toml and add additional dependencies if necessary

This will build a new package
```
pixi build
```

Upload to a server to install via pixi or conda-forge
```
pixi upload https://prefix.dev/api/v1/upload/uw-cryo grimpfunc-0.1.0-pyh4616a5c_0.conda
```
