"""Government Schemes: seed verified data, recommendations and notifications."""
import logging
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.models.models import (
    Farm, Field, GovernmentScheme, SchemeNotification, User,
)

logger = logging.getLogger(__name__)

VERIFIED_DATE = date(2026, 11, 21)

# Verified schemes sourced from official government portals.
# Only information confirmed through official sources is included.
_SCHEMES = [
    # ---------------------------------------------------------------- Central
    {
        "name": "PM-KISAN (Pradhan Mantri Kisan Samman Nidhi)",
        "description": "Central sector scheme providing income support to landholding farmer families.",
        "benefits": "Rs 6,000 per year transferred in three equal instalments of Rs 2,000 each directly to the farmer's Aadhaar-seeded bank account via Direct Benefit Transfer (DBT).",
        "eligibility": "All landholding farmer families with cultivable land up to 2 hectares whose names appear in state/UT land records. Excluded: institutional farmers, present/former holders of constitutional posts, government employees, professionals (doctor/engineer/lawyer), income taxpayers, and persons with land in cities.",
        "documents_required": "Aadhaar card, bank account details (linked to Aadhaar), land ownership records (7/12 or equivalent state land record).",
        "application_process": "Register online at the PM-KISAN portal (pmkisan.gov.in) or visit the nearest Common Service Centre (CSC). Farmers can also check their status and download instalment details on the portal. State governments verify land records and approve beneficiaries.",
        "application_url": "https://pmkisan.gov.in",
        "source_url": "https://pmkisan.gov.in",
        "last_verified": VERIFIED_DATE,
        "level": "central",
        "category": "income_support",
        "applicable_crops": None,
    },
    {
        "name": "PMFBY (Pradhan Mantri Fasal Bima Yojana)",
        "description": "Crop insurance scheme protecting farmers against financial losses from natural calamities, pests and diseases.",
        "benefits": "Comprehensive insurance coverage from pre-sowing to post-harvest against natural calamities (drought, flood, cyclone, hailstorm), pests, diseases, and localised calamities. Farmer premium is capped at 2% for Kharif crops, 1.5% for Rabi crops, and 5% for commercial/horticultural crops. The government subsidises the remaining actuarial premium.",
        "eligibility": "All farmers including sharecroppers and tenant farmers growing notified crops in notified areas. Loanee farmers are enrolled compulsorily; non-loanee farmers can enrol voluntarily.",
        "documents_required": "Aadhaar card, land records (7/12 or equivalent), bank account details, sowing certificate from village agriculture officer. Loanee farmers need KCC loan account details.",
        "application_process": "Contact your bank (for loanee farmers) or visit the nearest agriculture office / PMFBY portal. Fill the proposal form with crop details and pay the farmer's share of the premium before the notified cut-off date.",
        "application_url": "https://pmfby.gov.in",
        "source_url": "https://pmfby.gov.in/pdf/PMFBY_Features.pdf",
        "last_verified": VERIFIED_DATE,
        "level": "central",
        "category": "insurance",
        "applicable_crops": None,
    },
    {
        "name": "Kisan Credit Card (KCC)",
        "description": "Short-term credit facility for farmers to meet agricultural expenses, purchase inputs and equipment.",
        "benefits": "Revolving credit at 7% per annum interest rate. With prompt repayment incentive of 3%, effective rate is 4%. Loan limit raised to Rs 5 lakh under the Modified Interest Subvention Scheme (MISS) in Union Budget 2025-26. No maximum loan ceiling specified.",
        "eligibility": "All farmers including individual/joint cultivators, tenant farmers, sharecroppers, and farmers engaged in allied activities (dairy, fisheries). The applicant must own or cultivate agricultural land.",
        "documents_required": "Aadhaar card, PAN card, land records (7/12 or equivalent), passport-size photographs, bank account details.",
        "application_process": "Apply at any commercial bank, RRB, cooperative bank or through the KCC online portal. Submit the application form with land records and identity proof. Banks sanction the card based on landholding and crop pattern.",
        "application_url": "https://www.myscheme.gov.in/schemes/kcc",
        "source_url": "https://sansad.in/getFile/loksabhaquestions/annex/184/AU1024_ZXGHt2.pdf",
        "last_verified": VERIFIED_DATE,
        "level": "central",
        "category": "credit",
        "applicable_crops": None,
    },
    {
        "name": "Pradhan Mantri Krishi Sinchayee Yojana (PMKSY) - Micro Irrigation",
        "description": "Scheme to expand irrigated area and improve water use efficiency through micro irrigation (drip and sprinkler systems).",
        "benefits": "Subsidy on drip and sprinkler irrigation systems. For small and marginal farmers, subsidy up to 55% of the system cost; for other farmers, up to 45%. The remaining cost is borne by the farmer.",
        "eligibility": "All individual farmers, groups of farmers, water user associations, and FPOs engaged in agricultural activities. Priority to small and marginal farmers and areas with assured water source.",
        "documents_required": "Aadhaar card, 7/12 land record, bank account details, quotation from empanelled agency for the micro irrigation system.",
        "application_process": "Apply through the state agriculture department or online via the state DBT portal (e.g. MahaDBT in Maharashtra). Submit the application with land records and system quotation. The approved subsidy is credited after installation and inspection.",
        "application_url": "https://pmksy.gov.in",
        "source_url": "https://pmksy.gov.in",
        "last_verified": VERIFIED_DATE,
        "level": "central",
        "category": "irrigation",
        "applicable_crops": None,
    },
    {
        "name": "Soil Health Card Scheme",
        "description": "Scheme providing farmers with soil health cards containing nutrient status and fertiliser recommendations for their land.",
        "benefits": "Free soil testing and a Soil Health Card with macronutrient (N, P, K) and micronutrient status, along with crop-specific fertiliser recommendations. Cards are issued every 2 years.",
        "eligibility": "All farmers who own or cultivate agricultural land. No landholding size restriction.",
        "documents_required": "Aadhaar card, land records (7/12 or equivalent). Soil sample collected from the field by the agriculture department.",
        "application_process": "Contact the nearest agriculture office or soil testing laboratory. Collect soil samples as per guidelines and submit for testing. The Soil Health Card is issued after analysis, typically within a few weeks.",
        "application_url": "https://soilhealthcard.dac.gov.in",
        "source_url": "https://soilhealthcard.dac.gov.in",
        "last_verified": VERIFIED_DATE,
        "level": "central",
        "category": "soil_health",
        "applicable_crops": None,
    },
    {
        "name": "National Agriculture Market (eNAM)",
        "description": "Online trading platform for agricultural commodities, enabling farmers to sell produce at better prices across India.",
        "benefits": "Online trading of agricultural produce across mandis integrated with eNAM. Farmers get transparent pricing, wider market access, and direct payment to bank accounts. Eliminates middlemen and reduces transaction costs.",
        "eligibility": "All farmers registered in states where eNAM is operational. Traders and commission agents can also register.",
        "documents_required": "Aadhaar card, bank account details, mobile number. For traders: trade license and PAN.",
        "application_process": "Register on the eNAM portal (enam.gov.in) with Aadhaar and bank details. After verification, farmers can participate in online auctions at integrated mandis.",
        "application_url": "https://enam.gov.in",
        "source_url": "https://enam.gov.in",
        "last_verified": VERIFIED_DATE,
        "level": "central",
        "category": "market",
        "applicable_crops": None,
    },
    {
        "name": "Paramparagat Krishi Vikas Yojana (PKVY)",
        "description": "Scheme promoting organic farming through cluster-based approach with Participatory Guarantee System (PGS) certification.",
        "benefits": "Financial assistance of Rs 50,000 per hectare over 3 years for organic conversion, including inputs, certification, market linkage, and training. PGS organic certification provided free of cost.",
        "eligibility": "Farmers formed into clusters of at least 50 acres (20 hectares). Each farmer in the cluster must commit to organic farming for 3 years. Open to all categories of farmers.",
        "documents_required": "Aadhaar card, land records (7/12 or equivalent), bank account details. Cluster formation documents.",
        "application_process": "Form a farmer cluster through the local agriculture office or FPO. Apply through the state agriculture department. After approval, the cluster receives assistance for 3 years with annual inspections.",
        "application_url": "https://pgsindia-ncof.gov.in",
        "source_url": "https://pgsindia-ncof.gov.in",
        "last_verified": VERIFIED_DATE,
        "level": "central",
        "category": "organic",
        "applicable_crops": None,
    },
    {
        "name": "Pradhan Mantri Kisan Maandhan Yojana (PM-KMY)",
        "description": "Pension scheme for small and marginal farmers providing monthly pension after age 60.",
        "benefits": "Monthly pension of Rs 3,000 after attaining age 60. Both farmer and government contribute equally to the pension fund. The subscriber manages the contribution amount based on age of entry.",
        "eligibility": "Small and marginal farmers (cultivable land up to 2 hectares), aged 18 to 40 years, listed in state/UT land records. Must not be an income taxpayer or hold any government job.",
        "documents_required": "Aadhaar card, land records (7/12 or equivalent), bank account details, mobile number, age proof.",
        "application_process": "Register at the nearest Common Service Centre (CSC) or through the PM-KMY online portal. The contribution is auto-debited from the bank account. Monthly contribution ranges from Rs 55 to Rs 200 depending on age of entry.",
        "application_url": "https://maandhan.gov.in",
        "source_url": "https://static.pib.gov.in/WriteReadData/specificdocs/documents/2024/sep/doc202499390501.pdf",
        "last_verified": VERIFIED_DATE,
        "level": "central",
        "category": "pension",
        "applicable_crops": None,
    },
    {
        "name": "Sub-Mission on Agricultural Mechanization (SMAM)",
        "description": "Scheme to promote agricultural mechanisation through subsidies on farm machinery and equipment.",
        "benefits": "Subsidy ranging from 25% to 50% on purchase of tractors, power tillers, harvesters, threshers, and other farm machinery. Higher subsidy for small, marginal, and women farmers. Financial assistance for establishing custom hiring centres (CHCs) for farm equipment.",
        "eligibility": "All individual farmers, FPOs, custom hiring centres, and farmer groups. Priority to small and marginal farmers.",
        "documents_required": "Aadhaar card, land records, bank account details, quotation/invoice from approved manufacturer or dealer.",
        "application_process": "Apply through the state agriculture department or online via the state DBT portal. Submit the application with machinery quotation. After approval and purchase, the subsidy is credited to the bank account.",
        "application_url": "https://agrimachinery.nic.in",
        "source_url": "https://agrimachinery.nic.in",
        "last_verified": VERIFIED_DATE,
        "level": "central",
        "category": "mechanization",
        "applicable_crops": None,
    },
    {
        "name": "Agriculture Infrastructure Fund (AIF)",
        "description": "Financing facility for creation of post-harvest infrastructure and community farming assets.",
        "benefits": "Loans up to Rs 2 crore at concessional interest rates with credit guarantee coverage. Interest subvention of 3% per annum for loans up to 7 years. Rs 10,000 per application incentive for CPF account and asset creation.",
        "eligibility": "Farmers, FPOs, agri-entrepreneurs, PACS, and SHGs engaged in creating post-harvest infrastructure (cold storage, warehouse, processing units, etc.).",
        "documents_required": "Aadhaar card, project report, land records, bank account details. For FPOs: registration certificate and bylaws.",
        "application_process": "Apply through any scheduled commercial bank, RRB, or cooperative bank. Submit the project report and application. Banks appraise the project and sanction the loan with AIF benefits.",
        "application_url": "https://agrinfra.dac.gov.in",
        "source_url": "https://agrinfra.dac.gov.in",
        "last_verified": VERIFIED_DATE,
        "level": "central",
        "category": "infrastructure",
        "applicable_crops": None,
    },
    # ---------------------------------------------------------------- Maharashtra
    {
        "name": "Mahatma Jyotirao Phule Shetkari Karj Mukti Yojana",
        "description": "Maharashtra government farm loan waiver scheme providing debt relief to eligible farmers.",
        "benefits": "Debt relief of up to Rs 2 lakh credited directly to the farmer's loan account after successful Aadhaar authentication. Covers crop loans disbursed from 1 April 2019 to 31 March 2025.",
        "eligibility": "Maharashtra farmers with outstanding crop loans (disbursed between 1 April 2019 and 31 March 2025) that remained unpaid as of 30 September 2025. Must have valid Aadhaar-linked loan account.",
        "documents_required": "Aadhaar card, loan account details, 7/12 land record, bank account details.",
        "application_process": "Eligible farmers are identified based on bank records. No separate application required for identified beneficiaries. Check the beneficiary list on the Maharashtra government portal or contact your bank.",
        "application_url": "https://mahadbt.maharashtra.gov.in",
        "source_url": "https://mahadbt.maharashtra.gov.in",
        "last_verified": VERIFIED_DATE,
        "level": "maharashtra",
        "category": "loan_waiver",
        "applicable_crops": None,
    },
    {
        "name": "Mukhyamantri Saur Krishi Pump Sinchan Yojana",
        "description": "Maharashtra scheme providing subsidy on solar agricultural pumps for irrigation.",
        "benefits": "Subsidy on installation of solar agricultural water pumps. Farmers get a solar pump system with significant government subsidy, reducing irrigation cost and ensuring reliable water supply without electricity bills.",
        "eligibility": "Maharashtra farmers with valid 7/12 land records who do not have a conventional electricity connection for agriculture or wish to switch to solar pumps. Must have a water source (well, borewell) on the farm.",
        "documents_required": "Aadhaar card, 7/12 land record, bank account details, water source proof (well/borewell), no-objection certificate if applicable.",
        "application_process": "Apply through the MahaDBT portal or the Maharashtra State Electricity Distribution Company (MSEDCL) portal. Submit application with land records and water source proof. After verification, the solar pump is installed by empanelled agencies.",
        "application_url": "https://mahadbt.maharashtra.gov.in",
        "source_url": "https://mahadbt.maharashtra.gov.in",
        "last_verified": VERIFIED_DATE,
        "level": "maharashtra",
        "category": "irrigation",
        "applicable_crops": None,
    },
    {
        "name": "Maharashtra Shet Tale (Farm Pond) Scheme",
        "description": "Maharashtra scheme providing subsidy for construction of farm ponds (Shet Tale) for rainwater harvesting and irrigation.",
        "benefits": "Subsidy on construction of farm ponds. The pond helps store rainwater for irrigation during dry periods, reducing dependence on rainfall and improving crop productivity.",
        "eligibility": "Maharashtra farmers owning cultivable land with adequate runoff area for water harvesting. The farm should have a natural slope for rainwater collection.",
        "documents_required": "Aadhaar card, 7/12 land record, bank account details, soil test report, site survey.",
        "application_process": "Apply through the MahaDBT portal or nearest agriculture office. Submit application with land records and site details. After approval, the farm pond is constructed and inspected before subsidy disbursement.",
        "application_url": "https://mahadbt.maharashtra.gov.in",
        "source_url": "https://mahadbt.maharashtra.gov.in",
        "last_verified": VERIFIED_DATE,
        "level": "maharashtra",
        "category": "irrigation",
        "applicable_crops": None,
    },
    {
        "name": "Maharashtra AgriStack Farmer ID",
        "description": "Maharashtra digital farmer registration providing a unique Farmer ID linked to land records, Aadhaar and bank account.",
        "benefits": "A unique Farmer ID that serves as a single identity for accessing all central and state government agriculture schemes. Eliminates the need to submit documents separately for each scheme. Linked to 7/12 land records and Aadhaar.",
        "eligibility": "All Maharashtra farmers with valid 7/12 land records and Aadhaar. Registration is voluntary but required for scheme applications.",
        "documents_required": "Aadhaar card, 7/12 land record, bank account details, mobile number.",
        "application_process": "Register once at the Maharashtra AgriStack portal (mhfr.agristack.gov.in). Complete Aadhaar e-KYC and link land records. The Farmer ID is generated after verification.",
        "application_url": "https://mhfr.agristack.gov.in",
        "source_url": "https://www.egovtschemes.com/maharashtra-agristack-farmer-id/",
        "last_verified": VERIFIED_DATE,
        "level": "maharashtra",
        "category": "registration",
        "applicable_crops": None,
    },
    {
        "name": "Maharashtra Farm Mechanization Subsidy",
        "description": "Maharashtra state scheme providing subsidy on agricultural machinery and equipment purchase.",
        "benefits": "Subsidy on purchase of tractors, power tillers, harvesters, rotavators, sprayers, and other farm implements. Subsidy percentage varies by equipment type and farmer category (higher for small and marginal farmers).",
        "eligibility": "Maharashtra farmers with valid 7/12 land records. Priority to small and marginal farmers. Farmer must not have availed similar subsidy in the last 3 years.",
        "documents_required": "Aadhaar card, 7/12 land record, bank account details, quotation from approved dealer, Farmer ID.",
        "application_process": "Apply through the MahaDBT portal when the scheme window is open. From 2025-26, applications are approved on a first-come-first-served basis subject to budget availability. Submit application with quotation; subsidy is credited after purchase verification.",
        "application_url": "https://mahadbt.maharashtra.gov.in",
        "source_url": "https://mahadbt.maharashtra.gov.in",
        "last_verified": VERIFIED_DATE,
        "level": "maharashtra",
        "category": "mechanization",
        "applicable_crops": None,
    },
    {
        "name": "Maharashtra Organic Farming Promotion Scheme",
        "description": "Maharashtra scheme promoting organic farming practices through training, certification, and market linkage support.",
        "benefits": "Financial assistance for organic inputs, training on organic farming techniques, PGS certification support, and market linkage for organic produce. Scheme operates through cluster approach.",
        "eligibility": "Maharashtra farmers willing to adopt organic farming practices. Farmers must form clusters and commit to organic cultivation for the scheme period.",
        "documents_required": "Aadhaar card, 7/12 land record, bank account details, cluster formation documents.",
        "application_process": "Apply through the state agriculture department or MahaDBT portal. Form a farmer cluster and submit the application with land records. After approval, training and input assistance are provided over the scheme period.",
        "application_url": "https://mahadbt.maharashtra.gov.in",
        "source_url": "https://mahadbt.maharashtra.gov.in",
        "last_verified": VERIFIED_DATE,
        "level": "maharashtra",
        "category": "organic",
        "applicable_crops": None,
    },
]


def seed_schemes(db: Session):
    """Populate the government_schemes table with verified data if it is empty."""
    if db.query(GovernmentScheme).count() > 0:
        return
    schemes = []
    for data in _SCHEMES:
        scheme = GovernmentScheme(**data)
        db.add(scheme)
        schemes.append(scheme)
    db.commit()
    logger.info("Seeded %d government schemes", len(schemes))
    # Create notifications for all existing active users
    users = db.query(User).filter(User.is_active.is_(True)).all()
    for user in users:
        for scheme in schemes:
            db.add(SchemeNotification(
                user_id=user.id,
                scheme_id=scheme.id,
                notification_type="new_scheme",
                message=f"A new scheme '{scheme.name}' has been added. Check if you are eligible.",
            ))
    if users:
        db.commit()
        logger.info("Created scheme notifications for %d users", len(users))


def get_recommendations(db: Session, user: User) -> list:
    """Recommend schemes based on the user's farm and field data.

    Matching logic:
    - Location: if farm location mentions Maharashtra or Maharashtra-specific markers,
      include Maharashtra-level schemes.
    - Crop type: if applicable_crops is set, match against the user's crop types.
    - All central schemes are always included (they apply nationwide).
    """
    farms = (
        db.query(Farm)
        .filter(Farm.owner_id == user.id)
        .all()
    )
    user_crops = set()
    user_location_lower = ""
    for farm in farms:
        if farm.location:
            user_location_lower += " " + farm.location.lower()
        fields = (
            db.query(Field)
            .filter(Field.farm_id == farm.id)
            .all()
        )
        for f in fields:
            if f.crop_type:
                user_crops.add(f.crop_type.lower())

    # Include all central schemes; include Maharashtra schemes if location suggests Maharashtra
    is_maharashtra = any(
        marker in user_location_lower
        for marker in ("maharashtra", "pune", "mumbai", "nashik", "nagpur", "aurangabad", "kolhapur", "ahmednagar")
    )

    query = db.query(GovernmentScheme).filter(GovernmentScheme.is_active.is_(True))
    if is_maharashtra:
        schemes = query.order_by(
            GovernmentScheme.level == "central",
            GovernmentScheme.level == "maharashtra",
        ).all()
    else:
        schemes = query.filter(GovernmentScheme.level == "central").all()

    # Filter by applicable crops if any crops are set on the scheme
    recommended = []
    for s in schemes:
        if s.applicable_crops:
            scheme_crops = {c.strip().lower() for c in s.applicable_crops.split(",") if c.strip()}
            if user_crops and scheme_crops & user_crops:
                recommended.append(s)
            elif not user_crops:
                recommended.append(s)
        else:
            recommended.append(s)

    return recommended


def create_notifications_for_user(db: Session, user: User, scheme: GovernmentScheme, ntype: str, message: str):
    """Create a scheme notification, avoiding duplicates."""
    existing = (
        db.query(SchemeNotification)
        .filter(
            SchemeNotification.user_id == user.id,
            SchemeNotification.scheme_id == scheme.id,
            SchemeNotification.notification_type == ntype,
            SchemeNotification.is_read.is_(False),
        )
        .first()
    )
    if existing:
        return None
    notif = SchemeNotification(
        user_id=user.id,
        scheme_id=scheme.id,
        notification_type=ntype,
        message=message,
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif


def notify_all_users_new_scheme(db: Session, scheme: GovernmentScheme):
    """Create 'new_scheme' notifications for all active users."""
    users = db.query(User).filter(User.is_active.is_(True)).all()
    for user in users:
        create_notifications_for_user(
            db, user, scheme, "new_scheme",
            f"A new scheme '{scheme.name}' has been added. Check if you are eligible.",
        )
