"""
Naukri Scraper — uses Playwright to bypass bot detection.
Extracts job listings from search results pages and individual JD pages.
"""
import asyncio
import random
import re
import json
import urllib.parse
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from playwright_stealth import Stealth


async def get_search_results(page, role, location="", max_jobs=10, max_pages=15, existing_urls=None):
    """Get list of job URLs + basic info from search results pages (supports pagination)."""
    if existing_urls is None:
        existing_urls = set()
    if location:
        slug = f"{role.replace(' ', '-').lower()}-jobs-in-{location.replace(' ', '-').lower()}"
    else:
        slug = f"{role.replace(' ', '-').lower()}-jobs"
    
    all_cards = []
    new_count = 0
    page_num = 1
    
    while new_count < max_jobs and page_num <= max_pages:
        url = f"https://www.naukri.com/{slug}" if page_num == 1 else f"https://www.naukri.com/{slug}-{page_num}"
        print(f"  Loading search page {page_num}: {url}")
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            print(f"  Failed to load {url}: {e}")
            break
            
        await asyncio.sleep(random.uniform(6, 10))
        
        # Scroll to load lazy content
        for _ in range(3):
            await page.mouse.wheel(0, 500)
            await asyncio.sleep(random.uniform(1, 2))
        
        # Extract job cards
        cards = await page.evaluate('''() => {
            const results = [];
            document.querySelectorAll('.cust-job-tuple, .srp-jobtuple-wrapper, .jobTuple, article.jobTuple').forEach(card => {
                const titleEl = card.querySelector('a.title, a.jobTitle, .title a');
                const compEl  = card.querySelector('.comp-name, .comp-dtls-wrap a, .subTitle, .companyName');
                const descEl  = card.querySelector('.job-desc, .ellipsis, .job-description, .jobDescription');

                // Location
                const locEl   = card.querySelector('.loc-wrap, .location, .loc, .locWdth, .locWdth span');

                // Salary
                const salEl   = card.querySelector('.sal-wrap, .salary, .sal, .salaryText');

                // Tags / skills
                const tagEls  = card.querySelectorAll('.tags-gt .tag-li, .skills-list .tag-li, .tags-gt li, .tag-li, .techSkill');

                // --- Posted date: try multiple known selectors ---
                const dateSelectors = [
                    '.job-postdate', '.posted-date', '.postedVal',
                    '.postDate', '.job-post-day', '.date', '.days-ago',
                    'span.fleft.postedDate', 'span.postedDate',
                    '.jobTuple-right-cont .postedDate',
                    '[class*="postDate"]', '[class*="posted"]', '[class*="date"]',
                ];
                let rawDate = '';
                for (const sel of dateSelectors) {
                    const el = card.querySelector(sel);
                    if (el && el.textContent.trim()) {
                        rawDate = el.textContent.trim();
                        break;
                    }
                }

                // Fallback: scan ALL spans/divs in card for any text that looks like a date
                if (!rawDate) {
                    const datePattern = /\\d+\\s*(day|week|month|hour|minute|d\\b|w\\b|m\\b)|just\\s*posted|today|yesterday|few\\s+days/i;
                    const allEls = card.querySelectorAll('span, div, time, label');
                    for (const el of allEls) {
                        const txt = el.textContent.trim();
                        if (txt && datePattern.test(txt) && txt.length < 50) {
                            rawDate = txt;
                            break;
                        }
                    }
                }

                const tags = [];
                tagEls.forEach(tag => {
                    const text = tag.textContent.trim();
                    if (text) tags.push(text);
                });

                if (titleEl) {
                    results.push({
                        title:       titleEl.textContent.trim(),
                        url:         titleEl.href,
                        company:     compEl ? compEl.textContent.trim() : 'Unknown',
                        snippet:     descEl ? descEl.textContent.trim() : '',
                        location:    locEl  ? locEl.textContent.trim()  : 'Unknown',
                        salary:      salEl  ? salEl.textContent.trim()  : 'Not disclosed',
                        posted_date: rawDate || 'Just Posted',
                        skills:      tags
                    });
                }
            });
            return results;
        }''')
        
        if not cards:
            print(f"  No more jobs found on page {page_num}.")
            break

        matched, skipped = filter_cards_by_role(cards, role)
        for card in skipped:
            print(f"  [SKIP] Not a {role} role: {card.get('title', '')}")

        for card in matched:
            if card.get("url") in existing_urls:
                print(f"  [DUP] Skipping known URL: {card.get('title', '')}")
                continue
            if not any(c.get("url") == card["url"] for c in all_cards):
                all_cards.append(card)
                new_count += 1
                if new_count >= max_jobs:
                    break
        
        if new_count >= max_jobs:
            break
            
        page_num += 1
        await asyncio.sleep(random.uniform(4, 8))
        
    return all_cards[:new_count]

async def get_job_description(page, url):
    """Load individual job page and extract full description."""
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(random.uniform(4, 7))
        
        result = await page.evaluate('''() => {
            const descEl = document.querySelector('.styles_JDC__dang-inner-html__h0K4t, .job-desc, .dang-inner-html, [class*="job-desc"]');
            const compEl = document.querySelector('.styles_jd-header-comp-name__MvqAI, .jd-header-comp-name, [class*="comp-name"]');
            return {
                description: descEl ? descEl.innerText.trim() : '',
                company: compEl ? compEl.textContent.trim() : '',
            };
        }''')
        
        return result.get("description", "")
    except:
        return ""

def infer_job_type(title: str, description: str) -> str:
    title_lower = title.lower() if title else ""
    desc_lower  = description.lower() if description else ""

    # Title is the strongest signal
    if "intern" in title_lower or "internship" in title_lower or "trainee" in title_lower:
        return "Internship"
    if "part time" in title_lower or "part-time" in title_lower:
        return "Part Time"

    # Description fallback — only if very explicit (avoid false positives like
    # "we offer internship programs" in a full-time JD)
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
    """Significant role words from a search query (drops intern/trainee suffix noise)."""
    words = _normalize_role_text(search_query).split()
    return [
        w for w in words
        if w not in ROLE_SUFFIX_WORDS and (len(w) > 2 or w in ROLE_KEEP_SHORT)
    ]


def normalize_base_role(role: str) -> str:
    """Strip intern/trainee suffixes so 'Data Analyst Intern' → 'Data Analyst'."""
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
    """Build the platform search string from a base role + listing type."""
    base = normalize_base_role(role)
    return f"{base} intern" if internships else base


def title_matches_search(title: str, search_query: str) -> bool:
    """True when a listing title matches the specific role being scraped."""
    if not title or not search_query:
        return False

    title_norm = _normalize_role_text(title)
    query_norm = _normalize_role_text(search_query)
    query_is_intern = any(s in query_norm.split() for s in INTERN_SIGNALS)
    title_is_intern = any(s in title_norm for s in INTERN_SIGNALS)

    # Internship searches should only keep internship-style titles
    if query_is_intern and not title_is_intern:
        return False
    # Full-time searches should skip internship listings
    if not query_is_intern and title_is_intern:
        return False
    # Internship searches should reject senior-level titles
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
    """Split cards into (matching, skipped) based on title relevance."""
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

def extract_city_name(location_str: str) -> str:
    if not location_str:
        return "Unknown"
    
    loc_lower = location_str.lower()
    if "remote" in loc_lower or "work from home" in loc_lower or "wfh" in loc_lower:
        return "Remote"
        
    for city in CITIES_LIST:
        if city.lower() in loc_lower:
            if city.lower() == "bengaluru":
                return "Bangalore"
            return city
            
    # Clean up
    first_segment = re.split(r'[,|/]', location_str)[0].strip()
    return first_segment if first_segment else "Unknown"

# Recognized technical and professional skills (lowercase for matching)
KNOWN_SKILLS = {
    # Programming & scripting
    "python", "java", "javascript", "typescript", "c++", "c#", "c", "go", "golang", "rust",
    "ruby", "php", "swift", "kotlin", "scala", "perl", "r", "matlab", "bash", "shell",
    "dart", "lua", "groovy", "objective-c", "assembly", "vba", "vb.net", "cobol", "fortran",
    # Web & frontend
    "html", "css", "sass", "less", "react", "reactjs", "react.js", "angular", "angularjs",
    "vue", "vuejs", "vue.js", "next.js", "nextjs", "nuxt.js", "svelte", "jquery", "bootstrap",
    "tailwind", "tailwindcss", "webpack", "vite", "redux", "graphql", "rest api", "restful",
    "ajax", "dom", "web components", "pwa",
    # Backend & frameworks
    "node.js", "nodejs", "express", "expressjs", "django", "flask", "fastapi", "spring",
    "spring boot", "springboot", ".net", "asp.net", "rails", "laravel", "symfony",
    "gin", "fiber", "nest.js", "nestjs", "strapi", "koa",
    # Databases
    "sql", "mysql", "postgresql", "postgres", "mongodb", "redis", "elasticsearch",
    "oracle", "sqlite", "mariadb", "cassandra", "dynamodb", "couchdb", "neo4j",
    "firebase", "supabase", "pl/sql", "t-sql", "nosql", "hbase", "influxdb",
    # Cloud & DevOps
    "aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "k8s", "terraform",
    "ansible", "jenkins", "ci/cd", "github actions", "gitlab ci", "circleci",
    "nginx", "apache", "linux", "unix", "windows server", "cloudformation",
    "helm", "istio", "vagrant", "puppet", "chef", "prometheus", "grafana",
    "datadog", "splunk", "elk", "logstash", "kibana", "newrelic",
    # Data & ML/AI
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
    # Mobile
    "android", "ios", "react native", "flutter", "xamarin", "ionic", "cordova",
    "swiftui", "jetpack compose",
    # Testing
    "selenium", "cypress", "jest", "mocha", "chai", "pytest", "junit",
    "testng", "appium", "postman", "jmeter", "gatling", "cucumber",
    "unit testing", "integration testing", "automation testing", "manual testing",
    "qa", "quality assurance", "test automation", "load testing",
    # Version control
    "git", "github", "gitlab", "bitbucket", "svn", "mercurial",
    # Tools & Platforms
    "jira", "confluence", "trello", "slack", "figma", "sketch", "adobe xd",
    "photoshop", "illustrator", "invision", "zeplin", "miro",
    "salesforce", "sap", "servicenow", "workday", "hubspot",
    "shopify", "magento", "wordpress", "drupal",
    "excel", "ms excel", "advanced excel", "google sheets",
    "powerpoint", "ms office", "google analytics", "google ads",
    "seo", "sem", "digital marketing", "content marketing",
    # Security
    "cybersecurity", "penetration testing", "ethical hacking", "owasp",
    "soc", "siem", "firewall", "encryption", "ssl", "tls",
    "oauth", "jwt", "saml", "ldap",
    # Architecture & patterns
    "microservices", "monolith", "serverless", "api gateway",
    "event-driven", "message queue", "rabbitmq", "sqs", "pub/sub",
    "design patterns", "solid", "oop", "functional programming",
    "system design", "distributed systems", "caching",
    # Business & Domain
    "agile", "scrum", "kanban", "waterfall", "devops", "devsecops",
    "product management", "project management", "stakeholder management",
    "communication skills", "leadership", "problem solving", "critical thinking",
    "erp", "crm", "supply chain", "logistics", "accounting", "finance",
    "risk management", "compliance", "auditing", "taxation",
    "ui/ux", "ux design", "ui design", "user research", "wireframing", "prototyping",
    "a/b testing", "usability testing",
    # Networking
    "tcp/ip", "dns", "http", "https", "networking", "vpn", "load balancing",
    "cdn", "bgp", "ospf", "mpls", "sd-wan",
    # Misc tech
    "blockchain", "solidity", "web3", "smart contracts",
    "iot", "embedded systems", "rtos", "arm", "raspberry pi", "arduino",
    "3d modeling", "unity", "unreal engine", "ar/vr",
    "api", "sdk", "cli", "gui", "orm", "mvc", "mvvm",
}

# Generic words that are NOT skills
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
    """Crude stem: lowercase, strip common suffixes for overlap detection."""
    w = word.lower().rstrip('s').rstrip('ing').rstrip('ion').rstrip('ed').rstrip('er').rstrip('ist').rstrip('al')
    return w[:6] if len(w) > 6 else w  # Use first 6 chars as stem

def _role_overlap_ratio(skill_lower: str, context_words: set, context_stems: set) -> float:
    """Return ratio of skill words that match role/title words or their stems."""
    words = skill_lower.split()
    if not words:
        return 0.0
    matches = sum(
        1 for w in words
        if w in context_words or _stem(w) in context_stems
    )
    return matches / len(words)

def clean_skills(raw_skills: list, job_title: str = "", role: str = "") -> list:
    """Filter out non-skill tags: job title/role fragments, generic business words, etc."""
    if not raw_skills:
        return []

    # Build context from both job title and role name
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

        # Skip if blacklisted generic word
        if s_lower in BLACKLIST_WORDS:
            continue

        # Skip duplicates
        if s_lower in seen:
            continue

        # --- Role/title overlap check ---
        # If >= 70% of skill words are just role-name words (or stems), it's not a real skill
        overlap = _role_overlap_ratio(s_lower, context_words, context_stems)
        if overlap >= 0.7:
            continue

        # Accept if it's an exactly known skill
        if s_lower in KNOWN_SKILLS:
            seen.add(s_lower)
            cleaned.append(s)
            continue

        # For multi-word tags: keep if it contains at least one known technical word
        words = s_lower.split()
        if len(words) >= 2:
            has_tech = any(w in KNOWN_SKILLS for w in words)
            if has_tech:
                seen.add(s_lower)
                cleaned.append(s)
            continue

        # Single word unknown skill — only keep if it has digits/dots/special chars (e.g. "C++", "R", "3ds Max")
        if re.search(r'[0-9.+#/]', s):
            seen.add(s_lower)
            cleaned.append(s)

    return cleaned



def parse_relative_date(relative_str: str) -> str:
    if not relative_str:
        return datetime.today().strftime('%Y-%m-%d')
        
    s = relative_str.lower().strip()

    # "just posted", "today", "active today", "active now", "active 2 hours ago", "active 1 day ago" etc.
    if "just posted" in s or "today" in s or "now" in s or "hour" in s or "minute" in s or "second" in s:
        return datetime.today().strftime('%Y-%m-%d')
    if "yesterday" in s:
        return (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')

    # "few days ago" → treat as 3 days
    if "few days" in s or "few day" in s:
        return (datetime.today() - timedelta(days=3)).strftime('%Y-%m-%d')

    # "a month ago" / "an month" → 30 days
    if re.search(r'\ba\s+month|\ban?\s+month', s):
        return (datetime.today() - timedelta(days=30)).strftime('%Y-%m-%d')

    # "a week ago" / "an week" → 7 days
    if re.search(r'\ba\s+week|\ban?\s+week', s):
        return (datetime.today() - timedelta(weeks=1)).strftime('%Y-%m-%d')

    # Short formats: "6d", "6d ago", "3w", "2m" (Naukri mobile/app style)
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

    # Match strings like "3 days ago", "active 3 days ago", "30+ days ago", "15 days ago"
    match = re.search(r'(\d+)\+?\s+day', s)
    if match:
        days = int(match.group(1))
        return (datetime.today() - timedelta(days=days)).strftime('%Y-%m-%d')

    # Match strings like "1 week ago", "2 weeks ago"
    match_weeks = re.search(r'(\d+)\+?\s+week', s)
    if match_weeks:
        weeks = int(match_weeks.group(1))
        return (datetime.today() - timedelta(weeks=weeks)).strftime('%Y-%m-%d')

    # Match strings like "1 month ago", "2 months ago"
    match_months = re.search(r'(\d+)\+?\s+month', s)
    if match_months:
        months = int(match_months.group(1))
        return (datetime.today() - timedelta(days=months * 30)).strftime('%Y-%m-%d')

    return datetime.today().strftime('%Y-%m-%d')


def parse_linkedin_date(raw: str) -> str:
    """Parse LinkedIn date strings into YYYY-MM-DD.

    Handles:
      - ISO dates from <time datetime="2026-07-15">
      - Relative strings like "2 hours ago", "3 days ago", "1 week ago"
      - Short forms like "2h ago", "3d ago", "1w ago", "2mo ago"
      - "Just posted", "Yesterday", "Recent", "Active X ago"
    Falls back to today's date if nothing parses.
    """
    today_str = datetime.today().strftime('%Y-%m-%d')
    if not raw or not raw.strip():
        print(f"  [DATE] raw='' → fallback={today_str}")
        return today_str

    s = raw.strip()

    iso_match = re.match(r'^(\d{4}-\d{2}-\d{2})', s)
    if iso_match:
        parsed = iso_match.group(1)
        print(f"  [DATE] raw='{raw}' → iso={parsed}")
        return parsed

    low = s.lower()

    prefixes = ("active ", "reposted ", "listed ")
    for prefix in prefixes:
        if low.startswith(prefix):
            low = low[len(prefix):].strip()

    if any(kw in low for kw in ("just posted", "just now", "today", "recently", "now")):
        print(f"  [DATE] raw='{raw}' → today={today_str}")
        return today_str

    if "yesterday" in low:
        parsed = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')
        print(f"  [DATE] raw='{raw}' → yesterday={parsed}")
        return parsed

    m = re.search(r'(\d+)\s*h(?:ours?)?\s+ago', low)
    if m:
        print(f"  [DATE] raw='{raw}' → today={today_str}")
        return today_str

    m = re.search(r'(\d+)\s*min(?:utes?|s)?\s+ago', low)
    if m:
        print(f"  [DATE] raw='{raw}' → today={today_str}")
        return today_str

    m = re.search(r'(\d+)\s*s(?:econds?)?\s+ago', low)
    if m:
        print(f"  [DATE] raw='{raw}' → today={today_str}")
        return today_str

    m = re.search(r'(\d+)\s*d(?:ays?)?\s+ago', low)
    if m:
        days = int(m.group(1))
        parsed = (datetime.today() - timedelta(days=days)).strftime('%Y-%m-%d')
        print(f"  [DATE] raw='{raw}' → {days}d ago={parsed}")
        return parsed

    m = re.search(r'(\d+)\s*w(?:eeks?)?\s+ago', low)
    if m:
        weeks = int(m.group(1))
        parsed = (datetime.today() - timedelta(weeks=weeks)).strftime('%Y-%m-%d')
        print(f"  [DATE] raw='{raw}' → {weeks}w ago={parsed}")
        return parsed

    m = re.search(r'(\d+)\s*mo(?:nths?)?\s+ago', low)
    if m:
        months = int(m.group(1))
        parsed = (datetime.today() - timedelta(days=months * 30)).strftime('%Y-%m-%d')
        print(f"  [DATE] raw='{raw}' → {months}mo ago={parsed}")
        return parsed

    m = re.search(r'(\d+)\+?\s+day', low)
    if m:
        days = int(m.group(1))
        parsed = (datetime.today() - timedelta(days=days)).strftime('%Y-%m-%d')
        print(f"  [DATE] raw='{raw}' → {days}d={parsed}")
        return parsed

    m = re.search(r'(\d+)\+?\s+week', low)
    if m:
        weeks = int(m.group(1))
        parsed = (datetime.today() - timedelta(weeks=weeks)).strftime('%Y-%m-%d')
        print(f"  [DATE] raw='{raw}' → {weeks}w={parsed}")
        return parsed

    m = re.search(r'(\d+)\+?\s+month', low)
    if m:
        months = int(m.group(1))
        parsed = (datetime.today() - timedelta(days=months * 30)).strftime('%Y-%m-%d')
        print(f"  [DATE] raw='{raw}' → {months}mo={parsed}")
        return parsed

    print(f"  [DATE] raw='{raw}' → unparseable, fallback={today_str}")
    return today_str


async def scrape_naukri(search_query: str, location: str = "", max_jobs: int = 10, existing_urls=None):
    """Main scraping function. Returns list of job dicts."""
    if existing_urls is None:
        existing_urls = set()
    jobs = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-gpu",
                "--no-sandbox",
                "--window-size=1920,1080",
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.128 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
        )
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            window.chrome = {runtime: {}};
        """)
        
        page = await context.new_page()
        
        # Warm up session
        await page.goto("https://www.naukri.com/", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)
        
        # Get search results
        cards = await get_search_results(page, search_query, location, max_jobs, existing_urls=existing_urls)
        print(f"  Found {len(cards)} listings for {search_query} in {location or 'India'}")
        
        for i, card in enumerate(cards):
            if not title_matches_search(card.get("title", ""), search_query):
                print(f"  Skipping title mismatch: {card.get('title', '')}")
                continue

            # Visit each job page to get full description
            if i > 0:
                await asyncio.sleep(random.uniform(3, 6))
            
            desc = await get_job_description(page, card["url"])
            if not desc:
                desc = card.get("snippet", "No description available")
            
            email = None
            emails = re.findall(r'[a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9_-]+', desc)
            if emails:
                email = emails[0]
            
            loc = extract_city_name(card.get("location", ""))
            job_type = infer_job_type(card["title"], desc)
            workplace = infer_workplace_type(loc, desc)
            
            raw_date = card.get("posted_date", "Just Posted")
            jobs.append({
                "title": card["title"],
                "company": card["company"],
                "url": card["url"],
                "description": desc,
                "email": email,
                "location": loc,
                "country": "India",
                "platform": "Naukri",
                "job_type": job_type,
                "workplace_type": workplace,
                "posted_date": parse_relative_date(raw_date),
                "salary": card.get("salary", "Not disclosed"),
                "skills": clean_skills(card.get("skills", []), card["title"])
            })
            print(f"  [SUCCESS] [{i+1}/{len(cards)}] {card['company']}")
        
        await browser.close()
    
    return jobs


# ---------------------------------------------------------------------------
# Indeed Scraper Helper Functions
# ---------------------------------------------------------------------------

async def _human_delay(lo=2.0, hi=5.0):
    await asyncio.sleep(random.uniform(lo, hi))


async def _slow_scroll(page, steps=4):
    for _ in range(steps):
        delta = random.randint(300, 700)
        await page.mouse.wheel(0, delta)
        await _human_delay(0.8, 1.8)


async def _is_blocked(page) -> bool:
    try:
        title = await page.title()
        lower = title.lower()
        return any(kw in lower for kw in ("blocked", "just a moment", "access denied", "captcha"))
    except Exception:
        return True


async def _wait_for_cloudflare(page, max_wait_s=50, label=""):
    """Wait for Cloudflare challenge to auto-resolve."""
    elapsed = 0
    interval = 5
    while elapsed < max_wait_s:
        await asyncio.sleep(interval)
        elapsed += interval
        try:
            if not await _is_blocked(page):
                print(f"  [OK] Cloudflare passed{' (' + label + ')' if label else ''} after ~{elapsed}s")
                return True
        except Exception:
            return False
    print(f"  [FAIL] Cloudflare block persisted{' (' + label + ')' if label else ''} after {max_wait_s}s")
    return False


async def _safe_goto(page, url, timeout=60000):
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        return True
    except Exception as e:
        print(f"  Navigation error: {e}")
        return False


async def get_indeed_search_results(page, role, location="", max_jobs=10, max_pages=15, existing_urls=None):
    if existing_urls is None:
        existing_urls = set()
    all_cards = []
    new_count = 0
    start_offset = 0
    cf_failures = 0
    MAX_CF_FAILS = 3
    pages_fetched = 0

    while new_count < max_jobs and pages_fetched < max_pages:
        params = {"q": role}
        if location:
            params["l"] = location
        if start_offset > 0:
            params["start"] = str(start_offset)

        url = f"https://in.indeed.com/jobs?{urllib.parse.urlencode(params)}"
        print(f"  Loading search page (start={start_offset}): {url}")

        if not await _safe_goto(page, url):
            break

        await _human_delay(5, 9)

        if await _is_blocked(page):
            print("  [WARN] Cloudflare challenge detected. Waiting...")
            if not await _wait_for_cloudflare(page, max_wait_s=50, label=f"offset {start_offset}"):
                cf_failures += 1
                if cf_failures >= MAX_CF_FAILS:
                    print(f"  [FAIL] {MAX_CF_FAILS} consecutive CF blocks — aborting.")
                    break
                start_offset += 10
                pages_fetched += 1
                continue

        cf_failures = 0
        await _slow_scroll(page)

        try:
            cards = await page.evaluate('''() => {
                const results = [];
                const seen = new Set();

                // Indeed card selectors (multiple versions)
                const containerSelectors = [
                    '.job_seen_beacon',
                    '.resultContent',
                    '[data-jk]',
                    '.jobsearch-ResultsList > li',
                    '.tapItem',
                ];

                let allCards = [];
                for (const sel of containerSelectors) {
                    const found = document.querySelectorAll(sel);
                    if (found.length > 0) { allCards = found; break; }
                }

                allCards.forEach(card => {
                    const titleEl = card.querySelector(
                        'a.jcs-JobTitle, h2.jobTitle a, .jobTitle a, ' +
                        '[class*="jobTitle"] a, a[data-jk], .resultContent a'
                    );
                    if (!titleEl) return;

                    const compEl  = card.querySelector('[data-testid="company-name"], .companyName, span.companyName');
                    const locEl   = card.querySelector('[data-testid="text-location"], .companyLocation, div.companyLocation');
                    const descEl  = card.querySelector('.job-snippet, [class*="job-snippet"], .underShelfFooter, [class*="snippet"]');

                    const dateEl  = card.querySelector('.date, [class*="date"], .myJobsState, .date-written');

                    const jk = card.getAttribute('data-jk') || titleEl.getAttribute('data-jk') || '';
                    let href = titleEl.getAttribute('href') || '';
                    if (jk && !href.includes('/viewjob')) href = '/viewjob?jk=' + jk;
                    const fullUrl = href.startsWith('http') ? href : 'https://in.indeed.com' + href;

                    if (seen.has(fullUrl)) return;
                    seen.add(fullUrl);

                    let company = compEl ? compEl.textContent.trim() : 'Unknown';
                    let location = locEl ? locEl.textContent.trim() : '';
                    
                    // Strip duplicated company prefix from location
                    if (location.toLowerCase().startsWith(company.toLowerCase())) {
                        location = location.slice(company.length).trim();
                    }

                    results.push({
                        title:    titleEl.textContent.trim(),
                        url:      fullUrl,
                        company:  company,
                        location: location,
                        snippet:  descEl  ? descEl.textContent.trim()  : '',
                        posted_date: dateEl ? dateEl.textContent.trim() : 'Just Posted',
                        jk:       jk,
                    });
                });
                return results;
            }''')
        except Exception as e:
            print(f"  JS eval failed: {e}")
            break

        if not cards:
            print(f"  No jobs found at offset {start_offset}.")
            break

        matched, skipped = filter_cards_by_role(cards, role)
        for card in skipped:
            print(f"  [SKIP] Not a {role} role: {card.get('title', '')}")

        for card in matched:
            cid = card.get("jk") or card.get("url")
            card_url = card.get("url", "")
            if card_url in existing_urls:
                print(f"  [DUP] Skipping known URL: {card.get('title', '')}")
                continue
            if not any((c.get("jk") or c.get("url")) == cid for c in all_cards):
                all_cards.append(card)
                new_count += 1
                if new_count >= max_jobs:
                    break

        print(f"  Collected {new_count} new matching jobs so far...")
        if new_count >= max_jobs:
            break

        start_offset += 10
        pages_fetched += 1
        await _human_delay(4, 8)

    return all_cards[:new_count]


async def get_indeed_job_description(page, url):
    try:
        if not await _safe_goto(page, url, timeout=30000):
            return ""
        await _human_delay(4, 7)

        if await _is_blocked(page):
            if not await _wait_for_cloudflare(page, max_wait_s=30, label="JD"):
                return ""

        result = await page.evaluate('''() => {
            const sels = [
                '#jobDescriptionText',
                '.jobsearch-JobComponent-description',
                '[class*="jobDescription"]',
                '.jobsearch-jobDescriptionText',
                '#jobDescription',
            ];
            let el = null;
            for (const s of sels) { el = document.querySelector(s); if (el) break; }
            return { description: el ? el.innerText.trim() : '' };
        }''')
        return result.get("description", "")
    except Exception:
        return ""


async def scrape_indeed(search_query: str, location: str = "", max_jobs: int = 10, existing_urls=None):
    """Scrape in.indeed.com for job listings. Returns list of job dicts."""
    if existing_urls is None:
        existing_urls = set()
    jobs = []

    async with async_playwright() as p:
        # Use Firefox — it has a much better Cloudflare pass-rate than Chromium
        browser = await p.firefox.launch(
            headless=True,
            args=["--width=1920", "--height=1080"],
        )
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="en-IN",
            timezone_id="Asia/Kolkata",
            geolocation={"latitude": 19.076, "longitude": 72.8777},
            permissions=["geolocation"],
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) "
                "Gecko/20100101 Firefox/125.0"
            ),
        )

        page = await context.new_page()

        # Apply stealth patches (hides webdriver, overrides navigator props, etc.)
        await Stealth().apply_stealth_async(page)

        # Warm up — visit homepage to acquire cookies / solve initial CF
        print("  Warming up Indeed session (Firefox + stealth)...")
        if await _safe_goto(page, "https://in.indeed.com/", timeout=30000):
            await _human_delay(3, 5)
            if await _is_blocked(page):
                print("  [WARN] Cloudflare on homepage. Waiting...")
                await _wait_for_cloudflare(page, max_wait_s=60, label="homepage")
        else:
            print("  [WARN] Homepage warm-up failed.")

        # Scrape search results
        cards = await get_indeed_search_results(page, search_query, location, max_jobs, existing_urls=existing_urls)
        print(f"  Found {len(cards)} listings for '{search_query}' in '{location or 'India'}'")

        # Fetch full descriptions
        for i, card in enumerate(cards):
            if not title_matches_search(card.get("title", ""), search_query):
                print(f"  Skipping title mismatch: {card.get('title', '')}")
                continue

            if i > 0:
                await _human_delay(3, 6)

            desc = await get_indeed_job_description(page, card["url"])
            if not desc:
                desc = card.get("snippet", "No description available")

            email = None
            emails = re.findall(r'[a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9_-]+', desc)
            if emails:
                email = emails[0]

            loc = extract_city_name(card.get("location", ""))
            job_type = infer_job_type(card["title"], desc)
            workplace = infer_workplace_type(loc, desc)

            jobs.append({
                "title":    card["title"],
                "company":  card["company"],
                "url":      card["url"],
                "description": desc,
                "email":    email,
                "location": loc,
                "country": "India",
                "platform": "Indeed",
                "job_type": job_type,
                "workplace_type": workplace,
                "posted_date": parse_relative_date(card.get("posted_date", "Just Posted")),
                "salary": "Not disclosed",
                "skills": []
            })
            print(f"  [SUCCESS] [{i+1}/{len(cards)}] {card['company']}")

        await browser.close()

    return jobs


# ---------------------------------------------------------------------------
# LinkedIn Scraper
# ---------------------------------------------------------------------------

async def _linkedin_human_delay(lo=2.0, hi=4.5):
    await asyncio.sleep(random.uniform(lo, hi))


async def _linkedin_slow_scroll(page, times=3):
    for _ in range(times):
        await page.mouse.wheel(0, random.randint(400, 800))
        await asyncio.sleep(random.uniform(0.3, 0.6))


async def get_linkedin_search_results(page, search_query, location="", max_jobs=10, existing_urls=None, internships=False):
    if existing_urls is None:
        existing_urls = set()
    all_cards = []
    all_seen_urls = set()
    new_count = 0
    start = 0

    while new_count < max_jobs and start < 200:
        params_parts = [f"keywords={urllib.parse.quote_plus(search_query)}"]
        if location:
            params_parts.append(f"location={urllib.parse.quote_plus(location)}")
        if internships:
            params_parts.append("f_E=1")
        else:
            params_parts.append("f_E=2%2C3%2C4%2C5")
        if start > 0:
            params_parts.append(f"start={start}")

        url = f"https://www.linkedin.com/jobs/search/?{'&'.join(params_parts)}"
        print(f"  Loading LinkedIn search (start={start}): {url}")

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=40000)
        except Exception as e:
            print(f"  Failed to load LinkedIn page: {e}")
            break

        try:
            await page.wait_for_selector(
                "ul.jobs-search__results-list li, .job-search-card, .base-card",
                timeout=15000,
            )
        except Exception:
            pass

        await _linkedin_slow_scroll(page, times=2)
        await asyncio.sleep(random.uniform(1.0, 2.0))

        need_more = new_count < max_jobs
        if need_more:
            see_more = await page.query_selector(
                "button.infinite-scroller__show-more-button, button[aria-label*='more']"
            )
            if see_more:
                try:
                    await see_more.click()
                    await asyncio.sleep(random.uniform(1.0, 2.0))
                except Exception:
                    pass

        try:
            cards = await page.evaluate("""() => {
                const cards = document.querySelectorAll(
                    'ul.jobs-search__results-list li, .job-search-card, div.base-card'
                );
                return Array.from(cards).map(card => {
                    const titleEl = card.querySelector('h3, .base-search-card__title, .job-search-card__title');
                    const companyEl = card.querySelector('h4, .base-search-card__subtitle, .job-search-card__company-name');
                    const locationEl = card.querySelector('.job-search-card__location, [class*="location"]');
                    const linkEl = card.querySelector('a[href*="/jobs/view/"], a.base-card__full-link');
                    // --- Posted date: try <time> with datetime attr first, then broader selectors ---
                    let rawDate = '';
                    const timeEl = card.querySelector('time');
                    if (timeEl) {
                        const dt = timeEl.getAttribute('datetime');
                        if (dt) {
                            rawDate = dt;
                        } else {
                            rawDate = timeEl.textContent.trim();
                        }
                    }
                    if (!rawDate) {
                        const dateSelectors = [
                            '.job-search-card__listdate', '.job-search-card__listdate--new',
                            '[class*="listdate"]', '[class*="posted-date"]',
                            '[class*="date"]', '[class*="age"]',
                        ];
                        for (const sel of dateSelectors) {
                            const el = card.querySelector(sel);
                            if (el && el.textContent.trim()) {
                                rawDate = el.textContent.trim();
                                break;
                            }
                        }
                    }
                    if (!rawDate) {
                        const datePatterns = /(\d+\s*(?:hour|minute|second|day|week|month)s?\s+ago)|(\d+[hdwmy]\b)|(just now|today|yesterday|recently)/i;
                        const allEls = card.querySelectorAll('span, div, time, p');
                        for (const el of allEls) {
                            const txt = el.textContent.trim();
                            if (txt && datePatterns.test(txt) && txt.length < 60) {
                                rawDate = txt;
                                break;
                            }
                        }
                    }
                    if (!rawDate) rawDate = '';

                    const subtitleEls = card.querySelectorAll('.job-search-card__subtitle, .base-search-card__metadata');
                    let salary = '';
                    subtitleEls.forEach(el => {
                        const txt = el.textContent.trim();
                        if (txt.includes('₹') || txt.includes('$') || txt.includes('PA') || txt.includes('LPA') || /\\d{2,}/.test(txt)) {
                            salary = txt;
                        }
                    });
                    let skills = [];
                    const skillEls = card.querySelectorAll('.job-criteria__text, .job-criteria-subheader__value, [class*="skill"]');
                    skillEls.forEach(el => {
                        const t = el.textContent.trim();
                        if (t && t.length < 60) skills.push(t);
                    });
                    return {
                        title: titleEl ? titleEl.innerText.trim() : '',
                        company: companyEl ? companyEl.innerText.trim() : '',
                        location: locationEl ? locationEl.innerText.trim() : '',
                        url: linkEl ? linkEl.href.split('?')[0] : '',
                        posted_date_raw: rawDate,
                        salary: salary || 'Not disclosed',
                        skills: skills,
                    };
                }).filter(j => j.title && j.company && j.url);
            }""")
        except Exception as e:
            print(f"  LinkedIn JS eval failed: {e}")
            break

        if not cards:
            print(f"  No more LinkedIn jobs found at start={start}.")
            break

        dup_on_page = 0
        for card in cards:
            if card["url"] in existing_urls or card["url"] in all_seen_urls:
                dup_on_page += 1
                print(f"  [DUP] Skipping known LinkedIn URL: {card.get('title', '')}")
                continue
            if not title_matches_search(card.get("title", ""), search_query):
                print(f"  Skipping title mismatch: {card.get('title', '')}")
                continue
            all_seen_urls.add(card["url"])
            all_cards.append(card)
            new_count += 1
            if new_count >= max_jobs:
                break

        if cards and dup_on_page == len(cards):
            print(f"  All {len(cards)} cards on this page are duplicates — stopping LinkedIn pagination.")
            break

        print(f"  LinkedIn: {new_count} new matching jobs so far...")
        if new_count >= max_jobs:
            break

        start += 25
        await asyncio.sleep(random.uniform(2, 4))

    return all_cards[:new_count]


async def get_linkedin_job_description(page, url):
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(random.uniform(1.5, 3.0))

        result = await page.evaluate("""() => {
            const sels = [
                '.jobs-description-content__text', '.jobs-description__content',
                '.show-more-less-html__markup', '[class*="jobs-description"]',
                '.description__text',
            ];
            let el = null;
            for (const s of sels) { el = document.querySelector(s); if (el) break; }
            return { description: el ? el.innerText.trim() : '' };
        }""")
        return result.get("description", "")
    except Exception:
        return ""


async def scrape_linkedin(search_query: str, location: str = "", max_jobs: int = 10, existing_urls=None, internships: bool = False):
    """Scrape linkedin.com/jobs for listings. Returns list of job dicts matching our schema."""
    if existing_urls is None:
        existing_urls = set()
    jobs = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-gpu",
                "--no-sandbox",
                "--window-size=1920,1080",
            ],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.118 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
        )
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            window.chrome = {runtime: {}};
        """)

        page = await context.new_page()

        print("  Warming up LinkedIn session...")
        try:
            await page.goto("https://www.linkedin.com/jobs/", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(1.5)
        except Exception:
            print("  [WARN] LinkedIn warm-up failed, continuing anyway.")

        li_location = location if location else "India"
        cards = await get_linkedin_search_results(page, search_query, li_location, max_jobs, existing_urls=existing_urls, internships=internships)
        print(f"  Found {len(cards)} LinkedIn listings for '{search_query}' in '{li_location}'")

        for i, card in enumerate(cards):
            if card["url"] in existing_urls:
                print(f"  [DUP] Skipping known LinkedIn URL: {card.get('title', '')}")
                continue

            if not title_matches_search(card.get("title", ""), search_query):
                print(f"  Skipping title mismatch: {card.get('title', '')}")
                continue

            if i > 0:
                await asyncio.sleep(random.uniform(1.5, 3.0))

            desc = await get_linkedin_job_description(page, card["url"])
            if not desc:
                desc = card.get("snippet", "No description available")

            email = None
            emails = re.findall(r'[a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9_-]+', desc)
            if emails:
                email = emails[0]

            loc = extract_city_name(card.get("location", ""))
            job_type = infer_job_type(card["title"], desc)
            workplace = infer_workplace_type(loc, desc)

            raw_date = card.get("posted_date_raw", "")
            parsed_date = parse_linkedin_date(raw_date) if raw_date else parse_relative_date("Just Posted")
            jobs.append({
                "title": card["title"],
                "company": card["company"],
                "url": card["url"],
                "description": desc,
                "email": email,
                "location": loc,
                "country": "India",
                "platform": "LinkedIn",
                "job_type": job_type,
                "workplace_type": workplace,
                "posted_date": parsed_date,
                "salary": card.get("salary", "Not disclosed"),
                "skills": card.get("skills", []),
            })
            print(f"  [SUCCESS] [{i+1}/{len(cards)}] {card['company']}")

        await browser.close()

    return jobs

