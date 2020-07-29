# VTPK-Export

Downloading vector tiles from an Esri Vector Tile Service into a Vector Tile Package (`*.vtpk`) to use in creating a Mobile Map Package (`*.mmpk`)  designed for offline use from ArcGIS Pro is nearly impossible. The capability exists on the REST endpoint as the [exportTiles](https://developers.arcgis.com/rest/services-reference/export-tiles-vector-tile-service-.htm) method. This project makes this capability easier to access using Python. 

We'll see how far I get before getting pulled to something else, but for right now, the basic functionality is working and lives in `src/vtpk_export/__init__.py`. If you are able to read a bit of code, understand what it is doing, and use it, please do!

## Project Organization
------------
```
    ├── data
    │   ├── external       <- Data from third party sources.
    │   ├── interim        <- Intermediate data that has been transformed.
    │   ├── processed      <- The final, canonical data sets for modeling.
    │   └── raw            <- The original, immutable data dump.
    ├── docs               <- A default Sphinx project; see sphinx-doc.org for details
    ├── notebooks          <- Jupyter notebooks. Naming convention is a 2 digits (for ordering),
    │   │                     descriptive name. e.g.: 01_exploratory_analysis.ipynb
    │   └── notebook-template.ipynb                        
    ├── references         <- Data dictionaries, manuals, and all other explanatory materials.
    ├── reports            <- Generated analysis as HTML, PDF, LaTeX, etc.
    │   └── figures        <- Generated graphics and figures to be used in reporting
    ├── requirements.txt   <- The requirements file for reproducing the analysis 
    │                         environment using venv and PIP.                       
    ├── src                <- Source code and scripts for use in this project.
    │   └── vtpk_export    <- Library containing the bulk of code used in this 
    │                         project.
    ├── .env               <- Any environment variables here - created as part of project 
    │                         creation, but NOT syncronized with git repo for project. 
    ├── environment.yml    <- The requirements file for reproducing the analysis environment 
    │                         using Conda. 
    ├── LICENSE
    ├── Makefile           <- Makefile with commands like `make data`
    ├── make.bat           <- Windows batch file with commands like `make data`
    ├── setup.py           <- Setup script for the library (vtpk_export)     
    └── README.md          <- The top-level README for developers using this project.
```

<p><small>Project based on the <a target="_blank" href="https://github.com/knu2xs/cookiecutter-geoai">cookiecutter GeoAI project template</a>. This template, in turn, is simply an extension and light modification of the <a target="_blank" href="https://drivendata.github.io/cookiecutter-data-science/">cookiecutter data science project template</a>. #cookiecutterdatascience</small></p>
