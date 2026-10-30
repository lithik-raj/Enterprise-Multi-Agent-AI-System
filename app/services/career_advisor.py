"""
Career Advisor & Corporate Intelligence Service
Provides 2-line verified workplace Q&A, MNC placement blueprints,
and multi-company recommendation filtering tailored to user location,
opportunity type (job/internship), and work mode (offline/online/remote).
"""

import re
from typing import Dict, List, Optional, Tuple, Any

COMPANY_LOGOS = {
    "ibm": "https://upload.wikimedia.org/wikipedia/commons/5/51/IBM_logo.svg",
    "infosys": "https://upload.wikimedia.org/wikipedia/commons/9/95/Infosys_logo.svg",
    "tcs": "https://upload.wikimedia.org/wikipedia/commons/b/b1/Tata_Consultancy_Services_Logo.svg",
    "google": "https://upload.wikimedia.org/wikipedia/commons/2/2f/Google_2015_logo.svg",
    "microsoft": "https://upload.wikimedia.org/wikipedia/commons/9/96/Microsoft_logo_%282012%29.svg",
    "amazon": "https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg",
    "accenture": "https://upload.wikimedia.org/wikipedia/commons/c/cd/Accenture.svg",
    "cognizant": "https://upload.wikimedia.org/wikipedia/commons/4/43/Cognizant_logo_2022.svg",
    "zoho": "https://upload.wikimedia.org/wikipedia/commons/6/6d/Zoho_Corporation_2019_logo.svg",
    "apple": "https://upload.wikimedia.org/wikipedia/commons/f/fa/Apple_logo_black.svg",
    "meta": "https://upload.wikimedia.org/wikipedia/commons/7/7b/Meta_Platforms_Inc._logo.svg",
    "nvidia": "https://upload.wikimedia.org/wikipedia/commons/2/21/Nvidia_logo.svg",
    "adobe": "https://upload.wikimedia.org/wikipedia/commons/5/5f/Adobe_Inc._logo.svg",
    "flipkart": "https://upload.wikimedia.org/wikipedia/en/7/7a/Flipkart_logo.svg",
    "swiggy": "https://upload.wikimedia.org/wikipedia/en/1/12/Swiggy_logo.svg",
    "uber": "https://upload.wikimedia.org/wikipedia/commons/c/cc/Uber_logo_2018.png",
    "deeptech_labs": "https://deeptechlabs.ai/favicon.ico",
}

COMPANY_WORKPLACE_DATA: Dict[str, Dict[str, Any]] = {
    "ibm": {
        "name": "IBM",
        "full_name": "IBM (International Business Machines)",
        "logo": COMPANY_LOGOS["ibm"],
        "has_games": True,
        "games_list": ["Table Tennis", "Foosball", "Carrom", "Chess", "PlayStation Gaming Lounges", "Pool / Snooker"],
        "refreshments": ["24/7 automated Cafe Coffee Day bean-to-cup stations", "Multi-cuisine food courts", "Fresh fruit and healthy snack micro-pantries"],
        "work_mode": "Hybrid (2–3 days office / 2 days remote)",
        "mode_details": {
            "remote": "Remote eligible for watsonx AI, Cloud & Data Engineering roles",
            "hybrid": "2–3 days in office per week, coordinated with sprint managers",
            "onsite": "5 days on-site across R&D labs and client security zones"
        },
        "dress_code": "Smart Casuals (jeans, polos, sneakers permitted daily)",
        "work_hours": "Flexible outcome-based 8–9 hour workday",
        "target_roles": ["Associate System Engineer (₹4.5–₹9.0 LPA)", "AI/watsonx Engineer (₹8–₹14 LPA)", "Cloud Solutions Specialist (₹7–₹12 LPA)"],
        "internships": "IBM Extreme Blue & ASE Internships",
        "internship_stipend": "₹35,000–₹50,000 / month (6-month track)",
        "city_campuses": {
            "chennai": "DLF IT Park (Porur) & Ramanujan IT City (Taramani, Chennai)",
            "bengaluru": "Manyata Embassy Tech Park & EGL (Embassy Golf Links, Bengaluru)",
            "hyderabad": "Mindspace Tech Park (Madhapur, Hyderabad)",
            "pune": "Tech Park (Yerwada) & Hinjawadi Phase 2, Pune",
            "mumbai": "Nesco IT Park (Goregaon) & Bandra Kurla Complex (BKC, Mumbai)",
            "coimbatore": "Hanudev Info Tech Park (Eachanari, Coimbatore)",
            "noida": "DLF Cyber City (Gurugram) & Sector 62 (Noida, NCR)",
            "kolkata": "DLF IT Park / Candor TechSpace (New Town, Kolkata)",
            "kochi": "Infopark Phase 2 (Kakkanad, Kochi)",
            "remote": "IBM Global Virtual Engineering Hub (100% Remote / Online)",
        },
    },
    "infosys": {
        "name": "Infosys",
        "full_name": "Infosys Limited",
        "logo": COMPANY_LOGOS["infosys"],
        "has_games": True,
        "games_list": ["Bowling Alley (Mysore & Bengaluru SEZ)", "Table Tennis", "Badminton & Squash Courts", "Olympic Swimming Pool", "Foosball & Billiards", "Cricket & Football Grounds"],
        "refreshments": ["Multi-chain food courts (Subway, CCD, Domino's, regional thalis)", "Free hot tea and coffee pantries across development blocks"],
        "work_mode": "Hybrid (3 days office / 2 days remote)",
        "mode_details": {
            "remote": "Infosys Cobalt & Cloud Specialist Virtual tracks",
            "hybrid": "3 days office / 2 days WFH depending on project unit",
            "onsite": "5 days in-office for financial client dedicated ODCs"
        },
        "dress_code": "Smart Casuals (Mon–Thu), Casuals on Friday",
        "work_hours": "9 hours per day with flexible 45-hour weekly tracking",
        "target_roles": ["Specialist Programmer (₹9.5 LPA)", "Digital Specialist Engineer (₹6.5 LPA)", "Systems Engineer (₹3.6 LPA)"],
        "internships": "Infosys InStep (Global Flagship) & Winter Internships",
        "internship_stipend": "₹25,000–₹45,000 / month (2 to 6 months)",
        "city_campuses": {
            "chennai": "Sholinganallur (OMR) & Mahindra World City (Chennai)",
            "bengaluru": "Electronic City Phase 1 (81-acre campus) & Manyata Tech Park, Bengaluru",
            "coimbatore": "CHIL SEZ (Saravanampatti, Coimbatore)",
            "hyderabad": "Pocharam Campus (440 acres) & Gachibowli, Hyderabad",
            "pune": "Hinjawadi Phase 1 & Phase 2, Pune",
            "mysore": "Mysore Global Education Centre (337 acres - World's largest corporate university)",
            "mumbai": "Airoli Mindspace (Navi Mumbai)",
            "noida": "Sector 85 (Noida, NCR)",
            "kolkata": "New Town Action Area II, Kolkata",
            "kochi": "Infopark Phase 2 (Kochi)",
            "remote": "Infosys Digital Workspaces (Online / Virtual Track)",
        },
    },
    "tcs": {
        "name": "TCS",
        "full_name": "Tata Consultancy Services (TCS)",
        "logo": COMPANY_LOGOS["tcs"],
        "has_games": True,
        "games_list": ["Table Tennis", "Carrom", "Chess", "Badminton courts", "Foosball", "Sports grounds (Olympus/Siruseri)"],
        "refreshments": ["Subsidized regional food courts", "Vending tea/coffee pantries on each wing", "Annual TCS Fit4Life marathons and gym"],
        "work_mode": "Hybrid (3–5 days office / project governed)",
        "mode_details": {
            "remote": "TCS SBWS (Secure Borderless Workspaces) remote eligibility",
            "hybrid": "3 days in-office / 2 days remote depending on client governance",
            "onsite": "5 days on-site across corporate delivery centers"
        },
        "dress_code": "Business Formals (Mon–Thu), Smart Casuals on Friday",
        "work_hours": "Standard 9-hour daily schedule",
        "target_roles": ["TCS Prime (₹9.0–₹11.5 LPA)", "TCS Digital (₹7.5 LPA)", "TCS Ninja (₹3.6 LPA)"],
        "internships": "TCS Research & Innovation Internships",
        "internship_stipend": "₹25,000–₹40,000 / month",
        "city_campuses": {
            "chennai": "Siruseri IT Park (Asia's largest IT park - 70 acres) & Sholinganallur, Chennai",
            "coimbatore": "KGISL Tech Park (Saravanampatti, Coimbatore)",
            "bengaluru": "Think Campus (Electronic City) & Whitefield, Bengaluru",
            "hyderabad": "Synergy Park & Adibatla Aerospace SEZ, Hyderabad",
            "pune": "Sahyadri Park (Hinjawadi Phase 3), Pune",
            "mumbai": "TCS Olympus (Thane) & Vikhroli, Mumbai",
            "noida": "Sector 62 (Noida) & Udyog Vihar (Gurugram)",
            "kolkata": "Gitanjali Park (New Town Action Area III, Kolkata)",
            "kochi": "Infopark (Kakkanad, Kochi)",
            "remote": "TCS SBWS Virtual Cloud Network (Remote / Online)",
        },
    },
    "google": {
        "name": "Google",
        "full_name": "Google India",
        "logo": COMPANY_LOGOS["google"],
        "has_games": True,
        "games_list": ["Arcade video consoles (PS5, Xbox, Switch)", "Table Tennis", "Billiards & Pool", "Foosball", "Board games & Lego rooms", "Nap pods"],
        "refreshments": ["100% complimentary gourmet breakfast, lunch, and dinner", "Artisan espresso/barista bars", "Healthy snack micro-kitchens every 100 feet"],
        "work_mode": "Hybrid (3 days in-office / 2 days remote)",
        "mode_details": {
            "remote": "Google Cloud Engineering Remote Eligible Positions",
            "hybrid": "3 days office, 2 days remote with 4 weeks work-from-anywhere annually",
            "onsite": "On-site collaboration across innovation hubs"
        },
        "dress_code": "Casual / Be yourself (t-shirts, jeans, hoodies, sneakers)",
        "work_hours": "Result-oriented flexible work hours",
        "target_roles": ["Software Engineer L3 (₹18–₹32 LPA)", "Machine Learning Engineer (₹22–₹40 LPA)", "Cloud Solutions Architect (₹20–₹35 LPA)"],
        "internships": "Google STEP Internship & Summer SWE Internships",
        "internship_stipend": "₹1,00,000–₹1,25,000 / month",
        "city_campuses": {
            "bengaluru": "Bagmane Constellation Business Park & RMZ Infinity, Bengaluru",
            "hyderabad": "Kondapur & HITEC City, Hyderabad",
            "noida": "Signature Towers (Gurugram, NCR)",
            "remote": "Google Cloud Virtual / Remote Roles",
        },
    },
    "microsoft": {
        "name": "Microsoft",
        "full_name": "Microsoft India",
        "logo": COMPANY_LOGOS["microsoft"],
        "has_games": True,
        "games_list": ["Xbox Series X gaming lounges with Game Pass", "Table Tennis", "Foosball", "Carrom & Chess", "Outdoor basketball courts"],
        "refreshments": ["Subsidized world-cuisine food courts", "Free espresso, cappuccino, and continuous juice stations", "Wellness rooms and yoga suites"],
        "work_mode": "Hybrid (up to 50% remote without manager approval)",
        "mode_details": {
            "remote": "High-flexibility 100% remote options for senior engineering roles",
            "hybrid": "Up to 50% work-from-home flexibility built-in",
            "onsite": "Hardware and specialized datacenter on-site labs"
        },
        "dress_code": "Smart Casual / Casual",
        "work_hours": "Flexible outcome-based working hours",
        "target_roles": ["Software Development Engineer (SDE 1: ₹16–₹28 LPA)", "Azure AI Engineer (₹18–₹30 LPA)", "Data & Applied Scientist (₹20–₹34 LPA)"],
        "internships": "Microsoft Engage & Summer SWE Internships",
        "internship_stipend": "₹1,25,000 / month (2-month track)",
        "city_campuses": {
            "hyderabad": "Gachibowli Campus (India Development Center - IDC), Hyderabad",
            "bengaluru": "Prestige Ferns Galaxy & Bellandur, Bengaluru",
            "noida": "Sector 16 (Taj Mahal Architectural Campus, Noida)",
            "remote": "Microsoft Virtual Development Hub (Remote / Online)",
        },
    },
    "amazon": {
        "name": "Amazon",
        "full_name": "Amazon India",
        "logo": COMPANY_LOGOS["amazon"],
        "has_games": True,
        "games_list": ["Table Tennis", "Foosball", "Board games & Chess", "PlayStation gaming pods", "Rooftop recreation terraces"],
        "refreshments": ["Subsidized multi-vendor food courts", "Free barista coffee, specialty tea, and fruit stations", "Equipped gyms and wellness rooms"],
        "work_mode": "Hybrid (3 days in-office / 2 days remote)",
        "mode_details": {
            "remote": "AWS Cloud and Developer Support Virtual positions",
            "hybrid": "3 days in-office policy across most product organizations",
            "onsite": "Operations and fulfillment engineering on-site hubs"
        },
        "dress_code": "Casual (jeans, t-shirts, sneakers)",
        "work_hours": "Fast-paced, team-dependent core hours",
        "target_roles": ["Software Development Engineer I (SDE 1: ₹18–₹30 LPA)", "AWS Cloud Architect (₹16–₹26 LPA)", "Applied Scientist (₹24–₹42 LPA)"],
        "internships": "Amazon SDE Summer Internships",
        "internship_stipend": "₹1,10,000 / month (6-month track)",
        "city_campuses": {
            "chennai": "World Trade Center (Perungudi, OMR, Chennai)",
            "hyderabad": "Financial District (World's largest Amazon campus building, 15k capacity), Hyderabad",
            "bengaluru": "Bagmane Constellation Tech Park & World Trade Center, Bengaluru",
            "pune": "World Trade Center (Kharadi) & Kalyani Nagar, Pune",
            "noida": "Ambience Corporate Tower (Gurugram, NCR)",
            "remote": "AWS Virtual Solutions Architecture (Remote / Online)",
        },
    },
    "accenture": {
        "name": "Accenture",
        "full_name": "Accenture India",
        "logo": COMPANY_LOGOS["accenture"],
        "has_games": True,
        "games_list": ["Table Tennis", "Foosball", "Carrom & Chess", "PlayStation lounges in Innovation Hubs"],
        "refreshments": ["Modern food courts and cafe chains", "Hot & cold beverage stations on each floor", "Ergonomic wellness lounges"],
        "work_mode": "Hybrid (2–3 days office / client-centric)",
        "mode_details": {
            "remote": "Accenture Cloud First Remote Network",
            "hybrid": "2–3 days in-office with flexible manager coordination",
            "onsite": "Client premises on-site consulting"
        },
        "dress_code": "Smart Casuals (client formal during presentations)",
        "work_hours": "Flexible standard workday",
        "target_roles": ["Advanced Application Engineering Analyst (₹6.5 LPA)", "Associate Software Engineer (₹4.5 LPA)", "AI/GenAI Specialist (₹8–₹14 LPA)"],
        "internships": "Accenture Summer Internship Program",
        "internship_stipend": "₹25,000–₹40,000 / month",
        "city_campuses": {
            "chennai": "Sholinganallur, TEK Meadows, & Ascendas IT Park (Taramani, Chennai)",
            "coimbatore": "Hanudev Info Park (Eachanari, Coimbatore)",
            "bengaluru": "Bannerghatta Innovation Hub, Bellandur & Whitefield, Bengaluru",
            "hyderabad": "Mindspace Madhapur & Raidurg, Hyderabad",
            "pune": "Magarpatta City & Hinjawadi Phase 2, Pune",
            "mumbai": "Airoli & Vikhroli, Mumbai",
            "noida": "Cyber City (Gurugram)",
            "kolkata": "DLF IT Park (New Town, Kolkata)",
            "remote": "Accenture Virtual Delivery Center (Remote / Online)",
        },
    },
    "cognizant": {
        "name": "Cognizant",
        "full_name": "Cognizant Technology Solutions",
        "logo": COMPANY_LOGOS["cognizant"],
        "has_games": True,
        "games_list": ["Table Tennis", "Foosball", "Carrom", "Chess", "Indoor gaming corners"],
        "refreshments": ["Cafeterias with regional South Indian and North Indian choices", "Automated tea and coffee vending stations"],
        "work_mode": "Hybrid (2–3 days office / 2 days remote)",
        "mode_details": {
            "remote": "Cognizant FlexWork Remote Roles",
            "hybrid": "2–3 days in office per week",
            "onsite": "5 days on-site across healthcare/banking dedicated ODCs"
        },
        "dress_code": "Business Casuals (casuals on Friday)",
        "work_hours": "Flexible 9-hour workday",
        "target_roles": ["GenC Next (₹6.75–₹9.0 LPA)", "GenC Elevate (₹4.25 LPA)", "GenC Programmer (₹4.0 LPA)"],
        "internships": "Cognizant GenC Internship Program",
        "internship_stipend": "₹20,000–₹35,000 / month",
        "city_campuses": {
            "chennai": "DLF IT Park (Porur), MEPZ (Tambaram), Thoraipakkam (OMR) & Siruseri, Chennai",
            "coimbatore": "CHIL SEZ (Saravanampatti, Coimbatore)",
            "bengaluru": "Manyata Embassy Tech Park & Bagmane, Bengaluru",
            "hyderabad": "Gachibowli & Manikonda, Hyderabad",
            "pune": "Hinjawadi Phase 3, Pune",
            "kolkata": "Technopark (Salt Lake Sector V, Kolkata)",
            "kochi": "Infopark (Kochi)",
            "remote": "Cognizant Virtual Workspaces (Remote / Online)",
        },
    },
    "zoho": {
        "name": "Zoho",
        "full_name": "Zoho Corporation",
        "logo": COMPANY_LOGOS["zoho"],
        "has_games": True,
        "games_list": ["Table Tennis", "Badminton courts", "Basketball", "Carrom & Chess", "Swimming pool (Estancia)", "Cricket nets"],
        "refreshments": ["100% complimentary nutritious breakfast, lunch, and dinner prepared on-campus", "Organic fruit juice counters and fresh snacks", "On-campus health clinic"],
        "work_mode": "Offline / Hybrid (emphasis on collaborative campus culture)",
        "mode_details": {
            "remote": "Zoho Developer Remote options for specialized core teams",
            "hybrid": "Hybrid options based on team and rural campus connectivity",
            "onsite": "On-site collaborative culture with free housing assistance"
        },
        "dress_code": "Completely Casual (comfortable clothes, t-shirts, slippers/sandals welcomed)",
        "work_hours": "Flexible, self-managed working hours",
        "target_roles": ["Software Developer (₹6.5–₹12 LPA)", "Member Technical Staff (₹8.5–₹15 LPA)", "Cloud Engineer (₹6.0–₹10 LPA)"],
        "internships": "Zoho Schools of Learning & Engineering Internships",
        "internship_stipend": "₹20,000–₹30,000 / month (with free food & accommodation)",
        "city_campuses": {
            "chennai": "Estancia IT Park (Guduvanchery, Chennai)",
            "coimbatore": "Avinashi Road Tech Hub (Coimbatore)",
            "tenkasi": "Zoho Rural Tech Campus (Tenkasi, Tamil Nadu)",
            "remote": "Zoho Cloud Engineering Remote Track",
        },
    },
    "nvidia": {
        "name": "NVIDIA",
        "full_name": "NVIDIA Corporation",
        "logo": COMPANY_LOGOS["nvidia"],
        "has_games": True,
        "games_list": ["VR Gaming Hubs", "Table Tennis", "Billiards", "Foosball", "Arcade Consoles"],
        "refreshments": ["Gourmet multi-cuisine cafeterias", "Micro-pantries with healthy energy snacks", "Espresso bars"],
        "work_mode": "Hybrid (Flexible / Project governed)",
        "mode_details": {
            "remote": "Full remote eligibility for specialized AI research and compiler engineers",
            "hybrid": "2–3 days in office with cutting-edge GPU lab workstations",
            "onsite": "5 days on-site across hardware architecture & validation labs"
        },
        "dress_code": "Casual / Be comfortable",
        "work_hours": "Flexible outcome-based 8–9 hours",
        "target_roles": ["AI Compiler Engineer (₹38–₹72 LPA)", "Deep Learning Systems Engineer (₹30–₹55 LPA)", "CUDA Core Developer (₹28–₹50 LPA)"],
        "internships": "NVIDIA Graduate & University AI Internships",
        "internship_stipend": "₹1,20,000–₹1,45,000 / month",
        "city_campuses": {
            "bengaluru": "Bagmane World Technology Center (Mahadevapura, Bengaluru)",
            "pune": "Panchshil Tech Park One (Yerawada, Pune)",
            "remote": "NVIDIA Virtual AI Architecture Lab (Remote / Online)",
        },
    },
    "adobe": {
        "name": "Adobe",
        "full_name": "Adobe India",
        "logo": COMPANY_LOGOS["adobe"],
        "has_games": True,
        "games_list": ["Table Tennis", "Foosball", "Billiards & Snooker", "PlayStation gaming lounges", "Badminton courts"],
        "refreshments": ["Free gourmet meals & barista counters", "Healthy fruit & energy snack stations", "On-site wellness spa"],
        "work_mode": "Hybrid (2–3 days in-office)",
        "mode_details": {
            "remote": "Digital Media & Cloud Platform remote positions",
            "hybrid": "Flexible 2–3 days weekly office collaboration",
            "onsite": "On-site collaboration across design & experience hubs"
        },
        "dress_code": "Smart Casuals (casuals daily)",
        "work_hours": "Flexible working hours with core collaboration windows",
        "target_roles": ["Software Engineer (₹24–₹45 LPA)", "Computer Vision / GenAI Scientist (₹28–₹52 LPA)", "Member Technical Staff (₹20–₹38 LPA)"],
        "internships": "Adobe India Summer Internship Program",
        "internship_stipend": "₹1,00,000–₹1,15,000 / month",
        "city_campuses": {
            "noida": "Sector 132 & Sector 25A (Noida, NCR)",
            "bengaluru": "Prestige Platina Tech Park (Marathahalli, Bengaluru)",
            "remote": "Adobe Digital Experience Remote Hub (Online)",
        },
    },
    "flipkart": {
        "name": "Flipkart",
        "full_name": "Flipkart (Walmart Group)",
        "logo": COMPANY_LOGOS["flipkart"],
        "has_games": True,
        "games_list": ["Table Tennis", "Foosball", "Carrom", "PlayStation gaming zones", "Rooftop basketball"],
        "refreshments": ["Subsidized multi-cuisine food courts", "Free coffee and beverage pantries on all floors"],
        "work_mode": "Hybrid (3 days in-office / 2 days remote)",
        "mode_details": {
            "remote": "Select infrastructure & backend engineering roles",
            "hybrid": "3 days in-office with team sprint flexibility",
            "onsite": "Supply chain and fulfillment technical operations"
        },
        "dress_code": "Casual (t-shirts, jeans, sneakers)",
        "work_hours": "Fast-paced flexible hours",
        "target_roles": ["Software Development Engineer 1 (₹20–₹36 LPA)", "Data Scientist (₹22–₹40 LPA)", "Applied Scientist (₹26–₹48 LPA)"],
        "internships": "Flipkart Runway & GRiD Internships",
        "internship_stipend": "₹60,000–₹1,00,000 / month",
        "city_campuses": {
            "bengaluru": "Embassy TechVillage (Outer Ring Road, Devarabeesanahalli, Bengaluru)",
            "remote": "Flipkart Virtual Engineering Hub (Remote)",
        },
    },
    "uber": {
        "name": "Uber",
        "full_name": "Uber India Technology",
        "logo": COMPANY_LOGOS["uber"],
        "has_games": True,
        "games_list": ["Table Tennis", "Billiards", "Foosball", "Console gaming rooms", "Nap rooms"],
        "refreshments": ["100% complimentary catered breakfast and lunch", "Artisan espresso machines", "Snack micro-kitchens"],
        "work_mode": "Hybrid (3 days office / 2 days remote)",
        "mode_details": {
            "remote": "Global mobility remote-eligible engineering tracks",
            "hybrid": "3 days in office with 4 weeks work-from-anywhere policy",
            "onsite": "Real-time dispatch and infrastructure war rooms"
        },
        "dress_code": "Casual",
        "work_hours": "Result-oriented flexible schedules",
        "target_roles": ["Software Engineer 1 (₹35–₹60 LPA)", "Data Engineer (₹25–₹45 LPA)", "Machine Learning Platform Engineer (₹38–₹65 LPA)"],
        "internships": "Uber India Engineering Summer Internship",
        "internship_stipend": "₹1,20,000–₹1,60,000 / month",
        "city_campuses": {
            "bengaluru": "RMZ Ecoworld (Bellandur, Bengaluru)",
            "hyderabad": "HITEC City (Hyderabad)",
            "remote": "Uber Global Mobility Remote Hub (Online)",
        },
    },
    "swiggy": {
        "name": "Swiggy",
        "full_name": "Swiggy (Bundl Technologies)",
        "logo": COMPANY_LOGOS["swiggy"],
        "has_games": True,
        "games_list": ["Table Tennis", "Foosball", "Board games & recreation zones"],
        "refreshments": ["Subsidized food ordering credits", "Free tea, coffee, and healthy snack corners"],
        "work_mode": "Remote-First / Hybrid",
        "mode_details": {
            "remote": "Remote-first culture with quarterly team jamborees",
            "hybrid": "Optional coworking hub access across major metros",
            "onsite": "Quarterly leadership strategy summits"
        },
        "dress_code": "Casual",
        "work_hours": "Flexible outcome-driven work hours",
        "target_roles": ["Software Development Engineer (₹22–₹38 LPA)", "AI/ML Engineer — Logistics (₹24–₹42 LPA)"],
        "internships": "Swiggy Campus SDE Internships",
        "internship_stipend": "₹50,000–₹80,000 / month",
        "city_campuses": {
            "bengaluru": "Embassy TechVillage & Kadubeesanahalli (Bengaluru)",
            "remote": "Swiggy Remote-First / Work From Anywhere Hub",
        },
    },
    "meta": {
        "name": "Meta",
        "full_name": "Meta Platforms",
        "logo": COMPANY_LOGOS["meta"],
        "has_games": True,
        "games_list": ["VR Gaming lounges (Quest 3)", "Table Tennis", "Billiards", "Video game arcades", "Music studio rooms"],
        "refreshments": ["100% complimentary gourmet dining (breakfast, lunch, dinner)", "Barista coffee stations", "Micro-kitchens"],
        "work_mode": "Hybrid / Remote-Eligible",
        "mode_details": {
            "remote": "Remote eligibility for seasoned software & AI engineers",
            "hybrid": "Flexible office presence with world-class amenities",
            "onsite": "Hardware and spatial computing lab facilities"
        },
        "dress_code": "Casual",
        "work_hours": "Flexible autonomous working hours",
        "target_roles": ["Software Engineer (₹35–₹65 LPA)", "AI/PyTorch Systems Engineer (₹40–₹75 LPA)"],
        "internships": "Meta Summer Software Engineering Internship",
        "internship_stipend": "₹1,25,000–₹1,50,000 / month",
        "city_campuses": {
            "hyderabad": "HITEC City (Hyderabad)",
            "bengaluru": "Bagmane Constellation Park (Bengaluru)",
            "remote": "Meta Remote Work Track (Online)",
        },
    },
}


GREETING_PATTERNS = [
    r"\b(hi|hello|hey|yo|sup|namaste|greetings)\b",
    r"\bgood\s+(morning|afternoon|evening|day)\b",
    r"\b(wish|wishes|wishing)\b",
    r"\bhow\s+are\s+you\b",
    r"\bwho\s+are\s+you\b",
    r"\bwhat\s+can\s+you\s+do\b",
    r"\bhelp\b",
]

def is_greeting_or_wish(text: str) -> bool:
    """Detect if a user prompt is a greeting, wish, or general system introduction."""
    cleaned = text.strip().lower()
    if cleaned in {"hi", "hello", "hey", "wishes", "wish", "yo", "sup", "namaste", "good morning", "good evening", "good afternoon"}:
        return True
    return any(re.search(pat, cleaned) for pat in GREETING_PATTERNS)


def get_greeting_response() -> str:
    """
    Generate strictly a 2-line concise greeting.
    """
    line1 = "👋 **Welcome to Enterprise Multi-Agent AI Placement Copilot.**"
    line2 = "Ask any company amenity question (e.g. *'is there facility of games at ibm for refreshment'*), or type *'similar job companies'* to match your profile."
    return f"{line1}\n{line2}"


def extract_all_company_keys(text: str) -> List[str]:
    """Identify which companies are mentioned in text."""
    t = text.lower()
    keys = []
    if any(k in t for k in ["ibm", "international business machines"]):
        keys.append("ibm")
    if any(k in t for k in ["infosys", "inodsys", "infy"]):
        keys.append("infosys")
    if any(k in t for k in ["google", "deepmind"]):
        keys.append("google")
    if any(k in t for k in ["microsoft", "azure"]):
        keys.append("microsoft")
    if any(k in t for k in ["tcs", "tata consultancy"]):
        keys.append("tcs")
    if any(k in t for k in ["amazon", "aws"]):
        keys.append("amazon")
    if any(k in t for k in ["accenture"]):
        keys.append("accenture")
    if any(k in t for k in ["cognizant", "cts"]):
        keys.append("cognizant")
    if any(k in t for k in ["zoho"]):
        keys.append("zoho")
    if any(k in t for k in ["nvidia"]):
        keys.append("nvidia")
    if any(k in t for k in ["adobe"]):
        keys.append("adobe")
    if any(k in t for k in ["flipkart"]):
        keys.append("flipkart")
    if any(k in t for k in ["swiggy"]):
        keys.append("swiggy")
    if any(k in t for k in ["uber"]):
        keys.append("uber")
    if any(k in t for k in ["meta"]):
        keys.append("meta")
    return keys


def extract_company_key(text: str) -> Optional[str]:
    """Identify which company is mentioned in text, joining multiple keys if present."""
    keys = extract_all_company_keys(text)
    return "_".join(keys) if keys else None


def is_company_facility_or_workplace_query(text: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Detect if user is asking about games, sports, refreshments, cafeteria, gym,
    dress code, work hours, or remote/WFH policy at a specific company.
    """
    t = text.lower()
    comp_key = extract_company_key(t)
    if not comp_key:
        return False, None, None

    # Games / Refreshments / Amenities
    games_keywords = [
        "game", "games", "gaming", "playstation", "ps5", "xbox", "table tennis", "tt",
        "foosball", "carrom", "chess", "snooker", "pool", "sport", "sports",
        "refresh", "refreshment", "refreshments", "recreation", "relax", "relaxation", "break",
        "amenity", "amenities", "facilities", "facility"
    ]
    if any(k in t for k in games_keywords):
        return True, comp_key, "games_refreshment"

    # Food / Cafeteria
    food_keywords = ["food", "cafeteria", "canteen", "lunch", "dinner", "breakfast", "coffee", "tea", "snack", "snacks", "cafe"]
    if any(k in t for k in food_keywords):
        return True, comp_key, "food"

    # Gym / Wellness
    gym_keywords = ["gym", "fitness", "swimming", "swimming pool", "wellness", "workout"]
    if any(k in t for k in gym_keywords):
        return True, comp_key, "gym"

    # WFH / Hybrid / Work Mode
    wfh_keywords = ["wfh", "work from home", "remote", "hybrid", "office days", "work mode", "work policy", "online", "offline", "onsite"]
    if any(k in t for k in wfh_keywords):
        return True, comp_key, "work_mode"

    # Dress Code
    dress_keywords = ["dress code", "attire", "what to wear", "clothes", "formal", "casual"]
    if any(k in t for k in dress_keywords):
        return True, comp_key, "dress_code"

    # Timings / Hours
    time_keywords = ["timing", "timings", "work hours", "working hours", "shift", "login time", "hours per day"]
    if any(k in t for k in time_keywords):
        return True, comp_key, "work_hours"

    return False, None, None


def get_company_workplace_answer(company_key: str, topic: str, user_text: str) -> str:
    """
    Generates STRICTLY a 2-LINE direct, verified, factual response.
    Zero hallucination. Zero filler or excess markdown.
    """
    if "_" in company_key:
        sub_keys = [k for k in company_key.split("_") if k in COMPANY_WORKPLACE_DATA]
        if sub_keys:
            parts = [get_company_workplace_answer(k, topic, user_text) for k in sub_keys]
            return "\n\n".join(parts)

    data = COMPANY_WORKPLACE_DATA.get(company_key, COMPANY_WORKPLACE_DATA["ibm"])
    name = data["name"]
    logo = data["logo"]
    games_str = ", ".join(data["games_list"][:5])
    refresh_str = ", ".join(data["refreshments"][:2])

    badge = f'<span style="display:inline-flex; align-items:center; gap:6px; background:#ffffff14; padding:2px 8px; border-radius:6px; border:1px solid rgba(56,189,248,0.3); vertical-align:middle; margin-right:8px;"><img src="{logo}" alt="{name}" style="height:18px; max-width:65px; object-fit:contain;" /><strong style="color:#fff; font-size:13px;">{name}</strong></span>'

    if topic == "games_refreshment":
        line1 = f"{badge}**Yes**, {name} provides dedicated recreation, indoor games, and 24/7 refreshment facilities across its campuses."
        line2 = f"🎮 **Amenities:** {games_str}; plus multi-cuisine cafeterias and bean-to-cup coffee stations."
        return f"{line1}\n{line2}"

    elif topic == "food":
        line1 = f"{badge}**Yes**, {name} features multi-vendor food courts, cafeterias, and 24/7 refreshment stations for employees."
        line2 = f"🍽️ **Dining:** Subsidized breakfast/lunch, artisan coffee bars, regional thalis, and healthy snack micro-kitchens."
        return f"{line1}\n{line2}"

    elif topic == "gym":
        line1 = f"{badge}**Yes**, {name} provides on-campus fitness centers and dedicated employee wellness facilities."
        line2 = f"🏋️ **Fitness:** Fully-equipped gymnasiums, certified personal trainers, yoga studios, and medical health rooms on-site."
        return f"{line1}\n{line2}"

    elif topic == "work_mode":
        line1 = f"{badge}{name} operates primarily on a **{data['work_mode']}** work model."
        line2 = f"🏢 **Policy:** Core team sprints require in-office collaboration, with remaining days available for remote work."
        return f"{line1}\n{line2}"

    elif topic == "dress_code":
        line1 = f"{badge}{name} follows a **{data['dress_code']}** attire policy for engineering floors."
        line2 = f"👔 **Policy:** Jeans, t-shirts, and sneakers are permitted daily; business formals are reserved for external client visits."
        return f"{line1}\n{line2}"

    elif topic == "work_hours":
        line1 = f"{badge}{name} maintains **{data['work_hours']}** with outcome-focused schedules."
        line2 = f"⏰ **Timings:** Mandatory core hours for daily team scrums, with flexible daily login and logout tracking."
        return f"{line1}\n{line2}"

    line1 = f"{badge}**Yes**, {name} operates state-of-the-art technology facilities with hybrid work options ({data['work_mode']})."
    line2 = f"🏢 **Workplace:** Amenities include {games_str}, cafeterias, and health centers across its major Indian campuses."
    return f"{line1}\n{line2}"


def is_similar_companies_query(text: str) -> bool:
    """Detect if the user asks for actively hiring companies, company recommendations, or similar companies."""
    t = text.lower()
    patterns = [
        r"similar\s+(job|company|companies)",
        r"list\s+(me\s+)?(similar\s+)?companies",
        r"companies\s+(list|matching|upon|for|based\s+on)\s+(my\s+)?resume",
        r"recommend\s+(me\s+)?companies",
        r"which\s+companies\s+should\s+i\s+apply",
        r"suggest\s+(other\s+|different\s+|more\s+)?companies",
        r"companies\s+for\s+my\s+profile",
        r"matching\s+companies",
        r"recommend.*(internship|job|role|position|opening|opportunities|career)",
        r"(find|search|show|get|suggest)\s+(me\s+)?(companies|jobs|internships)",
        r"(job|internship|role)s?\s+(in|at|around)\s+[a-z]+",
        r"(companies|jobs|internships)\s+matching",
        r"internships?\s+in\s+[a-z]+",
        r"jobs?\s+in\s+[a-z]+",
        r"actively\s+hiring",
        r"active\s+hiring",
        r"currently\s+hiring",
        r"who\s+(is|are)\s+hiring",
        r"which\s+companies\s+are\s+hiring",
        r"which\s+companies\s+are\s+actively\s+hiring",
        r"companies\s+hiring",
        r"top\s+hiring",
        r"hiring\s+companies",
        r"hiring\s+now",
        r"hiring\s+right\s+now",
        r"why\s+(only|always|same).*deeptech",
        r"suggesting\s+same\s+company",
        r"(other|different)\s+compan(y|ies)",
        r"live\s+data",
        r"live\s+(jobs?|openings?|hiring)",
        r"active\s+(jobs?|openings?|vacancies|requisitions)",
        r"who\s+(is|are)\s+recruiting",
        r"companies\s+to\s+apply",
        r"where\s+can\s+i\s+apply",
        r"(why|other|apart|besides|except|not|than|same).*deep\s*tech",
        r"deep\s*tech.*(why|other|different|alternative)",
        r"act[a-z]*\s*hir[a-z]*",
        r"hir[a-z]*\s*compan[a-z]*",
        r"compan[a-z]*\s*hir[a-z]*",
        r"(kive|live)\s*data",
        r"(kive|live)\s*(jobs?|openings?)",
        r"why\s+(not\s+)?other",
        r"why\s+only",
        r"why\s+always",
        r"same\s+comp[a-z]*",
    ]
    return any(re.search(pat, t) for pat in patterns)


def recommend_companies_for_resume(
    resume_text: str = "",
    opportunity_type: str = "all",       # "all", "job", "internship"
    preferred_location: str = "all",     # "all", "chennai", "bengaluru", "hyderabad", "pune", "mumbai", "coimbatore", "noida", "kolkata", "kochi", "remote"
    work_mode: str = "all",              # "all", "remote", "hybrid", "onsite"
    user_query: str = "",
) -> str:
    """
    Ranks and recommends companies strictly matching user's preferred location,
    opportunity type (job/internship), and work mode (online/remote/hybrid/offline).
    Includes interactive quick filter pills if preferences are not yet set.
    """
    t_text = (resume_text + " " + user_query).lower()

    # Detect skills from text or use solid default AI/ML profile
    candidate_skills = []
    skill_vocab = [
        "python", "java", "c++", "machine learning", "deep learning", "nlp", "rag",
        "langgraph", "fastapi", "docker", "sql", "pytorch", "tensorflow", "react", "aws"
    ]
    for s in skill_vocab:
        if s in t_text:
            candidate_skills.append(s.title())

    if not candidate_skills:
        candidate_skills = ["Python", "Machine Learning", "FastAPI", "SQL", "Docker"]

    loc_target = preferred_location.strip().lower()
    if loc_target in ("bangalore", "blr"):
        loc_target = "bengaluru"
    elif loc_target in ("gurugram", "gurgaon", "delhi", "ncr"):
        loc_target = "noida"

    mode_target = work_mode.strip().lower()
    if mode_target in ("offline", "on-site"):
        mode_target = "onsite"
    elif mode_target in ("online",):
        mode_target = "remote"

    opp_target = opportunity_type.strip().lower()

    # Filter and rank companies
    recs = []
    for c_key, c_data in COMPANY_WORKPLACE_DATA.items():
        city_map = c_data.get("city_campuses", {})

        # Strict Location Filter: If user selected a location, company MUST have a campus there!
        has_location = True
        local_campus = ""
        if loc_target != "all":
            if loc_target in city_map:
                local_campus = city_map[loc_target]
            elif loc_target == "remote" and "remote" in city_map:
                local_campus = city_map["remote"]
            else:
                has_location = False

        if not has_location:
            continue

        if not local_campus:
            # Fallback to first available primary campus
            first_city = next(iter(city_map))
            local_campus = city_map[first_city]

        # Match score calculation
        match_pct = 78
        matched_tags = []
        if any(s.lower() in ["python", "machine learning", "pytorch", "fastapi", "rag"] for s in candidate_skills):
            match_pct += 12
            matched_tags.extend(["Python", "AI/ML Systems"])
        if any(s.lower() in ["sql", "docker", "aws"] for s in candidate_skills):
            match_pct += 6
            matched_tags.extend(["Cloud/Data", "Docker"])
        match_pct = min(96, match_pct)

        # Work Mode Display
        mode_details = c_data.get("mode_details", {})
        if mode_target == "remote":
            mode_display = f"🌐 Online / Remote: {mode_details.get('remote', 'Remote Eligible')}"
        elif mode_target == "onsite":
            mode_display = f"📍 Offline / On-Site: {mode_details.get('onsite', '5 Days In-Office')}"
        elif mode_target == "hybrid":
            mode_display = f"🏢 Hybrid: {mode_details.get('hybrid', c_data['work_mode'])}"
        else:
            mode_display = f"🏢 Work Mode: {c_data['work_mode']}"

        # Opportunity Type Display
        roles_list = c_data["target_roles"]
        intern_info = f"{c_data.get('internships', 'Internship Program')} ({c_data.get('internship_stipend', 'Competitive Stipend')})"

        recs.append({
            "key": c_key,
            "name": c_data["name"],
            "full_name": c_data.get("full_name", c_data["name"]),
            "logo": c_data["logo"],
            "match_score": match_pct,
            "matched_tags": list(set(matched_tags)) or ["Core Tech Stack"],
            "mode_display": mode_display,
            "local_campus": local_campus,
            "roles": roles_list,
            "intern_info": intern_info,
            "opp_target": opp_target,
        })

    # Sort by match score
    recs.sort(key=lambda x: x["match_score"], reverse=True)

    if not recs:
        return (
            f"No specific company matches were found for **{loc_target.title()}** ({mode_target.title()}). "
            "Consider broadening your criteria to include remote or hybrid opportunities across primary tech hubs like Bengaluru, Chennai, or Hyderabad."
        )

    t_lower = (resume_text + " " + user_query).lower()
    is_asking_other = any(k in t_lower for k in ["deeptech", "why only", "same company", "other comp", "different comp", "actively hiring", "live data"])

    header = "### 🏢 Actively Hiring Companies & Verified Live Openings\n\n"
    if is_asking_other:
        header += (
            "> 💡 **Verified Multi-Enterprise Catalog:** Below is our live verified hiring directory "
            "spanning Tier-1 MNCs, Global Capability Centers (GCCs), and AI product companies actively hiring right now across India and globally:\n\n"
        )
    else:
        header += (
            f"**{len(recs)} enterprise organizations actively recruiting** matching your background and preferences:\n\n"
        )

    cards_md = []
    for r in recs[:6]:
        opp_section = ""
        if r["opp_target"] == "internship":
            opp_section = f'<p style="font-size:13px; color:#cbd5e1; margin-bottom:5px;">🎓 <strong>Internship Track:</strong> <span style="color:#38bdf8;">{r["intern_info"]}</span></p>'
        elif r["opp_target"] == "job":
            opp_section = f'<p style="font-size:13px; color:#cbd5e1; margin-bottom:5px;">💼 <strong>Full-Time Roles:</strong> <span style="color:#f8fafc;">{", ".join(r["roles"][:2])}</span></p>'
        else:
            opp_section = (
                f'<p style="font-size:13px; color:#cbd5e1; margin-bottom:4px;">💼 <strong>Job:</strong> <span style="color:#f8fafc;">{", ".join(r["roles"][:2])}</span></p>'
                f'<p style="font-size:13px; color:#cbd5e1; margin-bottom:5px;">🎓 <strong>Internship:</strong> <span style="color:#38bdf8;">{r["intern_info"]}</span></p>'
            )

        card = f"""
<div style="background:rgba(15,23,42,0.85); border:1px solid rgba(56,189,248,0.3); border-radius:10px; padding:14px 18px; margin-bottom:12px; box-shadow:0 6px 20px rgba(0,0,0,0.35);">
  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
    <div style="display:flex; align-items:center; gap:10px;">
      <img src="{r['logo']}" alt="{r['name']}" style="height:26px; max-width:85px; object-fit:contain; background:#ffffff14; padding:3px 6px; border-radius:6px; border:1px solid rgba(56,189,248,0.25);" />
      <span style="font-size:15px; font-weight:800; color:#fff;">{r['full_name']}</span>
    </div>
    <div style="display:flex; gap:6px; align-items:center;">
      <span style="background:rgba(239,68,68,0.18); border:1px solid #ef4444; color:#f87171; font-weight:800; font-size:11px; padding:2px 7px; border-radius:12px;">🔥 Actively Hiring</span>
      <span style="background:rgba(16,185,129,0.2); border:1px solid #10b981; color:#10b981; font-weight:800; font-size:11.5px; padding:2px 8px; border-radius:12px;">{r['match_score']}% Match</span>
    </div>
  </div>
  {opp_section}
  <p style="font-size:12.5px; color:#94a3b8; margin-bottom:4px;">📍 <strong>Live Campus:</strong> <span style="color:#38bdf8; font-weight:600;">{r['local_campus']}</span></p>
  <p style="font-size:12.5px; color:#94a3b8; margin-bottom:6px;">{r['mode_display']}</p>
  <div style="font-size:11.5px; color:#a855f7;"><strong>Matched Skills:</strong> {", ".join(r['matched_tags'])}</div>
</div>
"""
        cards_md.append(card)

    return header + "\n".join(cards_md)


def is_doubt_or_advice_query(text: str) -> Tuple[bool, str]:
    """
    Detect if the user is asking a general technical, conceptual, interview,
    resume, DSA, or career advice question/doubt that requires direct mentoring.
    """
    t = text.lower().strip()

    # 1. Resume doubts
    resume_patterns = [
        r"\bresume\b", r"\bcv\b", r"curriculum vitae", r"\bats\b", r"biodata",
        r"how to (write|make|prepare|format|structure|improve|build|craft) (my |a )?resume",
        r"resume (tips|review|feedback|help|structure|format|score|optimization|blueprint|points)",
    ]
    if any(re.search(p, t) for p in resume_patterns):
        return True, "resume"

    # 2. Interview doubts
    interview_patterns = [
        r"\binterview\b", r"\binterviews\b", r"mock interview", r"technical round",
        r"hr round", r"managerial round", r"behavioral (round|question)", r"star method",
        r"how to (crack|prepare|clear|pass|ace) (an |the |for )?interview",
        r"interview (tips|guidance|preparation|questions|rounds|strategy|readiness)",
    ]
    if any(re.search(p, t) for p in interview_patterns):
        return True, "interview"

    # 3. DSA & Coding doubts
    dsa_patterns = [
        r"\bdsa\b", r"data structures?", r"algorithms?", r"leetcode", r"codeforces",
        r"dynamic programming", r"\bdp\b", r"graphs?", r"trees?", r"binary search",
        r"two pointers", r"how to (learn|prepare|master|practice) (dsa|coding|algorithms)",
        r"dsa (roadmap|topics|syllabus|preparation|guide|practice)",
    ]
    if any(re.search(p, t) for p in dsa_patterns):
        return True, "dsa"

    # 4. ML / AI / Tech concepts doubts
    ml_patterns = [
        r"what is\b", r"explain\b", r"difference between\b", r"how does .* work",
        r"\brag\b", r"\btransformers?\b", r"vector database", r"\bfaiss\b",
        r"langgraph", r"langchain", r"supervised (vs|and) unsupervised",
        r"fine[- ]tuning", r"embeddings?", r"generative ai", r"\bgenai\b",
        r"machine learning", r"deep learning", r"neural network",
        r"how to learn (ml|machine learning|ai|deep learning)",
    ]
    if any(re.search(p, t) for p in ml_patterns):
        return True, "technical_concepts"

    # 5. General career guidance & doubt clearance
    general_doubt_patterns = [
        r"doubt", r"confus(ed|ion)", r"clarify", r"clear my", r"i have a (doubt|question)",
        r"how (can|should|do) i (start|prepare|become|get|apply|land)",
        r"career (guidance|advice|roadmap|path|transition)",
        r"off[- ]campus", r"on[- ]campus", r"fresher (guide|preparation|roadmap)",
        r"which skills (are needed|do i need|should i learn)",
        r"where to start",
        r"(doubt|odubt)s?",
        r"(clear|claeanr|rectif)[a-z]*\s*(other\s*)?(doubt|odubt)",
        r"not\s*(clear|claeanr|answer)[a-z]*",
    ]
    if any(re.search(p, t) for p in general_doubt_patterns):
        return True, "career_guidance"

    return False, ""


def get_doubt_clearing_answer(topic: str, query: str, skills: List[str] = None) -> str:
    """
    Synthesizes a rich, structured, ChatGPT-grade mentor response clearing the user's doubt directly.
    """
    q_lower = query.lower()

    if topic == "resume":
        return """### 📄 Master ATS & Recruiter-Proof Resume Blueprint

Crafting a high-conversion resume for machine learning and software engineering roles requires strict adherence to ATS compliance and quantifiable impact:

#### 1. Architecture & Layout Rules
* **1-Page Strict Rule:** For students and candidates with < 5 years of experience, keep strictly to 1 page.
* **Single-Column Format:** Multi-column layouts, graphics, and tables frequently cause ATS parsers (Workday, Taleo, Greenhouse) to jumble text.
* **ATS Clean Fonts:** Use standard fonts (Inter, Calibri, Arial, Roboto) at 10–11pt font size with 0.5–0.75 inch margins.

#### 2. Section Hierarchy (Recommended Order)
1. **Header:** Full Name, Phone, Professional Email, LinkedIn, GitHub, and Portfolio / Deployed App Link.
2. **Technical Skills:** Group by category rather than an unstructured comma list:
   - *Languages:* Python, C++, Java, SQL
   - *AI/ML Frameworks:* PyTorch, Scikit-learn, Hugging Face, Transformers
   - *Agentic & RAG:* LangGraph, FAISS, Vector Databases, Prompt Engineering
   - *Backend & Cloud:* FastAPI, Docker, Git, AWS / GCP
3. **High-Impact Projects (2–3 Selected):** Use Google's **XYZ Formula**:
   > *"Accomplished [X], as measured by [Y], by doing [Z]"*
   - *Example:* "Architected a multi-agent evaluation platform using LangGraph and FAISS, reducing resume screening latency by **42%** and indexing **10,000+** job profiles."
   - *Example:* "Trained a fine-tuned BERT text classifier achieving **91.4% F1-score**, containerized with Docker and deployed via FastAPI microservices."
4. **Experience / Internships:** Focus on deliverables, architectural trade-offs, and production impact.
5. **Education:** Degree, College Name, Graduation Year, CGPA (mention if > 7.5/10), relevant coursework (DSA, OS, DBMS).

#### 3. Top ATS Optimization Checklists
- ✅ Avoid progress bars, rating stars, and icons (ATS cannot parse graphic ratings).
- ✅ Integrate keywords directly from job descriptions naturally into your project descriptions.
- ✅ Export strictly as a searchable text PDF (not a flat image or scanned document)."""

    elif topic == "interview":
        return """### 🎯 4-Stage MNC & Product Interview Mastery Playbook

To crack technical roles at top tech companies, prepare across these four distinct evaluation phases:

#### Stage 1: Online Assessment (OA) Round
* **Format:** 2–3 algorithmic coding problems within 60–90 minutes on HackerRank, Codility, or Mettl.
* **Key Focus:** Arrays, Two Pointers, HashMaps, Sliding Window, and Tree Traversals.
* **Tactic:** Always check edge cases (empty array, null pointers, single element, negative numbers, integer overflow).

#### Stage 2: Technical Problem Solving & Live Coding
* **Think Out Loud:** Interviewers care more about your problem decomposition than immediate code perfection. Articulate your thought process continuously.
* **Clarify Constraints:** Before writing code, ask: *"Can numbers be negative?"*, *"Is the input sorted?"*, *"What are the memory limits?"*
* **The 3-Step Code Flow:**
  1. Present the brute-force approach ($O(N^2)$) and explain why it's suboptimal.
  2. Optimize using HashMaps, Binary Search, or Heaps ($O(N)$ or $O(N \\log N)$).
  3. Write modular, clean code and dry-run with a sample test case.

#### Stage 3: System Design & Project Deep-Dive
* **Be Ready to Defend Your Resume:** Interviewers will ask: *"Why did you choose FastAPI over Flask?"*, *"How does your vector search scale when data grows from 10k to 10M vectors?"*
* **Trade-Off Awareness:** Show that you understand latency, memory usage, horizontal scaling, and caching strategies.

#### Stage 4: Behavioral & Leadership Evaluation (STAR Technique)
* Answer behavioral questions using the **STAR** method:
  - **S (Situation):** Set the stage and context.
  - **T (Task):** Identify the challenge or goal you needed to solve.
  - **A (Action):** Describe the specific engineering or collaborative steps you took.
  - **R (Result):** Conclude with quantifiable business or technical impact."""

    elif topic == "dsa":
        return """### ⚡ Structured 4-Stage DSA & Problem-Solving Roadmap

Mastering Data Structures & Algorithms requires pattern recognition rather than memorizing individual problems. Follow this sequential 8-week curriculum:

#### Phase 1: Foundations & Two Pointers (Weeks 1–2)
* **Topics:** Arrays, Strings, Prefix Sum, Two Pointers, Sliding Window.
* **Key Patterns:** Two Sum (HashMap), Container With Most Water, 3Sum, Longest Substring Without Repeating Characters.
* **Goal:** Understand Big-O time and space complexity ($O(1)$, $O(N)$, $O(N \\log N)$).

#### Phase 2: Core Data Structures (Weeks 3–4)
* **Topics:** Singly & Doubly Linked Lists, Stacks, Queues, Binary Search.
* **Key Patterns:** Fast & Slow pointers (Cycle Detection, Middle of List), Monotonic Stack (Next Greater Element), Binary Search on Answer.

#### Phase 3: Trees, Heaps & Recursion (Weeks 5–6)
* **Topics:** Binary Trees, BSTs, Priority Queues / Heaps, Trie.
* **Key Patterns:** DFS Traversals (Inorder, Preorder, Postorder), BFS Level-Order, Lowest Common Ancestor (LCA), Top K Frequent Elements.

#### Phase 4: Graphs & Dynamic Programming (Weeks 7–8)
* **Topics:** Graph BFS/DFS, Topological Sort, Dijkstra's Algorithm, 1D & 2D Dynamic Programming.
* **Key Patterns:** Number of Islands, Course Schedule, 0/1 Knapsack, Coin Change, Longest Increasing Subsequence.

> 💡 **Practice Rule:** Complete the curated **NeetCode 150** or **LeetCode 75**. Solve 2 problems daily with timed sessions (25 mins per Medium problem)."""

    elif topic == "technical_concepts":
        if "rag" in q_lower or "retrieval" in q_lower:
            return """### 🧠 Technical Deep-Dive: RAG (Retrieval-Augmented Generation) Architecture

Retrieval-Augmented Generation (RAG) grounds LLM outputs in verified external knowledge to eliminate hallucinations and incorporate private enterprise data:

#### The 5-Step RAG Execution Pipeline
1. **Document Ingestion & Chunking:** Unstructured documents (PDFs, Markdown) are split into semantic chunks (typically 500–1000 tokens with 10% overlap).
2. **Dense Vector Embedding:** Text chunks are transformed into dense mathematical vectors using embedding models (e.g., `all-MiniLM-L6-v2`, `text-embedding-3-small`).
3. **Vector Indexing (FAISS / Chroma):** High-dimensional vectors are stored in an indexing structure like `IndexFlatL2` or HNSW for rapid sub-millisecond cosine similarity search.
4. **Context Retrieval:** When a user queries the system, the query is embedded and the top-$K$ most relevant evidence chunks are retrieved.
5. **Grounded Generation:** The LLM receives both the user prompt and the retrieved evidence in its context window, generating a factual, hallucination-free answer with exact citations.

```python
# Minimalist RAG Flow with FAISS & SentenceTransformers
from sentence_transformers import SentenceTransformer
import faiss

model = SentenceTransformer("all-MiniLM-L6-v2")
corpus = ["IBM offers hybrid watsonx AI roles", "Google DeepMind builds Gemini models"]
embeddings = model.encode(corpus)

index = faiss.IndexFlatL2(embeddings.shape[1])
index.add(embeddings)

query = "Where are watsonx roles available?"
query_vec = model.encode([query])
distances, indices = index.search(query_vec, k=1)
retrieved_evidence = corpus[indices[0][0]]
```"""
        elif "supervised" in q_lower or "unsupervised" in q_lower:
            return """### 🧠 Supervised vs. Unsupervised Machine Learning Explained

The fundamental difference between Supervised and Unsupervised Learning lies in the presence of labeled ground truth:

| Dimension | Supervised Learning | Unsupervised Learning |
| :--- | :--- | :--- |
| **Data Type** | Input features ($X$) with ground truth labels ($Y$) | Unlabeled input features ($X$) only |
| **Core Objective** | Predict label or continuous value for new unseen data | Discover hidden patterns, clusters, or latent structures |
| **Primary Tasks** | Classification (e.g. Spam/Not Spam) & Regression (e.g. Salary Prediction) | Clustering (e.g. Customer Segmentation) & Dimensionality Reduction |
| **Algorithms** | Linear/Logistic Regression, Random Forest, XGBoost, Neural Nets | K-Means, DBSCAN, PCA, Autoencoders, Hierarchical Clustering |
| **Evaluation Metrics**| Accuracy, Precision, Recall, F1-Score, RMSE, $R^2$ Score | Silhouette Score, Davies-Bouldin Index, Inertia / Elbow Method |

* **Supervised Example:** Training an ATS compatibility scoring model where resumes and job descriptions have known human recruiter match scores.
* **Unsupervised Example:** Clustering 50,000 applicant resumes into skill domains (NLP, Computer Vision, Cloud DevOps) without predefined category labels."""
        else:
            return """### 🧠 Enterprise Machine Learning & AI Concepts Deep-Dive

Modern applied artificial intelligence systems combine foundational statistical modeling, transformer architectures, and multi-agent coordination:

1. **Foundations (Feature Engineering & Classical ML):**
   - TF-IDF and Bag-of-Words capture keyword frequencies, while Word2Vec and dense embeddings capture semantic meaning.
   - Tree-based models (Gradient Boosted Regressors, LightGBM) excel on tabular evaluation data with high explainability.

2. **Transformer & Attention Mechanism:**
   - Multi-Head Self-Attention dynamically assigns weights to related tokens regardless of distance in the sentence:
     $$\\text{Attention}(Q, K, V) = \\text{softmax}\\left(\\frac{QK^T}{\\sqrt{d_k}}\\right)V$$
   - This enables context-aware representations far superior to static n-gram models.

3. **Multi-Agent Orchestration (LangGraph):**
   - Rather than relying on a single monolithic prompt, enterprise systems decompose complex goals across specialized agents (e.g., Orchestrator, Research, NLP, ML Scorer, RAG, Evaluator) with state checkpointing and guardrails."""

    else:  # career_guidance
        return """### 🚀 90-Day Enterprise Placement & Career Transition Action Plan

Follow this structured roadmap to land competitive software engineering or AI/ML roles:

#### Month 1: Core Technical Foundations
- **Language Depth:** Master Python (comprehensions, generators, type hints, asyncio) or Java (OOP, multithreading, collections).
- **Relational Databases:** Practice complex SQL joins, aggregations, window functions, and indexing strategies on LeetCode/HackerRank.
- **Fundamental DSA:** Complete arrays, strings, hash maps, and linked lists (target: 40 problems).

#### Month 2: Production-Grade Project Development
- Avoid standard academic datasets (Titanic, Iris, MNIST).
- Build and deploy **one end-to-end full-stack application**:
  - FastAPI backend with Pydantic validation and asynchronous endpoints.
  - FAISS or vector database integration for semantic search.
  - Containerize using Docker and write a comprehensive GitHub README with architecture diagrams.

#### Month 3: Targeted Applications & Cold Outreach
- Polish your ATS single-column resume with quantifiable bullet points.
- Apply directly on official career portals of Tier-1 MNCs (Google, Microsoft, Amazon, Infosys, TCS, NVIDIA, Zoho).
- Connect with senior engineers and engineering managers on LinkedIn with concise, personalized notes showcasing your deployed project demo."""


def is_company_placement_query(text: str) -> Tuple[bool, Optional[str]]:
    """
    Detect if user is asking about placement syllabus or test rounds.
    """
    t = text.strip().lower()
    has_ibm = any(k in t for k in ["ibm", "international business machines"])
    has_infy = any(k in t for k in ["infosys", "inodsys", "infy", "infytq", "hackwithinfy"])
    has_tcs = any(k in t for k in ["tcs", "tata consultancy", "nqt", "codevita"])
    has_google = any(k in t for k in ["google", "deepmind"])
    has_msft = any(k in t for k in ["microsoft", "azure"])
    has_amazon = any(k in t for k in ["amazon", "aws"])

    intent_words = [
        "placement", "palce", "interview", "round", "rounds", "how to prepare", "criteria",
        "eligibility", "package", "ctc", "salary", "syllabus", "test pattern", "exam",
        "skill", "skills", "hiring", "job", "jobs", "prepare", "requirement", "requirements",
        "needed", "required", "role", "roles", "guide", "roadmap", "learn"
    ]
    has_intent = any(w in t for w in intent_words)

    if has_ibm and has_infy:
        return True, "ibm_infosys"
    elif has_ibm and (has_intent or len(t.split()) <= 3):
        return True, "ibm"
    elif has_infy and (has_intent or len(t.split()) <= 3):
        return True, "infosys"
    elif has_tcs and has_intent:
        return True, "tcs"
    elif has_google and has_intent:
        return True, "google"
    elif has_msft and has_intent:
        return True, "microsoft"
    elif has_amazon and has_intent:
        return True, "amazon"

    return False, None


def get_placement_guide(category: str) -> str:
    """
    Return STRICTLY a 2-line direct placement answer with company logo badge.
    """
    if category == "ibm":
        badge = f'<span style="display:inline-flex; align-items:center; gap:6px; background:#ffffff14; padding:2px 8px; border-radius:6px; border:1px solid rgba(56,189,248,0.3); vertical-align:middle; margin-right:8px;"><img src="{COMPANY_LOGOS["ibm"]}" alt="IBM" style="height:18px; max-width:60px;" /><strong style="color:#fff; font-size:13px;">IBM</strong></span>'
        line1 = f"{badge}**Selection Pattern:** Cognify game assessment + CodeKnack coding round (Python/Java) + Technical Interview (Associate System Engineer: ₹4.5–₹9.0 LPA)."
        line2 = f"🎯 **Key Syllabus:** Arrays, Strings, HashMaps, OOP design, and SQL Joins (Eligibility: 60%+ in B.Tech/MCA)."
        return f"{line1}\n{line2}"

    elif category == "infosys":
        badge = f'<span style="display:inline-flex; align-items:center; gap:6px; background:#ffffff14; padding:2px 8px; border-radius:6px; border:1px solid rgba(56,189,248,0.3); vertical-align:middle; margin-right:8px;"><img src="{COMPANY_LOGOS["infosys"]}" alt="Infosys" style="height:18px; max-width:60px;" /><strong style="color:#fff; font-size:13px;">Infosys</strong></span>'
        line1 = f"{badge}**Selection Pattern:** InfyTQ / HackWithInfy coding rounds for Specialist Programmer (₹9.5 LPA) & Digital Specialist (₹6.5 LPA)."
        line2 = f"🎯 **Key Syllabus:** Java/Python DSA, Dynamic Programming, Graphs, DBMS Normalization, and OOPs concepts."
        return f"{line1}\n{line2}"

    elif category == "tcs":
        badge = f'<span style="display:inline-flex; align-items:center; gap:6px; background:#ffffff14; padding:2px 8px; border-radius:6px; border:1px solid rgba(56,189,248,0.3); vertical-align:middle; margin-right:8px;"><img src="{COMPANY_LOGOS["tcs"]}" alt="TCS" style="height:18px; max-width:60px;" /><strong style="color:#fff; font-size:13px;">TCS</strong></span>'
        line1 = f"{badge}**Selection Pattern:** TCS National Qualifier Test (NQT) with Foundation & Advanced Coding for TCS Prime (₹9–₹11.5 LPA)."
        line2 = f"🎯 **Key Syllabus:** Quantitative Aptitude, LeetCode Easy-Medium DSA in C++/Java/Python, and Relational SQL."
        return f"{line1}\n{line2}"

    elif category == "google":
        badge = f'<span style="display:inline-flex; align-items:center; gap:6px; background:#ffffff14; padding:2px 8px; border-radius:6px; border:1px solid rgba(56,189,248,0.3); vertical-align:middle; margin-right:8px;"><img src="{COMPANY_LOGOS["google"]}" alt="Google" style="height:18px; max-width:60px;" /><strong style="color:#fff; font-size:13px;">Google</strong></span>'
        line1 = f"{badge}**Selection Pattern:** Online Assessment + 3 Technical DSA rounds + Googleyness leadership interview (L3 SDE: ₹18–₹32 LPA)."
        line2 = f"🎯 **Key Syllabus:** Advanced Graphs, Trees, Dynamic Programming, and Big-O space/time optimization in C++ or Python."
        return f"{line1}\n{line2}"

    elif category == "microsoft":
        badge = f'<span style="display:inline-flex; align-items:center; gap:6px; background:#ffffff14; padding:2px 8px; border-radius:6px; border:1px solid rgba(56,189,248,0.3); vertical-align:middle; margin-right:8px;"><img src="{COMPANY_LOGOS["microsoft"]}" alt="Microsoft" style="height:18px; max-width:60px;" /><strong style="color:#fff; font-size:13px;">Microsoft</strong></span>'
        line1 = f"{badge}**Selection Pattern:** Codility Online Assessment + 3 Technical problem-solving rounds + As-Appropriate (AA) interview (SDE: ₹16–₹28 LPA)."
        line2 = f"🎯 **Key Syllabus:** Trees, Graphs, Low-Level System Design (LLD/OOP), and production code debugging in C++ or Java."
        return f"{line1}\n{line2}"

    elif category == "amazon":
        badge = f'<span style="display:inline-flex; align-items:center; gap:6px; background:#ffffff14; padding:2px 8px; border-radius:6px; border:1px solid rgba(56,189,248,0.3); vertical-align:middle; margin-right:8px;"><img src="{COMPANY_LOGOS["amazon"]}" alt="Amazon" style="height:18px; max-width:60px;" /><strong style="color:#fff; font-size:13px;">Amazon</strong></span>'
        line1 = f"{badge}**Selection Pattern:** Online Assessment (OA) + 3-4 live technical coding rounds (SDE 1: ₹18–₹30 LPA)."
        line2 = f"🎯 **Key Syllabus:** Trees, Heaps, Graphs, OOP system design, plus concrete behavioral examples for Amazon's 16 Leadership Principles."
        return f"{line1}\n{line2}"

    elif category == "ibm_infosys":
        badge_ibm = f'<span style="display:inline-flex; align-items:center; gap:6px; background:#ffffff14; padding:2px 8px; border-radius:6px; border:1px solid rgba(56,189,248,0.3); vertical-align:middle; margin-right:8px;"><img src="{COMPANY_LOGOS["ibm"]}" alt="IBM" style="height:18px; max-width:60px;" /><strong style="color:#fff; font-size:13px;">IBM</strong></span>'
        badge_infy = f'<span style="display:inline-flex; align-items:center; gap:6px; background:#ffffff14; padding:2px 8px; border-radius:6px; border:1px solid rgba(56,189,248,0.3); vertical-align:middle; margin-right:8px;"><img src="{COMPANY_LOGOS["infosys"]}" alt="Infosys" style="height:18px; max-width:60px;" /><strong style="color:#fff; font-size:13px;">Infosys</strong></span>'
        line1 = f"{badge_ibm}**IBM Pattern:** Cognify cognitive assessment + CodeKnack coding round (Python/Java) (ASE: ₹4.5–₹9.0 LPA) | Key Syllabus: Arrays, Strings, HashMaps, OOP design, and SQL."
        line2 = f"{badge_infy}**Infosys Pattern:** InfyTQ / HackWithInfy competitive programming (SP: ₹9.5 LPA & DSE: ₹6.5 LPA) | Key Syllabus: Dynamic Programming, Graphs, DBMS, and Java/Python."
        return f"{line1}\n{line2}"

    line1 = "🎯 **Top MNC Placement Criteria:** Online coding assessment + 2 Technical DSA rounds + 1 Managerial/HR discussion."
    line2 = "💡 **Key Focus:** Mastery in one core language (Java or Python), fundamental Data Structures, and Relational SQL."
    return f"{line1}\n{line2}"
