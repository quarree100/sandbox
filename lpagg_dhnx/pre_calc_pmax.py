from CoolProp.CoolProp import PropsSI
import numpy as np
from scipy.optimize import fsolve
import math
import pandas as pd
import logging

# Define the logging function
logger = logging.getLogger(__name__)

# CoolProp
# http://www.coolprop.org/coolprop/wrappers/Python/index.html

# Berechnung Druckverlust siehe:
#   - http://www.math-tech.at/Beispiele/upload/gra_Druckverlust_in_Rohrleitungen.PDF
#   - https://www.schweizer-fn.de/stroemung/rauhigkeit/rauhigkeit.php


def delta_p(v, d_i, k=0.1, T_medium=90, l=1,
            pressure=1, fluid='IF97::Water'):

    """

    :param v:
    :param k:           [mm]    roughness of inner pipeline surface. see also https://www.schweizer-fn.de/stroemung/rauhigkeit/rauhigkeit.php
    :param l:
    :param d_i:
    :param medium:
    :param T_medium:
    :param pressure:
    :return:
    """

    def transition_eq(x):
        # FM FS S.13 - erste Formel (Übergangsbereich glatt-rau)
        # http://www.math-tech.at/Beispiele/upload/gra_Druckverlust_in_Rohrleitungen.PDF
        # 65 < Re * k/d < 1300
        return x + 2 * np.log10((2.51 * x) / R_e + k / (3.71 * d_i))

    def glatt_eq(x):
        # http://www.math-tech.at/Beispiele/upload/gra_Druckverlust_in_Rohrleitungen.PDF
        # Formel von Prandtl und v. Karman
        # FM FS S.12 - Technische Strömung - (a)
        return x - 2 * np.log10(R_e / (x*2.51))

    k = k * 0.001

    # get density of water [kg/m^3]
    d = PropsSI('D', 'T', T_medium + 273.15, 'P', pressure*101325, fluid)
    # dynamic viscosity eta [kg/(m*s)]
    d_v = PropsSI('V', 'T', T_medium + 273.15, 'P', pressure*101325, fluid)
    k_v = d_v/d     # kinematic viskosity [m^2/s]

    # Reynodszahl
    R_e = (v * d_i) / k_v

    if R_e < 2320:  # laminare Strömung

        lam = 64 / R_e      # S. 216 - (11.9), ISBN  978-3-540-73726-1
        d_p = lam * l / d_i * d / 2 * v ** 2

    else:  # turbulente Strömung

        if R_e * k / d_i < 65:
            # ==> Rohr hydraulisch glatt

            if R_e < 10**5:
                # siehe Fluidmechanik Formelsammlung, S.12 (2.)
                # nach Prandtl
                lam = 0.3164 * R_e ** (-0.25)

            elif R_e >= 10**5 and R_e < 10**6:
                # Nikuradse: http://www.math-tech.at/Beispiele/upload/gra_Druckverlust_in_Rohrleitungen.PDF
                # Fluidmechanik I FS: S.12,
                lam = 0.0032 + 0.221 * R_e ** (-0.237)

            else:
                # Re > 10^6
                # Prandtl and Karman / laut FM FS Nikurdase
                # Näherungswert als Startwert für fsolve
                lam_init = 0.3164 / (R_e ** 0.25)
                x = fsolve(glatt_eq, x0=lam_init)
                lam = 1/x[0]**2

        elif R_e * k / d_i > 1300:
            # ==> Rohr hydraulisch rau
            # entsprich FM, FS. S.13 zweite Formel von oben
            lam = (1 / (-2 * np.log10(k / (3.71 * d_i)))) ** 2

        else:
            # ==> Übergangsbereich 65 < Re * k/d < 1300

            # Näherung
            lam_init = 0.25 / R_e ** 0.2
            # FM FS S.13 - erste Formel (Übergangsbereich glatt-rau)
            # http://www.math-tech.at/Beispiele/upload/gra_Druckverlust_in_Rohrleitungen.PDF
            # 65 < Re * k/d < 1300
            x = fsolve(transition_eq, x0=lam_init)
            lam = 1 / x[0] ** 2

        d_p = lam * l / d_i * d / 2 * v**2

    return d_p


def calc_v(vol_flow, d_i):
    """

    :param vol_flow: volume flow [m3/h]
    :param d_i: inner diameter [m]
    :return: flow velocity [m/s]
    """

    return vol_flow / ((d_i*0.5)**2 * math.pi * 3600)


def calc_v_max(d_i, T_average, k=0.1, p_max=100,  p_epsilon=1,
               v_0=1, v_1=2,
               pressure=1, fluid='IF97::Water'):

    """
    :param d_i:         [m]     inner diameter
    :param T_average:   [°C]    average temperature
    :param k:           [mm]    roughness of inner pipeline surface
    :param p_max:       [Pa]    maximum pressure drop in pipeline
    :param p_epsilon:   [Pa]    accuracy
    :param v_init:      [m/s]   initial guess for maximum flow velocity
    :param pressure:    [bar]   pressure level
    :param fluid:       [-]     type of fluid, default: 'IF97::Water'
    :return:            [m/s]   maximum flow velocity
    """
    p_new = 0
    v_new = 0
    n = 0
    while n < 100:
        n += 1

        p_0 = delta_p(v_0, k=k, d_i=d_i, T_medium=T_average,
                      pressure=pressure, fluid=fluid)

        p_1 = delta_p(v_1, k=k, d_i=d_i, T_medium=T_average,
                      pressure=pressure, fluid=fluid)

        v_new = v_1 - (p_1 - p_max) * (v_1 - v_0) / (p_1 - p_0)

        p_new = delta_p(v_new, k=k, d_i=d_i, T_medium=T_average,
                        pressure=pressure, fluid=fluid)

        # print(n, ' P_0 [Pa]: ', p_0, 'v_0 [m/s]: ', v_0)
        # print(n, ' P_1 [Pa]: ', p_1, 'v_1 [m/s]: ', v_1)
        # print(n, ' P_new [Pa]: ', p_new, 'v_new [m/s]: ', v_new)
        # print(' --- ')

        if abs(p_new - p_max) < p_epsilon:
            break

        else:
            v_0 = v_1
            v_1 = v_new

    logger.debug('Number of Iterations: {}'.format(n))
    logger.debug('Resulting pressure drop: {}'.format(p_new))
    logger.debug('Resulting velocity: {}'.format(v_new))

    return v_new


def v_max_bisection(d_i, T_average, k=0.1, p_max=100,
                    p_epsilon=0.1, v_epsilon=0.001,
                    v_0=0.01, v_1=10,
                    pressure=1, fluid='IF97::Water'):

    """
    :param d_i:         [m]     inner diameter
    :param T_average:   [°C]    average temperature
    :param k:           [mm]    roughness of inner pipeline surface
    :param p_max:       [Pa]    maximum pressure drop in pipeline
    :param p_epsilon:   [Pa]    accuracy
    :param v_init:      [m/s]   initial guess for maximum flow velocity
    :param pressure:    [bar]   pressure level
    :param fluid:       [-]     type of fluid, default: 'IF97::Water'
    :return:            [m/s]   maximum flow velocity
    """

    p_0 = delta_p(v_0, k=k, d_i=d_i, T_medium=T_average,
                  pressure=pressure, fluid=fluid)

    p_1 = delta_p(v_1, k=k, d_i=d_i, T_medium=T_average,
                  pressure=pressure, fluid=fluid)

    if (p_0 - p_max) * (p_1 - p_max) >= 0:
        logger.error('The initial guesses are not assumed right!')
        return

    p_new = 0
    v_new = 0
    n = 0
    while n < 200:
        n += 1

        p_0 = delta_p(v_0, k=k, d_i=d_i, T_medium=T_average,
                      pressure=pressure, fluid=fluid)

        p_1 = delta_p(v_1, k=k, d_i=d_i, T_medium=T_average,
                      pressure=pressure, fluid=fluid)

        v_new = 0.5 * (v_1 + v_0)

        p_new = delta_p(v_new, k=k, d_i=d_i, T_medium=T_average,
                        pressure=pressure, fluid=fluid)

        # print(n, ' v_0 [m/s]: ', v_0, ' P_0 [Pa]: ', p_0)
        # print(n, ' v_n [m/s]: ', v_new, ' P_n [Pa]: ', p_new)
        # print(n, ' v_1 [m/s]: ', v_1, ' P_1 [Pa]: ', p_1)
        # print('--- ')

        if abs(p_new - p_max) < p_epsilon:
            logger.debug('p_epsilon criterion achieved!')
            break

        if abs(v_1 - v_0) < v_epsilon:
            logger.debug('v_epsilon criterion achieved!')
            break

        else:
            if (p_0 - p_max)*(p_new-p_max) < 0:
                v_1 = v_new
            else:
                v_0 = v_new

    logger.debug('Number of Iterations: {}'.format(n))
    logger.debug('Resulting pressure drop: {}'.format(p_new))
    logger.debug('Resulting velocity: {}'.format(v_new))

    return v_new


def calc_power(T_vl=80, T_rl=50, mf=3):
    """

    :param T_vl: forward temperature [°C]
    :param T_rl: return temperature [°C]
    :param mf: mass flow [kg/s]
    :return: thermal power [W]
    """

    T_av = (T_vl + T_rl)*0.5
    cp = PropsSI('C', 'T', T_av + 273.15, 'P', 101325, 'IF97::Water')

    return mf * cp * (T_vl - T_rl)     # [W]


def calc_mass_flow(v, di, T_av):
    """

    :param v: flow velocity [m/s]
    :param di: inner diameter [m]
    :param T_av: Temperature level [°C]
    :return: mass flow [kg/s]
    """

    rho = PropsSI('D', 'T', T_av + 273.15, 'P', 101325, 'IF97::Water')  # [kg/m^3]

    return rho * v * (0.5*di)**2 * math.pi      # [kg/s]


def calc_mass_flow_P(P, T_av, delta_T):
    """

    :param P: [W]
    :param T_av: [°C]
    :param delta_T: [K]
    :return: mass flow [kg/s]
    """

    cp = PropsSI('C', 'T', T_av + 273.15, 'P', 101325, 'IF97::Water')

    return P / (cp*delta_T)


def calc_v_mf(mf, di, T_av):
    """

    :param mf: mass flow [kg/s]
    :param di: inner diameter [m]
    :param T_av: average temperature [°C]
    :return:
    """

    rho = PropsSI(
        'D', 'T', T_av + 273.15, 'P', 101325, 'IF97::Water')  # [kg/m^3]

    return mf / (rho*(0.5*di)**2 * math.pi)


def calc_dataframe_german(df):
    """Calculate columns in a DataFrame prepared with german column names."""
    df['v_max [m/s]'] = df.apply(lambda row: v_max_bisection(
        d_i=row['Innendurchmesser [m]'],
        T_average=row['Temperaturniveau [°C]'],
        k=row['Rauhigkeit [mm]'],
        p_max=row['Max delta p [Pa/m]']), axis=1)

    df['Massenstrom [kg/s]'] = df.apply(lambda row: calc_mass_flow(
        v=row['v_max [m/s]'], di=row['Innendurchmesser [m]'],
        T_av=row['Temperaturniveau [°C]'],
        ), axis=1)

    df['P_max [kW]'] = df.apply(lambda row: 0.001*calc_power(
        T_vl=row['T_Vorlauf [°C]'],
        T_rl=row['T_Rücklauf [°C]'],
        mf=row['Massenstrom [kg/s]']
        ), axis=1)

    return df


if __name__ == "__main__":

    # d_inner = 0.015   # unit [m]
    # T_fluid = 65
    # del_p = delta_p(v=0.289, d_i=d_inner, T_medium=T_fluid)   # Pascal [N/m^2]
    # v_auslegung_bisection = v_max_bisection(d_i=d_inner, T_average=T_fluid,
    #                                         k=0.1, p_max=100)
    # v_auslegung_secant = calc_v_max(d_i=d_inner, T_average=T_fluid,
    #                                 k=0.1, p_max=100)

    df = pd.read_excel('data_kamp/Waermeleitungen/CaldoPex_new_costs.xlsx')

    df = calc_dataframe_german(df)

    df.to_excel('data_kamp/Waermeleitungen/CaldoPex_new_costs_export.xlsx')

    constants_costs = np.polyfit(df['P_max [kW]'], df['Kosten [eur]'], 1)
    constants_loss = np.polyfit(df['P_max [kW]'], df['Loss [W/m]'], 1)

    # get linear approximations
    # 1) all points
    # 2) just double (DN 25 - 75)
    # 3) just singel ( > DN 75)

    # df_1 = df[df['Rauhigkeit [mm]'] == 0.1]
    # df_1_double = df_1[df_1['Innendurchmesser [m]'] < 0.08]
    # df_1_single = df_1[df_1['Innendurchmesser [m]'] > 0.08]

    # c_double = np.polyfit(df_1_double['P_max [kW]'],
    #                       df_1_double['Kosten [eur]'], 1)

    # c_single = np.polyfit(df_1_single['P_max [kW]'],
    #                       df_1_single['Kosten [eur]'], 1)




