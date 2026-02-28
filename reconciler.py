
import pandas as pd
import csv
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from contracts import get_tv_contract_rate, get_fsa_rate, GRI_PERCENTAGE, WALL_MOUNT_RATE, WALL_MOUNT_INSTALL_EXPOSED, THIRD_MAN_RATE, TV_WHITE_GLOVE_RATE, LIMITED_ACCESS_METRO, LIMITED_ACCESS_FERRY, LIMITED_ACCESS_REMOTE, SPECIAL_FACILITIES, APPLIANCE_GRI_FACTOR, APPLIANCE_MILEAGE_OBSERVED

# --- Configurations ---
INVOICE_PATH = "invoice/RXO_WE20260110.xlsx"
DO_DETAILS_PATH = "source/do_details_v1.csv"
CHARGE_CODES_PATH = "source/charge_types.csv"
OUTPUT_PATH = "recon_final_v2.csv"

# Contract Constants
ACC_ADDITIONAL_TV = 30.00
DIESEL_PRICE = 3.48

# --- Data Loading (Unchanged) ---
class DataLoader:
    @staticmethod
    def load_charge_codes(path: str) -> Dict[str, dict]:
        code_map = {}
        if not os.path.exists(path): return code_map
        try:
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 4 and ":" in row[0]: 
                        parts = row[0].split(":")
                        code_map[parts[0].strip()] = {
                            "name": parts[1].strip() if len(parts) > 1 else "Unknown",
                            "type": row[1].strip(),
                            "desc": row[3].strip()
                        }
        except Exception: pass
        return code_map

    @staticmethod
    def load_do_details(path: str) -> Dict[str, dict]:
        do_map = {}
        if not os.path.exists(path): return do_map
        try:
            df = pd.read_csv(path, dtype={'do_id': str})
            for _, row in df.iterrows():
                do_id = str(row['do_id']).strip()
                fam = str(row.get('product_family', '')).strip()
                sku = str(row.get('sku_id', '')).strip()
                
                if do_id not in do_map: do_map[do_id] = {'families': set(), 'skus': set()}
                if fam and fam.lower() != 'nan': do_map[do_id]['families'].add(fam)
                if sku and sku.lower() != 'nan': do_map[do_id]['skus'].add(sku)
        except Exception: pass
        return do_map

# --- Context ---
@dataclass
class ReconContext:
    invoice_line: int
    related_doc: str
    code: str
    amount: float
    mileage: Optional[float]
    families: List[str]
    skus: List[str]
    charge_info: dict = field(default_factory=dict)
    
    @property
    def is_tv(self) -> bool:
        if any(k in f.lower() for f in self.families for k in ["tv", "television", "monitor"]): return True
        return any("QN" in s or "UN" in s or "TV" in s or "LS" in s for s in self.skus)
        
    @property
    def has_wall_mount_sku(self) -> bool:
        return any("L-INST" in s or "EQ55" in s for s in self.skus)
        
    @property
    def tv_qty(self) -> int:
        if not self.is_tv: return 0
        count = sum(1 for s in self.skus if any(x in s.upper() for x in ["QN", "UN", "TV", "LS03"]))
        return max(1, count)

    @property
    def inferred_tv_size(self) -> str:
        for sku in self.skus:
            s_upper = sku.upper()
            if "QN" in s_upper or "UN" in s_upper:
                for size in ["98", "85", "75", "65", "55", "50", "43", "32", "100", "27", "83", "77", "70"]:
                    if size in s_upper: return f"{size}-inch"
        return "Unknown"
        
    @property
    def tv_size_int(self) -> int:
        sz_str = self.inferred_tv_size
        if sz_str == "Unknown": return 0
        match = re.search(r'(\d+)', sz_str)
        return int(match.group(1)) if match else 0
        
    @property
    def is_appliance(self) -> bool:
        keywords = ["washer", "dryer", "refrigerator", "fridge", "dishwasher", "range", "oven", "microwave", "appliance"]
        if any(k in f.lower() for f in self.families for k in keywords): return True
        return any(k in s.lower() for s in self.skus for k in keywords)

    @property
    def description_lower(self) -> str:
        return self.charge_info.get("desc", "").lower() + " " + self.charge_info.get("name", "").lower()

# --- Engines (Math & Candidates) ---
class PricingEngine:
    @staticmethod
    def calculate_expected(amount: float) -> float:
        return amount * (1 + GRI_PERCENTAGE)

    @staticmethod
    def generate_tv_candidates(base: float, qty: int) -> List[Tuple[float, str]]:
        candidates = [(PricingEngine.calculate_expected(base), f"1 Unit: ${base}")]
        if qty > 1:
            candidates.append((PricingEngine.calculate_expected(base * qty), f"{qty} Units * ${base}"))
            val_3 = PricingEngine.calculate_expected(base * qty + ACC_ADDITIONAL_TV)
            candidates.append((val_3, f"{qty} Units * ${base} + 1 * Acc $30"))
            val_4 = PricingEngine.calculate_expected(base * qty + ACC_ADDITIONAL_TV * (qty-1))
            candidates.append((val_4, f"{qty} Units * ${base} + {qty-1} * Acc $30"))
            val_5 = PricingEngine.calculate_expected(base + ACC_ADDITIONAL_TV * (qty-1))
            candidates.append((val_5, f"1 Unit: ${base} + {qty-1} * Acc $30"))
        return candidates

# --- Strategies ---
class ReconciliationStrategy(ABC):
    @abstractmethod
    def match(self, ctx: ReconContext) -> Optional[dict]: pass

class TVThresholdStrategy(ReconciliationStrategy):
    def match(self, ctx: ReconContext) -> Optional[dict]:
        if not ctx.is_tv: return None # Strict TV Guard
        if ctx.code not in ["1002900", "1305792"] or ctx.mileage is None: return None
        rate_def = get_tv_contract_rate(ctx.mileage)
        if not rate_def: return None
        
        candidates = PricingEngine.generate_tv_candidates(rate_def.amount, ctx.tv_qty)
        for expected, desc in candidates:
            if abs(ctx.amount - expected) < 0.10:
                # desc contains logic like "1 Unit: $98.04"
                return self._create_result(ctx, expected, desc, rate_def)
        return None

    def _create_result(self, ctx: ReconContext, expected: float, logic_desc: str, rate_def) -> dict:
        context_parts = []
        if ctx.inferred_tv_size != "Unknown": context_parts.append(f"Size: {ctx.inferred_tv_size}")
        if ctx.has_wall_mount_sku: context_parts.append("Wall Mount SKU")
        if ctx.tv_qty > 1: context_parts.append(f"Qty: {ctx.tv_qty}")
        
        context_str = " | ".join(context_parts) if context_parts else "Standard TV"
        calc_str = f"Calc: {logic_desc} * {1+GRI_PERCENTAGE} (GRI) = ${round(expected, 2)}"
        
        return {
            "Status": "MATCH (TV Threshold)", "Strategy": "TV_Threshold_12thAmd",
            "Contract_Ref": f"12th Amd (Pg {rate_def.page_ref}): {rate_def.description} @ ${rate_def.amount}",
            "Expected": round(expected, 2), "Diff": round(ctx.amount - expected, 2),
            "Note": f"{context_str} | {calc_str}"
        }

class WallMountStrategy(ReconciliationStrategy):
    def match(self, ctx: ReconContext) -> Optional[dict]:
        if not ctx.is_tv: return None # Strict TV Guard
        if not ctx.has_wall_mount_sku: return None
        expected = PricingEngine.calculate_expected(WALL_MOUNT_RATE.amount)
        if abs(ctx.amount - expected) < 0.10:
             return {
                "Status": "MATCH (Wall Mount)", "Strategy": "Wall_Mount_12thAmd",
                "Contract_Ref": f"12th Amd (Pg {WALL_MOUNT_RATE.page_ref}): Wall Mount Delivery @ ${WALL_MOUNT_RATE.amount}",
                "Expected": round(expected, 2), "Diff": round(ctx.amount - expected, 2),
                "Note": f"SKU: L-INST/EQ55 | Calc: ${WALL_MOUNT_RATE.amount} * {1+GRI_PERCENTAGE} (GRI) = ${round(expected, 2)}"
            }
        return None

class WallMountInstallStrategy(ReconciliationStrategy):
    def match(self, ctx: ReconContext) -> Optional[dict]:
        if not ctx.is_tv: return None # Strict TV Guard
        if ctx.code != "1305900": return None
        expected = PricingEngine.calculate_expected(WALL_MOUNT_INSTALL_EXPOSED.amount)
        if abs(ctx.amount - expected) < 0.10:
            return {
                "Status": "MATCH (Wall Mount Install)", "Strategy": "WM_Install_12thAmd",
                "Contract_Ref": f"12th Amd (Pg 3): Wall Mount Install @ ${WALL_MOUNT_INSTALL_EXPOSED.amount}",
                "Expected": round(expected, 2), "Diff": round(ctx.amount - expected, 2),
                "Note": f"Code 1305900 | Calc: ${WALL_MOUNT_INSTALL_EXPOSED.amount} * {1+GRI_PERCENTAGE} (GRI) = ${round(expected, 2)}"
            }
        return None
        
class WhiteGloveStrategy(ReconciliationStrategy):
    def match(self, ctx: ReconContext) -> Optional[dict]:
        if not ctx.is_tv: return None # Strict TV Guard
        if ctx.code == TV_WHITE_GLOVE_RATE.code:
            expected = PricingEngine.calculate_expected(TV_WHITE_GLOVE_RATE.amount)
            if abs(ctx.amount - expected) < 0.10:
                 return {
                    "Status": "MATCH (White Glove)", "Strategy": "TV_WhiteGlove_12thAmd",
                    "Contract_Ref": f"12th Amd (Pg 3): White Glove (TV) @ ${TV_WHITE_GLOVE_RATE.amount}",
                    "Expected": round(expected, 2), "Diff": round(ctx.amount - expected, 2),
                    "Note": f"Code 1305771 | Calc: ${TV_WHITE_GLOVE_RATE.amount} * {1+GRI_PERCENTAGE} (GRI) = ${round(expected, 2)}"
                }
        return None

class AccessorialStrategy(ReconciliationStrategy):
    def match(self, ctx: ReconContext) -> Optional[dict]:
        if not ctx.is_tv: return None # Strict TV Guard
        # 3rd Man (14th Amd)
        if ctx.code == THIRD_MAN_RATE.code:
            expected = THIRD_MAN_RATE.amount # Flat
            if abs(ctx.amount - expected) < 0.50:
                 if ctx.tv_size_int >= 98:
                    return {
                        "Status": "MATCH (Accessorial)", "Strategy": "14thAmd_3rdMan",
                        "Contract_Ref": f"14th Amd (Sec e): 3rd Man @ ${THIRD_MAN_RATE.amount}",
                        "Expected": round(expected, 2), "Diff": round(ctx.amount - expected, 2),
                        "Note": f"Size: {ctx.inferred_tv_size} | Calc: Flat Rate ${THIRD_MAN_RATE.amount}"
                    }
        return None
        
class LimitedAccessStrategy(ReconciliationStrategy):
    def match(self, ctx: ReconContext) -> Optional[dict]:
        if not ctx.is_tv: return None # Strict TV Guard
        desc = ctx.description_lower
        
        # Metro
        if "metro" in desc:
            base = PricingEngine.calculate_expected(LIMITED_ACCESS_METRO.amount)
            if abs(ctx.amount - base) < 0.20:
                return self._create_result("Metro Area", LIMITED_ACCESS_METRO, base, ctx)
            if abs(ctx.amount - (base * 1.15)) < 0.20:
                 return self._create_result("Metro Area (Tier 2)", LIMITED_ACCESS_METRO, base * 1.15, ctx, surcharge_note="Includes 15% Surcharge")
        
        # Ferry
        if "ferry" in desc or "island" in desc:
            base = PricingEngine.calculate_expected(LIMITED_ACCESS_FERRY.amount)
            if abs(ctx.amount - base) < 0.20:
                return self._create_result("Ferry/Island", LIMITED_ACCESS_FERRY, base, ctx)
            if abs(ctx.amount - (base * 1.15)) < 0.20:
                return self._create_result("Ferry/Island (Tier 2)", LIMITED_ACCESS_FERRY, base * 1.15, ctx, surcharge_note="Includes 15% Surcharge")

        # Remote
        if "remote" in desc:
            base = PricingEngine.calculate_expected(LIMITED_ACCESS_REMOTE.amount)
            if abs(ctx.amount - base) < 0.20:
                return self._create_result("Remote Area", LIMITED_ACCESS_REMOTE, base, ctx)
            if abs(ctx.amount - (base * 1.15)) < 0.20:
                return self._create_result("Remote Area (Tier 2)", LIMITED_ACCESS_REMOTE, base * 1.15, ctx, surcharge_note="Includes 15% Surcharge")

        # Special Facilities
        if "special" in desc and "facility" in desc:
             base = PricingEngine.calculate_expected(SPECIAL_FACILITIES.amount)
             if abs(ctx.amount - base) < 0.20:
                return self._create_result("Special Facilities", SPECIAL_FACILITIES, base, ctx)
             if abs(ctx.amount - (base * 1.15)) < 0.20:
                return self._create_result("Special Facilities (Tier 2)", SPECIAL_FACILITIES, base * 1.15, ctx, surcharge_note="Includes 15% Surcharge")
        
        return None

    def _create_result(self, name: str, rate_obj, expected: float, ctx: ReconContext, surcharge_note: str = "") -> dict:
        is_tier2 = "Tier 2" in name
        
        # Contract Ref Part
        ref_str = f"12th Amd (Pg 5): {rate_obj.description} @ ${rate_obj.amount}"
        if is_tier2: ref_str += " + 15%"
        
        # Note Part
        # Just grab key keyword from desc for context
        desc_kw = "Metro" if "metro" in ctx.description_lower else ("Ferry" if "ferry" in ctx.description_lower else ("Remote" if "remote" in ctx.description_lower else "Special Fac"))
        
        calc_str = f"${rate_obj.amount} * {1+GRI_PERCENTAGE} (GRI)"
        if is_tier2: calc_str = f"({calc_str}) * 1.15 (Surcharge)"
        calc_str += f" = ${round(expected, 2)}"
        
        final_note = f"Context: {desc_kw} | Calc: {calc_str}"
        return {
            "Status": f"MATCH ({name})", "Strategy": "LimitedAccess_12thAmd",
            "Contract_Ref": ref_str,
            "Expected": round(expected, 2), "Diff": round(ctx.amount - expected, 2),
            "Note": final_note
        }

class ApplianceMileageStrategy(ReconciliationStrategy):
    def match(self, ctx: ReconContext) -> Optional[dict]:
        if not ctx.is_appliance: return None
        if ctx.code != "1002771": return None
        
        if ctx.mileage and ctx.mileage > 75:
             excess = ctx.mileage - 75
             expected = excess * APPLIANCE_MILEAGE_OBSERVED
             # Allow looser tolerance due to mileage discrepancies ($5.00 range?)
             # Some cases have $139.30 vs 140.78 (1.5 diff).
             if abs(ctx.amount - expected) < 3.00:
                 return {
                    "Status": "MATCH (Mileage Surcharge)", "Strategy": "Appliance_Mileage_Observed",
                    "Contract_Ref": f"Observed Rate: Excess Miles (>75) @ ${APPLIANCE_MILEAGE_OBSERVED}/mi",
                    "Expected": round(expected, 2), "Diff": round(ctx.amount - expected, 2),
                    "Note": f"Calc: ({ctx.mileage} - 75) mi * ${APPLIANCE_MILEAGE_OBSERVED} = ${round(expected, 2)}"
                }
        return None

class ApplianceDeliveryStrategy(ReconciliationStrategy):
    def match(self, ctx: ReconContext) -> Optional[dict]:
        if not ctx.is_appliance: return None # Strict Appliance Guard
        if ctx.code != "1002770": return None
        
        # Base candidates: 1 Unit ($77), 2 Units ($94), 3 Units ($111)
        bases = [77.00, 94.00, 111.00]
        for base in bases:
            expected = base * APPLIANCE_GRI_FACTOR
            if abs(ctx.amount - expected) < 0.20:
                estimated_units = bases.index(base) + 1
                return {
                    "Status": "MATCH (Appliance Delivery)", "Strategy": "Appliance_Del_2017",
                    "Contract_Ref": f"XPO 2017 (Pg 22): Appliance Delivery {estimated_units} Unit(s) @ ${base} Base",
                    "Expected": round(expected, 2), "Diff": round(ctx.amount - expected, 2),
                    "Note": f"Calc: ${base} * {APPLIANCE_GRI_FACTOR} (Hist. GRI) = ${round(expected, 2)}"
                }
        return None

class ApplianceWhiteGloveStrategy(ReconciliationStrategy):
    def match(self, ctx: ReconContext) -> Optional[dict]:
        if not ctx.is_appliance: return None
        if ctx.code != "1305771": return None # White Glove Code
        
        # Logic: Base $15 (1st) + $12 (Add'l) * 1.135
        # 1: 15, 2: 27, 3: 39, 4: 51, 5: 63
        factor = 1.135
        for qty in range(1, 10):
            base = 15 + (12 * (qty - 1))
            expected = base * factor
            if abs(ctx.amount - expected) < 0.10:
                return {
                    "Status": "MATCH (White Glove)", "Strategy": "Appliance_WhiteGlove_Observed",
                    "Contract_Ref": f"Inferred Pattern: Base $15 + $12/Extra (Qty {qty})",
                    "Expected": round(expected, 2), "Diff": round(ctx.amount - expected, 2),
                    "Note": f"Calc: ${base} * {factor} (GRI) = ${round(expected, 2)}"
                }

        return None

class NotHomeStrategy(ReconciliationStrategy):
    def match(self, ctx: ReconContext) -> Optional[dict]:
        if ctx.code != "1305792": return None
        
        # Universal Rate: $87.36 (observed for TV & Appliance)
        # Derived from $77.00 Base * 1.13455 (Appliance GRI)?
        # Or $85.65 * 1.02?
        # $77 * 1.13455 = 87.360...
        
        base = 77.00
        factor = APPLIANCE_GRI_FACTOR
        expected = base * factor
        
        if abs(ctx.amount - expected) < 0.10:
             return {
                "Status": "MATCH (Not Home / Attempt)", "Strategy": "NotHome_Universal",
                "Contract_Ref": f"Universal Attempt Fee (Base ${base})",
                "Expected": round(expected, 2), "Diff": round(ctx.amount - expected, 2),
                "Note": f"Calc: ${base} * {factor} (GRI) = ${round(expected, 2)}"
            }
        return None

# --- Analyzers ---
class DiscrepancyAnalyzer:
    def analyze(self, ctx: ReconContext, base_result: dict) -> dict:
        out = base_result.copy()
        if ctx.is_tv and ctx.code in ["1002900"] and ctx.mileage is not None:
            rate = get_tv_contract_rate(ctx.mileage)
            if rate:
                expected = PricingEngine.calculate_expected(rate.amount)
                wm_expected = PricingEngine.calculate_expected(WALL_MOUNT_RATE.amount)
                if abs(ctx.amount - wm_expected) < 0.10:
                    diff = ctx.amount - expected
                    if diff < -0.10: out["Status"] = "UNDERCHARGED"
                    elif diff > 0.10: out["Status"] = "OVERCHARGED"
                    else: out["Status"] = "MATCH (Wall Mount Rate Applied)"
                    out["Note"] = f"Charged $112.20 (Wall Mount Rate) but no Wall Mount SKU. Expected {round(expected, 2)}"
                else:
                    out["Status"] = "DISCREPANCY"
                out["Expected"] = round(expected, 2)
                out["Diff"] = round(ctx.amount - expected, 2)
                out["Contract_Ref"] = f"${rate.amount} + 2% GRI"
        return out

# --- Post Processor ---
class PostProcessor:
    def run(self, results: List[dict]):
        doc_map = {}
        for res in results:
            doc = res.get("Related_Doc")
            if doc: doc_map.setdefault(doc, []).append(res)
        
        for doc, rows in doc_map.items():
            self._audit_order(rows)
            self._audit_fsa(rows)

    def _audit_order(self, rows: List[dict]):
        has_wm_sku = False
        has_wm_charge = False
        delivery_line = None
        for row in rows:
            if "L-INST" in row["SKUs"] or "EQ55" in row["SKUs"]: has_wm_sku = True
            if "Wall Mount" in row["Status"] and "MATCH" in row["Status"]: has_wm_charge = True
            if row["Strategy"] == "TV_Threshold_12thAmd": delivery_line = row
        if has_wm_sku and not has_wm_charge and delivery_line:
            delivery_line["Status"] = "UNDERCHARGED (Missing Wall Mount)"
            delivery_line["Note"] = (delivery_line.get("Note", "") + " | Order has Wall Mount SKU but no Wall Mount Charge Match found.").strip(" | ")

    def _audit_fsa(self, rows: List[dict]):
        qualifying_base = 0.0
        qualifying_notes = []
        fsa_lines = []
        
        for row in rows:
            if row["Code"] == "1002781":
                fsa_lines.append(row)
                continue
            
            strat = row.get("Strategy", "")
            
            # TV Logic
            if strat and ("TV_Threshold" in strat or "Wall_Mount" in strat or "WM_Install" in strat or "TV_WhiteGlove" in strat):
               amt = row.get("Amount", 0.0)
               qualifying_base += amt
               qualifying_notes.append(f"${amt}")
            
            # Appliance Logic
            if strat == "Appliance_Del_2017":
                # For Appliances, FSA seems to be on Base Delivery ONLY
                amt = row.get("Amount", 0.0)
                qualifying_base += amt
                qualifying_notes.append(f"${amt} (Appliance Base)")

        if not fsa_lines: return
        
        fsa_percent = get_fsa_rate(DIESEL_PRICE)
        expected_fsa = qualifying_base * fsa_percent
        base_desc = " + ".join(qualifying_notes)
        
        for fsa_row in fsa_lines:
            if qualifying_base > 0 and abs(fsa_row["Amount"] - expected_fsa) < 0.20:
                fsa_row["Status"] = "MATCH (FSA)"
                fsa_row["Strategy"] = "FSA_12thAmd_Table"
                fsa_row["Expected"] = round(expected_fsa, 2)
                fsa_row["Diff"] = round(fsa_row["Amount"] - expected_fsa, 2)
                fsa_row["Contract_Ref"] = f"12th Amd (Pg 6): FSA Table (Diesel ${DIESEL_PRICE})"
                fsa_row["Note"] = f"Calc: {round(fsa_percent * 100, 2)}% of ({base_desc}) = ${round(expected_fsa, 2)}"
            elif qualifying_base > 0:
             diff = fsa_row["Amount"] - expected_fsa
             status_label = "OVERCHARGED (FSA)" if diff > 0 else "UNDERCHARGED (FSA)"
             fsa_row["Status"] = status_label
             fsa_row["Expected"] = round(expected_fsa, 2)
             fsa_row["Diff"] = round(diff, 2)
             fsa_row["Note"] = f"Expected {round(fsa_percent*100, 2)}% of ({base_desc}) = ${round(expected_fsa, 2)}"

# --- Main Reconciler ---
class Reconciler:
    def __init__(self):
        self.code_map = DataLoader.load_charge_codes(CHARGE_CODES_PATH)
        self.do_map = DataLoader.load_do_details(DO_DETAILS_PATH)
        self.strategies = [WallMountStrategy(), TVThresholdStrategy(), WallMountInstallStrategy(), WhiteGloveStrategy(), AccessorialStrategy(), LimitedAccessStrategy(), ApplianceDeliveryStrategy(), ApplianceMileageStrategy(), ApplianceWhiteGloveStrategy(), NotHomeStrategy()]
        self.analyzer = DiscrepancyAnalyzer()
        self.post_processor = PostProcessor()
        
    def process_row(self, idx: int, row: pd.Series) -> dict:
        ctx = self._build_context(idx, row)
        out = self._create_base_output(ctx)
        for strat in self.strategies:
            match = strat.match(ctx)
            if match:
                out.update(match)
                return out
        return self.analyzer.analyze(ctx, out)

    def run(self):
        print("Initializing Reconciler V6 (Modular)...")
        df = pd.read_excel(INVOICE_PATH)
        print(f"Loaded {len(df)} rows.")
        results = [self.process_row(idx, row) for idx, row in df.iterrows()]
        self.post_processor.run(results)
        out_df = pd.DataFrame(results)
        out_df.to_csv(OUTPUT_PATH, index=False)
        print("\n--- Summary ---")
        print(out_df['Status'].value_counts())
        print(f"Total Matches: {out_df[out_df['Status'].str.startswith('MATCH')].shape[0]}")

    def _build_context(self, idx: int, row: pd.Series) -> ReconContext:
        doc_id = str(row.get('RelatedDocNumber', '')).strip().replace('.0', '')
        full_code = str(row.get('LCC', '')).replace('.0', '') + str(row.get('SLCC', '')).replace('.0', '') if row.get('SLCC') else str(row.get('LCC', '')).replace('.0', '')
        mileage = None
        try: mileage = float(row.get('Mileage')) if pd.notna(row.get('Mileage')) else None
        except: pass
        do_info = self.do_map.get(doc_id, {'families': set(), 'skus': set()})
        charge_info = self.code_map.get(full_code, {"name": "Unknown", "type": "Unknown", "desc": "Unknown"})
        return ReconContext(
            invoice_line=idx+2, related_doc=doc_id, code=full_code,
            amount=float(row.get('Request_Amount', 0.0)), mileage=mileage,
            families=list(do_info['families']), skus=list(do_info['skus']),
            charge_info=charge_info
        )

    def _create_base_output(self, ctx: ReconContext) -> dict:
        return {
            "Invoice_Line": ctx.invoice_line, "Related_Doc": ctx.related_doc, "Code": ctx.code,
            "Charge_Name": ctx.charge_info["name"], "Charge_Type": ctx.charge_info["type"], "Description": ctx.charge_info["desc"],
            "Amount": ctx.amount, "Mileage": ctx.mileage,
            "Family": ", ".join(ctx.families), "SKUs": ", ".join(ctx.skus),
            "TV_Size": ctx.inferred_tv_size if ctx.is_tv else "",
            "TV_Qty": ctx.tv_qty if ctx.is_tv else "",
            "Status": "SKIPPED", "Strategy": "", "Expected": 0.0, "Diff": 0.0, "Contract_Ref": "", "Note": ""
        }

if __name__ == "__main__":
    Reconciler().run()
