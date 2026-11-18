# -*- coding: utf-8 -*-
"""
Updated: Nov 05, 2025
@author: dhfra + Grok
"""

import numpy as np
import numpy_financial as npf
import pandas as pd


# ----------------------------------------------------------------------
# 1. ORIGINAL FUNCTIONS (unchanged except for clarity)
# ----------------------------------------------------------------------
def target_total_energy(inputs):
    capacity_factor = inputs['capacity_factor']
    target_capacity = inputs['target_capacity']
    panel_rating = inputs['panel_rating']
    coverage_ratio = inputs['coverage_ratio']
    
    annual_energy_goal = capacity_factor * 8760 * target_capacity / 10**9  # TWh
    area_required = target_capacity / (panel_rating / 1000) / coverage_ratio / 2.59e6  # sq.mi.

    return annual_energy_goal, area_required


def calculate_bond_principal(inputs, buildout_years=10):
    initial_capacity = inputs['initial_capacity']  # kWp
    target_capacity = inputs['target_capacity']  # kWp
    hours_per_year = inputs['capacity_factor'] * 8760
    capital_cost_per_kwp = inputs['capital_cost_per_kwp']
    om_rate = inputs['om_rate']
    grid_maintenance = inputs['grid_maintenance_bn'] * 10**9
    revenue_per_kwh = inputs['revenue_per_kwh']
    avoided_fuel_per_kwh = inputs['avoided_fuel_per_kwh']
    degradation_rate = inputs['degradation_rate']
    us_emissions_tons = inputs['us_emissions_tons']
    carbon_tax_rate = inputs['carbon_tax_rate']
    carbon_tax_effective_rate = inputs['carbon_tax_effective_rate']
    displaceable_proportion = inputs['displaceable_proportion']
    efficiency_upgrade = inputs['efficiency_upgrade']
    
    if displaceable_proportion < 0 or displaceable_proportion > 1:
        raise ValueError("Displaceable proportion must be between 0 and 1")
    
    annual_addition = (target_capacity - initial_capacity) / buildout_years
    shortfall_sum = 0
    cumulative_capacity = initial_capacity
    effective_capacity = initial_capacity
    displaceable_emissions = us_emissions_tons * displaceable_proportion
    non_displaceable_emissions = us_emissions_tons * (1 - displaceable_proportion)
    carbon_tax_10yr = 0
    
    for t in range(buildout_years):
        planned_capacity = min(initial_capacity + annual_addition * t, target_capacity)
        target_energy_kwh = planned_capacity * hours_per_year
        effective_capacity *= (1 - degradation_rate)
        energy_kwh = effective_capacity * hours_per_year
        energy_shortfall = target_energy_kwh - energy_kwh
        additional_capacity = energy_shortfall / hours_per_year if energy_shortfall > 0 else 0
        total_new_capacity = annual_addition + additional_capacity
        cumulative_capacity += total_new_capacity
        effective_capacity += total_new_capacity
        capital_cost = total_new_capacity * capital_cost_per_kwp
        om_cost = cumulative_capacity * capital_cost_per_kwp * om_rate
        total_costs = capital_cost + om_cost + grid_maintenance
        revenue = energy_kwh * revenue_per_kwh
        avoided_fuel = energy_kwh / efficiency_upgrade * avoided_fuel_per_kwh
        remaining_emissions = displaceable_emissions * (1 - t / buildout_years) + non_displaceable_emissions
        annual_carbon_tax = carbon_tax_rate * remaining_emissions * carbon_tax_effective_rate
        carbon_tax_10yr += annual_carbon_tax
        total_inflows = revenue + avoided_fuel + annual_carbon_tax
        net_cash_flow = total_inflows - total_costs
        if net_cash_flow < 0:
            shortfall_sum += -net_cash_flow
    
    return shortfall_sum, carbon_tax_10yr


def calculate_cash_flows(inputs, bond_principal, project_lifespan=30):
    initial_capacity = inputs['initial_capacity']  # kWp
    target_capacity = inputs['target_capacity']  # kWp
    hours_per_year = inputs['capacity_factor'] * 8760
    revenue_per_kwh = inputs['revenue_per_kwh']
    avoided_fuel_per_kwh = inputs['avoided_fuel_per_kwh']
    capital_cost_per_kwp = inputs['capital_cost_per_kwp']
    om_rate = inputs['om_rate']
    grid_maintenance = inputs['grid_maintenance_bn'] * 10**9
    degradation_rate = inputs['degradation_rate']
    reinvestment_percentage = inputs['reinvestment_percentage']
    investment_return_rate = inputs['investment_return_rate']
    bond_interest_rate = inputs['bond_interest_rate']
    dividend_percentage = inputs['dividend_percentage']
    bond_term = inputs['bond_term']
    individual_investment = inputs['individual_investment']
    efficiency_upgrade = inputs['efficiency_upgrade']
    
    annual_addition = (target_capacity - initial_capacity) / 10
    annual_debt_service = -npf.pmt(bond_interest_rate, bond_term, bond_principal) if bond_term > 0 else 0
    annual_debt_service_list = [annual_debt_service if t < bond_term else 0 for t in range(project_lifespan)]
    
    data = {
        'Year': list(range(1, project_lifespan + 1)),
        'New Capacity (GWp)': [],
        'Cumulative Capacity (GWp)': [],
        'Energy Yield (TWh)': [],
        'Cash Flow Pre-Debt ($B)': [],
        'Total Costs ($B)': [],
        'Total Inflows ($B)': [],
        'Interest Payment ($B)': [],
        'Principal Payment ($B)': [],
        'Cash Flow Post-Debt ($B)': [],
        'Outstanding Principal ($B)': [],
        'Reinvested Balance ($B)': [],
        'Dividends ($B)': [],
        'Amount Paid Out ($B)': [],
        'Investor Interest ($)': [],
        'Investor Principal ($)': [],
        'Investor Dividends ($)': [],
        'Investor Total Cash Flow ($)': []
    }
    
    cumulative_capacity = initial_capacity
    effective_capacity = initial_capacity
    reinvested_balance = 0
    current_principal = bond_principal
    investor_share = individual_investment / bond_principal if bond_principal > 0 else 0
    
    for t in range(project_lifespan):
        planned_capacity = min(initial_capacity + annual_addition * t, target_capacity)
        target_energy_kwh = planned_capacity * hours_per_year
        effective_capacity *= (1 - degradation_rate)
        energy_kwh = effective_capacity * hours_per_year
        energy_shortfall = target_energy_kwh - energy_kwh
        additional_capacity = energy_shortfall / hours_per_year if energy_shortfall > 0 else 0
        planned_new_capacity = annual_addition if t < 10 else 0
        total_new_capacity = planned_new_capacity + additional_capacity
        cumulative_capacity += total_new_capacity
        effective_capacity += total_new_capacity
        revenue = energy_kwh * revenue_per_kwh
        avoided_fuel = energy_kwh / efficiency_upgrade * avoided_fuel_per_kwh
        total_annual_inflows = revenue + avoided_fuel
        capital_cost = total_new_capacity * capital_cost_per_kwp
        om_cost = cumulative_capacity * capital_cost_per_kwp * om_rate
        total_annual_costs = capital_cost + om_cost + grid_maintenance
        net_cash_flow_pre_debt = total_annual_inflows - total_annual_costs
        
        debt_service = annual_debt_service_list[t]
        interest_payment = current_principal * bond_interest_rate if t < bond_term else 0
        principal_payment = debt_service - interest_payment if t < bond_term else 0
        net_cash_flow_post_debt = net_cash_flow_pre_debt - debt_service
        current_principal = max(0, current_principal - principal_payment)
        
        reinvested_amount = max(net_cash_flow_post_debt, 0) * reinvestment_percentage
        original_paid_out = net_cash_flow_post_debt * (1 - reinvestment_percentage) if net_cash_flow_post_debt > 0 else net_cash_flow_post_debt
        dividend_amount = original_paid_out * dividend_percentage if original_paid_out > 0 else 0
        amount_paid_out_val = original_paid_out * (1 - dividend_percentage) if original_paid_out > 0 else original_paid_out
        reinvested_balance = reinvested_balance * (1 + investment_return_rate) + reinvested_amount
        
        investor_interest = interest_payment * investor_share
        investor_principal = principal_payment * investor_share
        investor_dividend = dividend_amount * investor_share
        investor_cash_flow = investor_interest + investor_principal + investor_dividend
        
        data['New Capacity (GWp)'].append(total_new_capacity / 10**6)
        data['Cumulative Capacity (GWp)'].append(cumulative_capacity / 10**6)
        data['Energy Yield (TWh)'].append(energy_kwh / 10**9)
        data['Cash Flow Pre-Debt ($B)'].append(net_cash_flow_pre_debt / 10**9)
        data['Total Costs ($B)'].append(total_annual_costs / 10**9)
        data['Total Inflows ($B)'].append(total_annual_inflows / 10**9)
        data['Interest Payment ($B)'].append(interest_payment / 10**9)
        data['Principal Payment ($B)'].append(principal_payment / 10**9)
        data['Cash Flow Post-Debt ($B)'].append(net_cash_flow_post_debt / 10**9)
        data['Outstanding Principal ($B)'].append(current_principal / 10**9)
        data['Reinvested Balance ($B)'].append(reinvested_balance / 10**9)
        data['Dividends ($B)'].append(dividend_amount / 10**9)
        data['Amount Paid Out ($B)'].append(amount_paid_out_val / 10**9)
        data['Investor Interest ($)'].append(investor_interest)
        data['Investor Principal ($)'].append(investor_principal)
        data['Investor Dividends ($)'].append(investor_dividend)
        data['Investor Total Cash Flow ($)'].append(investor_cash_flow)
    
    return pd.DataFrame(data)


# ----------------------------------------------------------------------
# 2. LCOE: CORRECTED & DIAGNOSTIC VERSION
# ----------------------------------------------------------------------
def calculate_lcoe_simple(inputs: dict, project_lifespan: int = 30) -> dict:
    """
    LCOE in $/MWh. Units: kW, kWh, $.
    NO extra CAPEX to offset degradation.
    """
    discount_rate      = inputs['discount_rate']
    capex_per_kw       = inputs['capital_cost_per_kwp']
    om_rate            = inputs['om_rate']
    grid_maintenance   = inputs['grid_maintenance_bn'] * 10**9
    cf                 = inputs['capacity_factor']
    deg_rate           = inputs['degradation_rate']
    init_kw            = inputs['initial_capacity']
    target_kw          = inputs['target_capacity']
    buildout_years     = 10

    annual_add_kw = (target_kw - init_kw) / buildout_years
    hours_per_year = cf * 8760

    # In calculate_lcoe_simple — replace the CAPEX part
    capex_usd = np.zeros(project_lifespan)

    for yr in range(project_lifespan):
        if yr < 10:
            new_kw_this_year = annual_add_kw
        else:
            new_kw_this_year = 0.0
        capex_usd[yr] = new_kw_this_year * capex_per_kw
        
    om_usd      = np.zeros(project_lifespan)
    grid_usd    = np.zeros(project_lifespan)
    energy_kwh  = np.zeros(project_lifespan)

    cum_kw = init_kw
    eff_kw = init_kw

    for yr in range(project_lifespan):
        new_kw = annual_add_kw if yr < buildout_years else 0.0
        eff_kw *= (1 - deg_rate)
        eff_kw += new_kw
        cum_kw += new_kw

        capex_usd[yr] = new_kw * capex_per_kw
        om_usd[yr]    = cum_kw * capex_per_kw * om_rate
        grid_usd[yr]  = grid_maintenance
        energy_kwh[yr] = eff_kw * hours_per_year

    total_cost_usd = capex_usd + om_usd + grid_usd
    dfac = 1.0 / (1.0 + discount_rate) ** np.arange(1, project_lifespan + 1)

    pv_cost_usd   = np.sum(total_cost_usd * dfac)
    pv_energy_kwh = np.sum(energy_kwh * dfac)
    lcoe_per_kwh  = pv_cost_usd / pv_energy_kwh

    return {
        "LCOE ($/MWh)": round(lcoe_per_kwh * 1000, 2),
        "PV Costs ($)": pv_cost_usd,
        "PV Energy (TWh)": pv_energy_kwh / 1e12,
        "Total CAPEX ($)": np.sum(capex_usd),
        "Total O&M + Grid ($)": np.sum(om_usd) + np.sum(grid_usd),
    }


# ----------------------------------------------------------------------
# 3. NREL ATB-STYLE FCR LCOE (for comparison)
# ----------------------------------------------------------------------
def calculate_lcoe_nrel_style(
    capex_per_kw: float,
    fom_per_kw_yr: float,
    cf: float,
    wacc_real: float = 0.048,
    project_life: int = 30,
    vom_per_mwh: float = 0.0,
    fuel_per_mwh: float = 0.0,
    profinfactor: float = 1.0
) -> float:
    """
    NREL ATB LCOE using FCR. Real terms.
    """
    if wacc_real == 0:
        crf = 1.0 / project_life
    else:
        crf = wacc_real / (1 - (1 + wacc_real) ** (-project_life))
    fcr = crf * profinfactor
    annual_energy_mwh_per_kw = cf * 8760 / 1000
    fixed_cost_per_mwh = (fcr * capex_per_kw + fom_per_kw_yr) / annual_energy_mwh_per_kw
    lcoe = fixed_cost_per_mwh + vom_per_mwh + fuel_per_mwh
    return round(lcoe, 2)


# ----------------------------------------------------------------------
# 4. DIAGNOSTIC LCOE (for debugging)
# ----------------------------------------------------------------------
def calculate_lcoe_diagnostic(inputs: dict, project_lifespan: int = 30) -> dict:
    discount_rate      = inputs['discount_rate']
    capex_per_kw       = inputs['capital_cost_per_kwp']
    om_rate            = inputs['om_rate']
    grid_maintenance   = inputs['grid_maintenance_bn'] * 10**9
    cf                 = inputs['capacity_factor']
    deg_rate           = inputs['degradation_rate']
    init_kw            = inputs['initial_capacity']
    target_kw          = inputs['target_capacity']
    buildout_years     = 10

    annual_add_kw = (target_kw - init_kw) / buildout_years
    hours_per_year = cf * 8760

    capex_usd   = np.zeros(project_lifespan)
    om_usd      = np.zeros(project_lifespan)
    grid_usd    = np.zeros(project_lifespan)
    energy_kwh  = np.zeros(project_lifespan)
    eff_kw_arr  = np.zeros(project_lifespan)
    cum_kw_arr  = np.zeros(project_lifespan)

    cum_kw = init_kw
    eff_kw = init_kw

    for yr in range(project_lifespan):
        new_kw = annual_add_kw if yr < buildout_years else 0.0
        eff_kw *= (1 - deg_rate)
        eff_kw += new_kw
        cum_kw += new_kw

        capex_usd[yr] = new_kw * capex_per_kw
        om_usd[yr]    = cum_kw * capex_per_kw * om_rate
        grid_usd[yr]  = grid_maintenance
        energy_kwh[yr] = eff_kw * hours_per_year

        eff_kw_arr[yr] = eff_kw
        cum_kw_arr[yr] = cum_kw

    total_cost_usd = capex_usd + om_usd + grid_usd
    years = np.arange(1, project_lifespan + 1)
    dfac  = 1.0 / (1.0 + discount_rate) ** years

    pv_cost_usd   = np.sum(total_cost_usd * dfac)
    pv_energy_kwh = np.sum(energy_kwh * dfac)
    lcoe_per_kwh  = pv_cost_usd / pv_energy_kwh

    return {
        "LCOE ($/MWh)": round(lcoe_per_kwh * 1000, 2),
        "PV Costs ($)": pv_cost_usd,
        "PV Energy (TWh)": pv_energy_kwh / 1e12,
        "Total CAPEX ($)": np.sum(capex_usd),
        "Final Eff Capacity (TW)": eff_kw_arr[-1] / 1e9,
        "Year 1 Energy (TWh)": energy_kwh[0] / 1e12,
        "Year 30 Energy (TWh)": energy_kwh[-1] / 1e12,
        "Discount Year 1": dfac[0],
        "Discount Year 30": dfac[-1],
    }


# ----------------------------------------------------------------------
# 5. REST OF ORIGINAL FUNCTIONS (unchanged)
# ----------------------------------------------------------------------
def cumulative_post_debt_cash_flow(cash_flows_df: pd.DataFrame) -> pd.DataFrame:
    df = cash_flows_df[['Year']].copy()
    df['Cumulative Post-Debt Cash Flow ($B)'] = cash_flows_df['Cash Flow Post-Debt ($B)'].cumsum()
    return df

def calculate_funding_mix(inputs, bond_principal, buildout_years=10):
    us_adult_population = inputs['us_adult_population']
    participation_rate_low = inputs['participation_rate_low']
    participation_rate_mid = inputs['participation_rate_mid']
    participation_rate_high = inputs['participation_rate_high']
    individual_investment = inputs['individual_investment']

    # Estimate U.S. households (2023: ~132 million)
    # Source: U.S. Census Bureau – https://www.census.gov/housing/hvs/files/currenthvspress.pdf
    us_households = 132_000_000

    # Annual diverted funds (mid-case)
    diverted_funds_annual_mid = (12.5 + 2.5 + 7.5) * 10**9
    diverted_funds_10yr_mid = diverted_funds_annual_mid * buildout_years

    funding_mix = []
    for pr in [participation_rate_low, participation_rate_mid, participation_rate_high]:
        num_investors = us_adult_population * pr
        bond_proceeds = num_investors * individual_investment
        bond_coverage = bond_proceeds / bond_principal * 100 if bond_principal > 0 else 0

        # NEW: Household investment to fully cover bond
        household_investment = bond_principal / us_households if us_households > 0 else 0

        diverted_funds = diverted_funds_10yr_mid
        tax_revenue_needed = bond_principal - bond_proceeds - diverted_funds
        tax_revenue_percent = tax_revenue_needed / bond_principal * 100 if bond_principal > 0 else 0

        funding_mix.append({
            'Participation Rate (%)': pr * 100,
            'Number of Investors (M)': round(num_investors / 1e6, 1),
            'Bond Proceeds ($B)': round(bond_proceeds / 1e9, 2),
            'Bond Coverage (%)': round(bond_coverage, 1),
            'Diverted Funds (Fossil Fuel Subsidies) ($B)': round(diverted_funds / 1e9, 2),
            'Diverted Funds Coverage (%)': round(diverted_funds / bond_principal * 100, 1) if bond_principal > 0 else 0,
            'Tax Revenue Needed ($B)': round(tax_revenue_needed / 1e9, 2),
            'Tax Revenue Coverage (%)': round(tax_revenue_percent, 1)
            # NEW COLUMN
            # 'Household Investment Required ($)': round(household_investment, 0)
        })

    return pd.DataFrame(funding_mix)

def calculate_metrics(inputs, cash_flows_df, bond_principal, project_lifespan=30):
    discount_rate = inputs['discount_rate']
    bond_term = inputs['bond_term']
    bond_interest_rate = inputs['bond_interest_rate']
    individual_investment = inputs['individual_investment']
    
    cash_flows_post_debt = cash_flows_df['Cash Flow Post-Debt ($B)'] * 10**9
    npv_post_debt = npf.npv(discount_rate, cash_flows_post_debt) / 10**12
    irr_post_debt = npf.irr(cash_flows_post_debt) * 100 if npf.irr(cash_flows_post_debt) is not None else float('nan')
    payback_year_post_debt = next((i + 1 for i, cf in enumerate(np.cumsum(cash_flows_post_debt)) if cf > 0), project_lifespan) if any(cf > 0 for cf in np.cumsum(cash_flows_post_debt)) else project_lifespan
    cumulative_surplus_post_debt = sum(cash_flows_post_debt) / 10**12
    total_interest_paid = sum(cash_flows_df['Interest Payment ($B)']) * 10**9 / 10**12
    total_dividends_paid = sum(cash_flows_df['Dividends ($B)']) * 10**9 / 10**12
    debt_coverage_ratio_year10 = (cash_flows_df['Cash Flow Pre-Debt ($B)'].iloc[9] * 10**9 / (-npf.pmt(bond_interest_rate, bond_term, bond_principal))) if bond_term > 0 and bond_principal > 0 else float('nan')
    final_reinvested_balance = cash_flows_df['Reinvested Balance ($B)'].iloc[-1] * 10**9 / 10**12
    
    investor_cash_flows = [-individual_investment] + cash_flows_df['Investor Total Cash Flow ($)'].tolist()
    investor_irr = npf.irr(investor_cash_flows) * 100 if npf.irr(investor_cash_flows) is not None else float('nan')
    investor_ending_value = sum(investor_cash_flows[1:])
    investor_cagr = ((investor_ending_value / individual_investment) ** (1 / project_lifespan) - 1) * 100
    return {
        'NPV Post-Debt ($T)': npv_post_debt,
        'IRR Post-Debt (%)': irr_post_debt,
        'Project Payback Period (Years)': payback_year_post_debt,
        'Cumulative Surplus ($T)': cumulative_surplus_post_debt,
        'Total Interest Paid ($T)': total_interest_paid,
        'Total Dividends Paid ($T)': total_dividends_paid,
        'Debt Coverage Ratio Year 10': debt_coverage_ratio_year10,
        'Final Reinvested943 Balance ($T)': final_reinvested_balance,
        'Individual Bond Investor CAGR (%)': investor_cagr,
        'Individual Bond Investor IRR (%)': investor_irr,
        'Individual Bond Investor Ending Balance ($)': investor_ending_value
    }





















