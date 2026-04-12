import re
import requests
import json
from bs4 import BeautifulSoup
import urllib.request
import os

def phrase_match(text: str, phrases: list) -> str:
    lower_text = text.lower()
    for phrase in phrases:
        if phrase in lower_text:
            return phrase
    return None

def count_emojis(text: str) -> int:
    emoji_pattern = re.compile("[\U0001f600-\U0001f64f\U0001f300-\U0001f5ff\U0001f680-\U0001f6ff\U0001f1e0-\U0001f1ff\u2600-\u26ff\u2700-\u27bf\U0001f900-\U0001f9ff\U0001fa00-\U0001fa6f\U0001fa70-\U0001faff]")
    return len(emoji_pattern.findall(text))

def count_ghost_chars(text: str) -> int:
    ghost_pattern = re.compile("[\u200B\u200C\u200D\u200E\u200F\u2060\u2061\u2062\u2063\u2064\uFEFF\u00AD\u034F\u061C\u115F\u1160\u17B4\u17B5\u180E\u202A-\u202E\u2066-\u2069\u2800\u3164]")
    return len(ghost_pattern.findall(text))



def analyze_job(full_text: str, company: str, email: str):
    flags = []
    trust_score = 0
    raw_threats = []
    official_domain = ""
    
    free_providers = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "protonmail.com", "aol.com", "ymail.com", "zoho.com"]
    
    recruiter_domain = "none"
    has_corporate_email = False

    if email and "@" in email:
        recruiter_domain = email.split('@')[1].lower()
        if recruiter_domain in free_providers:
            raw_threats.append({"penalty": 15, "message": "Recruiter uses a free email provider.", "paramId": 1, "severity": "warn", "category": "identity", "trustPiercing": False})
        else:
            has_corporate_email = True
            trust_score += 15
    else:
        raw_threats.append({"penalty": 5, "message": "[P2] No contact email found in listing.", "paramId": 2, "severity": "info", "category": "identity", "trustPiercing": False})

    company_verified = False
    
    # Simulate API blocks with naive fallback or hit Clearbit
    if company and company != "Unknown":
        clean_query = re.sub(r'\b(limited|ltd|pvt|private|inc|corp|corporation|llc|co|group|holdings)\b', '', company.lower())
        clean_query = re.sub(r'[^a-z0-9 ]', '', clean_query).strip()
        
        try:
            req = urllib.request.Request(f"https://autocomplete.clearbit.com/v1/companies/suggest?query={urllib.parse.quote(clean_query)}", headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=3) as response:
                api_data = json.loads(response.read().decode())
                if api_data:
                    official_domain = api_data[0].get("domain", "")
                    company_verified = True
                    trust_score += 20
                    flags.append(f"SAFE: Verified globally as {api_data[0]['name']}")
                    
                    if recruiter_domain != "none" and recruiter_domain != official_domain and recruiter_domain not in free_providers:
                        if has_corporate_email:
                            trust_score -= 15
                            has_corporate_email = False
                        raw_threats.append({"penalty": 50, "message": f"Email domain @{recruiter_domain} doesn't match official @{official_domain}", "paramId": 4, "severity": "crit", "category": "identity", "trustPiercing": True})
                    else:
                        if recruiter_domain == official_domain:
                            trust_score += 15
                else:
                    raw_threats.append({"penalty": 8, "message": "[P3] Company not found in global registry.", "paramId": 3, "severity": "info", "category": "verification", "trustPiercing": False})
                    raw_threats.append({"penalty": 5, "message": "[P4] Cannot verify domain.", "paramId": 4, "severity": "info", "category": "verification", "trustPiercing": False})
        except Exception as e:
            flags.append("WARN: [P3] Registry API temporarily unavailable.")
    
    # P5: RDAP Domain Age Check
    domain_established = False
    if official_domain:
        try:
            rdap_req = urllib.request.Request(
                f"https://rdap.org/domain/{official_domain}",
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            with urllib.request.urlopen(rdap_req, timeout=5) as rdap_response:
                rdap_data = json.loads(rdap_response.read().decode())
                reg_event = None
                for event in rdap_data.get("events", []):
                    if event.get("eventAction", "").lower() in ("registration",):
                        reg_event = event
                        break
                if reg_event and reg_event.get("eventDate"):
                    from datetime import datetime, timezone
                    reg_date = datetime.fromisoformat(reg_event["eventDate"].replace("Z", "+00:00"))
                    age_days = (datetime.now(timezone.utc) - reg_date).days
                    if age_days < 90:
                        raw_threats.append({"penalty": 35, "message": f"Domain registered {age_days} days ago — very new.", "paramId": 5, "severity": "crit", "category": "verification", "trustPiercing": False})
                    elif age_days < 180:
                        raw_threats.append({"penalty": 15, "message": f"Domain is less than 6 months old.", "paramId": 5, "severity": "warn", "category": "verification", "trustPiercing": False})
                    else:
                        domain_established = True
                        trust_score += 10
                        flags.append(f"SAFE: Domain age verified ({age_days // 365}+ years).")
        except Exception:
            pass  # RDAP lookup failed — skip silently

    trust_tier = 1
    if company_verified and (has_corporate_email or domain_established):
        trust_tier = 3
    elif company_verified or has_corporate_email or domain_established:
        trust_tier = 2

    # CONTENT THREATS (Phase 2)
    txt = full_text.lower() if full_text else ""
    if txt:
        p6Phrases = ["send your aadhar", "share your aadhar", "aadhar card number", "aadhar number", "send your pan", "share your pan", "pan card number", "pan card details", "send passport", "passport number", "passport copy", "bank account number", "bank account details", "share bank details", "send bank details", "credit card", "debit card number"]
        p6_match = phrase_match(txt, p6Phrases)
        if p6_match:
            raw_threats.append({"penalty": 55, "message": f'Requests sensitive documents in listing ("{p6_match}").', "paramId": 6, "severity": "crit", "category": "data_theft", "trustPiercing": False})
            
        p7Phrases = ["security deposit", "registration fee", "refundable deposit", "processing fee", "training fee", "pay for training", "pay for materials", "send money", "transfer money", "pay via bitcoin", "pay via crypto", "send bitcoin", "payment required before", "advance payment"]
        p7_match = phrase_match(txt, p7Phrases)
        if p7_match:
            raw_threats.append({"penalty": 60, "message": f'Requires upfront payment ("{p7_match}").', "paramId": 7, "severity": "crit", "category": "financial", "trustPiercing": False})

        p8Phrases = ["interview on telegram", "interview via telegram", "interview through telegram", "contact on telegram", "contact via telegram", "add on telegram", "message on telegram", "join telegram group", "telegram group for interview", "interview on whatsapp", "interview via whatsapp", "apply on whatsapp", "send resume on whatsapp", "send cv on whatsapp", "whatsapp interview", "contact on whatsapp", "reach us on whatsapp", "interview on signal", "download signal app", "use signal for", "interview via wire", "download wire app"]
        p8_match = phrase_match(txt, p8Phrases)
        if p8_match:
            raw_threats.append({"penalty": 30, "message": f'Conducts recruitment via unofficial channel ("{p8_match}").', "paramId": 8, "severity": "warn", "category": "communication", "trustPiercing": False})

        p9Phrases = ["earn unlimited", "unlimited earning", "daily payout", "earn from home easily", "easy money", "earn lakhs", "earn thousands daily", "guaranteed income", "fixed daily income", "earn without working", "passive income guaranteed", "make money fast", "get rich quick"]
        p9_match = phrase_match(txt, p9Phrases)
        if p9_match:
            raw_threats.append({"penalty": 20, "message": f'Uses unrealistic earning promises ("{p9_match}").', "paramId": 9, "severity": "warn", "category": "language", "trustPiercing": False})

        p10Phrases = ["act now or lose", "hurry up and apply", "last few vacancies", "closing today", "apply immediately before", "don't miss this chance", "only today", "offer expires", "limited time offer", "urgent hiring apply now", "respond immediately"]
        p10_match = phrase_match(txt, p10Phrases)
        if p10_match:
            raw_threats.append({"penalty": 15, "message": f'Uses pressure tactics ("{p10_match}").', "paramId": 10, "severity": "warn", "category": "language", "trustPiercing": False})

        p11Phrases = ["no skills required", "no qualification required", "no qualification needed", "anyone can apply", "any degree any branch", "just need a smartphone", "just need a phone", "just need a laptop", "no interview required", "no experience no problem", "housewife can also do", "students can earn", "earn from your phone"]
        p11_match = phrase_match(txt, p11Phrases)
        if p11_match:
            raw_threats.append({"penalty": 20, "message": f'Suspiciously low requirements ("{p11_match}").', "paramId": 11, "severity": "warn", "category": "language", "trustPiercing": False})

        p13Phrases = ["bit.ly/", "tinyurl.com/", "forms.gle/", "docs.google.com/forms", "jotform.com/", "typeform.com/", "apply at bit.ly", "fill this form bit.ly", "register at tinyurl"]
        p13_match = phrase_match(txt, p13Phrases)
        if p13_match:
            raw_threats.append({"penalty": 25, "message": f"Uses shortened URL or free form builder.", "paramId": 13, "severity": "warn", "category": "technical", "trustPiercing": False})

        p14Phrases = ["we will send you a check", "send you a check", "purchase your own equipment", "buy your own laptop", "buy your own equipment", "vendor payment", "buy supplies with the check", "deposit the check", "cash the check", "use the funds to buy"]
        p14_match = phrase_match(txt, p14Phrases)
        if p14_match:
            raw_threats.append({"penalty": 60, "message": f'Matches Fake Check scam pattern ("{p14_match}").', "paramId": 14, "severity": "crit", "category": "financial", "trustPiercing": False})

        exc_punc = len(re.findall(r'[!]{4,}', txt)) + len(re.findall(r'[?]{4,}', txt))
        exc_sym = len(re.findall(r'[$₹€£]{3,}', txt))
        if exc_punc + exc_sym >= 2:
            raw_threats.append({"penalty": 12, "message": "Multiple instances of excessive punctuation/symbols.", "paramId": 15, "severity": "warn", "category": "quality", "trustPiercing": False})

        p16Phrases = ["be your own boss", "build your downline", "downline", "multi-level marketing", "network marketing opportunity", "join my team and earn", "refer and earn unlimited", "chain referral", "pyramid"]
        p16_match = phrase_match(txt, p16Phrases)
        if p16_match:
            raw_threats.append({"penalty": 25, "message": f'Contains MLM/Pyramid language ("{p16_match}").', "paramId": 16, "severity": "warn", "category": "scheme", "trustPiercing": False})

        p17Phrases = ["guaranteed placement", "100% selection", "direct joining", "100% job guarantee", "guaranteed job", "confirm joining", "sure selection", "guaranteed offer letter"]
        p17_match = phrase_match(txt, p17Phrases)
        if p17_match:
            raw_threats.append({"penalty": 30, "message": f'Promises guaranteed selection ("{p17_match}").', "paramId": 17, "severity": "crit", "category": "language", "trustPiercing": False})

        if len(txt) < 200:
            raw_threats.append({"penalty": 15, "message": "[P18] Job description is extremely short.", "paramId": 18, "severity": "warn", "category": "quality", "trustPiercing": False})
        elif len(txt) < 400:
            raw_threats.append({"penalty": 5, "message": "[P18] Job description is shorter than typical.", "paramId": 18, "severity": "info", "category": "quality", "trustPiercing": False})
        else:
            trust_score += 5

        emoji_count = count_emojis(txt)
        if emoji_count > 12:
            raw_threats.append({"penalty": 25, "message": f'Excessive emoji usage ({emoji_count} emojis).', "paramId": 19, "severity": "crit", "category": "quality", "trustPiercing": False})
        elif emoji_count > 6:
            raw_threats.append({"penalty": 10, "message": f'Elevated emoji count ({emoji_count}).', "paramId": 19, "severity": "warn", "category": "quality", "trustPiercing": False})

        ghost_count = count_ghost_chars(full_text)
        if ghost_count > 5:
            raw_threats.append({"penalty": 40, "message": f'{ghost_count} hidden zero-width characters found.', "paramId": 20, "severity": "crit", "category": "steganography", "trustPiercing": False})
        elif ghost_count > 0:
            raw_threats.append({"penalty": 15, "message": f'{ghost_count} invisible Unicode character(s).', "paramId": 20, "severity": "warn", "category": "steganography", "trustPiercing": False})

        if len(txt) < 50:
            raw_threats.append({"penalty": 5, "message": "[P12] Text too short for plagiarism analysis.", "paramId": 12, "severity": "info", "category": "quality", "trustPiercing": False})

    # CORROBORATION ENGINE (Phase 3)
    threat_categories = {t["category"] for t in raw_threats}
    category_count = len(threat_categories)
    
    crit_count = sum(1 for t in raw_threats if t["severity"] == "crit")
    warn_count = sum(1 for t in raw_threats if t["severity"] == "warn")
    total_signals = crit_count + warn_count

    adjusted_penalty = 0
    crit_penalty_sum = 0

    for thread in raw_threats:
        effective_penalty = thread["penalty"]
        
        if not thread.get("trustPiercing", False):
            if trust_tier == 3:
                if thread["severity"] == "info": effective_penalty = 0
                elif thread["severity"] == "warn": effective_penalty = int(effective_penalty * 0.4)
            elif trust_tier == 2:
                if thread["severity"] == "info": effective_penalty = int(effective_penalty * 0.25)
                elif thread["severity"] == "warn": effective_penalty = int(effective_penalty * 0.7)
                
        if thread["severity"] == "crit": crit_penalty_sum += effective_penalty
        adjusted_penalty += effective_penalty

    has_identity_crit = any(t["severity"] == "crit" and t["category"] == "identity" for t in raw_threats)
    
    if total_signals == 1 and crit_count == 0:
        adjusted_penalty = int(adjusted_penalty * 0.3)
    elif total_signals == 1 and crit_count == 1 and not has_identity_crit:
        adjusted_penalty = int(adjusted_penalty * 0.7)

    if category_count >= 4 and crit_count >= 2:
        adjusted_penalty = int(adjusted_penalty * 1.15)
    elif category_count >= 3 and total_signals >= 3:
        adjusted_penalty = int(adjusted_penalty * 1.1)

    if crit_count > 0:
        min_survival = int(crit_penalty_sum * 0.4)
        adjusted_penalty = max(min_survival, adjusted_penalty - trust_score)
    else:
        adjusted_penalty = max(0, adjusted_penalty - trust_score)

    final_score = min(100, adjusted_penalty)

    for threat in raw_threats:
        if trust_tier == 3 and threat["severity"] == "info": continue
        if trust_tier == 2 and threat["severity"] == "info" and threat["penalty"] <= 5: continue

        if threat["severity"] == "crit":
            flags.append(f"CRIT: {threat['message']}")
        else:
            flags.append(f"WARN: {threat['message']}")

    return {
        "final_score": float(final_score),
        "trust_tier": trust_tier,
        "flags": flags,
        "raw_threats": raw_threats
    }

