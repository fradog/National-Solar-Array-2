# -*- coding: utf-8 -*-
"""
National Solar Array Bond Initiative
Integrated with pvfactors + CEC Single-Diode + Racking-Integrated LFP Storage
"""

import numpy as np
import numpy_financial as npf
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import importlib
import sys
from typing import Union

# --- RELOAD LOCAL MODULES ---
if "efficiency_upgrade" in sys.modules:
    importlib.reload(sys.modules["efficiency_upgrade"])
#if "physics_engine" in sys.modules:
#    importlib.reload(sys.modules["physics_engine"])

from efficiency_upgrade import calculate_efficiency_upgrade
from physics_engine import (
    LOCATION_PRESETS,
    MODULE_SPECS,
    CELL_SPECS,
    run_site_simulation,
    compute_national_scaleup,
)
from solar_model import (
    target_total_energy,
    calculate_bond_principal,
    calculate_cash_flows,
    calculate_funding_mix,
    calculate_metrics,
    calculate_lcoe_simple,
    calculate_lcoe_nrel_style,
    calculate_lcoe_diagnostic,
)

# --- PLOTLY LEGEND ABOVE CHART ---
LEGEND_ABOVE = dict(
    legend=dict(
        title=None,
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
    ),
    hovermode="x unified",
)

# =============================================
# PAGE TITLE & DESCRIPTION
# =============================================
st.set_page_config(page_title="National Solar Array: Net Zero Economics", layout="wide")
st.markdown("[Full README](https://github.com)")

st.title("National Solar Array Finance Calculator")
st.write(
    "<span style='font-size:0.85rem; font-style:italic;'>"
    "This calculator allows the user to better understand that a massive solar + storage array can indeed and realistically "
    "help drive the U.S. to Net Zero carbon dioxide emissions by ~2035–2037, "
    "with strong financial returns, energy independence, and no one left behind. Funded via bonds or budget, "
    "revenues at current electricity prices far exceed costs. This is the potential that massive deployment, "
    "on a scale one order of magnitude greater than currently discussed, offers."
    "</span>",
    unsafe_allow_html=True,
)

# =============================================
# DEFAULT INPUTS
# =============================================
default_inputs = {
    "project_lifespan": 30,
    "initial_capacity": 230_000_000,      # kWp
    "revenue_per_kwh": 0.16,
    "avoided_fuel_per_kwh": 0.03,
    "om_rate": 0.01,
    "grid_maintenance_bn": 50,            # $Billion
    "discount_rate": 0.04,
    "degradation_rate": 0.007,
    "reinvestment_percentage": 0.5,
    "investment_return_rate": 0.03,
    "bond_interest_rate": 0.025,
    "bond_term": 10,
    "dividend_percentage": 0.5,
    "individual_investment": 10_000,
    "us_adult_population": 258_000_000,
    "participation_rate_low": 0.05,
    "participation_rate_mid": 0.10,
    "participation_rate_high": 0.15,
    "carbon_tax_rate": 100.00,
    "us_emissions_tons": 4700000000,
    "carbon_tax_effective_rate": 0.75,
    "displaceable_proportion": 1.0,
    "vehicle_ice_eff": 0.200,
    "vehicle_elec_eff": 0.800,
    "utility_ice_elec_eff": 0.370,
    # New Physics & Racking Storage Defaults
    "home_preset": "Newbury Park, CA (Home)",
    "nat_preset": "Yuma, AZ (Southwest Desert)",
    "gcr": 0.35,
    "home_storage_hours": 12.0,
    "nat_storage_hours": 12.0,
    "soc_min": 0.20,
    "soc_max": 0.80,
    "pv_cost_per_w": 1.00,
    "racking_batt_cost_per_kwh": 90.0,
    "megapack_cost_per_kwh": 235.0,
}

def _ss(key, default):
    return st.session_state.get(key, default)

# =============================================
# EFFICIENCY SLIDERS (MAIN BODY)
# =============================================
st.subheader("Fossil-to-Electric Efficiency Assumptions")
st.write(
    "<span style='font-size:0.85rem; font-style:italic;'>"
    "Electrifying energy use reduces total consumption due to efficiency gains. "
    "This model adjusts 2023 fossil energy (77.1 quads) downward accordingly."
    "</span>",
    unsafe_allow_html=True,
)

col1, col2, col3 = st.columns(3)
with col1:
    vehicle_ice_eff = st.slider(
        "ICE Vehicle Efficiency", 0.10, 0.35,
        _ss("vehicle_ice_eff", default_inputs["vehicle_ice_eff"]),
        0.005, format="%.3f"
    )
with col2:
    vehicle_elec_eff = st.slider(
        "EV Drivetrain Efficiency", 0.60, 0.95,
        _ss("vehicle_elec_eff", default_inputs["vehicle_elec_eff"]),
        0.005, format="%.3f"
    )
with col3:
    utility_ice_elec_eff = st.slider(
        "Fossil Plant Efficiency", 0.30, 0.60,
        _ss("utility_ice_elec_eff", default_inputs["utility_ice_elec_eff"]),
        0.005, format="%.3f"
    )

mix_inputs = {
    "total_energy_quads": 77.10,
    "petroleum_fraction": 0.459, "gas_fraction": 0.436, "coal_fraction": 0.105,
    "petroleum_trans_fraction": 0.696, "petroleum_heating_fraction": 0.296, "petroleum_elec_fraction": 0.008,
    "gas_trans_fraction": 0.040, "gas_heating_fraction": 0.560, "gas_elec_fraction": 0.400,
    "coal_trans_fraction": 0.0, "coal_heating_fraction": 0.114, "coal_elec_fraction": 0.886,
    "vehicle_ice_eff": vehicle_ice_eff,
    "vehicle_elec_eff": vehicle_elec_eff,
    "utility_ice_elec_eff": utility_ice_elec_eff,
    "petroleum_heating_eff": 1.0, "gas_heating_eff": 1.0, "coal_heating_eff": 1.0,
    "elec_heating_eff": 1.0, "elec_elec_eff": 1.0,
}

efficiency_upgrade_ratio = calculate_efficiency_upgrade(mix_inputs)
target_energy_quads = efficiency_upgrade_ratio * mix_inputs["total_energy_quads"]
target_energy_twh = target_energy_quads * 293.07

st.write(
    f"**Efficiency Upgrade Ratio**: {efficiency_upgrade_ratio:,.3f}  |  "
    f"**Post-Electrification U.S. Energy Target**: {target_energy_twh:,.0f} TWh/yr"
)

# =============================================
# SIDEBAR INPUTS
# =============================================
st.sidebar.header("Input Parameters")

if st.sidebar.button("Restore Defaults", type="primary", use_container_width=True):
    for key, val in default_inputs.items():
        st.session_state[key] = val
    st.session_state["initial_capacity_gw"] = int(default_inputs["initial_capacity"] / 1_000_000)
    st.session_state["us_adpop_mil"] = int(default_inputs["us_adult_population"] / 1_000_000)
    st.success("All inputs restored to defaults!")
    st.rerun()

inputs = {}

def _make_slider(container, param: str, default: Union[float, int], unit: str = "", **kwargs):
    pretty = param.replace("_", " ").title()
    label = f"{pretty} {unit}".strip()
    return container.slider(label, value=_ss(param, default), **kwargs)

# -------------------------------------------------
# 1. Solar Array & Racking Storage Physics Inputs
# -------------------------------------------------
with st.sidebar.expander("Solar & Racking Storage Physics", expanded=True):
    preset_names = list(LOCATION_PRESETS.keys()) + ["Custom Coordinates"]

    home_preset = st.selectbox(
        "Home Array Location", preset_names,
        index=preset_names.index(_ss("home_preset", default_inputs["home_preset"]))
    )
    if home_preset != "Custom Coordinates":
        h_cfg = LOCATION_PRESETS[home_preset]
        home_lat, home_lon, home_tz, home_alt = h_cfg["lat"], h_cfg["lon"], h_cfg["tz"], h_cfg["alt"]
        home_albedo = st.slider("Home Ground Albedo", 0.10, 0.50, h_cfg["albedo"], 0.01)
    else:
        home_lat = st.number_input("Home Latitude", value=34.1842, format="%.4f")
        home_lon = st.number_input("Home Longitude", value=-118.9101, format="%.4f")
        home_tz = st.text_input("Home Timezone", value="America/Los_Angeles")
        home_alt = st.number_input("Home Altitude (m)", value=200.0)
        home_albedo = st.slider("Home Ground Albedo", 0.10, 0.50, 0.20, 0.01)

    nat_preset = st.selectbox(
        "National Array Location", preset_names,
        index=preset_names.index(_ss("nat_preset", default_inputs["nat_preset"]))
    )
    if nat_preset != "Custom Coordinates":
        n_cfg = LOCATION_PRESETS[nat_preset]
        nat_lat, nat_lon, nat_tz, nat_alt = n_cfg["lat"], n_cfg["lon"], n_cfg["tz"], n_cfg["alt"]
        nat_albedo = st.slider("National Array Albedo", 0.10, 0.50, n_cfg["albedo"], 0.01)
    else:
        nat_lat = st.number_input("National Latitude", value=32.6984, format="%.4f")
        nat_lon = st.number_input("National Longitude", value=-114.6504, format="%.4f")
        nat_tz = st.text_input("National Timezone", value="America/Phoenix")
        nat_alt = st.number_input("National Altitude (m)", value=75.0)
        nat_albedo = st.slider("National Array Albedo", 0.10, 0.50, 0.28, 0.01)

    gcr = st.slider(
        "Ground Coverage Ratio (GCR)", 0.20, 0.65,
        _ss("gcr", default_inputs["gcr"]), 0.01, format="%.2f"
    )
    home_storage_hours = st.slider(
        "Home Storage Backup (Hours/day)", 0.0, 48.0,
        _ss("home_storage_hours", default_inputs["home_storage_hours"]), 1.0
    )
    nat_storage_hours = st.slider(
        "National Array Storage (Hours/day)", 0.0, 48.0,
        _ss("nat_storage_hours", default_inputs["nat_storage_hours"]), 1.0
    )
    soc_min = st.slider(
        "Battery Min SoC", 0.05, 0.40,
        _ss("soc_min", default_inputs["soc_min"]), 0.05, format="%.2f"
    )
    soc_max = st.slider(
        "Battery Max SoC (Variable Upper Bound)", 0.50, 1.00,
        _ss("soc_max", default_inputs["soc_max"]), 0.05, format="%.2f"
    )
# -------------------------------------------------
# 2. System Scale & Lifespan
# -------------------------------------------------
with st.sidebar.expander("System Scale & Lifespan", expanded=False):
    inputs["project_lifespan"] = st.text_input(
        "Project Lifespan (Yrs)", value=str(_ss("project_lifespan", default_inputs["project_lifespan"]))
    )
    gw_default = int(default_inputs["initial_capacity"] / 1_000_000)
    gw_value = _ss("initial_capacity_gw", gw_default)
    inputs["initial_capacity"] = st.slider(
        "Initial Capacity (GWp)", 0, 1000, value=gw_value, step=10
    ) * 1_000_000

    inputs["degradation_rate"] = _make_slider(
        st, "degradation_rate", default_inputs["degradation_rate"],
        unit="/yr", min_value=0.0, max_value=0.015, step=0.001, format="%.3f"
    )

# -------------------------------------------------
# 3. Costs (PV + Racking Battery vs. Megapack)
# -------------------------------------------------
with st.sidebar.expander("Costs (PV & Racking Storage)", expanded=False):
    pv_cost_per_w = st.slider(
        "Solar PV Cost ($/W DC)", 0.40, 2.50,
        _ss("pv_cost_per_w", default_inputs["pv_cost_per_w"]), 0.05, format="$%.2f"
    )
    racking_batt_cost_per_kwh = st.slider(
        "Racking-Integrated LFP Cost ($/kWh)", 40.0, 200.0,
        _ss("racking_batt_cost_per_kwh", default_inputs["racking_batt_cost_per_kwh"]), 5.0, format="$%.0f"
    )
    megapack_cost_per_kwh = st.slider(
        "Megapack 2 XL Benchmark ($/kWh)", 150.0, 400.0,
        _ss("megapack_cost_per_kwh", default_inputs["megapack_cost_per_kwh"]), 5.0, format="$%.0f"
    )
    inputs["om_rate"] = _make_slider(
        st, "om_rate", default_inputs["om_rate"],
        unit="(fraction/yr)", min_value=0.0, max_value=0.05, step=0.001, format="%.3f"
    )
    inputs["grid_maintenance_bn"] = _make_slider(
        st, "grid_maintenance_bn", default_inputs["grid_maintenance_bn"],
        unit="$/yr", min_value=0, max_value=200, step=5, format="$%.0f"
    )

# -------------------------------------------------
# 4. Revenue & Savings
# -------------------------------------------------
with st.sidebar.expander("Revenue & Savings", expanded=False):
    inputs["revenue_per_kwh"] = _make_slider(
        st, "revenue_per_kwh", default_inputs["revenue_per_kwh"],
        unit="$/kWh", min_value=0.00, max_value=0.30, step=0.001, format="$%.3f"
    )
    inputs["avoided_fuel_per_kwh"] = _make_slider(
        st, "avoided_fuel_per_kwh", default_inputs["avoided_fuel_per_kwh"],
        unit="$/kWh", min_value=0.0, max_value=0.10, step=0.001, format="$%.3f"
    )
    inputs["carbon_tax_rate"] = _make_slider(
        st, "carbon_tax_rate", default_inputs["carbon_tax_rate"],
        unit="$/ton", min_value=0.0, max_value=200.0, step=5.0, format="$%.0f"
    )
    inputs["carbon_tax_effective_rate"] = _make_slider(
        st, "carbon_tax_effective_rate", default_inputs["carbon_tax_effective_rate"],
        unit="", min_value=0.5, max_value=1.0, step=0.05, format="%.2f"
    )
    inputs["displaceable_proportion"] = _make_slider(
        st, "displaceable_proportion", default_inputs["displaceable_proportion"],
        unit="", min_value=0.0, max_value=1.0, step=0.05, format="%.2f"
    )
    inputs["us_emissions_tons"] = st.text_input(
        "Annual U.S. CO₂e Emissions (tons)",
        value=str(_ss("us_emissions_tons", f"{default_inputs['us_emissions_tons']:,}"))
    )

# -------------------------------------------------
# 5. Reinvestment
# -------------------------------------------------
with st.sidebar.expander("Reinvestment", expanded=False):
    inputs["reinvestment_percentage"] = _make_slider(
        st, "reinvestment_percentage", default_inputs["reinvestment_percentage"],
        unit="(fraction)", min_value=0.0, max_value=1.0, step=0.05, format="%.2f"
    )
    inputs["investment_return_rate"] = _make_slider(
        st, "investment_return_rate", default_inputs["investment_return_rate"],
        unit="", min_value=0.0, max_value=0.20, step=0.005, format="%.3f"
    )
    inputs["discount_rate"] = _make_slider(
        st, "discount_rate", default_inputs["discount_rate"],
        unit="", min_value=0.0, max_value=0.20, step=0.005, format="%.3f"
    )

# -------------------------------------------------
# 6. Bond Financing
# -------------------------------------------------
with st.sidebar.expander("Bond Financing", expanded=False):
    us_adpop_default = int(default_inputs["us_adult_population"] / 1_000_000)
    us_adpop_value = _ss("us_adpop_mil", us_adpop_default)
    inputs["us_adult_population"] = st.slider(
        "US Adult Population (M)", 200, 350, value=us_adpop_value, step=2
    ) * 1_000_000

    inputs["bond_interest_rate"] = _make_slider(
        st, "bond_interest_rate", default_inputs["bond_interest_rate"],
        unit="", min_value=0.0, max_value=0.10, step=0.001, format="%.3f"
    )
    inputs["bond_term"] = st.number_input(
        "Bond Term (years)", min_value=1, max_value=30,
        value=int(_ss("bond_term", default_inputs["bond_term"])), step=1
    )
    inputs["dividend_percentage"] = _make_slider(
        st, "dividend_percentage", default_inputs["dividend_percentage"],
        unit="(fraction)", min_value=0.0, max_value=1.0, step=0.05, format="%.2f"
    )
    inputs["individual_investment"] = _make_slider(
        st, "individual_investment", default_inputs["individual_investment"],
        unit="$", min_value=0, max_value=100_000, step=100, format="$%.0f"
    )
    inputs["participation_rate_low"] = _make_slider(
        st, "participation_rate_low", default_inputs["participation_rate_low"],
        unit="", min_value=0.0, max_value=1.00, step=0.05, format="%.2f"
    )
    inputs["participation_rate_mid"] = _make_slider(
        st, "participation_rate_mid", default_inputs["participation_rate_mid"],
        unit="", min_value=0.0, max_value=1.00, step=0.05, format="%.2f"
    )
    inputs["participation_rate_high"] = _make_slider(
        st, "participation_rate_high", default_inputs["participation_rate_high"],
        unit="", min_value=0.0, max_value=1.00, step=0.05, format="%.2f"
    )

# ===============================================================
# SAVE TO SESSION STATE & CONVERT TYPES
# ===============================================================
for key, value in inputs.items():
    if key not in {"initial_capacity", "us_adult_population"}:
        st.session_state[key] = value

st.session_state["initial_capacity_gw"] = inputs["initial_capacity"] // 1_000_000
st.session_state["us_adpop_mil"] = inputs["us_adult_population"] // 1_000_000
st.session_state["vehicle_ice_eff"] = vehicle_ice_eff
st.session_state["vehicle_elec_eff"] = vehicle_elec_eff
st.session_state["utility_ice_elec_eff"] = utility_ice_elec_eff
st.session_state["home_preset"] = home_preset
st.session_state["nat_preset"] = nat_preset
st.session_state["gcr"] = gcr
st.session_state["home_storage_hours"] = home_storage_hours
st.session_state["nat_storage_hours"] = nat_storage_hours
st.session_state["soc_min"] = soc_min
st.session_state["soc_max"] = soc_max
st.session_state["pv_cost_per_w"] = pv_cost_per_w
st.session_state["racking_batt_cost_per_kwh"] = racking_batt_cost_per_kwh
st.session_state["megapack_cost_per_kwh"] = megapack_cost_per_kwh

def _to_num(val, is_int=False):
    try:
        cleaned = str(val).replace(",", "")
        return int(float(cleaned)) if is_int else float(cleaned)
    except Exception:
        return val

for k in ["project_lifespan", "bond_term", "individual_investment"]:
    if k in inputs:
        inputs[k] = _to_num(inputs[k], is_int=True)

for k in list(inputs.keys()):
    if k not in {"initial_capacity", "us_adult_population", "project_lifespan", "bond_term", "individual_investment"}:
        inputs[k] = _to_num(inputs[k], is_int=False)

# =============================================
# RUN PHYSICS ENGINE (HOME & NATIONAL SITES)
# =============================================
if soc_max <= soc_min:
    st.error("Battery Max SoC must be strictly greater than Battery Min SoC.")
    st.stop()

home_res = run_site_simulation(
    site_name=home_preset,
    lat=home_lat, lon=home_lon, tz=home_tz, alt=home_alt,
    albedo=home_albedo, gcr=gcr,
    storage_hours=home_storage_hours, soc_min=soc_min, soc_max=soc_max,
)

nat_res = run_site_simulation(
    site_name=nat_preset,
    lat=nat_lat, lon=nat_lon, tz=nat_tz, alt=nat_alt,
    albedo=nat_albedo, gcr=gcr,
    storage_hours=nat_storage_hours, soc_min=soc_min, soc_max=soc_max,
)

scale_res = compute_national_scaleup(
    nat_res=nat_res,
    us_energy_target_twh=target_energy_twh,
    pv_cost_per_w=pv_cost_per_w,
    racking_batt_cost_per_kwh=racking_batt_cost_per_kwh,
    megapack_cost_per_kwh=megapack_cost_per_kwh,
)

# Wire physics outputs directly into solar_model inputs
inputs["efficiency_upgrade"] = efficiency_upgrade_ratio
inputs["target_capacity"] = scale_res["target_capacity_kwp"]
inputs["capacity_factor"] = scale_res["capacity_factor_ac"]
inputs["panel_rating"] = nat_res["panel_rating_w_per_m2"]
inputs["coverage_ratio"] = gcr
inputs["capital_cost_per_kwp"] = scale_res["blended_capex_per_kwp"]

# =============================================
# LCOE VALIDATION MODE
# =============================================
validate_lcoe = st.sidebar.checkbox("LCOE Validation Mode (Zero extras + Unlevered NPV)")
if validate_lcoe:
    for key in ["avoided_fuel_per_kwh", "carbon_tax_rate", "grid_maintenance_bn", "degradation_rate"]:
        inputs[key] = 0.0
    inputs["bond_interest_rate"] = 0.0
    inputs["bond_term"] = 0

# =============================================
# NEW: SOLAR SYSTEM DESCRIPTION BLOCK
# =============================================
st.markdown("---")
st.header("Solar System Description (Physics & Racking Storage)")
st.write(
    "<span style='font-size:0.85rem; font-style:italic;'>"
    "System sizing, capacity factor, and unit-block storage are dynamically calculated using PVGIS TMY weather, "
"2D view-factor bifacial shading (pvfactors), and the CEC single-diode model."
"",
unsafe_allow_html=True,
)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Target National Capacity", f"{scale_res['target_capacity_gwp']:,.0f} GWp", f"{scale_res['total_panels']/1e9:.2f}B Panels")
c2.metric("National Capacity Factor (AC)", f"{scale_res['capacity_factor_ac']*100:.2f}%", f"DC CF: {scale_res['capacity_factor_dc']*100:.2f}%")
c3.metric("Panel Rating & Density", f"{nat_res['panel_rating_w']:.0f} W", f"{nat_res['panel_rating_w_per_m2']:.1f} W/m² (GCR {gcr:.2f})")
c4.metric("Blended System CapEx", f"${scale_res['blended_capex_per_kwp']:,.0f}/kWp", f"PV ${pv_cost_per_w:.2f}/W + LFP ${racking_batt_cost_per_kwh:.0f}/kWh")
c5, c6, c7, c8 = st.columns(4)
c5.metric("National Land Footprint", f"{scale_res['total_area_sqmi']:,.0f} sq mi", f"{scale_res['square_side_miles']:.0f} mi × {scale_res['square_side_miles']:.0f} mi")
c6.metric("Integrated LFP Storage", f"{scale_res['total_storage_gwh']:,.0f} GWh", f"{scale_res['total_cells_billions']:.2f}B × 314Ah Cells")
c7.metric("Integrated vs. Megapack CapEx", f"${scale_res['total_capex_integrated_usd']/1e12:.2f}T", f"Saves ${scale_res['capex_savings_usd']/1e12:.2f}T vs. Megapack")
c8.metric("Home Self-Sufficiency", f"{home_res['self_sufficiency']:.1f}%", f"{home_res['cells_per_unit']} cells ({home_res['batt_mass_kg']/home_res['total_rail_m']:.1f} kg/m rail)")
with st.expander("Detailed Unit Block & Site Comparison Table", expanded=False):
    comp_df = pd.DataFrame([
    {
    "Site": home_res["site_name"],
    "Unit Array (kW DC)": round(home_res["nameplate_kw"], 2),
    "Annual AC Yield (kWh)": round(home_res["annual_ac_kwh"], 0),
    "AC Capacity Factor (%)": round(home_res["cf_ac"] * 100, 2),
    "Avg Home Load (kWh/day)": round(home_res["avg_daily_kwh"], 1),
    "Racking Battery (kWh)": round(home_res["actual_batt_kwh"], 2),
    "314Ah Cells / Unit": home_res["cells_per_unit"],
    "Cell Mass / Rail (kg/m)": round(home_res["batt_mass_kg"] / home_res["total_rail_m"], 2),
    "Self-Sufficiency (%)": round(home_res["self_sufficiency"], 1),
    },
    {
    "Site": nat_res["site_name"],
    "Unit Array (kW DC)": round(nat_res["nameplate_kw"], 2),
    "Annual AC Yield (kWh)": round(nat_res["annual_ac_kwh"], 0),
    "AC Capacity Factor (%)": round(nat_res["cf_ac"] * 100, 2),
    "Avg Home Load (kWh/day)": round(nat_res["avg_daily_kwh"], 1),
    "Racking Battery (kWh)": round(nat_res["actual_batt_kwh"], 2),
    "314Ah Cells / Unit": nat_res["cells_per_unit"],
    "Cell Mass / Rail (kg/m)": round(nat_res["batt_mass_kg"] / nat_res["total_rail_m"], 2),
    "Self-Sufficiency (%)": round(nat_res["self_sufficiency"], 1),
    },
    ])
    st.dataframe(comp_df, use_container_width=True, hide_index=True)

# --- Interactive Physics & Storage Plots ---

with st.expander("Physics & Racking Battery Simulation Charts (Home vs. National Site)", expanded=True):
    tab_yield, tab_july = st.tabs(["Monthly Yield & Bifacial Irradiance", "July 1–7 Battery SoC & Seasonal Load"])
    
    with tab_yield:
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        m_home = home_res["dc_kwh_series"].groupby(home_res["dc_kwh_series"].index.month).sum()
        m_nat = nat_res["dc_kwh_series"].groupby(nat_res["dc_kwh_series"].index.month).sum()
        fig_phys = make_subplots(
            rows=1, cols=2,
            subplot_titles=("Monthly Unit Block DC Yield (kWh)", "Daily Avg Rear Bifacial Irradiance (W/m²)")
        )
        fig_phys.add_trace(go.Bar(x=months, y=m_home.values, name=home_res["site_name"], marker_color="steelblue"), row=1, col=1)
        fig_phys.add_trace(go.Bar(x=months, y=m_nat.values, name=nat_res["site_name"], marker_color="darkorange"), row=1, col=1)
        rear_home = home_res["irrad"]["total_inc_back"].resample("D").mean().values[:365]
        rear_nat = nat_res["irrad"]["total_inc_back"].resample("D").mean().values[:365]
        fig_phys.add_trace(go.Scatter(x=list(range(1, 366)), y=rear_home, name=f"{home_res['site_name']} Rear", line=dict(color="steelblue")), row=1, col=2)
        fig_phys.add_trace(go.Scatter(x=list(range(1, 366)), y=rear_nat, name=f"{nat_res['site_name']} Rear", line=dict(color="darkorange")), row=1, col=2)
        fig_phys.update_layout(height=400, barmode="group", **LEGEND_BELOW)
        st.plotly_chart(fig_phys, use_container_width=True)

    with tab_july:
        fig_july = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                f"Battery SoC (%) – {home_res['site_name']}",
                f"Battery SoC (%) – {nat_res['site_name']}",
                f"Load & Solar AC Gen (kWh) – {home_res['site_name']}",
                f"Load & Solar AC Gen (kWh) – {nat_res['site_name']}",
            )
        )
        for col_idx, res in enumerate([home_res, nat_res], start=1):
            mask = (res["tmy"].index.month == 7) & (res["tmy"].index.day <= 7)
            hr_axis = list(range(mask.sum()))
            fig_july.add_trace(go.Scatter(x=hr_axis, y=res["soc"][mask].values, name=f"{res['site_name']} SoC", line=dict(color="purple")), row=1, col=col_idx)
            fig_july.add_hline(y=soc_max * 100, line_dash="dash", line_color="red", row=1, col=col_idx)
            fig_july.add_hline(y=soc_min * 100, line_dash="dash", line_color="orange", row=1, col=col_idx)
            fig_july.add_trace(go.Scatter(x=hr_axis, y=res["base_load"][mask].values, name="Base Load", stackgroup="load", line=dict(color="steelblue")), row=2, col=col_idx)
            fig_july.add_trace(go.Scatter(x=hr_axis, y=res["ac_elec"][mask].values, name="Summer AC", stackgroup="load", line=dict(color="firebrick")), row=2, col=col_idx)
            fig_july.add_trace(go.Scatter(x=hr_axis, y=res["ac_gen_kwh"][mask].values, name="Solar AC Gen", line=dict(color="goldenrod", width=2)), row=2, col=col_idx)

        fig_july.update_yaxes(range=[0, 100], row=1, col=1)
        fig_july.update_yaxes(range=[0, 100], row=1, col=2)
        fig_july.update_layout(height=550, showlegend=False)
        st.plotly_chart(fig_july, use_container_width=True)

# =============================================
# FINANCIAL & BOND CALCULATIONS (solar_model.py)
# =============================================

annual_energy_goal, required_area = target_total_energy(inputs)
bond_principal, carbon_tax_10yr = calculate_bond_principal(inputs)
cash_flows_df = calculate_cash_flows(inputs, bond_principal, project_lifespan=inputs["project_lifespan"])
cash_flows_df["Cumulative Post-Debt Cash Flow ($B)"] = cash_flows_df["Cash Flow Post-Debt ($B)"].cumsum()
funding_mix_df = calculate_funding_mix(inputs, bond_principal)
metrics = calculate_metrics(inputs, cash_flows_df, bond_principal)
final_energy_twh = cash_flows_df.loc[cash_flows_df["Year"] == inputs["project_lifespan"], "Energy Yield (TWh)"].iloc[0]
energy_gap = final_energy_twh - target_energy_twh
st.markdown("---")
st.header("System Size & Energy Target Reconciliation")
st.write(
f""
f"The size of the solar system represented here is that which is required to replace fossil fueled energy in 2023, {mix_inputs['total_energy_quads']:.2f} quads ({mix_inputs['total_energy_quads'] * 293.07:,.0f} TWh). "
f"The existing other renewables and nuclear as of 2023 remain as is over the lifetime of the system."
f"",
unsafe_allow_html=True,
)
st.write(f"Target Annual Energy: {target_energy_twh:,.0f} TWh")
st.write(f"System Annual Energy (Year {inputs['project_lifespan']} post-degradation): {final_energy_twh:,.0f} TWh")
st.write(f"Area Required: {scale_res['total_area_sqmi']:,.0f} sq mi (GCR: {gcr:.2f})")
st.metric(
"Energy Gap (Target vs. Array Energy Output at Full Capacity incl. degradation)",
f"{energy_gap:,.2f} TWh",
delta=f"{(energy_gap / target_energy_twh)*100:+.1f}%",
)

# LCOE

lcoe_full = calculate_lcoe_simple(inputs)
nrel_lcoe = calculate_lcoe_nrel_style(
capex_per_kw=inputs["capital_cost_per_kwp"],
fom_per_kw_yr=inputs["capital_cost_per_kwp"] * inputs["om_rate"],
cf=inputs["capacity_factor"],
wacc_real=inputs["discount_rate"],
project_life=inputs["project_lifespan"],
)

# UNLEVERED NPV

lifespan = inputs["project_lifespan"]
target_kw = inputs["target_capacity"]
init_kw = inputs["initial_capacity"]
capex_per_kw = inputs["capital_cost_per_kwp"]
om_rate = inputs["om_rate"]
cf = inputs["capacity_factor"]
hours = cf * 8760
annual_add_kw = (target_kw - init_kw) / 10
capex_series = np.array([annual_add_kw * capex_per_kw if yr < 10 else 0 for yr in range(lifespan)])
om_series = np.zeros(lifespan)
cum_kw = init_kw
for yr in range(lifespan):
    if yr < 10:
        cum_kw += annual_add_kw
    om_series[yr] = cum_kw * capex_per_kw * om_rate

energy_series = np.array([
    min(init_kw + annual_add_kw * min(yr + 1, 10), target_kw) * hours
    for yr in range(lifespan)
])
revenue_series = energy_series * inputs["revenue_per_kwh"]
unlevered_cf = revenue_series - capex_series - om_series
unlevered_npv = npf.npv(inputs["discount_rate"], unlevered_cf) / 1e12
st.markdown("---")
st.subheader("Levelized Cost of Energy (LCOE)")
col1, col2 = st.columns(2)
with col1:
    st.metric("Your Model (PV + Racking LFP Storage + Degradation)", f"${lcoe_full['LCOE ($/MWh)']:.2f}/MWh")
    st.caption(f"→ {lcoe_full['LCOE ($/MWh)']/1000:.6f} $/kWh")
with col2:
    delta = nrel_lcoe - lcoe_full["LCOE ($/MWh)"]
    st.metric("NREL ATB Style (FCR, no Degradation)", f"${nrel_lcoe:.2f}/MWh", f"{delta:+.2f} $/MWh", delta_color="inverse")
if validate_lcoe:
    inputs["revenue_per_kwh"] = lcoe_full["LCOE ($/MWh)"] / 1000
    st.success(f"Validation Mode ON: Revenue = LCOE → Unlevered NPV = ${unlevered_npv:+.3f}T")
else:
    st.metric("Unlevered Solar + Storage NPV", f"${unlevered_npv:+.2f}T")

# =============================================
# BOND PRINCIPAL, KEY METRICS & FUNDING MIX
# =============================================

st.header("Bond Principal")
st.write(f"Bond Principal: ${bond_principal/1e9:.2f}B")
st.write(f"Carbon Tax Revenue (10yr): ${carbon_tax_10yr/1e9:.2f}B")
st.header("Key Metrics")
metrics_df = pd.DataFrame([metrics]).round(2)
last_col = "Individual Bond Investor Ending Balance ($)"
format_dict = {col: "{:,.0f}" if col == last_col else "{:,.2f}" for col in metrics_df.select_dtypes("number").columns}
styled = (
metrics_df.style
.format(format_dict)
.set_properties(**{"text-align": "right"}, subset=[last_col])
.set_table_styles([{"selector": "th, td", "props": [("text-align", "center"), ("white-space", "normal")]}])
.hide(axis="index")
)
st.write(f'{styled.to_html()}', unsafe_allow_html=True)
st.header("Annual Capacity and Cash Flows")
st.dataframe(cash_flows_df.round(2), hide_index=True)
st.header("Funding Mix")
household_invest = bond_principal / 132_000_000
st.metric(
"Investment per U.S. Household to Fully Fund Bond",
f"${household_invest:,.0f}",
help="Assumes 132 million U.S. households (Census 2023)",
)
st.subheader(f"Funding Mix Based on U.S. Adult Investor Participation Rates at ${inputs['individual_investment']:,.0f} per Investor")
st.dataframe(funding_mix_df.round(2), hide_index=True)

# =============================================
# FINANCIAL & EMISSIONS PLOTS
# =============================================

st.header("Financial Metrics Over Time")
fig1 = px.line(
cash_flows_df,
x="Year",
y=["Cash Flow Pre-Debt ($B)", "Cash Flow Post-Debt ($B)", "Total Costs ($B)", "Total Inflows ($B)"],
title="Cash Flows",
)
fig1.update_layout(**LEGEND_ABOVE)
st.plotly_chart(fig1, use_container_width=True)
st.header("Balances & Cumulative Cash Flow")
fig2 = px.line(
cash_flows_df,
x="Year",
y=["Reinvested Balance ($B)", "Outstanding Principal ($B)", "Cumulative Post-Debt Cash Flow ($B)"],
title="National Solar Array: Balances & Cumulative Cash Flow",
)
fig2.for_each_trace(lambda t: t.update(line=dict(width=3)) if "Cumulative" in t.name else None)
fig2.update_layout(**LEGEND_ABOVE)
st.plotly_chart(fig2, use_container_width=True)
st.header("CO2 Emissions Reduction")
emissions_data = [
{
"Year": t + 1,
"Total Emissions (B tons)": (
inputs["us_emissions_tons"] * inputs["displaceable_proportion"] * (1 - t / 10)
+ inputs["us_emissions_tons"] * (1 - inputs["displaceable_proportion"])
) / 1e9,
}
for t in range(10)
]
fig3 = px.line(pd.DataFrame(emissions_data), x="Year", y="Total Emissions (B tons)", title="Emissions Reduction")
fig3.update_layout(**LEGEND_ABOVE)
st.plotly_chart(fig3, use_container_width=True)

