# -*- coding: utf-8 -*-
"""
National Solar Array Bond Initiative
Cleaned & Optimized: Nov 06, 2025
"""

import numpy as np
import numpy_financial as npf
import streamlit as st
import pandas as pd
import plotly.express as px
import importlib
import sys

# --- RELOAD MODULES (for live editing) ---
st.cache_data.clear()
if 'efficiency_upgrade' in sys.modules:
    importlib.reload(sys.modules['efficiency_upgrade'])
from efficiency_upgrade import calculate_efficiency_upgrade

from typing import Union


# --- IMPORT MODEL FUNCTIONS ---
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
        x=1
    ),
    hovermode='x unified'
)

# =============================================
# PAGE TITLE & DESCRIPTION
# =============================================
#st.share()
st.markdown("[Full README](https://github.com/fradog/national-solar-array/blob/main/README.md)")


st.set_page_config(page_title="National Solar Array: Net Zero Economics")
st.title("National Solar Array Finance Calculator")
st.write(
    "<span style='font-size:0.85rem; font-style:italic;'>"
    "This claculator allows the user to better understand that a massive solar + storage array can indeed and realistically \
    help drive the U.S. to Net Zero carbon dioxide emissions by ~2035–2037, "
    "with strong financial returns, energy independence, and no one left behind. Funded via bonds or budget, "
    "revenues at current electricity prices far exceed costs. This is the potential that massive deployment, \
    on a scale one order of magnitude greater than currently discussed, offers."
    "</span>",
    unsafe_allow_html=True
)

# =============================================
# DEFAULT INPUTS
# =============================================
default_inputs = {
    'project_lifespan': 30,
    'initial_capacity': 230_000_000,      # kWp
    'target_capacity': 5_498_000_000,     # kWp
    'capacity_factor': 0.2700,
    'revenue_per_kwh': 0.16,
    'avoided_fuel_per_kwh': 0.03,
    'efficiency_upgrade': 0.10,
    'capital_cost_per_kwp': 1_730,
    'om_rate': 0.01,
    'grid_maintenance_bn': 50, # $Billion 
    'discount_rate': 0.04,
    'degradation_rate': 0.007,
    'reinvestment_percentage': 0.5,
    'investment_return_rate': 0.03,
    'bond_interest_rate': 0.025,
    'bond_term': 10,
    'dividend_percentage': 0.5,
    'individual_investment': 10_000,
    'us_adult_population': 258_000_000,
    'participation_rate_low': 0.05,
    'participation_rate_mid': 0.10,
    'participation_rate_high': 0.15,
    'carbon_tax_rate': 100.00,
    'us_emissions_tons': 4700000000,
    'carbon_tax_effective_rate': 0.75,
    'displaceable_proportion': 1.0,
    'panel_rating': 700 / 2.57,
    'coverage_ratio': 0.4,
    'vehicle_ice_eff': 0.200,
    'vehicle_elec_eff': 0.800,
    'utility_ice_elec_eff': 0.370,
}


# =============================================
# EFFICIENCY SLIDERS
# =============================================
st.subheader("Fossil-to-Electric Efficiency Assumptions")
st.write(
    "<span style='font-size:0.85rem; font-style:italic;'>"
    "Electrifying energy use reduces total consumption due to efficiency gains. "
    "This model adjusts 2023 fossil energy (77.1 quads) downward accordingly."
    "</span>",
    unsafe_allow_html=True
)

col1, col2, col3 = st.columns(3)
with col1:
    vehicle_ice_eff = st.slider(
        "ICE Vehicle Efficiency", 0.10, 0.35,
        st.session_state.get('vehicle_ice_eff', default_inputs['vehicle_ice_eff']),
        0.005, format="%.3f"
    )
with col2:
    vehicle_elec_eff = st.slider(
        "EV Drivetrain Efficiency", 0.60, 0.95,
        st.session_state.get('vehicle_elec_eff', default_inputs['vehicle_elec_eff']),
        0.005, format="%.3f"
    )
with col3:
    utility_ice_elec_eff = st.slider(
        "Fossil Plant Efficiency", 0.30, 0.60,
        st.session_state.get('utility_ice_elec_eff', default_inputs['utility_ice_elec_eff']),
        0.005, format="%.3f"
    )

# Rebuild mix_inputs with live values
mix_inputs = {
    'total_energy_quads': 77.10,
    'petroleum_fraction': .459, 'gas_fraction': .436, 'coal_fraction': .105,
    'petroleum_trans_fraction': .696, 'petroleum_heating_fraction': .296, 'petroleum_elec_fraction': .008,
    'gas_trans_fraction': .040, 'gas_heating_fraction': .560, 'gas_elec_fraction': .400,
    'coal_trans_fraction': 0.0, 'coal_heating_fraction': .114, 'coal_elec_fraction': .886,
    'vehicle_ice_eff': vehicle_ice_eff,
    'vehicle_elec_eff': vehicle_elec_eff,
    'utility_ice_elec_eff': utility_ice_elec_eff,
    'petroleum_heating_eff': 1.0, 'gas_heating_eff': 1.0, 'coal_heating_eff': 1.0,
    'elec_heating_eff': 1.0, 'elec_elec_eff': 1.0,
}


# -------------------------------------------------
# Helper: read a value from session_state with a default
# -------------------------------------------------
def _ss(key, default):
    return st.session_state.get(key, default)

# Calculate efficiency upgrade
efficiency_upgrade_ratio = calculate_efficiency_upgrade(mix_inputs)
default_inputs['efficiency_upgrade'] = efficiency_upgrade_ratio
st.write(f"**Efficiency Upgrade Ratio**: {efficiency_upgrade_ratio:,.3f}")


# =============================================
# SIDEBAR INPUTS – GROUPED & CUSTOM LABELS
# =============================================
st.sidebar.header("Input Parameters")

# =============================================
# SIDEBAR INPUTS – RESTORE DEFAULTS BUTTON
# =============================================
if st.sidebar.button("Restore Defaults", type="primary", use_container_width=True):
    for key in default_inputs:
        st.session_state[key] = default_inputs[key]
    # reset the three main-body efficiency sliders
    st.session_state['vehicle_ice_eff']        = default_inputs['vehicle_ice_eff']
    st.session_state['vehicle_elec_eff']       = default_inputs['vehicle_elec_eff']
    st.session_state['utility_ice_elec_eff']  = default_inputs['utility_ice_elec_eff']
    # reset the GW helpers
    st.session_state['initial_capacity_gw'] = int(default_inputs['initial_capacity'] / 1_000_000)
    st.session_state['target_capacity_gw']  = int(default_inputs['target_capacity'] / 1_000_000)
    st.session_state['us_adpop_mil'] = int(default_inputs['us_adult_population'] / 1_000_000)
    st.session_state['bond_term'] = default_inputs['bond_term']
    
    st.success("All inputs restored to defaults!")
    st.rerun()          # <-- forces a clean rerun so everything redraws correctly

inputs = {}

# -------------------------------------------------
# 1. Helper: skip efficiency params (they live in main body)
# -------------------------------------------------
SKIP_EFFICIENCY = {
    'vehicle_ice_eff',
    'vehicle_elec_eff',
    'utility_ice_elec_eff'
}

# -------------------------------------------------
# 2. Custom label + slider logic
# -------------------------------------------------
def _make_slider(container, param: str, default: Union[float, int], unit: str = "", **kwargs):
    pretty = param.replace('_', ' ').title()
    label = f"{pretty} {unit}".strip()
    return container.slider(
        label,
        value=st.session_state.get(param, default),
        **kwargs
    )

# -------------------------------------------------
# 3. System Scale (mixed – keep as-is)
# -------------------------------------------------
with st.sidebar.expander("System Scale", expanded=True):
    # text boxes for lifespan & efficiency (you wanted them here)
    inputs['project_lifespan'] = st.text_input(
        "Project Lifespan (Yrs)", value=st.session_state.get('project_lifespan', str(default_inputs['project_lifespan']))
    )
    inputs['efficiency_upgrade'] = st.text_input(
        "Efficiency Upgrade Ratio", value=st.session_state.get('efficiency_upgrade', f"{efficiency_upgrade_ratio:,.3f}")
    )
    
    
    # ----- Initial Capacity (GWp) -----
    gw_default = int(default_inputs['initial_capacity'] / 1_000_000)      # 230 → 230 GW
    gw_value   = _ss('initial_capacity_gw', gw_default)   # keep the GW value in session_state

    inputs['initial_capacity'] = st.slider(
        "Initial Capacity (GWp)", 0, 1000,
        value=gw_value,      # <-- the value the slider shows (in GW)
        step=10
        ) * 1_000_000            # <-- convert back to kWp for the model
   
    # ----- Target Capacity (GWp) -----
    gw_target_default = int(default_inputs['target_capacity'] / 1_000_000)   # 5498 → 5498 GW
    gw_target_value   = _ss('target_capacity_gw', gw_target_default)

    inputs['target_capacity'] = st.slider(
        "Target Capacity (GWp)", 3000, 7000, 
        value=gw_target_value,
        step=2
        ) * 1_000_000
    
    inputs['capacity_factor'] = _make_slider(
        st, 'capacity_factor', default_inputs['capacity_factor'],
        unit="", min_value=0.15, max_value=0.31, step=0.0001, format="%.4f"
    )
    inputs['panel_rating'] = _make_slider(
        st, 'panel_rating', default_inputs['panel_rating'],
        unit="W/m²", min_value=200.0, max_value=350.0, step=0.1, format="%.1f"
    )
    inputs['coverage_ratio'] = _make_slider(
        st, 'coverage_ratio', default_inputs['coverage_ratio'],
        unit="", min_value=0.0, max_value=1.0, step=0.05, format="%.2f"
    )
    inputs['degradation_rate'] = _make_slider(
        st, 'degradation_rate', default_inputs['degradation_rate'],
        unit="/yr", min_value=0.0, max_value=0.015, step=0.001, format="%.3f"
    )

# -------------------------------------------------
# 4. Costs
# -------------------------------------------------
with st.sidebar.expander("Costs", expanded=False):
    inputs['capital_cost_per_kwp'] = _make_slider(
        st, 'capital_cost_per_kwp', default_inputs['capital_cost_per_kwp'],
        unit="$/kWp", min_value=500, max_value=3_000, step=10,
        format="$%.0f"
    )
    inputs['om_rate'] = _make_slider(
        st, 'om_rate', default_inputs['om_rate'],
        unit="(fraction/yr)", min_value=0.0, max_value=0.05, step=0.001,
        format="%.3f"
    )
    inputs['grid_maintenance_bn'] = _make_slider(
        st, 'grid_maintenance_bn', default_inputs['grid_maintenance_bn'],
        unit="$/yr", min_value=0, max_value=200,
        step=5, format="$%.0f"
    )

# -------------------------------------------------
# 5. Revenue & Savings
# -------------------------------------------------
with st.sidebar.expander("Revenue & Savings", expanded=False):
    inputs['revenue_per_kwh'] = _make_slider(
        st, 'revenue_per_kwh', default_inputs['revenue_per_kwh'],
        unit="$/kWh", min_value=0.00, max_value=0.30, step=0.001,
        format="$%.3f"
    )
    inputs['avoided_fuel_per_kwh'] = _make_slider(
        st, 'avoided_fuel_per_kwh', default_inputs['avoided_fuel_per_kwh'],
        unit="$/kWh", min_value=0.0, max_value=0.10, step=0.001,
        format="$%.3f"
    )
    inputs['carbon_tax_rate'] = _make_slider(
        st, 'carbon_tax_rate', default_inputs['carbon_tax_rate'],
        unit="$/ton", min_value=0.0, max_value=200.0, step=5.0,
        format="$%.0f"
    )
    inputs['carbon_tax_effective_rate'] = _make_slider(
        st, 'carbon_tax_effective_rate', default_inputs['carbon_tax_effective_rate'],
        unit="", min_value=0.5, max_value=1.0, step=0.05,
        format="%.2f"
    )
    inputs['displaceable_proportion'] = _make_slider(
        st, 'displaceable_proportion', default_inputs['displaceable_proportion'],
        unit="", min_value=0.0, max_value=1.0, step=0.05,
        format="%.2f"
    )
    # emissions – keep as text box (large number)
    inputs['us_emissions_tons'] = st.text_input(
        "Annual U.S. CO₂e Emissions (tons)",
        value=st.session_state.get('us_emissions_tons',f"{default_inputs['us_emissions_tons']:,}")
    )

# -------------------------------------------------
# 6. Reinvestment
# -------------------------------------------------
with st.sidebar.expander("Reinvestment", expanded=False):
    inputs['reinvestment_percentage'] = _make_slider(
        st, 'reinvestment_percentage', default_inputs['reinvestment_percentage'],
        unit="(fraction)", min_value=0.0, max_value=1.0, step=0.05,
        format="%.2f"
    )
    inputs['investment_return_rate'] = _make_slider(
        st, 'investment_return_rate', default_inputs['investment_return_rate'],
        unit="", min_value=0.0, max_value=0.20, step=0.005,
        format="%.3f"
    )
    inputs['discount_rate'] = _make_slider(
        st, 'discount_rate', default_inputs['discount_rate'],
        unit="", min_value=0.0, max_value=0.20, step=0.005,
        format="%.3f"
    )

# -------------------------------------------------
# 7. Bond Financing
# -------------------------------------------------
with st.sidebar.expander("Bond Financing", expanded=False):
    

    # ----- US Adult Popualation -----
    us_adpop_default = int(default_inputs['us_adult_population'] / 1_000_000)   # us adult pop in millions
    us_adpop_value = _ss('us_adpop_mil', us_adpop_default)

    inputs['us_adult_population'] = st.slider(
        "US Adult Population (M)", 200, 350, 
        value=us_adpop_value,
        step=2
        ) * 1_000_000
    
    
    inputs['bond_interest_rate'] = _make_slider(
        st, 'bond_interest_rate', default_inputs['bond_interest_rate'],
        unit="", min_value=0.0, max_value=0.10, step=0.001,
        format="%.3f"
    )
    inputs['bond_term'] = st.number_input(
    "Bond Term (years)",
    min_value=1, max_value=30,
    value=_ss('bond_term', default_inputs['bond_term']),
    step=1
)
    inputs['dividend_percentage'] = _make_slider(
        st, 'dividend_percentage', default_inputs['dividend_percentage'],
        unit="(fraction)", min_value=0.0, max_value=1.0, step=0.05,
        format="%.2f"
    )
    inputs['individual_investment'] = _make_slider(
        st, 'individual_investment', default_inputs['individual_investment'],
        unit="$", min_value=0, max_value=100_000, step=100,
        format="$%.0f"
    )
    inputs['participation_rate_low'] = _make_slider(
        st, 'participation_rate_low',
        default_inputs['participation_rate_low'],
        unit="",
        min_value=0.0, max_value=1.00, step=0.05,
        format="%.2f"
    )
    inputs['participation_rate_mid'] = _make_slider(
        st, 'participation_rate_mid',
        default_inputs['participation_rate_mid'],
        unit="",
        min_value=0.0, max_value=1.00, step=0.05,
        format="%.2f"
    )
    inputs['participation_rate_high'] = _make_slider(
        st, 'participation_rate_high',
        default_inputs['participation_rate_high'],
        unit="",
        min_value=0.0, max_value=1.00, step=0.05,
        format="%.2f"
    )

# ===============================================================
# SAVE TO SESSION_STATE – MUST BE BEFORE TYPE CONVERSION
# ===============================================================

# 1. Save ALL normal inputs (sliders that use the real value directly)
for key, value in inputs.items():
    if key not in {'initial_capacity', 'target_capacity', 'us_adult_population', 'bond_term'}:
        st.session_state[key] = value

# 2. Save the big scaled ones via their display units
st.session_state['initial_capacity_gw']   = inputs['initial_capacity']   // 1_000_000
st.session_state['target_capacity_gw']    = inputs['target_capacity']    // 1_000_000
st.session_state['us_adpop_mil']          = inputs['us_adult_population'] // 1_000_000
st.session_state['bond_term']             = inputs['bond_term']

# 3. Save the three main-body efficiency sliders
st.session_state['vehicle_ice_eff']       = vehicle_ice_eff
st.session_state['vehicle_elec_eff']      = vehicle_elec_eff
st.session_state['utility_ice_elec_eff']  = utility_ice_elec_eff

# -------------------------------------------------
# 6. TYPE CONVERSION – everything must be int/float
# -------------------------------------------------
def _to_num(val, is_int=False):
    """Convert text → int/float, fall back to default on error."""
    try:
        if is_int:
            return int(float(val.replace(',', '')))
        return float(val.replace(',', ''))
    except Exception:
        return default_inputs.get(val, val)   # fallback

# ---- integers (ONLY the ones that come from text/number inputs) ----
int_keys = ['project_lifespan', 'bond_term', 'individual_investment']
for k in int_keys:
    if k in inputs:
        try:
            inputs[k] = int(float(str(inputs[k]).replace(',', '')))
        except:
            inputs[k] = default_inputs[k]

# The big scaled inputs (initial_capacity, target_capacity, us_adult_population)
# are already perfect integers from the slider * 1_000_000 — DO NOT TOUCH THEM

# ---- integers (skip the big scaled ones — they are already correct integers) ----
# int_keys = ['project_lifespan', 'bond_term', 'individual_investment']
# for k in int_keys:
#     if k in inputs:
#         try:
#             inputs[k] = int(float(str(inputs[k]).replace(',', '')))
#         except:
#             inputs[k] = default_inputs[k]

# ---- floats --------------------------------------------------
for k in default_inputs:
    if k not in inputs or k in SKIP_EFFICIENCY:
        continue
    inputs[k] = _to_num(inputs[k], is_int=False)

# =============================================
# LCOE VALIDATION MODE (ONE TOGGLE)
# =============================================
validate_lcoe = st.sidebar.checkbox("LCOE Validation Mode (Zero extras + Unlevered NPV)")

if validate_lcoe:
    for key in ['avoided_fuel_per_kwh', 'carbon_tax_rate', 'grid_maintenance', 'degradation_rate']:
        inputs[key] = 0.0
    inputs['bond_interest_rate'] = 0.0
    inputs['bond_term'] = 0

# =============================================
# CALCULATIONS
# =============================================
annual_energy_goal, required_area = target_total_energy(inputs)
bond_principal, carbon_tax_10yr = calculate_bond_principal(inputs)
cash_flows_df = calculate_cash_flows(inputs, bond_principal, project_lifespan=inputs['project_lifespan'])
cash_flows_df['Cumulative Post-Debt Cash Flow ($B)'] = cash_flows_df['Cash Flow Post-Debt ($B)'].cumsum()

funding_mix_df = calculate_funding_mix(inputs, bond_principal)
metrics = calculate_metrics(inputs, cash_flows_df, bond_principal)

# Target energy with efficiency
target_energy_quads = efficiency_upgrade_ratio * mix_inputs['total_energy_quads']       #77.10
target_energy_twh = target_energy_quads * 293.07
final_energy_twh = cash_flows_df.loc[cash_flows_df['Year'] == 30, 'Energy Yield (TWh)'].iloc[0] 
energy_gap = final_energy_twh - target_energy_twh 

st.header("System Size")
st.write(f"<span style='font-size:0.85rem; font-style:italic;'>"
         f"The size of the solar system represented here is that which is required to replace fossil fueled energy in 2023, {mix_inputs['total_energy_quads']:.2f} quads ({mix_inputs['total_energy_quads'] * 293.07:,.0f} TWh). \
         The existing other renewables and nuclear as of 2023 remain as is over the lifetime of the system. If these are upgraded or added \
         to, those additions would reduce the size of the array assuming total U.S consumption remains level over the life of the system.\
         In theory they could be left as is, but next gen nuclear offers local energy density for extreme local demands like those of future AI training datacenters."
         f"</span>",
         unsafe_allow_html=True)
st.write(f"**Target Annual Energy**: {target_energy_twh:,.0f} TWh")
st.write(f"**System Annual Energy**: {final_energy_twh:,.0f} TWh")
st.write(f"**Area Required**: {required_area:,.0f} sq mi (coverage ratio: {inputs['coverage_ratio']:.2f})")
st.metric(
    "Energy Gap (Target vs. Array Energy Output at Full Capacity (incl. degradation))",
    f"{energy_gap:,.2f} TWh",
    delta=f"{(energy_gap / target_energy_twh)*100:+.1f}%"
)

# LCOE
lcoe_full = calculate_lcoe_simple(inputs)
nrel_lcoe = calculate_lcoe_nrel_style(
    capex_per_kw=inputs['capital_cost_per_kwp'],
    fom_per_kw_yr=inputs['capital_cost_per_kwp'] * inputs['om_rate'],
    cf=inputs['capacity_factor'],
    wacc_real=inputs['discount_rate'],
    project_life=inputs['project_lifespan']
)
diag = calculate_lcoe_diagnostic(inputs)

# =============================================
# UNLEVERED NPV (EXACT MATCH WITH LCOE)
# =============================================
lifespan = inputs['project_lifespan']
target_kw = inputs['target_capacity']
init_kw = inputs['initial_capacity']
capex_per_kw = inputs['capital_cost_per_kwp']
om_rate = inputs['om_rate']
cf = inputs['capacity_factor']
hours = cf * 8760

# Build-out
annual_add_kw = (target_kw - init_kw) / 10
capex_series = np.array([annual_add_kw * capex_per_kw if yr < 10 else 0 for yr in range(lifespan)])

# O&M
om_series = np.zeros(lifespan)
cum_kw = init_kw
for yr in range(lifespan):
    if yr < 10:
        cum_kw += annual_add_kw
    om_series[yr] = cum_kw * capex_per_kw * om_rate

# Energy
energy_series = np.array([
    min(init_kw + annual_add_kw * min(yr + 1, 10), target_kw) * hours
    for yr in range(lifespan)
])

# Revenue
revenue_series = energy_series * inputs['revenue_per_kwh']

# Unlevered cash flow
unlevered_cf = revenue_series - capex_series - om_series
unlevered_npv = npf.npv(inputs['discount_rate'], unlevered_cf) / 1e12

# =============================================
# DISPLAY: LCOE + VALIDATION
# =============================================
st.markdown("---")
st.subheader("Levelized Cost of Energy (LCOE)")

col1, col2 = st.columns(2)
with col1:
    st.metric("**Your Model (PV (+ Battery Storage) + Degradation)**", f"${lcoe_full['LCOE ($/MWh)']:.2f}/MWh")
    st.caption(f"→ {lcoe_full['LCOE ($/MWh)']/1000:.6f} $/kWh")
with col2:
    delta = nrel_lcoe - lcoe_full['LCOE ($/MWh)'] 
    st.metric("**NREL ATB Style (PV (+ Battery Storage) FCR, no Degradation.)**", f"${nrel_lcoe:.2f}/MWh", f"{delta:+.2f} $/MWh", delta_color="inverse")

# Validation result
if validate_lcoe:
    inputs['revenue_per_kwh'] = lcoe_full['LCOE ($/MWh)'] / 1000
    st.success(f"Validation Mode ON: Revenue = LCOE → **Unlevered NPV = ${unlevered_npv:+.3f}T**")
else:
    st.metric("Unlevered Solar NPV", f"${unlevered_npv:+.2f}T")

# =============================================
# DIAGNOSTIC TABLE
# =============================================
# st.markdown("#### Diagnostic Breakdown")
# diag_df = pd.DataFrame([
#     {"Metric": "Total CAPEX", "Value": f"${lcoe_full['Total CAPEX ($)']/1e9:,.2f} B"},
#     {"Metric": "PV of Total Costs", "Value": f"${lcoe_full['PV Costs ($)']/1e9:,.2f} B"},
#     {"Metric": "PV of Total Energy", "Value": f"{lcoe_full['PV Energy (TWh)']:.2f} TWh"},
#     {"Metric": "Final Eff Capacity", "Value": f"{diag['Final Eff Capacity (TW)']:.2f} TW"},
#     {"Metric": "Year 1 Energy", "Value": f"{diag['Year 1 Energy (TWh)']:.2f} TWh"},
#     {"Metric": "Year 30 Energy", "Value": f"{diag['Year 30 Energy (TWh)']:.2f} TWh"},
# ])
# st.dataframe(diag_df, use_container_width=True, hide_index=True)

# =============================================
# RESULTS
# =============================================

st.header("Bond Principal")
st.write(f"**Bond Principal**: ${bond_principal/1e9:.2f}B")
st.write(f"**Carbon Tax Revenue (10yr)**: ${carbon_tax_10yr/1e9:.2f}B")
st.write("<span style='font-size:0.85rem; font-style:italic;'>"
         "Note: Carbon tax revenue applied as cash flow to reduce bond principal."
         "</span>",
    unsafe_allow_html=True)
st.write("<span style='font-size:0.85rem; font-style:italic;'>"
         "The Bond Principal is essentially how much we would need to build the array, its associated storage, grid upgrades and grid maintenance.\
         It is roughly on the order of one year's defense budget. Investors in this bond will see compound annual growth rates \
         competitive with other much higher risk investments. \
         Try moving the Reinvestment Percentage slider toward zero and push the Dividend Percentage slider toward one and watch the \
         investor's balance syrocket. This simulation divides the net cash-flow-in into a mix of an amount paid out to investors as dividends \
         and an amount paid out for other purposes. Those could be to pay unforeseen bills, for reinvestment, or any other creative\
         purpose in the interest of the nation."
         "</span>",
    unsafe_allow_html=True)

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
st.write(f'<div style="overflow-x:auto;">{styled.to_html()}</div>', unsafe_allow_html=True)

st.header("Annual Capacity and Cash Flows")
st.dataframe(cash_flows_df.round(2), hide_index=True)

st.header("Funding Mix")
st.subheader("Funding Mix & Household Investment")
household_invest = bond_principal / 132_000_000
st.metric(
    "Investment per U.S. Household to Fully Fund Bond",
    f"${household_invest:,.0f}",
    help="Assumes 132 million U.S. households (Census 2023)"
)
st.subheader(f"Funding Mix Based on U.S. Adult Investor Participation Rates at ${inputs['individual_investment']:,.0f} per Investor")
st.dataframe(
    funding_mix_df.round(2),
    hide_index=True
)

# =============================================
# PLOTS
# =============================================
st.header("Financial Metrics Over Time")
fig1 = px.line(
    cash_flows_df,
    x='Year',
    y=['Cash Flow Pre-Debt ($B)', 'Cash Flow Post-Debt ($B)', 'Total Costs ($B)', 'Total Inflows ($B)'],
    title="Cash Flows"
)
fig1.update_layout(**LEGEND_ABOVE)
st.plotly_chart(fig1, use_container_width=True)

st.header("Balances & Cumulative Cash Flow")
fig2 = px.line(
    cash_flows_df,
    x='Year',
    y=['Reinvested Balance ($B)', 'Outstanding Principal ($B)', 'Cumulative Post-Debt Cash Flow ($B)'],
    title="National Solar Array: Balances & Cumulative Cash Flow"
)
fig2.for_each_trace(lambda t: t.update(line=dict(width=3)) if 'Cumulative' in t.name else None)
fig2.update_layout(**LEGEND_ABOVE)
st.plotly_chart(fig2, use_container_width=True)

st.header("CO2 Emissions Reduction")
emissions_data = [
    {'Year': t+1, 'Total Emissions (B tons)': (
        inputs['us_emissions_tons'] * inputs['displaceable_proportion'] * (1 - t/10) +
        inputs['us_emissions_tons'] * (1 - inputs['displaceable_proportion'])
    ) / 1e9} for t in range(10)
]
fig3 = px.line(pd.DataFrame(emissions_data), x='Year', y='Total Emissions (B tons)', title='Emissions Reduction')
fig3.update_layout(**LEGEND_ABOVE)
st.plotly_chart(fig3, use_container_width=True)














































































































































































