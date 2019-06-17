#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 17 15:25:25 2019

@author: ggaregnani
"""


from pint import UnitRegistry
import numpy as np
import resutils.unit as resu

ureg = UnitRegistry()


def search(indicator_list, name):
    """
    Return a value of a name in the list of indicators

    :param indicator_list: list with the dictionaries with the indicators
    :param name: name to search for

    :returns: the value related to the name or None if missing
    >>> ind = [{'unit': 'MWh/year', 'name': 'Total energy production',
    ...         'value': '2887254.54'},
    ...        {'unit': 'Million of currency', 'name': 'Total setup costs',
    ...         'value': '6137'},
    ...        {'unit': '-', 'name': 'Number of installed systems',
    ...         'value': '1022847'},
    ...        {'unit': 'currency/kWh', 'name': 'Levelized Cost of Energy',
    ...         'value': '0.17'}]
    >>> search(ind, 'Total energy production')
    (2887254.54, 'MWh/year')
    """
    for dic in indicator_list:
        if dic['name'] == name:
            return float(dic['value']), dic['unit']
    return None


def production_per_plant(json, kind='PV'):
    """
    Return the value of the production of a single plant

    :param json: json to parse with results

    :returns: the vale
    """
    value, unit = search(json['result']['indicator'],
                         '{} total energy production'.format(kind))
    energy = ureg.Quantity(value, unit)
    n_plants, unit = search(json['result']['indicator'],
                            'Number of installed {} Systems'.format(kind))
    e_plant = energy/n_plants
    return e_plant


def get_indicators(kind, plant, most_suitable,
                   n_plant_raster, discount_rate):
    """
    Return a dictionary with main indicator of the specific source
    """
    n_plants = n_plant_raster.sum()
    tot_en_gen_per_year = plant.energy_production * plant.n_plants
    tot_en_gen, unit, factor = resu.best_unit(tot_en_gen_per_year,
                                              current_unit='kWh/year',
                                              no_data=0,
                                              fstat=np.min,
                                              powershift=0)
    tot_setup_costs = plant.financial.investement_cost * n_plants
    lcoe_plant = plant.financial.lcoe(plant.energy_production,
                                      i_r=discount_rate/100)
    return [{"unit": unit,
             "name": "{} total energy production".format(kind),
             "value": str(round(tot_en_gen, 2))},
            {"unit": "Million of currency",
             "name": "{} total setup costs".format(kind),  # M€
             "value": str(round(tot_setup_costs/1000000))},
            {"unit": "-",
             "name": "Number of installed {} Systems".format(kind),
             "value": str(round(n_plants))},
            {"unit": "currency/kWh",
             "name": "Levelized Cost of {} Energy".format(kind),
             "value": str(round(lcoe_plant, 2))}]


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
    equivalent_hours = tot_energy/capacity
    return (tot_energy, working_hours, equivalent_hours)


if __name__ == "__main__":
    import doctest
    doctest.testmod()
