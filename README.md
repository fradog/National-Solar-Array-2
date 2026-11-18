# National Solar Array Modeling Tool

**A financial and energy modeling tool demonstrating that a massive U.S. solar + storage array can achieve Net Zero by ~2035–2037 with strong economic returns, energy independence, and broad public participation.**

[Live Demo (Streamlit)](https://national-solar-array-ouuqzyhcvnqsmfbmy5cxnm.streamlit.app/) *(replace with actual link after deployment)*

---

## Overview

This project simulates a **national-scale solar photovoltaic (PV) + battery storage system** designed to replace all U.S. fossil fuel energy consumption by the mid-2030s. It models:

- **Energy production** with realistic capacity factor, degradation, and 10-year build-out
- **Financial cash flows** including CAPEX, O&M, grid maintenance, bond financing, carbon tax revenue, avoided fuel costs
- **Investor returns** via bond participation, dividends, and reinvestment
- **Levelized Cost of Energy (LCOE)** with full PV-based calculation and NREL ATB-style benchmark
- **CO₂ emissions phase-out** over the build period
- **Efficiency gains** from electrification (ICE → EV, fossil plants → direct solar)

The model shows that **at current average electricity prices (~$0.16/kWh)**, the system generates **massive surplus cash flows**, enabling:
- Full debt repayment
- High investor returns
- National reinvestment or public dividends

## Scenario: Maximizing Annual Payouts to Bondholders

A compelling configuration minimizes reinvestment, allowing the **reinvestment fund** to grow only enough to finance a full array replacement every 30 years. This frees the vast majority of annual cash flows for:

- **Debt service** (bond principal + interest)  
- **Dividend distributions** to bondholders  

**Result**: With a high *dividend percentage* (e.g., 80–90%), individual bondholders receive **exceptionally high annual yields**, transforming the bonds into one of the most attractive fixed-income investments available.  

This scenario represents **maximum annual redistribution** of solar proceeds to public investors—effectively treating the array as a high-yield, infrastructure-backed annuity.

---

## Inflation and Economic Assumptions

- **All costs and revenues are in *2024 real dollars***. The model does **not** apply inflation to construction, O&M, or energy prices.  
- In a real-world rollout, any cost inflation would likely be offset by corresponding increases in **wholesale electricity prices** (passed through to consumers).  
- **Discount rate** (used for NPV and LCOE via WACC) is therefore expressed in **real terms**, consistent with constant-dollar modeling.

---

## Macro-Scale Implications

At full deployment, the National Solar Array generates **trillions in annual cash flow**—a scale comparable to a significant portion of the current U.S. GDP (~$30 trillion in 2025).  

Given energy’s role as a foundational input, **controlled solar pricing** could serve as a powerful **anti-inflationary lever**. By stabilizing or reducing real energy costs, the array introduces a new degree of monetary and economic control.

In effect, the array functions as a **controllable asset of the U.S. Treasury**—with built-in feedback loops via pricing, reinvestment, and dividend policies. Over decades, the U.S. economy would increasingly **anchor to solar abundance**, shifting from fossil scarcity to renewable plenty as the primary growth constraint. 

## Philosophical Considerations in Costs and Revenues

This model incorporates three revenue sources that involve philosophical or policy judgments. Each can be adjusted or zeroed out using the sliders in the tool. Their inclusion has a meaningful but not decisive impact on the overall results.

1. **Avoided Fossil Fuel Costs**  
   I treat the *energy content* of fossil fuels that would otherwise be burned to generate an equivalent amount of electricity as a revenue stream over the array’s lifetime. This is equivalent to the wholesale cost of the displaced fuel (e.g., natural gas, coal).  
   *Rationale*: Society avoids purchasing and combusting that fuel.  
   *Debate*: Whether this should count as “revenue” to the project (vs. a societal saving) is subjective. Set the “Avoided fuel cost per kWh” slider to $0 to exclude it.

2. **Carbon Tax Revenue**  
   A hypothetical carbon tax is applied to residual fossil generation during the build-out phase. The resulting revenue is used **exclusively to reduce bond principal** in the years it is collected.  
   *Behavior*: Tax revenue declines to zero as the solar array displaces fossil generation.  
   *Rationale*: Captures the declining externality cost of carbon during the transition.  
   *Debate*: Assumes a specific tax exists and that its proceeds are earmarked for this project.

3. **Reallocated Fossil Fuel Subsidies**  
   The model assumes the $22.5 billion in annual U.S. fossil fuel subsidies is redirected **as a one-time lump-sum contribution** at project start. This reduces the bond principal that must be raised from investors (and thus any residual taxpayer exposure if bonds are undersubscribed).  
   *Rationale*: Public funds currently supporting fossil fuels are instead used to accelerate clean infrastructure.  
   *Debate*: Requires explicit policy change; treated here as a scenario assumption.

**Transparency Note**  
All three items are isolated inputs. Users can set any or all to zero to see results under more conservative accounting that counts only direct electricity sales and investment returns. 

---

## Background and Motivation

This interactive model allows users to explore the financial and energy impacts of a **national-scale solar + storage array** sized to replace all U.S. fossil fuel energy by ~2035–2037. All inputs are adjustable via sliders and text fields; reload the app to reset to defaults.

The core question: **Can solar energy at current U.S. electricity prices (~16.5¢/kWh) generate enough cash flow over 30 years to benefit all stakeholders — investors, taxpayers, and future generations?**

The answer is a resounding **yes**.

Built first as a detailed spreadsheet and now in Python, this model leverages **NREL’s 2024 Annual Technology Baseline (ATB)** for cost, performance, and financial benchmarks ([nrel.gov/atb](https://atb.nrel.gov/electricity/2024/about)).

Key insights:
- Once installed, solar produces energy for decades at a small fraction of O&M cost.
- **Revenue per kWh** is the most sensitive driver — even modest price assumptions yield massive surplus.
- A **nationalized grid** changes the financial context: no tax incentives, no subsidies, no equity return hurdles — just direct cash flow from energy sales.

Unlike conventional utility-scale projects (where solar barely edges out fossil fuels), this **hypothetical national effort** delivers **unmatched ROI**, paying off bonds, funding dividends, and building wealth.

### Why Nationalize?

The U.S. grid and energy supply are **critical national infrastructure**. This model proposes **public ownership** — not government bureaucracy — with construction led by proven high-performance contractors (e.g., SpaceX, Tesla).

Fossil fuel giants like ExxonMobil — who pioneered early PV tech — could bid to build vertically integrated, automated panel and battery factories in the Southwest, earning **returns exceeding their current fossil business**.

### Raw Materials & Feasibility

Early spreadsheet analysis of panel and battery material requirements (including full transport electrification) shows **no critical shortages**. This feature will be added to the app soon.

### Global Implications

If the U.S. leads with a **prosperity-driven Net Zero**, other nations will follow — not out of obligation, but **economic self-interest**.

---

This isn’t just about climate.  
It’s about **energy independence**, **financial security**, and **a future where clean energy pays for itself — and then some**.

Contributions welcome from those who see solar not as a cost, but as **the greatest economic engine of the 21st century**.

---

**Let’s build it.**

---

## Key Features

| Feature | Description |
|-------|-----------|
| **Interactive Dashboard** | Built with Streamlit — adjust all inputs in real time |
| **LCOE Validation Mode** | Toggle to zero extras and verify `Revenue = LCOE → NPV ≈ 0` |
| **Unlevered NPV** | Exact match with LCOE logic (no debt, no extras) |
| **NREL ATB Comparison** | Side-by-side FCR-based LCOE (no degradation) |
| **Efficiency Downgrade** | Models energy savings from electrifying transport & heating |
| **Bond + Dividend Model** | Public participation via $10k bonds, with CAGR/IRR tracking |


---

## File Structure

```
national-solar-array/
├── app.py                  # Main Streamlit dashboard
├── solar_model.py          # Core financial & energy calculations
├── efficiency_downgrade.py # Efficiency gain logic (electrification)
├── README.md               # This file
└── requirements.txt        # Python dependencies
```

---

## How to Run Locally

```bash
# 1. Clone the repo
git clone https://github.com/yourusername/national-solar-array.git
cd national-solar-array

# 2. Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
streamlit run app.py
```

---

## `requirements.txt`

```txt
streamlit
pandas
numpy
numpy-financial
plotly
```

---

## Model Inputs (Sidebar)

| Category | Key Parameters |
|--------|----------------|
| **System Scale** | Initial/Target Capacity (GWp), Capacity Factor |
| **Costs** | CAPEX ($/kWp), O&M Rate, Grid Maintenance ($B/yr) |
| **Revenue** | Revenue $/kWh, Avoided Fuel $/kWh |
| **Financing** | Bond Rate, Term, Reinvestment %, Dividend % |
| **Emissions** | Carbon Tax $/ton, Displaceable Proportion |
| **Efficiency** | ICE/EV/Utility efficiencies (sliders) |

---

## Validation Mode

Enable **"LCOE Validation Mode"** in the sidebar to:
- Zero: avoided fuel, carbon tax, grid maintenance, degradation, bond costs
- Force `revenue_per_kwh = LCOE`
- Display **Unlevered NPV ≈ $0.00T** → confirms model consistency

---

## LCOE Methodology

- **Your Model**: Full PV of costs ÷ PV of energy (with degradation & build-out)
- **NREL ATB Style**: Fixed Charge Rate (FCR), constant output, no degradation
- **Diagnostic Table**: CAPEX, energy, capacity over time

---

## Sample Results (Default Inputs)

| Metric | Value |
|------|-------|
| **Target Capacity** | 5,498 GWp |
| **LCOE (Your Model)** | ~$58.24/MWh |
| **LCOE (NREL FCR)** | ~$55.10/MWh |
| **Bond Principal** | ~$9.5T |
| **NPV Post-Debt** | +$10–15T |
| **Individual Investor CAGR** | 6–15% |
| **Payback Period** | ~8–12 years |
| **Area Required** | ~21,000 sq mi |

---

## Assumptions & Conservatism

- 10-year linear build-out
- 0.7%/yr panel degradation
- No additional CAPEX to offset degradation
- Grid maintenance: $50B/yr fixed
- Carbon tax applied only during build
- Efficiency gains: ~75–80% reduction in primary energy via electrification
- All values in **real dollars** (no inflation)

---

## Contributing

Contributions welcome! Open an issue or PR for:
- New sensitivity charts
- CSV export
- Multi-scenario comparison
- API integration
- Deployment scripts

---

## License

[MIT License](LICENSE) – Free to use, modify, and distribute.

---

## Author

**Doug Frasher**  
With modeling support from **Grok (xAI)**

> *"We don’t need to choose between climate action and prosperity — this model proves we can have both."*

---

**Deployed on Streamlit Community Cloud** – [Launch App](#) *(update link)*

---

*Last updated: November 06, 2025*
