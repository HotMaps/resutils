#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 17 15:25:25 2019

@author: ggaregnani
"""
from typing import Any, Dict, List, Optional, Tuple

from pint import UnitRegistry
import numpy as np
import resutils.unit as resu
from osgeo import gdal
from matplotlib import colors

CLRS_SUN = "#F19B03 #F6B13D #F9C774 #FDDBA3 #FFF0CE".split()
CMAP_SUN = colors.LinearSegmentedColormap.from_list("solar", CLRS_SUN)
ureg = UnitRegistry()


def search(
    indicator_list: List[Dict[str, str]], name: str
) -> Optional[Tuple[float, str]]:
    """
    Return a value of a name in the list of indicators

    :param indicator_list: list with the dictionaries with the indicators
    :param name: name to search for

    :returns: the value related to the name or None if missing
    >>> ind = [{'unit': 'MWh/yr', 'name': 'Total energy production',
    ...         'value': '2887254.54'},
    ...        {'unit': 'Million of EUR', 'name': 'Total setup costs',
    ...         'value': '6137'},
    ...        {'unit': '-', 'name': 'Number of installed systems',
    ...         'value': '1022847'},
    ...        {'unit': 'EUR/kWh', 'name': 'Levelized Cost of Energy',
    ...         'value': '0.17'}]
    >>> search(ind, 'Total energy production')
    (2887254.54, 'MWh/yr')
    """
    for dic in indicator_list:
        if dic["name"] == name:
            return float(dic["value"]), dic["unit"]
    return None


def production_per_plant(json: Dict[str, Any], kind: str = "PV") -> float:
    """
    Return the value of the production of a single plant

    :param json: json to parse with results

    :returns: the vale
    """
    value, unit = search(
        json["result"]["indicator"], "{} total energy production".format(kind)
    )
    energy = ureg.Quantity(value, unit)
    n_plants, unit = search(
        json["result"]["indicator"], "Number of installed {} Systems".format(kind)
    )
    e_plant = energy / n_plants
    return e_plant


def get_indicators(
    kind: str, plant: Any, most_suitable: Any, n_plant_raster: Any, discount_rate: float
) -> List[Dict[str, str]]:
    """
    Return a dictionary with main indicator of the specific source
    """
    n_plants = n_plant_raster.sum()
    tot_en_gen_per_year = plant.energy_production * plant.n_plants
    tot_en_gen, unit, factor = resu.best_unit(
        tot_en_gen_per_year,
        current_unit="kWh/yr",
        no_data=0,
        fstat=np.min,
        powershift=0,
    )
    tot_setup_costs = plant.financial.investement_cost * n_plants
    lcoe_plant = plant.financial.lcoe(plant.energy_production, i_r=discount_rate / 100)
    return [
        {
            "unit": unit,
            "name": "{} total energy production".format(kind),
            "value": str(round(tot_en_gen, 2)),
        },
        {
            "unit": "Million of EUR",
            "name": "{} total setup costs".format(kind),  # MEUR
            "value": str(round(tot_setup_costs / 1000000)),
        },
        {
            "unit": "-",
            "name": "Number of installed {} systems".format(kind.lower()),
            "value": str(round(n_plants)),
        },
        {
            "unit": "EUR/kWh",
            "name": "Levelized cost of {} energy".format(kind.lower()),
            "value": str(round(lcoe_plant, 2)),
        },
    ]


def get_raster(
    most_suitable: Any, output_suitable: str, ds: Any, kind: str
) -> List[Dict[str, str]]:
    """
    Return a dictionary with the output raster and the simbology
    """
    most_suitable, unit, factor = resu.best_unit(
        most_suitable,
        current_unit="kWh/pixel/yr",
        no_data=0,
        fstat=np.min,
        powershift=0,
    )
    out_ds, symbology = quantile_colors(
        most_suitable,
        output_suitable,
        proj=ds.GetProjection(),
        transform=ds.GetGeoTransform(),
        qnumb=6,
        no_data_value=0,
        gtype=gdal.GDT_Byte,
        unit=unit,
        options="compress=DEFLATE TILED=YES " "TFW=YES " "ZLEVEL=9 PREDICTOR=1",
    )
    del out_ds

    return [
        {
            "name": "layers of most suitable roofs for {}".format(kind),
            "path": output_suitable,
            "type": "custom",
            "symbology": symbology,
        }
    ]


def hourly_indicators(df, capacity):
    """
    Compute the indicators based on the df profile

    >>> df = pd.Series([0.2, 0, 0, 1] , index=pd.date_range('2000',
    ...                freq='h', periods=4))
    >>> hourly_indicators(df, 1)
    (1.2, 2, 1.2)
    """

    # there is no difference by using integration methods such as
    # trap integration
    tot_energy = df.sum()
    working_hours = df[df > 0].count()
    equivalent_hours = tot_energy / capacity
    return (tot_energy, working_hours, equivalent_hours)


def colorizeMyOutputRaster(out_ds):
    ct = gdal.ColorTable()
    ct.SetColorEntry(0, (0, 0, 0, 255))
    ct.SetColorEntry(1, (110, 220, 110, 255))
    out_ds.SetColorTable(ct)
    return out_ds


def quantile(array, qnumb=6, round_decimals=-2):
    # define the quantile limits
    qvalues, qstep = np.linspace(0, 1.0, qnumb, retstep=True)

    quantiles = np.quantile(array, qvalues)
    # round the number
    while True:
        q0 = np.round(quantiles, round_decimals)
        if len(set(q0)) != len(quantiles):
            print("Increase decimals")
            round_decimals += 1
        else:
            break

    return qvalues, q0


def quantile_colors(
    array,
    output_suitable,
    proj,
    transform,
    qnumb=6,
    no_data_value=0,
    no_data_color=(0, 0, 0, 255),
    gtype=gdal.GDT_Byte,
    options="compress=DEFLATE TILED=YES TFW=YES" " ZLEVEL=9 PREDICTOR=1",
    round_decimals=-2,
    unit="kWh/yr",
):
    """Generate a GTiff categorical raster map based on quantiles
    values.

    "symbology": [
        {"red":50,"green":50,"blue":50,"opacity":0.5,"value":"50","label":"50MWh"},
        {"red":100,"green":150,"blue":10,"opacity":0.5,"value":"150MWh","label":"150MWh"},
        {"red":50,"green":50,"blue":50,"opacity":0.5,"value":"200MWh","label":"200MWh"},
        {"red":50,"green":50,"blue":50,"opacity":0.5,"value":"250MWh","label":"250MWh"}
    ]
    """
    valid = array != no_data_value
    qvalues, quantiles = quantile(
        array[valid], qnumb=qnumb, round_decimals=round_decimals
    )

    symbology = [
        {
            "red": no_data_color[0],
            "green": no_data_color[1],
            "blue": no_data_color[2],
            "opacity": no_data_color[3],
            "value": no_data_value,
            "label": "no data",
        }
    ]

    # create a categorical derived map
    array_cats = np.zeros_like(array, dtype=np.uint8)
    qv0 = quantiles[0] - 1.0
    array_cats[~valid] = 0
    for i, (qk, qv) in enumerate(zip(qvalues[1:], quantiles[1:])):
        label = ("{qv0} {unit} < Solar potential <= {qv1} {unit}" "").format(
            qv0=qv0, qv1=qv, unit=unit
        )
        print(label)
        qindex = (qv0 < array) & (array <= qv)
        array_cats[qindex] = i + 1
        qv0 = qv
        symbology.append(dict(value=int(i + 1), label=label))

    # create a color table
    ct = gdal.ColorTable()
    ct.SetColorEntry(no_data_value, no_data_color)
    for i, (clr, symb) in enumerate(zip(CMAP_SUN(qvalues), symbology[1:])):
        r, g, b, a = (np.array(clr) * 255).astype(np.uint8)
        ct.SetColorEntry(i + 1, (r, g, b, a))
        symb.update(dict(red=int(r), green=int(g), blue=int(b), opacity=int(a)))

    # create a new raster map
    gtiff_driver = gdal.GetDriverByName("GTiff")
    ysize, xsize = array_cats.shape

    out_ds = gtiff_driver.Create(
        output_suitable, xsize, ysize, 1, gtype, options.split()
    )
    out_ds.SetProjection(proj)
    out_ds.SetGeoTransform(transform)

    out_ds_band = out_ds.GetRasterBand(1)
    out_ds_band.SetNoDataValue(no_data_value)
    out_ds_band.SetColorTable(ct)
    out_ds_band.WriteArray(array_cats)
    out_ds.FlushCache()
    return out_ds, symbology


# TODO: fix color map according to raster visualization


def line(
    x,
    y_labels,
    y_values,
    unit,
    xLabel="Percentage of buildings",
    yLabel="Energy production [{}]",
):
    """
    Define the dictionary for defining a multiline plot
    :param x: list of x data
    :param y_labels: list of strings with y labels of dataset
    :param y_values: lists of dataset with their values
    :returns: the dictionary for the app
    """
    dic = []
    palette = ["#0483a3", "#72898b", "#a38b6f", "#ca8b50", "#ec8729"]
    for i, lab in enumerate(y_labels):
        dic.append(
            {
                "label": lab,
                "backgroundColor": palette[i],
                "data": ["{:7.3f}".format(y) for y in y_values[i]],
            }
        )

    graph = {
        "xLabel": xLabel,
        "yLabel": yLabel.format(unit),
        "type": "line",
        "data": {"labels": [str(xx) for xx in x], "datasets": dic},
    }
    return graph


def reducelabels(x, steps=10):
    """
    Insert an empty string in order to better visualize x labels
    :param x: list of x data
    :param steps: integer with the number of x values to visualize

    >>> x = [str(i) for i in range(0,10)]
    >>> reducelabels(x, steps=3)
    ['0', '', '', '3', '', '', '6', '', '', '9']
    """
    x_rep = ["" for i in range(0, len(x))]
    for i in range(0, len(x), round(len(x) / steps)):
        x_rep[i] = x[i]
    return x_rep


if __name__ == "__main__":
    import doctest

    doctest.testmod()
