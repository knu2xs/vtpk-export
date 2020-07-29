import os

from arcgis.gis import GIS
from dotenv import find_dotenv, load_dotenv
import pytest

from vtpk_export import VectorTileLayer

# load environment variables from .env
load_dotenv(find_dotenv())


@pytest.fixture
def gis():
    return GIS(
        url=os.getenv('ESRI_GIS_URL'),
        username=os.getenv('ESRI_GIS_USERNAME'),
        password=os.getenv('ESRI_GIS_PASSWORD')
    )


@pytest.fixture
def lyr(gis):
    lyr_url = 'https://basemaps.arcgis.com/arcgis/rest/services/World_Basemap_v2/VectorTileServer'
    return VectorTileLayer(lyr_url, gis)


def test_get_tiles_oly(lyr):
    """Testing for single request and response - less than the maximum number of tiles."""
    lods = [0, 1, 2]
    ext = {
        'xmin': -13627763,
        'ymin': 5896810,
        'xmax': -13727382,
        'ymax': 5984182,
        'spatialReference': {
            'wkid': 102100,
            'latestWkid': 3857
        }
    }
    resp = lyr.export_tiles(levels_of_detail=lods, extent=ext)
    assert resp


def test_get_tiles_wa(lyr):
    """Testing for multiple requests and responses - exceeding the maximum number of tiles for one request."""
    ext = {
        'xmin': -13957416.7735,
        'ymin': 5638646.356700003,
        'xmax': -12946003.8225,
        'ymax': 6348834.4032000005,
        'spatialReference': {
            'wkid': 102100,
            'latestWkid': 3857
        }
    }
    resp = lyr.export_tiles(extent=ext)
    assert resp
