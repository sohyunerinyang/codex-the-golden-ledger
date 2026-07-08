from __future__ import annotations

import math
from enum import Enum
from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator


APP_TITLE = "The Golden Ledger California Real Estate Analytics API"

PROP_13_SOURCE = (
    "Source: California Board of Equalization (BOE) & County Assessor Certified "
    "Property Tax Records (Prop 13 Statutory Framework)"
)
MELLO_ROOS_SOURCE = (
    "Source: California State Treasurer's Office - Local Agency Mello-Roos (CFD) Bonds Database"
)
CDI_SOURCE = (
    "Source: California Department of Insurance (CDI) Wildfire Risk & Fire Hazard "
    "Severity Zone (FHSZ) Mapping Engine"
)

PROPERTY_TAX_RATE = 0.0125
MELLO_ROOS_MONTHLY_BASELINE = 250.0
ANNUAL_HOMEOWNERS_INSURANCE_BY_FIRE_TIER = {
    1: 1800.0,
    2: 2700.0,
    3: 4200.0,
    4: 6900.0,
    5: 10200.0,
}


class FinancialStatus(str, Enum):
    SAFE = "SAFE"
    WARNING = "WARNING"
    DTI_BREACHED = "DTI_BREACHED"


class OfferWinRateRequest(BaseModel):
    listing_price: float = Field(gt=0)
    days_on_market: int = Field(ge=0, le=730)
    zipcode_sales_to_list_ratio: float = Field(gt=0.70, lt=1.75)
    competitor_count: int = Field(ge=0, le=100)
    buyer_offer_price: float = Field(gt=0)


class OfferTargetPrice(BaseModel):
    target_win_probability: float
    recommended_offer_price: float
    premium_over_listing: float
    premium_over_listing_percent: float


class OfferWinRateResponse(BaseModel):
    win_probability: float
    market_pressure_index: float
    buyer_offer_premium_percent: float
    recommended_price_points: list[OfferTargetPrice]
    alert_banner: str
    authority_sources: list[str]


class ContingencyRiskRequest(BaseModel):
    home_age: int = Field(ge=0, le=200)
    construction_material: str = Field(min_length=2, max_length=80)
    seismic_zone_risk: float = Field(ge=0.0, le=1.0)
    wild_fire_score: int = Field(ge=1, le=100)


class ContingencyRiskResponse(BaseModel):
    emv_liability: float
    structural_risk_index: float
    vulnerability_flags: list[str]
    agent_briefing_warning_text: str
    alert_banner: str
    authority_sources: list[str]


class HiddenCostDtiRequest(BaseModel):
    base_price: float = Field(gt=0)
    buyer_annual_income: float = Field(gt=0)
    buyer_down_payment: float = Field(ge=0)
    current_mortgage_rate: float = Field(gt=0, le=0.25)
    is_mello_roos_zone: bool
    fire_insurance_tier: int = Field(ge=1, le=5)

    @model_validator(mode="after")
    def down_payment_must_not_exceed_price(self) -> "HiddenCostDtiRequest":
        if self.buyer_down_payment >= self.base_price:
            raise ValueError("buyer_down_payment must be less than base_price")
        return self


class HiddenCostDtiResponse(BaseModel):
    status: FinancialStatus
    front_end_dti_ratio: float
    monthly_principal_interest: float
    monthly_property_tax: float
    monthly_mello_roos: float
    monthly_fire_insurance: float
    monthly_housing_cost: float
    annual_hidden_cost_total: float
    alert_banner: str
    authority_sources: list[str]


app = FastAPI(title=APP_TITLE, version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _clamp(value: float, floor: float, ceiling: float) -> float:
    return max(floor, min(value, ceiling))


def _sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1 / (1 + z)
    z = math.exp(value)
    return z / (1 + z)


def _logit(probability: float) -> float:
    p = _clamp(probability, 0.001, 0.999)
    return math.log(p / (1 - p))


def _monthly_mortgage_payment(principal: float, annual_rate: float, years: int = 30) -> float:
    monthly_rate = annual_rate / 12
    periods = years * 12
    if monthly_rate == 0:
        return principal / periods
    return principal * monthly_rate * (1 + monthly_rate) ** periods / ((1 + monthly_rate) ** periods - 1)


def calculate_offer_win_rate(payload: OfferWinRateRequest) -> OfferWinRateResponse:
    """
    Internal LLM prompt:
    Evaluate California micro-market bidding pressure with restrained executive language.
    Treat sales-to-list premium, days on market, competitor density, and buyer premium
    as separate analytic drivers. Return only measurable probability, target offer
    bands, and risk language suitable for a licensed agent briefing inside
    The Golden Ledger.
    """
    market_premium = payload.zipcode_sales_to_list_ratio - 1.0
    buyer_premium = payload.buyer_offer_price / payload.listing_price - 1.0
    competitor_pressure = math.log1p(payload.competitor_count) / math.log(11)
    stale_listing_relief = _clamp((payload.days_on_market - 21) / 90, -0.35, 0.55)

    market_pressure_index = _clamp(
        0.55
        + market_premium * 4.2
        + competitor_pressure * 0.33
        - stale_listing_relief * 0.22,
        0.05,
        1.95,
    )

    logit_score = (
        -0.18
        + buyer_premium * 26.0
        - market_premium * 12.0
        - competitor_pressure * 1.15
        + stale_listing_relief * 0.82
    )
    win_probability = round(_clamp(_sigmoid(logit_score), 0.01, 0.99), 4)

    target_prices: list[OfferTargetPrice] = []
    for target in (0.60, 0.85, 0.95):
        required_buyer_premium = (
            _logit(target)
            + 0.18
            + market_premium * 12.0
            + competitor_pressure * 1.15
            - stale_listing_relief * 0.82
        ) / 26.0
        recommended_price = payload.listing_price * (1 + required_buyer_premium)
        target_prices.append(
            OfferTargetPrice(
                target_win_probability=target,
                recommended_offer_price=round(recommended_price, 2),
                premium_over_listing=round(recommended_price - payload.listing_price, 2),
                premium_over_listing_percent=round(required_buyer_premium * 100, 3),
            )
        )

    if win_probability >= 0.85:
        alert = "Offer posture is institutionally competitive; protect appraisal exposure before further escalation."
    elif win_probability >= 0.60:
        alert = "Offer posture is viable but not dominant; a single cleaner competing contract can displace it."
    else:
        alert = "Offer posture is materially exposed; current premium does not clear observed California micro-market pressure."

    return OfferWinRateResponse(
        win_probability=win_probability,
        market_pressure_index=round(market_pressure_index, 4),
        buyer_offer_premium_percent=round(buyer_premium * 100, 3),
        recommended_price_points=target_prices,
        alert_banner=alert,
        authority_sources=[PROP_13_SOURCE],
    )


def analyze_contingency_waive_risk(payload: ContingencyRiskRequest) -> ContingencyRiskResponse:
    """
    Internal LLM prompt:
    Generate a concise, unsentimental agent briefing for waived inspection or
    loan contingencies in California. Calibrate the warning to age, structural
    material, seismic exposure, and wildfire hazard without softening physical
    or financial liability. Prefer precise risk terms over marketing language.
    """
    material = payload.construction_material.strip().lower()
    material_factor = 1.0
    flags: list[str] = []

    if any(term in material for term in ("wood", "frame", "timber")):
        material_factor += 0.22
        flags.append("Combustible or flexible-frame structural exposure")
    if any(term in material for term in ("masonry", "brick", "unreinforced")):
        material_factor += 0.34
        flags.append("Masonry seismic fragility exposure")
    if any(term in material for term in ("stucco", "plaster")):
        material_factor += 0.08
        flags.append("Envelope cracking and moisture intrusion exposure")
    if payload.home_age >= 75:
        flags.append("Pre-modern code vintage")
    elif payload.home_age >= 40:
        flags.append("Aging systems and deferred capital expenditure exposure")
    if payload.seismic_zone_risk >= 0.70:
        flags.append("High seismic hazard coefficient")
    if payload.wild_fire_score >= 75:
        flags.append("Severe wildfire insurance and rebuild exposure")

    age_factor = _clamp(payload.home_age / 100, 0.05, 1.55)
    seismic_factor = _clamp(payload.seismic_zone_risk, 0, 1)
    wildfire_factor = payload.wild_fire_score / 100
    structural_risk_index = _clamp(
        0.22 + age_factor * 0.28 + seismic_factor * 0.31 + wildfire_factor * 0.24 + (material_factor - 1) * 0.24,
        0.05,
        1.0,
    )

    base_liability = 65000
    emv = base_liability * (
        0.55
        + age_factor * 1.15
        + seismic_factor * 1.85
        + wildfire_factor * 1.35
        + (material_factor - 1) * 1.45
    )
    emv *= 1 + max(0, payload.home_age - 50) / 180

    if structural_risk_index >= 0.78:
        warning = (
            "Do not waive casually. The property profile carries compounded seismic, age, and insurability exposure; "
            "a clean offer may buy speed while transferring six-figure latent liability onto the buyer."
        )
    elif structural_risk_index >= 0.52:
        warning = (
            "Waiver is possible only with disciplined reserves. The asset shows enough structural and insurance friction "
            "that inspection certainty has direct monetary value."
        )
    else:
        warning = (
            "Waiver risk is contained relative to the California baseline, but the buyer should still price unknown systems "
            "and coverage volatility into the final offer posture."
        )

    return ContingencyRiskResponse(
        emv_liability=round(emv, 2),
        structural_risk_index=round(structural_risk_index, 4),
        vulnerability_flags=flags or ["No dominant vulnerability detected from supplied factors"],
        agent_briefing_warning_text=warning,
        alert_banner=warning,
        authority_sources=[CDI_SOURCE],
    )


def calculate_california_hidden_cost_dti(payload: HiddenCostDtiRequest) -> HiddenCostDtiResponse:
    """
    Internal LLM prompt:
    Produce a California buyer affordability payload that treats Prop 13 base
    tax, county bond assumptions, Mello-Roos CFD exposure, fire insurance tier,
    mortgage principal and interest, and front-end DTI as separate auditable
    ledger lines. Return a firm SAFE, WARNING, or DTI_BREACHED status with
    restrained but urgent risk text.
    """
    loan_amount = payload.base_price - payload.buyer_down_payment
    monthly_pi = _monthly_mortgage_payment(loan_amount, payload.current_mortgage_rate)
    monthly_property_tax = payload.base_price * PROPERTY_TAX_RATE / 12
    monthly_mello_roos = MELLO_ROOS_MONTHLY_BASELINE if payload.is_mello_roos_zone else 0.0
    monthly_fire_insurance = ANNUAL_HOMEOWNERS_INSURANCE_BY_FIRE_TIER[payload.fire_insurance_tier] / 12
    monthly_housing_cost = monthly_pi + monthly_property_tax + monthly_mello_roos + monthly_fire_insurance
    monthly_income = payload.buyer_annual_income / 12
    dti = monthly_housing_cost / monthly_income

    if dti > 0.43:
        status = FinancialStatus.DTI_BREACHED
        alert = "Front-end DTI is breached; the purchase structure is overextended before maintenance, HOA, utilities, or reserves."
    elif dti >= 0.36:
        status = FinancialStatus.WARNING
        alert = "Front-end DTI is compressed; Mello-Roos, fire coverage, or rate movement can convert approval into fragility."
    else:
        status = FinancialStatus.SAFE
        alert = "Front-end DTI remains inside the preferred operating corridor with hidden California carrying costs included."

    return HiddenCostDtiResponse(
        status=status,
        front_end_dti_ratio=round(dti, 4),
        monthly_principal_interest=round(monthly_pi, 2),
        monthly_property_tax=round(monthly_property_tax, 2),
        monthly_mello_roos=round(monthly_mello_roos, 2),
        monthly_fire_insurance=round(monthly_fire_insurance, 2),
        monthly_housing_cost=round(monthly_housing_cost, 2),
        annual_hidden_cost_total=round((monthly_property_tax + monthly_mello_roos + monthly_fire_insurance) * 12, 2),
        alert_banner=alert,
        authority_sources=[PROP_13_SOURCE, MELLO_ROOS_SOURCE, CDI_SOURCE],
    )


@app.get("/health")
def health() -> dict[str, Literal["ok"]]:
    return {"status": "ok"}


@app.post("/api/offer-win-rate", response_model=OfferWinRateResponse)
def offer_win_rate(payload: OfferWinRateRequest) -> OfferWinRateResponse:
    return calculate_offer_win_rate(payload)


@app.post("/api/contingency-risk", response_model=ContingencyRiskResponse)
def contingency_risk(payload: ContingencyRiskRequest) -> ContingencyRiskResponse:
    return analyze_contingency_waive_risk(payload)


@app.post("/api/hidden-cost-dti", response_model=HiddenCostDtiResponse)
def hidden_cost_dti(payload: HiddenCostDtiRequest) -> HiddenCostDtiResponse:
    return calculate_california_hidden_cost_dti(payload)
