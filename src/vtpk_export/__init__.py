from copy import deepcopy
import itertools
import json
import math
from pathlib import Path
import re
import tempfile
from time import sleep

from arcgis.gis import Layer
from arcgis.geometry import Geometry, SpatialReference
import dask.bag as db
import requests


def get_extent(input_object: [list, tuple, Geometry, dict], spatial_reference: [dict, SpatialReference] = None) -> dict:
    """
    No matter what type of extent representation
    passed in, return standardized extent as a
    dictionary.

    :param input_object: Representation of an extent
        as an iterable, geometry or extent dictionary.
    :param spatial_reference: Spatial reference for
        the extent. Required if the input object is
        a tuple or list.

    :return: Dictionary representation of the extent.
        in the form of {"xmin": <float>, "ymin": <float>,
        "xmax": <float>, "ymax": <float>,
        "spatialReference": {"wkid": <int>} }
    """
    # make sure the input is one of the acceptable data types
    assert isinstance(input_object, (list, tuple, Geometry, dict))

    # if already an extent dictionary
    if isinstance(input_object, dict) and not isinstance(input_object, Geometry):

        assert list(input_object.keys()) == ['xmin', 'ymin', 'xmax', 'ymax', 'spatialReference'], \
            'Extent dictionary must be in the form of {"xmin": <float>, "ymin": <float>, "xmax": <float>, ' \
            '"ymax": <float>, "spatialReference": {"wkid": <int>} }'

        ext = input_object

    # if a geometry object is provided
    elif isinstance(input_object, Geometry):

        # get the extent and set the spatial reference
        spatial_reference = input_object.spatial_reference
        input_object = input_object.extent

    # if simply passed in as series of four values as iterables
    if isinstance(input_object, (list, tuple)):

        # ensure the max values are, in fact, greater than the min values
        assert input_object[0] < input_object[2], 'xmax value must be greater than xmin value'
        assert input_object[1] < input_object[3], 'ymax value must be greater than ymin value'

        # make sure the spatial reference is correctly provided
        assert spatial_reference is not None, 'If providing the extent as an iterable, you must provide a spatial ' \
                                              'reference.'

        # make sure the dictionary is set up correctly if provided as a dictionary
        if isinstance(spatial_reference, dict):
            assert 'wkid' in spatial_reference.keys(), 'wkid must be defined in the spatial_reference'
            assert isinstance(spatial_reference['wkid'], int), 'spatial_reference wkid must be an integer'

        ext = {'xmin': input_object[0], 'ymin': input_object[1], 'xmax': input_object[2], 'ymax': input_object[3],
               'spatialReference': spatial_reference}

    return ext


def _download_file(url, out_name=None, out_dir=None):
    """Helper method to download large files"""
    # get the file name from the url if none is provided
    if out_name is None:
        url_root = url.split('?')[0]
        out_name = url_root.split('/')[-1]

    # if the output directory is not provided, simply save to the temp directory
    if out_dir is None:
        out_dir = tempfile.gettempdir()

    # combine to get entire path to output file
    out_pth = Path(out_dir)/out_name

    # create a requests get object to do the work
    with requests.get(url, stream=True) as req_get:  # NOTE stream=True parameter

        # check for any errors
        req_get.raise_for_status()

        # stream down the file in roughly 8MB chunks to not blow up RAM
        with open(out_pth, 'wb') as f:
            for chunk in req_get.iter_content(chunk_size=8192):
                f.write(chunk)

    return Path(out_pth).absolute()


def _slice_extent_axis(ext_min, ext_max, fctr):
    """Slice an extent into multiple extents along an axis."""
    strd = (ext_max - ext_min) / fctr
    return [(ext_min + i * strd, ext_max - (fctr - i - 1) * strd) for i in range(fctr)]


def _new_extent(ext, xmin=None, ymin=None, xmax=None, ymax=None):
    """Little helper to create new extents based on needed inputs."""
    in_vals = locals()
    new_ext = deepcopy(ext)
    ext_keys = [k for k in in_vals.keys()][1:]
    for ext_key in ext_keys:
        if in_vals[ext_key] is not None:
            new_ext[ext_key] = in_vals[ext_key]
    return new_ext


def _get_job_result(input_params: [list, tuple]):
    """Helper function to check and download the job result."""

    req_resp, root_url, token, out_dir = input_params
    resp = req_resp.json()

    # get the job id from the response
    assert 'jobId' in resp.keys()
    job_id = resp['jobId']

    # keep checking until the job is complete
    job_complete = False
    while job_complete is False:

        # check on the job status
        job_resp = requests.get(f'{root_url}/jobs/{job_id}?token={token}')
        job_json = job_resp.json()

        # if the job is not finished, wait five seconds before trying again
        if job_json['jobStatus'] != 'esriJobSucceeded':
            sleep(5)
        else:
            job_complete = True

    # download the generated vtpk file
    out_file = _download_file(job_json['output']['outputUrl'][0], out_dir=out_dir)

    return out_file


class VectorTileLayer(Layer):
    """
    Vector Tile Layer, subclassed FeatureLayer to add ability to export tiles.
    """
    def __init__(self, url, gis=None):
        """
        Constructs a Vector Tile Layer object given a Vector Tile Layer URL.
        :param url: feature layer url
        :param gis: optional, the GIS that this layer belongs to. Required for secured services.
        """
        super().__init__(url, gis)
        if not str(url).endswith('/VectorTileServer'):
            raise Exception(
                f'url does not appear to be for a vector tile server - it does not end with /VectorTileServer')
        self._job_pct = 0  # for tracking tile generation progress

    def _post(self, url, params=None):
        return self._con.post(path=url, postdata=params, token=self._token)

    def _call_export_tiles(self, levels_of_detail=None, extent=None, _params=None):
        """Helper function to make the initial call to export tiles."""

        # input parameter checking for params and levels of detail
        if _params is None:
            _params = dict()
        elif not isinstance(_params, dict):
            raise Exception(f'params must be a dictionary, not {type(_params)}')

        extent = json.dumps(extent) if isinstance(extent, dict) else extent

        if levels_of_detail is None:
            levels_of_detail = range(self.properties.minLOD, self.properties.maxLOD+1, )
        elif not isinstance(levels_of_detail, list):
            raise Exception(f'levels_of_detail must be a list, not {type(levels_of_detail)}')

        # add levels and extent to request parameters
        _params['levels'] = ','.join([str(i) for i in levels_of_detail])
        _params['exportExtent'] = extent
        _params['token'] = self._token

        # make the request to export tiles REST endpoint
        resp = requests.post(url=f'{self.url}/exportTiles', data=_params)

        return resp

    def _get_job_result(self, request_resp):
        return _get_job_result((request_resp, self.url, self._con.token))

    def export_tiles(self, levels_of_detail=None, extent: Geometry = None, params: dict = None, output_dir: str = None):
        """Export tiles to vtpk."""
        # get the extent formatted
        ext = get_extent(extent)

        # make the initial call to the REST endpoint, which will return a job id
        init_resp = self._call_export_tiles(levels_of_detail=levels_of_detail, extent=ext, _params=params)

        # if there is an error in the initial response
        if 'error' in init_resp.json().keys():

            err = init_resp.json()['error']

            if err['code'] == 500:
                msg = err['message']

                # check the error message
                mtch = re.search(
                    pattern=r"estimated tile count.*?\((\d*)\).*?greater than.*?max export tiles? count.*?\((\d*)\)",
                    string=msg
                )

                # if too many tiles, slice up the job
                if mtch:
                    
                    # from the error message, get the number of tiles needed divided by the max response
                    mtch_vals = [int(val) for val in mtch.groups()]

                    # get a factor to slice by, the square root of the ratio we are short by
                    fctr = math.ceil(math.sqrt(mtch_vals[0] / mtch_vals[1]))

                    # slice up both axes by the rounded up number we are short
                    x_slc = _slice_extent_axis(extent['xmin'], extent['xmax'], fctr)
                    y_slc = _slice_extent_axis(extent['ymin'], extent['ymax'], fctr)

                    # get a list of new extents slicing up the total extent
                    ext_lst = [_new_extent(extent, v[0][0], v[1][0], v[0][1], v[1][1])
                               for v in itertools.product(x_slc, y_slc)]

                    # kick off the creation of tiles by calling the REST endpoint as many times as necessary
                    job_lst = [(
                            self._call_export_tiles(levels_of_detail=levels_of_detail, extent=ext, _params=params),
                            self.url,
                            self._con.token,
                            output_dir
                        ) for ext in ext_lst]

                    # load all responses into a dask bag and retrieve results asynchronously
                    vtpk_lst = db.from_sequence(job_lst).map(_get_job_result).compute()

                else:
                    raise Exception(f'500 error received from server - /"{msg}/"')

        else:
            vtpk_lst = self._get_job_result(init_resp)

        return vtpk_lst
