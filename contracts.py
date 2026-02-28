
from dataclasses import dataclass
from typing import Optional, Dict

@dataclass
class ContractRate:
    code: str
    description: str
    amount: float
    source_doc: str
    page_ref: int
    section_ref: str
    conditions: Dict[str, float]  # e.g., {'min_mileage': 0, 'max_mileage': 25}
    effective_date: str

# 12th Amendment (Nov 2023) - TV Threshold Rates
# Source: RXO 12th Amendment (2)_MARKER_ANONYMIZED.md
# Page: 3, Section: c. TV Threshold and White Glove Rate separation
TV_MILEAGE_RATES = [
    ContractRate(
        code="1002900", # Shared Code, context determined by Mileage Logic
        description="TV Threshold 0-25 Miles",
        amount=90.85,
        source_doc="RXO 12th Amendment",
        page_ref=3,
        section_ref="c. TV Threshold",
        conditions={"min_mileage": 0.0, "max_mileage": 25.0},
        effective_date="2023-11-13"
    ),
    ContractRate(
        code="1002900",
        description="TV Threshold 25-50 Miles",
        amount=98.04,
        source_doc="RXO 12th Amendment",
        page_ref=3,
        section_ref="c. TV Threshold",
        conditions={"min_mileage": 25.0, "max_mileage": 50.0},
        effective_date="2023-11-13"
    ),
    ContractRate(
        code="1002900",
        description="TV Threshold 50-75 Miles",
        amount=108.02,
        source_doc="RXO 12th Amendment",
        page_ref=3,
        section_ref="c. TV Threshold",
        conditions={"min_mileage": 50.0, "max_mileage": 75.0},
        effective_date="2023-11-13"
    ),
    ContractRate(
        code="1002900",
        description="TV Threshold 75-100 Miles",
        amount=119.96,
        source_doc="RXO 12th Amendment",
        page_ref=3,
        section_ref="c. TV Threshold",
        conditions={"min_mileage": 75.0, "max_mileage": 100.0},
        effective_date="2023-11-13"
    ),
    ContractRate(
        code="1002900",
        description="TV Threshold 100-125 Miles",
        amount=126.67,
        source_doc="RXO 12th Amendment",
        page_ref=3,
        section_ref="c. TV Threshold",
        conditions={"min_mileage": 100.0, "max_mileage": 125.0},
        effective_date="2023-11-13"
    ),
    ContractRate(
        code="1002900",
        description="TV Threshold 125-150 Miles",
        amount=152.38,
        source_doc="RXO 12th Amendment",
        page_ref=3,
        section_ref="c. TV Threshold",
        conditions={"min_mileage": 125.0, "max_mileage": 150.0},
        effective_date="2023-11-13"
    ),
    ContractRate(
        code="1002900",
        description="TV Threshold 150-175 Miles",
        amount=156.68,
        source_doc="RXO 12th Amendment",
        page_ref=3,
        section_ref="c. TV Threshold",
        conditions={"min_mileage": 150.0, "max_mileage": 175.0},
        effective_date="2023-11-13"
    ),
    ContractRate(
        code="1002900",
        description="TV Threshold 175+ Miles",
        amount=275.00,
        source_doc="RXO 12th Amendment",
        page_ref=3,
        section_ref="c. TV Threshold",
        conditions={"min_mileage": 175.0, "max_mileage": 9999.0},
        effective_date="2023-11-13"
    ),
]

# 13th Amendment (Aug 2024) - GRI
# Source: RXO 13th Amendment (3)_MARKER_ANONYMIZED.md
# Page: 1, Section: 4.f
GRI_PERCENTAGE = 0.02
GRI_EFFECTIVE_DATE = "2024-08-16"

def get_tv_contract_rate(mileage: float) -> Optional[ContractRate]:
    """Finds the contractual rate for a TV delivery based on mileage."""
    # Strict boundary check (e.g. 0-25 includes 25? Usually "0 up to 25" vs "25 up to 50".
    # Table says 0-25, 25-50. Ambiguous boundaries.
    # Logic: 25.0 matches 0-25 or 25-50?
    # Usually strictly inequalities: min <= x < max?
    # Let's assume inclusive lower, exclusive upper, except last.
    
    for rate in TV_MILEAGE_RATES:
        mn = rate.conditions["min_mileage"]
        mx = rate.conditions["max_mileage"]
        
        # 175+ Case
        if mn == 175.0 and mileage >= 175.0:
            return rate
            
        # Standard Bands (Left Inclusive)
        if mn <= mileage < mx:
            return rate
            
        # Handle the boundary edge case if mileage is exactly 25.0
        # If we use < mx, 25.0 fails 0-25, falls to 25-50.
        # This seems standard.
    
    return None

# Wall Mount Delivery (12th Amd, Page 3)
WALL_MOUNT_RATE = ContractRate(
    code="1002900", # Often billed under generic code
    description="Wall-Mount Delivery",
    amount=110.00,
    source_doc="RXO 12th Amendment",
    page_ref=3,
    section_ref="c. TV Threshold",
    conditions={}, 
    effective_date="2023-11-13"
)

# Wall Mount Install (Wires Exposed)
WALL_MOUNT_INSTALL_EXPOSED = ContractRate(
    code="1305900", # Seen in invoice for Install
    description="Wall-Mount Install Wires Exposed",
    amount=95.00,
    source_doc="RXO 12th Amendment",
    page_ref=3,
    section_ref="c. Wall-Mount Install",
    conditions={},
    effective_date="2023-11-13"
)

# TV White Glove Install (12th Amd, Page 3)
TV_WHITE_GLOVE_RATE = ContractRate(
    code="1305771",
    description="White Glove Install (TV)",
    amount=24.00,
    source_doc="RXO 12th Amendment",
    page_ref=3,
    section_ref="c. TV Threshold",
    conditions={},
    effective_date="2023-11-13"
)

# 3rd Man Rate (14th Amd, Section e)
THIRD_MAN_RATE = ContractRate(
    code="1305805",
    description="3rd Man Rate for 98+ inch TV",
    amount=157.00,
    source_doc="RXO 14th Amendment",
    page_ref=4,
    section_ref="e. Pre-Approved Third Man",
    conditions={"min_size": 98.0},
    effective_date="2025-03-15"
)

# Limited Access / Accessorials (12th Amd, Page 5)
LIMITED_ACCESS_METRO = ContractRate(
    code="1002783", # Based on Invoice observation
    description="Limited Access (Metro Area)",
    amount=60.00,
    source_doc="RXO 12th Amendment",
    page_ref=5,
    section_ref="e. Accessorial Table (Item 172)",
    conditions={},
    effective_date="2023-11-13"
)

LIMITED_ACCESS_FERRY = ContractRate(
    code="1002784", 
    description="Limited Access (Ferry/Island)",
    amount=125.00,
    source_doc="RXO 12th Amendment",
    page_ref=5,
    section_ref="e. Accessorial Table (Item 174)",
    conditions={},
    effective_date="2023-11-13"
)

LIMITED_ACCESS_REMOTE = ContractRate(
    code="1002785", 
    description="Limited Access (Remote Area)",
    amount=45.00,
    source_doc="RXO 12th Amendment",
    page_ref=5,
    section_ref="e. Accessorial Table (Item 176)",
    conditions={},
    effective_date="2023-11-13"
)

SPECIAL_FACILITIES = ContractRate(
    code="Unknown", # Need to check invoice
    description="Special Facilities",
    amount=60.00,
    source_doc="RXO 12th Amendment",
    page_ref=5,
    section_ref="e. Accessorial Table (Item 170)",
    conditions={},
    effective_date="2023-11-13"
)

# FSA Logic (12th Amd, Page 6)
# Base $1.151 -> 4.35%. Increases 0.35% per $0.10.
def get_fsa_rate(diesel_price: float) -> float:
    """Calculates Fuel Surcharge % based on Diesel Price."""
    if diesel_price < 1.151: return 0.0
    
    # Steps above base
    diff = diesel_price - 1.151
    steps = int(diff / 0.10)
    
    rate = 4.35 + (steps * 0.35)
    return round(rate / 100.0, 4) # Return as float (e.g. 0.1240)

# Appliance Constants (Historical / Observed)
# 2017 Contract Base ($77.00) -> 2024 Observed ($87.36)
# Factor = 87.36 / 77.00 = 1.134545...
APPLIANCE_GRI_FACTOR = 1.13455

# Appliance Accessorials (2017 + GRI or Observed)
NOT_HOME_RATE = 77.00 * APPLIANCE_GRI_FACTOR # ~$87.36
HAUL_AWAY_RATE = 18.00 # Placeholder (2017)
ADD_ITEM_RATE = 17.00 # Placeholder (2017)

# Appliance Mileage
APPLIANCE_MILEAGE_CONTRACT = 2.50 # 2017 Rate
APPLIANCE_MILEAGE_OBSERVED = 2.00 # Observed in data
