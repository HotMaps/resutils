#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 17 15:25:16 2019

@author: ggaregnani
"""

from osgeo import osr
import numpy as np


def xy2latlong(x, y, ds):
    """Return lat long coordinate by x, y

    >>> import gdal
    >>> path = "../../../tests/data/raster_for_test.tif"
    >>> ds = gdal.Open(path)
    >>> xy2latlong(3715171, 2909857, ds)
    (1.7036231518576481, 48.994284431891565)
    """
    old_cs = osr.SpatialReference()
    old_cs.ImportFromWkt(ds.GetProjectionRef())
    # create the new coordinate system
    wgs84_wkt = """
    GEOGCS["WGS 84",
        DATUM["WGS_1984",
            SPHEROID["WGS 84",6378137,298.257223563,
                AUTHORITY["EPSG","7030"]],
            AUTHORITY["EPSG","6326"]],
        PRIMEM["Greenwich",0,
            AUTHORITY["EPSG","8901"]],
        UNIT["degree",0.01745329251994328,
            AUTHORITY["EPSG","9122"]],
        AUTHORITY["EPSG","4326"]]"""
    new_cs = osr.SpatialReference()
    new_cs .ImportFromWkt(wgs84_wkt)
    # create a transform object to convert between coordinate systems
    transform = osr.CoordinateTransformation(old_cs, new_cs)
    # get the coordinates in lat long
    latlong = transform.TransformPoint(x, y)
    return latlong[0], latlong[1]


def diff_raster(raster_in, raster_out):
    """
    Verify the position of the pixel and the consistent with the input file

    :param raster_in: array with the input values
    :param raster_out: array with the putput values

    :returns: the relative error of missing pixels
    >>> raster_in = np.array([[1, 2], [3, 4]])
    >>> raster_out = np.array([[1, 2], [3, 0]])
    >>> diff_raster(raster_in, raster_out)
    0.4
    """
    # count cell of the two rasters
    diff = np.nansum(raster_in) - np.nansum(raster_out)
    error = diff/np.nansum(raster_in)
    return error


def raster_resize(ras1, ras2):
    """
    Adapt the resoltution and the extent of raster1 to raster2

    :param raster1: gdal object
    :param raster2: gdal object

    :returns a new_matrix with array1 values and array2
    dimension and resolution
    """
    matrix1 = np.nan_to_num(ras1.ReadAsArray())
    matrix2 = ras2.ReadAsArray()
    matrix2 = np.nan_to_num(matrix2)
    ds_1 = ras1.GetGeoTransform()
    ds_2 = ras2.GetGeoTransform()
    x_offset = int((ds_2[0] - ds_1[0]) / ds_2[1])
    y_offset = int((ds_2[3] - ds_1[3]) / (-ds_2[5]))
    x_incr = ds_1[1]/ds_2[1]
    y_incr = ds_1[5]/ds_2[5]
    # ds_2 = ras2.GetGeoTransform()
    # resize shape
    new_matrix = np.zeros(matrix2.shape)
    for y in range(0, matrix1.shape[0]):
        i = max(0, int(y * y_incr) + y_offset)
        i_incr = min(i + int(y_incr), new_matrix.shape[0])
        for x in range(0, matrix1.shape[1]):
            j = max(0, int(x * x_incr) - x_offset)
            j_incr = min(j + int(x_incr), new_matrix.shape[1])
            print(i, j)
            new_matrix[i:i_incr, j:j_incr] = matrix1[y, x]
    return new_matrix

    # allignement
#    ncols_offset = (ds_1[0] - ds_2[0]) / ds_1[1]
#    nrows_offset = (ds_1[3] - ds_2[3]) / ds_1[5]
#
#    new_speed[nrows_offset:nrows_offset+speed.shape[1],
#              ncols_offset:ncols_offset+speed.shape[0]] = speed

    # FIXME: the speed is considered with the same resolution
    # and extent of available area
    # by default available area has higher resolution


def get_lat_long(ds, most_suitable):
    """
    Return the lat_long of the pixel with mean value of the resources
    """
    diff = most_suitable - np.mean(most_suitable[most_suitable > 0])
    i, j = np.unravel_index(np.abs(diff).argmin(), diff.shape)
    ds_geo = ds.GetGeoTransform()
    x = ds_geo[0] + i * ds_geo[1]
    y = ds_geo[3] + j * ds_geo[5]
    long, lat = xy2latlong(x, y, ds)
    # generation of the output time profile
    return lat, long


if __name__ == "__main__":
    import doctest
    doctest.testmod()
