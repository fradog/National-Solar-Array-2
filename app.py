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

from pathlib import Path
import streamlit as st
ASSETS_DIR = Path(__file__).parent / "Images"


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
    margin=dict(t=150),
    legend=dict(
        title=None,
        orientation="h",
        yanchor="bottom",
        y=1.2,
        xanchor="center",
        x=0.5,
    ),
    hovermode="x unified",
)

# =============================================
# PAGE TITLE & DESCRIPTION
# =============================================
st.set_page_config(page_title="National Solar Array: Net Zero Economics", layout="wide")
st.markdown("[Full README](https://github.com)")

st.title("National Solar Array Finance Calculator")
st.markdown(
    """
    <div style="font-size: 0.85rem; font-style: italic; line-height: 1.55; margin-bottom: 0.75rem;">
    Eliminating carbon-emitting energy generation is an urgent imperative—and incremental deployment will not get us there in time. This model demonstrates how a national solar-plus-storage buildout, deployed an order of magnitude faster and larger than conventional plans, can realistically drive the U.S. to Net Zero CO₂ emissions by ~2035–2037. Funded through bonds or federal appropriations, this scale delivers true energy independence and leaves no community behind—generating revenues at current electricity prices that far exceed total buildout costs.
    </div>

    <div style="font-size: 0.85rem; font-style: italic; line-height: 1.55; margin-bottom: 0.75rem;">
    Beyond decarbonization, this infrastructure serves as a sovereign fiscal engine capable of transforming federal finances and household take-home pay. By using the electricity price lever across ~9,660 TWh of annual clean generation, the array can retire the entire ~$32.8 trillion publicly held National Debt over 20 to 30 years while permanently funding 100% of U.S. National Defense (~$1.05T/yr) and Social Security (~$1.65T/yr) at ~$0.44–$0.50/kWh—or fund Defense and Social Security indefinitely at ~$0.33/kWh once the debt is cleared. Shifting those ~$2.70 trillion in annual obligations off income taxes and paycheck FICA withholdings translates to roughly $16,800 per year in tax relief per tax filer (~$7,740 per U.S. resident), leaving working families thousands of dollars ahead each year even after accounting for electricity pricing.
    </div>

    <div style="font-size: 0.85rem; font-style: italic; line-height: 1.55; margin-bottom: 1rem;">
    Crucially, executing this buildout as a unified national undertaking yields vastly superior financial returns compared to fragmented private commercial development. Operating at the industrial scale and urgency of a national war effort unlocks massive learning-curve and supply-chain economies while stripping away layers of convoluted project-finance fees, tax-equity middlemen, and commercial insurance markups. By replacing slow, fragmented public-private utility monopolies with a vertically integrated, first-principles engineering organization—operating with the speed, cost discipline, and technical execution of SpaceX—capital flows directly into physical hardware and gigawatts rather than bureaucratic overhead.
    </div>
    """,
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
with st.sidebar:
    st.header("Input Parameters")

    # 1. Keep "Restore Defaults" OUTSIDE the form so st.button() works
    if st.button("Restore Defaults", type="primary", use_container_width=True):
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

    # 2. Start the form AFTER "Restore Defaults" and _make_slider
    with st.form(key="national_solar_inputs_form"):
        # Indent all your _make_slider(...) calls and expanders here (8 spaces)
        # ...
        # ...
    
        # -------------------------------------------------
        # 1. Solar Array & Racking Storage Physics Inputs
        # -------------------------------------------------
        with st.expander("Solar & Racking Storage Physics", expanded=True):
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
        with st.expander("System Scale & Lifespan", expanded=False):
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
            base_daily_kwh = st.slider("Base Daily Residential Load (kWh)", 5.0, 60.0, 25.0, step=1.0)
        
        # -------------------------------------------------
        # 3. System Scale & Lifespan EV Charging 
        # -------------------------------------------------
        with st.expander("EV Charging Parameters", expanded=False):
            n_evs = st.slider("Number of EVs", 0, 4, 1, step=1)
            ev_cons = st.slider("EV EPA Combined Wh/mi)", 50.0, 400.0, 310.0, step=1.0)
            ev_daily = st.slider("Daily EV Driving (miles)", 0, 100, 30, step=5)
            ev_chrg_max_I_home = st.slider("Home Chargeport Max Current", 0, 60, 40, step=2)
        
        # -------------------------------------------------
        # 4. Factory Carbon & Abatement 
        # -------------------------------------------------
        
        with st.expander("🏭 Factory CapEx & Carbon Parameters", expanded=False):
            build_years = st.slider(
                "Buildout Horizon (Years)",
                min_value=1,
                max_value=30,
                value=10,
                step=1,
                help="Years over which the factory capital cost is amortized across total array output.",
            )
            capex_per_kw_yr = st.slider(
                "Greenfield Factory CapEx ($/kW-yr capacity)",
                min_value=150.0,
                max_value=450.0,
                value=280.0,
                step=10.0,
                help="Includes greenfield building, cleanrooms, CZ pullers, DWS, cell lines, and module assembly.",
            )
            module_bom_opex_per_wdc = st.slider(
                "Module Raw Materials & Factory OpEx ($/Wdc)",
                min_value=0.06,
                max_value=0.25,
                value=0.12,
                step=0.01,
                help="Polysilicon, solar glass, aluminum, silver paste, encapsulants, and factory O&M.",
            )
            grid_kg_per_kwh = st.slider(
                "Grid Carbon Intensity (kg CO₂/kWh)",
                min_value=0.00,
                max_value=0.80,
                value=0.38,
                step=0.01,
                help="0.00 = 100% self-powered on-site solar; 0.38 = SW U.S. grid average.",
            )
            factory_mw_per_46gw = st.slider(
                "Factory Power Load (MW per 4.6 GW/yr)",
                min_value=80.0,
                max_value=220.0,
                value=140.0,
                step=5.0,
                help="Continuous electrical draw for CZ pullers, cell furnaces, and chillers (~267 kWh/kWp).",
            )
            scope3_kg_per_kwp = st.slider(
                "Upstream Material Carbon — Scope 3 (kg CO₂/kWp)",
                min_value=0.0,
                max_value=500.0,
                value=280.0,
                step=10.0,
                help="Embodied carbon in polysilicon, solar glass, and aluminum frames (0 = exclude Scope 3).",
            )
            capture_cost_per_ton = st.slider(
                "Carbon Capture / Removal Cost ($/ton CO₂)",
                min_value=0.0,
                max_value=800.0,
                value=65.0,
                step=5.0,
                help="$0 = unabated; ~$65/ton = industrial CCS offsets; ~$600/ton = Direct Air Capture (DAC).",
            )
        
        # -------------------------------------------------
        # 5. Costs (PV + Racking Battery vs. Megapack)
        # -------------------------------------------------
        with st.expander("Costs (PV & Racking Storage)", expanded=False):
            automated_bos_per_wdc = st.slider(
            "Automated Field Balance of System ($/Wdc)",
            min_value=0.15,
            max_value=1.00,
            value=0.45,
            step=0.05,
            help="Runners, automated field 'printer' assembly machines, plug-and-play racking, inverters, and site prep.",
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
        # 6. Revenue & Savings
        # -------------------------------------------------
        with st.expander("Revenue & Savings", expanded=False):
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
        # 7. Reinvestment
        # -------------------------------------------------
        with st.expander("Reinvestment", expanded=False):
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
        # 8. Bond Financing
        # -------------------------------------------------
        with st.expander("Bond Financing", expanded=False):
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


        submitted = st.form_submit_button(
            "🔄 Recalculate Model",
            type="primary",
            use_container_width=True,
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
pv_cost_per_w = module_bom_opex_per_wdc + automated_bos_per_wdc
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
        
# 1. Amortized Factory CapEx ($/Wdc) — independent of total GW!
amortized_capex_per_wdc = capex_per_kw_yr / (build_years * 1000.0)

# 2. Carbon Capture Cost ($/Wdc) — independent of total GW!
kwh_per_kwp_produced = (factory_mw_per_46gw * 1000.0 * 8760.0) / (4.6 * 1_000_000.0)
total_kg_per_kwp = (kwh_per_kwp_produced * grid_kg_per_kwh) + scope3_kg_per_kwp
capture_cost_per_wdc = (total_kg_per_kwp / 1000.0) * capture_cost_per_ton / 1000.

# 3. Complete Installed Solar PV Cost ($/Wdc) — ready BEFORE physics_engine runs!
pv_cost_per_w = (
    module_bom_opex_per_wdc
    + automated_bos_per_wdc
    + amortized_capex_per_wdc
    + capture_cost_per_wdc
)
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
    base_daily_kwh=base_daily_kwh,
    n_evs=n_evs,
    ev_cons=ev_cons,
    ev_daily=ev_daily,
    ev_chrg_max_I_home=ev_chrg_max_I_home
)

nat_res = run_site_simulation(
    site_name=nat_preset,
    lat=nat_lat, lon=nat_lon, tz=nat_tz, alt=nat_alt,
    albedo=nat_albedo, gcr=gcr,
    storage_hours=nat_storage_hours, soc_min=soc_min, soc_max=soc_max,
    base_daily_kwh=base_daily_kwh,
    n_evs=n_evs,
    ev_cons=ev_cons,
    ev_daily=ev_daily,
    ev_chrg_max_I_home=ev_chrg_max_I_home
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
# FACTORY LAYOUT BREAKDOWN AND SCALING
# ============================================

def render_factory_layout(
    build_years: int = 10,
    num_farms: int = 100,
    ingot_diameter_in: int = 8,
):
    # Calculate fresh from scale_res every time the function runs (kWp -> GW)
    total_target_gw = float(scale_res["target_capacity_kwp"]) / 1_000_000.0

    st.header("🏭 Colocated Vertically Integrated Factory Layout")
    st.markdown(
        "Each solar farm includes an on-site, rail-fed manufacturing facility that converts "
        "raw polysilicon, glass, and aluminum directly into finished solar modules—eliminating "
        "outbound long-haul module shipping."
    )

    # --- 1. Interactive / Dynamic Inputs (Defaults match your National Array baseline) ---
    with st.expander("⚙️ Factory Sizing & Ingot Parameters", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            target_gw = float(total_target_gw)
            st.metric(
                label="Total Array Target (GW)",
                value=f"{target_gw:,.1f} GW",
            )

        with col2:
            years = int(build_years)
            st.metric("Buildout Horizon", f"{years} Years")

        with col3:
            farms = st.number_input(
                "Colocated Farms / Factories",
                min_value=1,
                max_value=500,
                value=int(num_farms),
                step=5,
            )
        with col4:
            ingot_choice = st.selectbox(
                "CZ Ingot Diameter",
                options=[
                    "8-inch (~200 mm) — ~28.75 MW/puller/yr",
                    "12-inch (~300 mm) — ~40.0 MW/puller/yr",
                ],
                index=0 if ingot_diameter_in == 8 else 1,
            )

    # --- 2. Core Capacity & Scaling Math ---
    annual_national_gw = target_gw / years
    factory_annual_gw = annual_national_gw / farms
    farm_total_gw = target_gw / farms
    scale_factor = factory_annual_gw / 4.6  # Normalized to 4.6 GW/yr baseline

    is_8_inch = "8-inch" in ingot_choice
    mw_per_puller = 28.75 if is_8_inch else 40.0
    pullers_needed = int(round((factory_annual_gw * 1000.0) / mw_per_puller))

    # --- 3. Top-Level KPI Metrics ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(
        "Factory Annual Output",
        f"{factory_annual_gw:.2f} GW/yr",
        f"{farm_total_gw:.1f} GW per farm over {years} yrs",
    )
    m2.metric(
        "Parallel CZ Ingot Lines",
        f"{pullers_needed:,} pullers",
        "8-in baseline" if is_8_inch else "12-in high-throughput",
    )

    # --- 4. Ingot Workshop Breakdown ---
    # Per puller: ~7.6 m2 furnace body, ~64 m2 working bay, ~103 m2 w/ aisles & shaping
    furnace_body_m2 = pullers_needed * 7.6
    working_bay_m2 = pullers_needed * 64.0
    ingot_workshop_m2 = pullers_needed * 103.125  # ~16,500 m2 at 160 pullers

    # --- 5. Full Factory Zone Breakdown (Scaled to Factory Annual GW) ---
    zones = [
        {
            "Zone": "1. Rail Receiving & Raw Material Silos",
            "Key Processes": "Covered dual rail spur, polysilicon silos, solar glass, aluminum extrusions, EVA/backsheet, chemical tank farm",
            "Ceiling Height": "12–14 m",
            "Area_m2": 18400.0 * scale_factor,
        },
        {
            "Zone": "2. Ingot Growth & Squaring (High-Bay)",
            "Key Processes": f"{pullers_needed} CZ pullers, seed/tail cropping, cylindrical grinding, squaring saws",
            "Ceiling Height": "16–18 m (High-Bay)",
            "Area_m2": ingot_workshop_m2,
        },
        {
            "Zone": "3. Wafering & Cleaning",
            "Key Processes": "Diamond wire saws (DWS), degumming, automated optical inspection (AOI), ultrasonic cleaning",
            "Ceiling Height": "8–10 m",
            "Area_m2": 20700.0 * scale_factor,
        },
        {
            "Zone": "4. Solar Cell Fab (Cleanroom)",
            "Key Processes": "Texturing, diffusion/TOPCon/HJT deposition, laser doping, screen printing, firing, IV sorting",
            "Ceiling Height": "8–10 m (+sub-fab)",
            "Area_m2": 25300.0 * scale_factor,
        },
        {
            "Zone": "5. Module Assembly & Field Dispatch",
            "Key Processes": "Tabber-stringers, layup, vacuum laminators, framing, J-box potting, flash testing, direct-to-field loading",
            "Ceiling Height": "8–10 m",
            "Area_m2": 29900.0 * scale_factor,
        },
    ]

    df_zones = pd.DataFrame(zones)
    total_m2 = df_zones["Area_m2"].sum()
    total_sqft = total_m2 * 10.7639
    under_roof_acres = total_sqft / 43560.0
    total_parcel_acres = under_roof_acres * 2.65  # Includes rail spurs, utility yard & marshaling

    # Finish KPI metrics now that totals are computed
    m3.metric(
        "Building Under-Roof Area",
        f"{total_m2:,.0f} m²",
        f"{total_sqft:,.0f} sq ft ({under_roof_acres:.1f} acres)",
    )
    m4.metric(
        "Total Industrial Parcel",
        f"{total_parcel_acres:.0f} acres",
        f"~{140 * scale_factor:.0f} MW continuous plant load",
    )

    # Format display table
    df_display = pd.DataFrame(
        {
            "Factory Zone": df_zones["Zone"],
            "Key Processes": df_zones["Key Processes"],
            "Ceiling Height": df_zones["Ceiling Height"],
            "Area (m²)": df_zones["Area_m2"].map(lambda x: f"{x:,.0f}"),
            "Area (sq ft)": (df_zones["Area_m2"] * 10.7639).map(lambda x: f"{x:,.0f}"),
            "Share (%)": (df_zones["Area_m2"] / total_m2 * 100.0).map(lambda x: f"{x:.1f}%"),
        }
    )

    # Append Total Row
    total_row = pd.DataFrame(
        [
            {
                "Factory Zone": "TOTAL UNDER-ROOF FACILITY",
                "Key Processes": "Full Polysilicon-to-Panel Vertically Integrated Line",
                "Ceiling Height": "Step-down profile",
                "Area (m²)": f"{total_m2:,.0f}",
                "Area (sq ft)": f"{total_sqft:,.0f}",
                "Share (%)": "100.0%",
            }
        ]
    )
    df_display = pd.concat([df_display, total_row], ignore_index=True)

    st.subheader("📊 Building Footprint Breakdown (Per Factory)")
    st.dataframe(df_display, use_container_width=True, hide_index=True)

    # --- 6. Ingot Puller Detail Table ---
    st.subheader("🔬 CZ Ingot Puller Hall Breakdown")
    df_ingot = pd.DataFrame(
        [
            {
                "Space Level": "Furnace Body Only",
                "Dimensions / Allowance": "~2.3 m × 3.3 m (closed)",
                "Area per Line": "7.6 m² (~82 sq ft)",
                f"Total ({pullers_needed} Lines)": f"{furnace_body_m2:,.0f} m² ({furnace_body_m2 * 10.7639:,.0f} sq ft)",
            },
            {
                "Space Level": "Complete Puller Bay",
                "Dimensions / Allowance": "~8.0 m × 8.0 m (swing clearance, vacuum pumps, power cabinets, operator zone)",
                "Area per Line": "64.0 m² (~690 sq ft)",
                f"Total ({pullers_needed} Lines)": f"{working_bay_m2:,.0f} m² ({working_bay_m2 * 10.7639:,.0f} sq ft)",
            },
            {
                "Space Level": "Full Ingot Workshop",
                "Dimensions / Allowance": "Adds +60% for AGV/crane aisles, polysilicon prep & shared cropping/squaring saws",
                "Area per Line": "103.1 m² (~1,110 sq ft)",
                f"Total ({pullers_needed} Lines)": f"{ingot_workshop_m2:,.0f} m² ({ingot_workshop_m2 * 10.7639:,.0f} sq ft)",
            },
        ]
    )
    st.dataframe(df_ingot, use_container_width=True, hide_index=True)

    # --- 7. Engineering & Site Layout Notes ---
    st.subheader("🏗️ Linear Flow & Southwestern U.S. Site Strategy")
    c1, c2 = st.columns(2)

    with c1:
        st.markdown(
            f"""
            **1. Linear Flow-Through Geometry (~{int(620 * (scale_factor**0.5))} m × {int(180 * (scale_factor**0.5))} m)**
            * **West Edge — Dual Rail Spur (~{total_parcel_acres * 0.25:.1f} acres):** Parallel tracks allow continuous unloading of polysilicon chunks, quartz crucibles, and argon near the north CZ hall, while glass, aluminum frames, and encapsulants unload at the south module end.
            * **Step-Down Roof Profile:** High-bay **16–18 m (52–60 ft)** ceilings are restricted to the Ingot Hall (to accommodate ~14.6 m open puller height + bridge cranes), stepping down to **8–10 m** for Wafering, Cell, and Module zones to slash desert cooling loads.
            * **Cleanroom Isolation:** Wet diamond-wire sawing is isolated from the ISO Class 7/8 Cell Fab via positive-pressure airlocks.
            """
        )

    with c2:
        st.markdown(
            f"""
            **2. Direct-to-Field Dispatch & Utilities**
            * **East Edge — Field Marshaling Yard (~{total_parcel_acres * 0.25:.1f} acres):** Replaces semi-truck loading docks with drive-through doors feeding an outdoor staging yard where flatbeds haul modules straight into the surrounding **{farm_total_gw:.1f} GW** solar array.
            * **8-Inch vs. 12-Inch Trade-off:** Modern high-efficiency cells (M10 182 mm / G12 210 mm) require **250–300+ mm (10–12 in)** ingots. Switching from 8-inch to 12-inch pullers reduces your line count from **160** to **~115 pullers** per factory.
            * **Utilities & Water:** Requires **~{140 * scale_factor:.0f} MW** continuous power and a **Zero-Liquid-Discharge (ZLD)** ultrapure water recycling plant for Southwestern desert operation.
            """
        )
    
    # --- 8. Factory Capital Expenditure (CapEx) ---
    st.subheader("💰 Factory Capital Expenditure (CapEx)")
    single_factory_capex_usd = factory_annual_gw * 1_000_000.0 * capex_per_kw_yr
    total_factories_capex_usd = single_factory_capex_usd * farms
    amortized_capex_per_wdc = total_factories_capex_usd / (target_gw * 1_000_000_000.0)

    c_cap1, c_cap2, c_cap3 = st.columns(3)
    c_cap1.metric(
        "CapEx per Factory",
        f"${single_factory_capex_usd / 1e9:.2f}B",
        f"For {factory_annual_gw:.2f} GW/yr plant (@ ${capex_per_kw_yr:.0f}/kW-yr)",
    )
    c_cap2.metric(
        f"Total CapEx ({farms} Factories)",
        f"${total_factories_capex_usd / 1e9:.1f}B",
        "Upfront manufacturing buildout",
    )
    c_cap3.metric(
        "Amortized Factory Cost",
        f"${amortized_capex_per_wdc:.3f}/Wdc",
        f"${amortized_capex_per_wdc * 1000:.2f}/kWdc over {years} yrs",
    )

    # --- 9. Factory CO2 Emissions & Abatement Strategies ---
    st.subheader("🌍 Factory CO₂ Emissions & Carbon Abatement")
    st.markdown(
        "On-site factory emissions are **Scope 2 (electricity)** while raw polysilicon, glass, "
        "and aluminum carry **Scope 3 (upstream material)** embodied carbon. "
        "*(Adjust assumptions in the **🏭 Factory CapEx & Carbon Parameters** sidebar section.)*"
    )

    # Pull specific solar yield (kWh/kWp/yr) directly from physics_engine scale_res
    if "specific_yield_kwh_kwp" in scale_res:
        physics_yield_kwh_per_kwp = float(scale_res["specific_yield_kwh_kwp"])
    elif "annual_energy_kwh" in scale_res and float(scale_res["target_capacity_kwp"]) > 0:
        physics_yield_kwh_per_kwp = float(scale_res["annual_energy_kwh"]) / float(scale_res["target_capacity_kwp"])
    elif "annual_gen_twh" in scale_res and target_gw > 0:
        physics_yield_kwh_per_kwp = (float(scale_res["annual_gen_twh"]) * 1e9) / (target_gw * 1e6)
    else:
        physics_yield_kwh_per_kwp = 2100.0  # Fallback only if yield key isn't in scale_res

    # Factory electricity demand (kWh per kWp produced) & Scope 2 + 3 intensity
    kwh_per_kwp_produced = (factory_mw_per_46gw * 1000.0 * 8760.0) / (4.6 * 1_000_000.0)
    scope2_kg_per_kwp = kwh_per_kwp_produced * grid_kg_per_kwh
    total_kg_per_kwp = scope2_kg_per_kwp + scope3_kg_per_kwp

    # Annual and buildout totals (Metric Tons CO2)
    single_factory_annual_tons = (factory_annual_gw * 1_000_000.0 * total_kg_per_kwp) / 1000.0
    all_factories_annual_tons = single_factory_annual_tons * farms
    total_buildout_millions_tons = (all_factories_annual_tons * years) / 1_000_000.0

    # Carbon capture / removal costs
    total_capture_cost_usd = (all_factories_annual_tons * years) * capture_cost_per_ton
    capture_cost_per_wdc = total_capture_cost_usd / (target_gw * 1_000_000_000.0)

    # Carbon payback time using physics_engine yield & 0.38 kg CO2/kWh displaced grid mix
    avoided_kg_per_kwp_yr = physics_yield_kwh_per_kwp * 0.38
    carbon_payback_months = (
        (total_kg_per_kwp / avoided_kg_per_kwp_yr) * 12.0
        if avoided_kg_per_kwp_yr > 0
        else 0.0
    )

    m_co1, m_co2, m_co3, m_co4 = st.columns(4)
    m_co1.metric(
        "Embodied Carbon Intensity",
        f"{total_kg_per_kwp:,.0f} kg CO₂/kWp",
        f"Scope 2: {scope2_kg_per_kwp:.0f} | Scope 3: {scope3_kg_per_kwp:.0f} kg",
    )
    m_co2.metric(
        "Annual Emissions (All Factories)",
        f"{all_factories_annual_tons / 1e6:,.1f}M tons/yr",
        f"{single_factory_annual_tons / 1e3:,.0f}k tons/yr per factory",
    )
    m_co3.metric(
        f"{years}-Year Buildout Carbon Debt",
        f"{total_buildout_millions_tons:,.1f}M tons",
        f"Paid back in ~{carbon_payback_months:.1f} mos (@ {physics_yield_kwh_per_kwp:,.0f} kWh/kWp)",
    )
    m_co4.metric(
        "Carbon Capture / Offset Cost",
        f"${total_capture_cost_usd / 1e9:,.1f}B",
        f"+${capture_cost_per_wdc:.4f}/Wdc added module cost",
    )

    return {
        "single_factory_capex_usd": single_factory_capex_usd,
        "total_factories_capex_usd": total_factories_capex_usd,
        "amortized_capex_per_wdc": amortized_capex_per_wdc,
        "total_capture_cost_usd": total_capture_cost_usd,
        "capture_cost_per_wdc": capture_cost_per_wdc,
        "total_buildout_tons_co2": all_factories_annual_tons * years,
        "factory_annual_gw": factory_annual_gw,
        "total_plant_mw": factory_mw_per_46gw * scale_factor * farms,
    }

    
factory_fin = render_factory_layout(build_years=build_years)

solar_pv_cost_per_wdc = (
    module_bom_opex_per_wdc
    + factory_fin["amortized_capex_per_wdc"]
    + factory_fin["capture_cost_per_wdc"]
    + automated_bos_per_wdc
)

# Optional read-only summary metric showing the live bottom-up total
st.metric(
    "Total Installed Solar PV Cost ($/Wdc)",
    f"${solar_pv_cost_per_wdc:.3f}/Wdc",
    (
        f"Factory CapEx ${factory_fin['amortized_capex_per_wdc']:.3f} + "
        f"BOM/OpEx ${module_bom_opex_per_wdc:.2f} + "
        f"CO₂ ${factory_fin['capture_cost_per_wdc']:.3f} + "
        f"Auto-BOS ${automated_bos_per_wdc:.2f}"
    ),
)

# --- U.S. Commercial Utility Benchmark Comparison ---
st.subheader("📊 Capital Savings vs. Commercial U.S. Utility Benchmarks")

target_watts_dc = float(scale_res["target_capacity_kwp"]) * 1000.0
us_commercial_pv_benchmark_wdc = 1.20          # DOE/SEIA U.S. utility tracking PV (~$1.12-$1.32/Wdc)
us_commercial_pv_storage_benchmark_wdc = 1.76  # DOE U.S. utility PV + 4-hr storage (~$1.71-$1.81/Wdc)

# Your live model PV-only vs. combined PV+Storage $/Wdc
your_pv_wdc = float(pv_cost_per_w)
# Uses your total_capex_usd if defined, or adds battery CapEx if stored separately
your_combined_wdc = (
    total_capex_usd / target_watts_dc
    if "total_capex_usd" in locals()
    else your_pv_wdc
)

pv_capex_savings_trillions = ((us_commercial_pv_benchmark_wdc - your_pv_wdc) * target_watts_dc) / 1e12
combined_capex_savings_trillions = ((us_commercial_pv_storage_benchmark_wdc - your_combined_wdc) * target_watts_dc) / 1e12

b1, b2, b3 = st.columns(3)
b1.metric(
    "Your PV Cost vs. U.S. Utility ($1.20/Wdc)",
    f"${your_pv_wdc:.3f}/Wdc",
    f"-${us_commercial_pv_benchmark_wdc - your_pv_wdc:.3f}/Wdc ({((us_commercial_pv_benchmark_wdc - your_pv_wdc) / us_commercial_pv_benchmark_wdc) * 100:.0f}% cheaper)",
)
b2.metric(
    "PV-Only CapEx Saved vs. Commercial",
    f"${pv_capex_savings_trillions:,.2f} Trillion",
    f"Across {target_watts_dc / 1e9:,.0f} GWdc buildout",
)
b3.metric(
    "Combined PV + Storage vs. U.S. Utility ($1.76/Wdc)",
    f"${your_combined_wdc:.3f}/Wdc",
    f"Saves ${combined_capex_savings_trillions:,.2f}T total CapEx",
)



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
col1, col2 = st.columns(2)

with col1:
    st.image(
        str(ASSETS_DIR / "pergola.jpg"),
        caption="2.1 kW DualAxis Tracking Home Pergola With Integrated Battery Storage",
        use_container_width=True,
    )

with col2:
    st.image(
        str(ASSETS_DIR / "factory.jpg"),
        caption="National Solar Array Fully Automated Production and Assembly on Location",
        use_container_width=True,
    )
#st.image(
#    str(ASSETS_DIR / "factory2.jpg"),
#    caption="Colocated Vertically Integrated Solar Factory & Automated Field Deployment — Yuma, AZ",
#    use_container_width=True,
#)

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
        fig_phys.update_layout(height=400, barmode="group", **LEGEND_ABOVE)
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

