# -*- coding: utf-8 -*-
"""
Physics & Racking-Integrated Battery Engine for National Solar Array
Uses pvlib + pvfactors (solarfactors) + CEC Single-Diode + 314Ah LFP Cell Sizing
"""

import gc
import math
import numpy as np
import pandas as pd
import streamlit as st
import pvlib
from pvlib import location, tracking, temperature, pvsystem
from pvlib.iotools import get_pvgis_tmy
from pvlib.bifacial.pvfactors import pvfactors_timeseries

# Preset locations for quick dropdown selection + Custom Coordinates option
LOCATION_PRESETS = {
    "Newbury Park, CA (Home)": {
        "lat": 34.1842, "lon": -118.9101, "tz": "America/Los_Angeles", "alt": 200.0, "albedo": 0.20
    },
    "Yuma, AZ (Southwest Desert)": {
        "lat": 32.6984, "lon": -114.6504, "tz": "America/Phoenix", "alt": 75.0, "albedo": 0.28
    },
    "Daggett / Mojave, CA": {
        "lat": 34.8636, "lon": -116.8881, "tz": "America/Los_Angeles", "alt": 588.0, "albedo": 0.26
    },
    "Tonopah, NV": {
        "lat": 38.0672, "lon": -117.2301, "tz": "America/Los_Angeles", "alt": 1840.0, "albedo": 0.25
    },
    "El Paso, TX": {
        "lat": 31.7619, "lon": -106.4850, "tz": "America/Denver", "alt": 1140.0, "albedo": 0.25
    },
}

MODULE_SPECS = {
    "Name": "LONGi Hi-MO 9 LR8-66HYD-670M",
    "STC": 670.0,             # W (24.8% efficiency)
    "Cells_in_Series": 132,
    "I_sc_ref": 16.86,        # A
    "V_oc_ref": 50.12,        # V
    "I_mp_ref": 16.19,        # A
    "V_mp_ref": 41.38,        # V
    "alpha_sc": 0.00843,      # A/C
    "beta_voc": -0.10024,     # V/C
    "gamma_pmp": -0.26,       # %/C
    "bifaciality": 0.75,      # 75% bifaciality
    "length_m": 2.382,        # m
    "width_m": 1.134,         # m
    "frame_m": 0.0032,        # m
}

CELL_SPECS = {
    "name": "3.2V 314Ah Prismatic LFP",
    "voltage": 3.2,
    "ah": 314.0,
    "kwh": (3.2 * 314.0) / 1000.0,  # 1.0048 kWh/cell
    "mass_kg": 5.5,
    "volume_l": 2.59,
}


@st.cache_data(show_spinner=False)
def fit_module_cec():
    """Fits CEC single-diode parameters for LONGi Hi-MO 9 once."""
    return pvlib.ivtools.sdm.fit_cec_sam(
        celltype="monoSi",
        v_mp=MODULE_SPECS["V_mp_ref"],
        i_mp=MODULE_SPECS["I_mp_ref"],
        v_oc=MODULE_SPECS["V_oc_ref"],
        i_sc=MODULE_SPECS["I_sc_ref"],
        alpha_sc=MODULE_SPECS["alpha_sc"],
        beta_voc=MODULE_SPECS["beta_voc"],
        gamma_pmp=MODULE_SPECS["gamma_pmp"],
        cells_in_series=MODULE_SPECS["Cells_in_Series"],
        temp_ref=25,
    )


#import gc
# ... keep existing imports ...

def run_simulation_slider_imports(
    base_daily_kwh=25.0,
    n_evs=1,
    ev_daily_miles=30.0,
    ev_chrg_max_I_home=48
)
    
@st.cache_data(show_spinner="Downloading PVGIS TMY & running pvfactors bifacial + storage simulation...")
def run_site_simulation(
    site_name: str,
    lat: float,
    lon: float,
    tz: str,
    alt: float,
    albedo: float,
    gcr: float,
    storage_hours: float,
    soc_min: float,
    soc_max: float,
    n_modules: int = 5,
    n_columns: int = 3,
    n_rows: int = 5,
    dc_ac_ratio: float = 0.93,
    batt_eff: float = 0.90,
):
    """Runs hourly pvfactors + CEC single-diode + seasonal load + racking LFP storage."""
    I_L_ref, I_o_ref, R_s, R_sh_ref, a_ref, Adjust = fit_module_cec()

    nameplate_kw = MODULE_SPECS["STC"] * n_modules * n_columns / 1000.0
    pv_w = MODULE_SPECS["width_m"]
    pv_l = MODULE_SPECS["length_m"]
    pv_f = MODULE_SPECS["frame_m"]
    ns_space = 0.025
    ew_space = (pv_w + pv_f) / gcr - pv_w

    module_aperture_m2 = pv_w * pv_l
    panel_rating_w_per_m2 = MODULE_SPECS["STC"] / module_aperture_m2
    unit_area_m2 = (((n_rows - 1) * ((pv_w + pv_f) / gcr)) + (pv_w + pv_f)) * (pv_l + ns_space) * n_columns - ns_space
    gross_land_m2_per_unit = unit_area_m2 + (ew_space * (pv_l + pv_f))
    total_rail_m = n_rows * (n_columns * (pv_l + ns_space))

    # 1. Weather & Sun Position
    tmy_data, _ = get_pvgis_tmy(
        latitude=lat, longitude=lon, outputformat="json", usehorizon=True, map_variables=True, timeout=60
    )
    tmy_data = tmy_data.tz_convert(tz)
    site = location.Location(lat, lon, tz=tz, altitude=alt, name=site_name)
    solpos = site.get_solarposition(tmy_data.index)

    # 2. Single-Axis Tracking & Daytime-Only pvfactors 2D View-Factor Bifacial Irradiance
    tracker_data = tracking.singleaxis(
        apparent_zenith=solpos["apparent_zenith"],
        solar_azimuth=solpos["azimuth"],
        axis_tilt=0.0,
        axis_azimuth=180.0,
        max_angle=90.0,
        backtrack=False,
        gcr=gcr,
    )
    surface_tilt = tracker_data["surface_tilt"].fillna(0.0)
    surface_azimuth = tracker_data["surface_azimuth"].fillna(180.0)

    # Filter strictly to daytime hours with irradiance to cut pvfactors RAM usage in half
    day_mask = (solpos["apparent_zenith"] < 89.5) & ((tmy_data["dni"] + tmy_data["dhi"]) > 0)
    safe_tilt = surface_tilt[day_mask].replace(0.0, 1e-4)

    irrad_day = pvfactors_timeseries(
        solar_azimuth=solpos.loc[day_mask, "azimuth"],
        solar_zenith=solpos.loc[day_mask, "apparent_zenith"],
        surface_azimuth=surface_azimuth[day_mask],
        surface_tilt=safe_tilt,
        axis_azimuth=180.0,
        timestamps=tmy_data.index[day_mask],
        dni=tmy_data.loc[day_mask, "dni"],
        dhi=tmy_data.loc[day_mask, "dhi"],
        gcr=gcr,
        pvrow_height=2.0,
        pvrow_width=pv_w,
        albedo=albedo,
        n_pvrows=3,  # Using 3 rows instead of 5 captures center-row shading with 40% less RAM
        index_observed_pvrow=1,
    )
    irrad_day = pd.concat(irrad_day, axis=1)

    # Reindex back to full 8760-hour TMY index with 0.0 at night
    irrad = pd.DataFrame(0.0, index=tmy_data.index, columns=["total_inc_front", "total_inc_back"])
    irrad.loc[day_mask, "total_inc_front"] = irrad_day["total_inc_front"].fillna(0.0)
    irrad.loc[day_mask, "total_inc_back"] = irrad_day["total_inc_back"].fillna(0.0)

    # Free heavy pvfactors objects before continuing
    del irrad_day
    gc.collect()

    effective_irrad = irrad["total_inc_front"] + MODULE_SPECS["bifaciality"] * irrad["total_inc_back"]
    # ... continue with step 3 (Cell Temperature & CEC Single-Diode) unchanged ...


    # 3. Cell Temperature & CEC Single-Diode DC/AC Output
    temp_cell = temperature.sapm_cell(
        effective_irrad, tmy_data["temp_air"], tmy_data["wind_speed"], a=-3.47, b=-0.048, deltaT=3
    )
    cec_params = pvsystem.calcparams_cec(
        effective_irradiance=effective_irrad,
        temp_cell=temp_cell,
        alpha_sc=MODULE_SPECS["alpha_sc"],
        a_ref=a_ref,
        I_L_ref=I_L_ref,
        I_o_ref=I_o_ref,
        R_sh_ref=R_sh_ref,
        R_s=R_s,
        Adjust=Adjust,
    )
    iv_results = pvsystem.singlediode(*cec_params)
    dc_watts_unit = (iv_results["p_mp"] * n_modules * n_columns).fillna(0.0).clip(lower=0.0)
    ac_gen_kwh = (dc_watts_unit / 1000.0) * dc_ac_ratio


    # --- Seasonal Residential Load Profile ---
    
    #BASE_DAILY_KWH       = 21.0
    #EV_CONS              = 300          # Wh/mi
    #EV_DAILY             = 40           # mi
    #N_EVS                = 2            # EVs in household
    ev_chrg_max_home    = (240 * ev_chrg_max_I_home / 1000) # Max charge rate at home
    EV_chrg_kwh = ev_cons * ev_daily * n_evs / 1000
    EV_wt_bump = ev_chrg_max_home / base_daily_kwh

    
    # --- Seasonal Residential Load Profile ---
    base_weights = np.array([
        0.026, 0.023, 0.021, 0.021, 0.023, 0.032,  # 00:00 - 05:00
        0.045, 0.054, 0.048, 0.037, 0.034, 0.034,  # 06:00 - 11:00
        0.035, 0.035, 0.037, 0.041, 0.049, 0.061,  # 12:00 - 17:00
        0.067, 0.065, 0.057, 0.047, 0.037, 0.031   # 18:00 - 23:00
    ])
    base_weights /= base_weights.sum()

    exact_hrs = min(24.0, EV_chrg_kwh / ev_chrg_max_home)
    full_hrs = int(exact_hrs)
    partial_hr_fraction = exact_hrs - full_hrs
    
    start_hr = 23  # Example: 10:00 PM start
    
    # Apply full power bump to complete hours
    full_indices = np.arange(start_hr, start_hr + full_hrs) % 24
    base_weights[full_indices] += EV_wt_bump
    
    # Apply prorated bump to the final partial hour
    if partial_hr_fraction > 0 and full_hrs < 24:
        last_idx = (start_hr + full_hrs) % 24
        base_weights[last_idx] += EV_wt_bump * partial_hr_fraction

    
    base_load = pd.Series([BASE_DAILY_KWH * base_weights[h] for h in tmy_data.index.hour], index=tmy_data.index)
    
    ac_elec = np.zeros(len(tmy_data))
    hp_elec = np.zeros(len(tmy_data))
    aux_th = np.zeros(len(tmy_data))

    for i, t_amb in enumerate(tmy_data["temp_air"]):
        if t_amb > 24.0:
            cool_th = 0.22 * (t_amb - 24.0)
            ac_cop = max(2.2, 3.8 - 0.04 * (t_amb - 24.0))
            ac_elec[i] = cool_th / ac_cop
        elif t_amb < 16.0:
            heat_th = 0.22 * (16.0 - t_amb)
            if t_amb >= -10.0:
                hp_cop = max(1.6, 3.2 - 0.06 * (16.0 - t_amb))
                hp_elec[i] = min(heat_th / hp_cop, 3.5)
                aux_th[i] = max(0.0, heat_th - (hp_elec[i] * hp_cop))
            else:
                aux_th[i] = heat_th

    ac_series = pd.Series(ac_elec, index=tmy_data.index)
    hp_series = pd.Series(hp_elec, index=tmy_data.index)
    aux_series = pd.Series(aux_th, index=tmy_data.index)
    load_kwh = base_load + ac_series + hp_series
    avg_daily_kwh = load_kwh.sum() / 365.0

    # 5. Cell-Level Battery Sizing & Dispatch
    usable_window = max(0.05, soc_max - soc_min)
    usable_kwh_needed = (avg_daily_kwh / 24.0) * storage_hours
    target_batt_kwh = usable_kwh_needed / usable_window

    cells_per_unit = math.ceil(target_batt_kwh / CELL_SPECS["kwh"])
    actual_batt_kwh = cells_per_unit * CELL_SPECS["kwh"]
    batt_mass_kg = cells_per_unit * CELL_SPECS["mass_kg"]
    batt_vol_l = cells_per_unit * CELL_SPECS["volume_l"]

    min_e = actual_batt_kwh * soc_min
    max_e = actual_batt_kwh * soc_max
    eta_c = math.sqrt(batt_eff)
    eta_d = math.sqrt(batt_eff)

    soc = np.zeros(len(tmy_data))
    grid_imp = np.zeros(len(tmy_data))
    grid_exp = np.zeros(len(tmy_data))
    curr_e = np.clip(0.50 * actual_batt_kwh, min_e, max_e)

    for i in range(len(tmy_data)):
        net = ac_gen_kwh.iloc[i] - load_kwh.iloc[i]
        if net > 0:
            stored = min(net * eta_c, max_e - curr_e)
            curr_e += stored
            grid_exp[i] = net - (stored / eta_c)
        elif net < 0:
            deficit = abs(net)
            drawn = min(deficit / eta_d, curr_e - min_e)
            curr_e -= drawn
            grid_imp[i] = deficit - (drawn * eta_d)
        soc[i] = (curr_e / actual_batt_kwh) * 100.0

    annual_dc_kwh = dc_watts_unit.sum() / 1000.0
    annual_ac_kwh = ac_gen_kwh.sum()
    cf_dc = annual_dc_kwh / (nameplate_kw * len(tmy_data))
    cf_ac = annual_ac_kwh / (nameplate_kw * len(tmy_data))

    return {
        "site_name": site_name,
        "albedo": albedo,
        "gcr": gcr,
        "storage_hours": storage_hours,
        "nameplate_kw": nameplate_kw,
        "total_panels_unit": n_modules * n_columns,
        "panel_rating_w": MODULE_SPECS["STC"],
        "panel_rating_w_per_m2": panel_rating_w_per_m2,
        "panel_name": MODULE_SPECS["Name"],
        "unit_area_m2": unit_area_m2,
        "gross_land_m2_per_unit": gross_land_m2_per_unit,
        "total_rail_m": total_rail_m,
        "tmy": tmy_data,
        "irrad": irrad,
        "dc_kwh_series": dc_watts_unit / 1000.0,
        "ac_gen_kwh": ac_gen_kwh,
        "annual_dc_kwh": annual_dc_kwh,
        "annual_ac_kwh": annual_ac_kwh,
        "specific_yield_dc": annual_dc_kwh / nameplate_kw,
        "cf_dc": cf_dc,
        "cf_ac": cf_ac,
        "load_kwh": load_kwh,
        "base_load": base_load,
        "ac_elec": ac_series,
        "hp_elec": hp_series,
        "aux_heat_th": aux_series,
        "avg_daily_kwh": avg_daily_kwh,
        "soc": pd.Series(soc, index=tmy_data.index),
        "cells_per_unit": cells_per_unit,
        "actual_batt_kwh": actual_batt_kwh,
        "batt_mass_kg": batt_mass_kg,
        "batt_vol_l": batt_vol_l,
        "grid_import_kwh": grid_imp.sum(),
        "grid_export_kwh": grid_exp.sum(),
        "self_sufficiency": (1.0 - grid_imp.sum() / load_kwh.sum()) * 100.0,
}


def compute_national_scaleup(
    nat_res: dict,
    us_energy_target_twh: float,
    pv_cost_per_w: float,
    racking_batt_cost_per_kwh: float,
    megapack_cost_per_kwh: float,
):
    """Scales the unit block from the National Array site to meet the U.S. TWh target."""
    us_target_kwh = us_energy_target_twh * 1e9
    scale_factor = us_target_kwh / nat_res["annual_ac_kwh"]

    target_capacity_kwp = scale_factor * nat_res["nameplate_kw"]
    target_capacity_gwp = target_capacity_kwp / 1e6
    total_panels = nat_res["total_panels_unit"] * scale_factor
    total_area_sqmi = (nat_res["gross_land_m2_per_unit"] * scale_factor / 1e6) * 0.386102

    total_storage_gwh = (nat_res["actual_batt_kwh"] * scale_factor) / 1e6
    total_cells_billions = (nat_res["cells_per_unit"] * scale_factor) / 1e9
    megapack_equiv_units = (total_storage_gwh * 1e6) / 3916.0

    pv_capex_usd = target_capacity_kwp * 1000.0 * pv_cost_per_w
    racking_batt_capex_usd = total_storage_gwh * 1e6 * racking_batt_cost_per_kwh
    megapack_batt_capex_usd = total_storage_gwh * 1e6 * megapack_cost_per_kwh

    blended_capex_per_kwp = (pv_capex_usd + racking_batt_capex_usd) / target_capacity_kwp

    return {
        "scale_factor": scale_factor,
        "target_capacity_kwp": target_capacity_kwp,
        "target_capacity_gwp": target_capacity_gwp,
        "capacity_factor_ac": nat_res["cf_ac"],
        "capacity_factor_dc": nat_res["cf_dc"],
        "total_panels": total_panels,
        "total_area_sqmi": total_area_sqmi,
        "square_side_miles": math.sqrt(total_area_sqmi),
        "total_storage_gwh": total_storage_gwh,
        "total_cells_billions": total_cells_billions,
        "megapack_equiv_units": megapack_equiv_units,
        "pv_capex_usd": pv_capex_usd,
        "racking_batt_capex_usd": racking_batt_capex_usd,
        "megapack_batt_capex_usd": megapack_batt_capex_usd,
        "total_capex_integrated_usd": pv_capex_usd + racking_batt_capex_usd,
        "total_capex_megapack_usd": pv_capex_usd + megapack_batt_capex_usd,
        "capex_savings_usd": megapack_batt_capex_usd - racking_batt_capex_usd,
        "blended_capex_per_kwp": blended_capex_per_kwp,
    }

