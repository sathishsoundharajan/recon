# Reconciliation Strategies (v6)

This document defines the currently active reconciliation strategies implemented in `reconciler_v6.py`.
**Global Guard:** All strategies below currently enforce `is_tv = True` (checking for TV Family or SKU patterns) and will NOT run for Appliance orders.

## 1. TV Threshold Delivery
*   **Strategy Key**: `TV_Threshold_12thAmd`
*   **Purpose**: Reconciles the base delivery charge for TVs based on mileage bands.
*   **Contract Reference**: RXO 12th Amendment, Page 3, Section c.
*   **Trigger Code(s)**: `1002900`, `1305792`
*   **Logic**:
    1.  Determine Contract Rate based on Mileage (e.g., 0-25 miles = $90.85, 25-50 miles = $98.04, etc.).
    2.  Apply GRI: `Rate * 1.02`.
    3.  Check Multi-Unit scenarios (e.g., 2 Units = `2 * Rate * 1.02`).
    4.  Match against Invoiced Amount.

## 2. Wall Mount Delivery
*   **Strategy Key**: `Wall_Mount_12thAmd`
*   **Purpose**: Reconciles the specific delivery rate for orders containing Wall Mount SKUs.
*   **Contract Reference**: RXO 12th Amendment, Page 3.
*   **Trigger**: Presence of known Wall Mount SKUs (`L-INST`, `EQ55`).
*   **Rate**: $110.00 Base.
*   **Calculation**: `$110.00 * 1.02 (GRI) = $112.20`.

## 3. Wall Mount Installation
*   **Strategy Key**: `WM_Install_12thAmd`
*   **Purpose**: Reconciles the installation labor charge for Wall Mounts (Wires Exposed).
*   **Contract Reference**: RXO 12th Amendment, Page 3.
*   **Trigger Code**: `1305900`.
*   **Rate**: $95.00 Base.
*   **Calculation**: `$95.00 * 1.02 (GRI) = $96.90`.

## 4. White Glove Service (TV)
*   **Strategy Key**: `TV_WhiteGlove_12thAmd`
*   **Purpose**: Reconciles the premium white glove service add-on for TVs.
*   **Contract Reference**: RXO 12th Amendment, Page 3.
*   **Trigger Code**: `1305771`.
*   **Rate**: $24.00 Base.
*   **Calculation**: `$24.00 * 1.02 (GRI) = $24.48`.

## 5. Accessorial: 3rd Man Service
*   **Strategy Key**: `14thAmd_3rdMan`
*   **Purpose**: Reconciles charges for an extra crew member required for massive TVs.
*   **Contract Reference**: RXO 14th Amendment, Section e.
*   **Trigger Code**: `1305805`.
*   **Condition**: TV Size must be inferred as ≥ 98 inches.
*   **Rate**: $157.00 Flat (No GRI applied in logic).

## 6. Limited Access & Special Facilities
*   **Strategy Key**: `LimitedAccess_12thAmd`
*   **Purpose**: Reconciles surcharges for difficult delivery locations.
*   **Contract Reference**: RXO 12th Amendment, Page 5 (Accessorial Table).
*   **Trigger**: Keyword match in Charge Description (Metro, Ferry, Remote, Special Facility).
*   **Variants**:
    *   **Metro Area**: $60.00 Base.
    *   **Remote Area**: $45.00 Base.
    *   **Ferry/Island**: $125.00 Base.
    *   **Special Facilities**: $60.00 Base.
*   **Tier 2 Surcharge**: If the amount matches `(Base * GRI) * 1.15`, it is identified as a "Tier 2" charge (systematic 15% surcharge detected).

## 7. Fuel Surcharge (FSA) Audit
*   **Strategy Key**: `FSA_12thAmd_Table`
*   **Purpose**: Validates the "Last Mile Fuel Surcharge" line item.
*   **Contract Reference**: RXO 12th Amendment, Page 6 (FSA Table).
*   **Trigger Code**: `1002781`.
*   **Logic**:
    1.  Identify all "Qualifying Charges" on the invoice (TV Threshold, Wall Mount, Install, White Glove).
    2.  Sum their amounts.
    3.  Lookup FSA % based on National Diesel Average (Fixed at $3.48 -> 12.4%).
    4.  Expected FSA = `Sum * 12.4%`.

## 8. Appliance Delivery
*   **Strategy Key**: `Appliance_Del_2017`
*   **Purpose**: Reconciles the base delivery charge for Appliances (Washers, Dryers, etc.).
*   **Contract Reference**: XPO 2017 Contract, Page 22 + Historical GRI.
*   **Trigger Code**: `1002770`.
*   **Guard**: `is_appliance = True`.
*   **Logic**:
    *   Base Rate (2017): $77.00 (1 Unit), $94.00 (2 Units), $111.00 (3 Units).
    *   Observed Factor: ~1.13455 (Cumulative GRI).
    *   **Calculation**: `$77.00 * 1.13455 = $87.36`.
    *   Multi-Unit: `$94.00 * 1.13455 = $106.65`.

## 9. Appliance Fuel Surcharge (FSA)
*   **Strategy Key**: `Appliance_FSA`
*   **Purpose**: Validates FSA for Appliance orders.
*   **Guard**: `is_appliance = True`.
*   **Logic**:
    *   Unlike TVs, Appliance FSA is calculated **ONLY** on the Base Delivery Charge (Code 1002770).
    *   It excludes White Glove, Attempt Fees, or Mileage Surcharges.
    *   **Calculation**: `Base Delivery Amount * 12.4%`.

## 10. Appliance Mileage Surcharge
*   **Strategy Key**: `Appliance_Mileage_Observed`
*   **Purpose**: Reconciles Last Mile Surcharge for Appliances.
*   **Trigger Code**: `1002771`.
*   **Guard**: `is_appliance = True`.
*   **Logic**:
    *   Applies to mileage > 75 (Threshold 75 miles).
    *   **Observed Rate**: $2.00 per excess mile.
    *   Notes: Small variances (up to $3.00) allowed due to mileage calculation differences.
    *   **Calculation**: `(Mileage - 75) * $2.00`.

## 11. Appliance White Glove (Observed Pattern)
*   **Strategy Key**: `Appliance_WhiteGlove_Observed`
*   **Purpose**: Reconciles White Glove / Accessorial charges for Appliances.
*   **Trigger Code**: `1305771`.
*   **Guard**: `is_appliance = True`.
*   **Status**: **Derived / Reverse-Engineered**.
*   **Logic**: Analysis of invoicing patterns ($17.03, $30.65) reveals a strict tiered pricing structure consistent with Base + GRI.
*   **Derived Rates**:
    *   **1 Unit**: Base $15.00 * 1.135 = $17.03.
    *   **Additional Units**: Base $12.00.
    *   **Formula**: `($15 + ($12 * (Qty-1))) * 1.135`.
    *   **Formula**: `($15 + ($12 * (Qty-1))) * 1.135`.
    *   *Note: This specific rate table is not found in the provided contract snippets but is applied consistently (0.01 tolerance) across 190+ orders.*

## 12. Not Home / Attempt Fee
*   **Strategy Key**: `NotHome_Universal`
*   **Purpose**: Reconciles "Not Home" Attempt Fees (Code 1305792).
*   **Trigger Code**: `1305792`.
*   **Guard**: None (Universal for TV and Appliance).
*   **Status**: **Consistent Pattern (Derived)**.
*   **Logic**: Applies the **Appliance Base Delivery Rate** ($87.36) as a flat fee for attempted delivery.
    *   **Calculation**: `$77.00 (Base) * 1.13455 (GRI) = $87.36`.
    *   Matches consistently for both TV and Appliance orders.

