"""
Pure utility functions for ShieldDB — zero Playwright / web-scraper dependencies.
Safe to import from Vercel serverless functions.
"""
import re
from datetime import datetime, timedelta


def infer_job_type(title: str, description: str) -> str:
    title_lower = title.lower() if title else ""
    desc_lower  = description.lower() if description else ""

    if "intern" in title_lower or "internship" in title_lower or "trainee" in title_lower:
        return "Internship"
    if "part time" in title_lower or "part-time" in title_lower:
        return "Part Time"

    explicit_intern_phrases = [
        "this is an internship", "internship role", "internship position",
        "internship opportunity", "joining as an intern", "you will be an intern",
        "stipend", "duration: ", "duration of internship",
    ]
    if any(p in desc_lower for p in explicit_intern_phrases):
        return "Internship"
    if "part time" in desc_lower or "part-time" in desc_lower:
        return "Part Time"

    return "Full Time"


def infer_workplace_type(location: str, description: str) -> str:
    loc_lower = location.lower() if location else ""
    desc_lower = description.lower() if description else ""
    if "remote" in loc_lower or "work from home" in loc_lower or "remote" in desc_lower or "wfh" in desc_lower:
        return "Online"
    if "hybrid" in loc_lower or "hybrid" in desc_lower:
        return "Hybrid"
    return "Offline"


ROLE_SUFFIX_WORDS = {
    "intern", "internship", "trainee", "apprentice", "fresher", "graduate",
    "job", "jobs", "opening", "openings", "position", "role", "vacancy",
    "early", "career", "campus", "hiring", "urgent", "immediate", "joiner",
    "joiners", "wanted", "required", "looking", "for", "the", "and", "or",
}

INTERN_SIGNALS = ("intern", "internship", "trainee", "apprentice", "co-op", "coop")

SENIORITY_CONFLICT_TERMS = {
    "senior", "lead", "manager", "director", "principal",
    "staff", "vp", "head", "chief", "sr.", "sr",
}

ROLE_KEEP_SHORT = {"ui", "ux", "hr", "qa", "ai", "ml", "go", "r", "it"}


def _normalize_role_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s/+.-]", " ", text)
    return " ".join(text.replace("-", " ").replace("/", " ").split())


def extract_role_keywords(search_query: str) -> list[str]:
    words = _normalize_role_text(search_query).split()
    return [
        w for w in words
        if w not in ROLE_SUFFIX_WORDS and (len(w) > 2 or w in ROLE_KEEP_SHORT)
    ]


def normalize_base_role(role: str) -> str:
    if not role:
        return role
    r = role.strip()
    r = re.sub(r"\s[-–]\s*(intern(ship)?|trainee|apprentice)\s*$", "", r, flags=re.I).strip()
    low = r.lower()
    for suffix in (" internship", " intern", " trainee", " apprentice"):
        if low.endswith(suffix):
            return r[: len(r) - len(suffix)].strip()
    return r


def build_scrape_query(role: str, internships: bool = False) -> str:
    base = normalize_base_role(role)
    return f"{base} intern" if internships else base


def title_matches_search(title: str, search_query: str) -> bool:
    if not title or not search_query:
        return False

    title_norm = _normalize_role_text(title)
    query_norm = _normalize_role_text(search_query)
    query_is_intern = any(s in query_norm.split() for s in INTERN_SIGNALS)
    title_is_intern = any(s in title_norm for s in INTERN_SIGNALS)

    if query_is_intern and not title_is_intern:
        return False
    if not query_is_intern and title_is_intern:
        return False
    if query_is_intern:
        title_words = set(title_norm.split())
        for term in SENIORITY_CONFLICT_TERMS:
            if term in title_words:
                return False

    keywords = extract_role_keywords(search_query)
    if not keywords:
        core = " ".join(w for w in query_norm.split() if w not in ROLE_SUFFIX_WORDS)
        return bool(core) and core in title_norm

    title_words = set(title_norm.split())
    for kw in keywords:
        if kw in title_words:
            continue
        if re.search(rf"\b{re.escape(kw)}", title_norm):
            continue
        return False
    return True


def filter_cards_by_role(cards: list, search_query: str) -> tuple[list, list]:
    matched, skipped = [], []
    for card in cards:
        title = card.get("title", "")
        if title_matches_search(title, search_query):
            matched.append(card)
        else:
            skipped.append(card)
    return matched, skipped


CITIES_LIST = [
    "Mumbai", "Bangalore", "Bengaluru", "Delhi", "Hyderabad", "Ahmedabad", "Chennai", "Kolkata", "Pune",
    "Gurgaon", "Gurugram", "Noida", "Faridabad", "Ghaziabad", "Jaipur", "Lucknow", "Nagpur", "Indore",
    "Thane", "Bhopal", "Patna", "Vadodara", "Agra", "Nashik", "Rajkot", "Varanasi", "Amritsar",
    "Dehradun", "Kochi", "Chandigarh", "Guwahati", "Mysore", "Bhubaneswar", "Coimbatore", "Vijayawada",
    "Jodhpur", "Raipur", "Shimla", "Panaji", "Goa", "Pondicherry", "Puducherry"
]

def extract_city_name(location_str: str, company_name: str = "") -> str:
    if not location_str:
        return "Unknown"

    location_str = location_str.strip()
    if not location_str or len(location_str) > 50:
        return "Unknown"

    if re.search(r'https?://|@|www\.', location_str, re.I):
        return "Unknown"

    if company_name and location_str.strip().lower() == company_name.strip().lower():
        return "Unknown"

    if re.search(r'\b(inc|llc|corp|ltd|pvt|private|limited|co\b|group|technologies|solutions|services|international)\.?', location_str, re.I):
        return "Unknown"

    loc_lower = location_str.lower()
    if "remote" in loc_lower or "work from home" in loc_lower or "wfh" in loc_lower:
        return "Remote"

    for city in CITIES_LIST:
        if city.lower() in loc_lower:
            if city.lower() == "bengaluru":
                return "Bangalore"
            return city

    first_segment = re.split(r'[,|/]', location_str)[0].strip()
    return first_segment if first_segment else "Unknown"


KNOWN_SKILLS = {
    "python", "java", "javascript", "typescript", "c++", "c#", "c", "go", "golang", "rust",
    "ruby", "php", "swift", "kotlin", "scala", "perl", "r", "matlab", "bash", "shell",
    "dart", "lua", "groovy", "objective-c", "assembly", "vba", "vb.net", "cobol", "fortran",
    "html", "css", "sass", "less", "react", "reactjs", "react.js", "angular", "angularjs",
    "vue", "vuejs", "vue.js", "next.js", "nextjs", "nuxt.js", "svelte", "jquery", "bootstrap",
    "tailwind", "tailwindcss", "webpack", "vite", "redux", "graphql", "rest api", "restful",
    "ajax", "dom", "web components", "pwa",
    "node.js", "nodejs", "express", "expressjs", "django", "flask", "fastapi", "spring",
    "spring boot", "springboot", ".net", "asp.net", "rails", "laravel", "symfony",
    "gin", "fiber", "nest.js", "nestjs", "strapi", "koa",
    "sql", "mysql", "postgresql", "postgres", "mongodb", "redis", "elasticsearch",
    "oracle", "sqlite", "mariadb", "cassandra", "dynamodb", "couchdb", "neo4j",
    "firebase", "supabase", "pl/sql", "t-sql", "nosql", "hbase", "influxdb",
    "aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "k8s", "terraform",
    "ansible", "jenkins", "ci/cd", "github actions", "gitlab ci", "circleci",
    "nginx", "apache", "linux", "unix", "windows server", "cloudformation",
    "helm", "istio", "vagrant", "puppet", "chef", "prometheus", "grafana",
    "datadog", "splunk", "elk", "logstash", "kibana", "newrelic",
    "machine learning", "deep learning", "nlp", "natural language processing",
    "computer vision", "tensorflow", "pytorch", "keras", "scikit-learn", "sklearn",
    "pandas", "numpy", "scipy", "matplotlib", "seaborn", "plotly",
    "spark", "pyspark", "hadoop", "hive", "pig", "airflow", "kafka",
    "data science", "data engineering", "etl", "data pipeline", "data warehouse",
    "data modeling", "data visualization", "data mining",
    "tableau", "power bi", "powerbi", "looker", "qlik", "qlikview", "qliksense",
    "sas", "spss", "stata", "alteryx", "knime",
    "llm", "chatgpt", "openai", "langchain", "hugging face", "transformers",
    "generative ai", "gen ai", "rag", "vector database", "pinecone",
    "regression", "classification", "clustering", "neural network", "cnn", "rnn", "lstm",
    "random forest", "xgboost", "lightgbm", "catboost", "decision tree",
    "android", "ios", "react native", "flutter", "xamarin", "ionic", "cordova",
    "swiftui", "jetpack compose",
    "selenium", "cypress", "jest", "mocha", "chai", "pytest", "junit",
    "testng", "appium", "postman", "jmeter", "gatling", "cucumber",
    "unit testing", "integration testing", "automation testing", "manual testing",
    "qa", "quality assurance", "test automation", "load testing",
    "git", "github", "gitlab", "bitbucket", "svn", "mercurial",
    "jira", "confluence", "trello", "slack", "figma", "sketch", "adobe xd",
    "photoshop", "illustrator", "invision", "zeplin", "miro",
    "salesforce", "sap", "servicenow", "workday", "hubspot",
    "shopify", "magento", "wordpress", "drupal",
    "excel", "ms excel", "advanced excel", "google sheets",
    "powerpoint", "ms office", "google analytics", "google ads",
    "seo", "sem", "digital marketing", "content marketing",
    "cybersecurity", "penetration testing", "ethical hacking", "owasp",
    "soc", "siem", "firewall", "encryption", "ssl", "tls",
    "oauth", "jwt", "saml", "ldap",
    "microservices", "monolith", "serverless", "api gateway",
    "event-driven", "message queue", "rabbitmq", "sqs", "pub/sub",
    "design patterns", "solid", "oop", "functional programming",
    "system design", "distributed systems", "caching",
    "agile", "scrum", "kanban", "waterfall", "devops", "devsecops",
    "product management", "project management", "stakeholder management",
    "communication skills", "leadership", "problem solving", "critical thinking",
    "erp", "crm", "supply chain", "logistics", "accounting", "finance",
    "risk management", "compliance", "auditing", "taxation",
    "ui/ux", "ux design", "ui design", "user research", "wireframing", "prototyping",
    "a/b testing", "usability testing",
    "tcp/ip", "dns", "http", "https", "networking", "vpn", "load balancing",
    "cdn", "bgp", "ospf", "mpls", "sd-wan",
    "blockchain", "solidity", "web3", "smart contracts",
    "iot", "embedded systems", "rtos", "arm", "raspberry pi", "arduino",
    "3d modeling", "unity", "unreal engine", "ar/vr",
    "api", "sdk", "cli", "gui", "orm", "mvc", "mvvm",
}

BLACKLIST_WORDS = {
    "analysis", "analytics", "analyst", "business", "management", "manager",
    "developer", "engineer", "engineering", "development", "designing",
    "associate", "executive", "coordinator", "consultant", "consulting",
    "senior", "junior", "lead", "head", "intern", "internship", "trainee",
    "support", "service", "services", "operations", "operating",
    "requirement", "requirements", "requirement gathering", "documentation",
    "hiring", "urgent", "immediate", "opening", "openings", "vacancy",
    "freshers", "fresher", "experienced", "years", "experience",
    "work from home", "wfh", "remote", "hybrid", "onsite", "full time", "part time",
    "salary", "ctc", "lpa", "package", "benefits", "perks",
    "india", "mumbai", "delhi", "bangalore", "hyderabad", "pune", "chennai",
    "kolkata", "noida", "gurgaon", "gurugram",
    "company", "organization", "team", "department", "role", "position",
    "candidate", "candidates", "applicant", "profile", "job",
    "good", "strong", "excellent", "ability", "understanding", "knowledge",
    "strategy", "strategic", "planning", "process", "processes",
    "reporting", "report", "reports", "presentation", "presentations",
    "data", "information", "system", "systems", "solution", "solutions",
    "technology", "technologies", "technical", "non-technical",
    "market", "marketing", "sales", "research", "testing",
    "implementation", "integration", "deployment", "delivery",
    "client", "customer", "vendor", "stakeholder", "stakeholders",
    "product", "project", "program", "portfolio",
    "quality", "performance", "optimization", "improvement",
}

def _stem(word: str) -> str:
    w = word.lower().rstrip('s').rstrip('ing').rstrip('ion').rstrip('ed').rstrip('er').rstrip('ist').rstrip('al')
    return w[:6] if len(w) > 6 else w

def _role_overlap_ratio(skill_lower: str, context_words: set, context_stems: set) -> float:
    words = skill_lower.split()
    if not words:
        return 0.0
    matches = sum(
        1 for w in words
        if w in context_words or _stem(w) in context_stems
    )
    return matches / len(words)

def clean_skills(raw_skills: list, job_title: str = "", role: str = "") -> list:
    if not raw_skills:
        return []

    context_str = f"{job_title} {role}".lower()
    context_words = set(context_str.split())
    context_stems = {_stem(w) for w in context_words}

    cleaned = []
    seen = set()

    for skill in raw_skills:
        s = skill.strip()
        if not s or len(s) < 2:
            continue

        s_lower = s.lower()

        if s_lower in BLACKLIST_WORDS:
            continue

        if s_lower in seen:
            continue

        overlap = _role_overlap_ratio(s_lower, context_words, context_stems)
        if overlap >= 0.7:
            continue

        if s_lower in KNOWN_SKILLS:
            seen.add(s_lower)
            cleaned.append(s)
            continue

        words = s_lower.split()
        if len(words) >= 2:
            has_tech = any(w in KNOWN_SKILLS for w in words)
            if has_tech:
                seen.add(s_lower)
                cleaned.append(s)
            continue

        if re.search(r'[0-9.+#/]', s):
            seen.add(s_lower)
            cleaned.append(s)

    return cleaned


def parse_relative_date(relative_str: str) -> str:
    if not relative_str:
        return datetime.today().strftime('%Y-%m-%d')

    s = relative_str.lower().strip()

    if "just posted" in s or "today" in s or "now" in s or "hour" in s or "minute" in s or "second" in s:
        return datetime.today().strftime('%Y-%m-%d')
    if "yesterday" in s:
        return (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')

    if "few days" in s or "few day" in s:
        return (datetime.today() - timedelta(days=3)).strftime('%Y-%m-%d')

    if re.search(r'\ba\s+month|\ban?\s+month', s):
        return (datetime.today() - timedelta(days=30)).strftime('%Y-%m-%d')

    if re.search(r'\ba\s+week|\ban?\s+week', s):
        return (datetime.today() - timedelta(weeks=1)).strftime('%Y-%m-%d')

    match_short_d = re.search(r'(\d+)\s*d\b', s)
    if match_short_d:
        days = int(match_short_d.group(1))
        return (datetime.today() - timedelta(days=days)).strftime('%Y-%m-%d')

    match_short_w = re.search(r'(\d+)\s*w\b', s)
    if match_short_w:
        weeks = int(match_short_w.group(1))
        return (datetime.today() - timedelta(weeks=weeks)).strftime('%Y-%m-%d')

    match_short_m = re.search(r'(\d+)\s*m\b', s)
    if match_short_m:
        months = int(match_short_m.group(1))
        return (datetime.today() - timedelta(days=months * 30)).strftime('%Y-%m-%d')

    match = re.search(r'(\d+)\+?\s+day', s)
    if match:
        days = int(match.group(1))
        return (datetime.today() - timedelta(days=days)).strftime('%Y-%m-%d')

    match_weeks = re.search(r'(\d+)\+?\s+week', s)
    if match_weeks:
        weeks = int(match_weeks.group(1))
        return (datetime.today() - timedelta(weeks=weeks)).strftime('%Y-%m-%d')

    match_months = re.search(r'(\d+)\+?\s+month', s)
    if match_months:
        months = int(match_months.group(1))
        return (datetime.today() - timedelta(days=months * 30)).strftime('%Y-%m-%d')

    return datetime.today().strftime('%Y-%m-%d')


def parse_linkedin_date(raw: str) -> str:
    today_str = datetime.today().strftime('%Y-%m-%d')
    if not raw or not raw.strip():
        return today_str

    s = raw.strip()

    iso_match = re.match(r'^(\d{4}-\d{2}-\d{2})', s)
    if iso_match:
        return iso_match.group(1)

    low = s.lower()

    prefixes = ("active ", "reposted ", "listed ")
    for prefix in prefixes:
        if low.startswith(prefix):
            low = low[len(prefix):].strip()

    if any(kw in low for kw in ("just posted", "just now", "today", "recently", "now")):
        return today_str

    if "yesterday" in low:
        return (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')

    m = re.search(r'(\d+)\s*h(?:ours?)?\s+ago', low)
    if m:
        return today_str

    m = re.search(r'(\d+)\s*min(?:utes?|s)?\s+ago', low)
    if m:
        return today_str

    m = re.search(r'(\d+)\s*s(?:econds?)?\s+ago', low)
    if m:
        return today_str

    m = re.search(r'(\d+)\s*d(?:ays?)?\s+ago', low)
    if m:
        days = int(m.group(1))
        return (datetime.today() - timedelta(days=days)).strftime('%Y-%m-%d')

    m = re.search(r'(\d+)\s*w(?:eeks?)?\s+ago', low)
    if m:
        weeks = int(m.group(1))
        return (datetime.today() - timedelta(weeks=weeks)).strftime('%Y-%m-%d')

    m = re.search(r'(\d+)\s*mo(?:nths?)?\s+ago', low)
    if m:
        months = int(m.group(1))
        return (datetime.today() - timedelta(days=months * 30)).strftime('%Y-%m-%d')

    m = re.search(r'(\d+)\+?\s+day', low)
    if m:
        days = int(m.group(1))
        return (datetime.today() - timedelta(days=days)).strftime('%Y-%m-%d')

    m = re.search(r'(\d+)\+?\s+week', low)
    if m:
        weeks = int(m.group(1))
        return (datetime.today() - timedelta(weeks=weeks)).strftime('%Y-%m-%d')

    m = re.search(r'(\d+)\+?\s+month', low)
    if m:
        months = int(m.group(1))
        return (datetime.today() - timedelta(days=months * 30)).strftime('%Y-%m-%d')

    return today_str
