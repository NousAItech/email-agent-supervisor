import re
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional


@dataclass
class Email:
    sender: str
    subject: str
    body: str


FREE_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "live.com", "icloud.com", "proton.me", "protonmail.com"
}

ROLE_TERMS = [
    "ceo", "cfo", "coo", "cto", "chairman", "board", "director", "vp", "vice president",
    "general counsel", "legal counsel", "head of", "founder", "owner", "president",
    "dirección", "director", "consejo", "presidente", "propietario", "fundador", "asesoría jurídica"
]

URGENCY_TERMS = [
    "urgent", "asap", "immediately", "today", "right away", "time-sensitive", "confidential",
    "urgente", "inmediato", "hoy", "confidencial", "reservado"
]

SECURITY_TERMS = [
    "password", "reset", "2fa", "authentication", "login", "breach", "hack", "phishing",
    "contraseña", "acceso", "intrusión", "hackeo", "suplantación", "phishing",
    "wire transfer", "bank details", "change payment", "invoice change",
    "transferencia", "cambiar pago", "cambio de cuenta", "datos bancarios"
]

INTENT_RULES = {
    "M_AND_A": {
        "weight": 5,
        "terms": [
            "acquire", "acquisition", "buy your company", "purchase your company", "merger", "m&a",
            "investment proposal", "valuation", "term sheet", "due diligence", "equity", "stake",
            "adquirir", "compra de la empresa", "comprar la compañía", "fusión", "adquisición",
            "oferta de compra", "valoración", "participación", "inversión"
        ]
    },
    "LEGAL": {
        "weight": 4,
        "terms": [
            "contract", "agreement", "nda", "gdpr", "compliance", "lawsuit", "legal notice",
            "contrato", "acuerdo", "nda", "rgpd", "cumplimiento", "demanda", "notificación legal"
        ]
    },
    "SECURITY": {
        "weight": 5,
        "terms": SECURITY_TERMS
    },
    "SALES": {
        "weight": 2,
        "terms": [
            "pricing", "quote", "proposal", "demo", "partnership", "reseller",
            "precio", "presupuesto", "propuesta", "demostración", "colaboración"
        ]
    },
    "SUPPORT": {
        "weight": 1,
        "terms": [
            "help", "issue", "bug", "problem", "doesn't work", "error",
            "ayuda", "incidencia", "fallo", "no funciona", "problema"
        ]
    }
}


def extract_email_domain(sender: str) -> Optional[str]:
    m = re.search(r"@([A-Za-z0-9.-]+\.[A-Za-z]{2,})", sender)
    return m.group(1).lower() if m else None


def contains_any(text: str, terms: List[str]) -> bool:
    t = text.lower()
    return any(term in t for term in terms)


def count_any(text: str, terms: List[str]) -> int:
    t = text.lower()
    return sum(1 for term in terms if term in t)


def find_money(text: str) -> List[str]:
    patterns = [
        r"€\s?\d[\d.,]*\b",
        r"\$\s?\d[\d.,]*\b",
        r"\b\d[\d.,]*\s?(m|million|millones|b|billion|mil)\b",
        r"\b\d{2,}\s?€\b",
        r"\b\d{2,}\s?\$\b",
    ]
    found = []
    for p in patterns:
        found.extend(re.findall(p, text, flags=re.IGNORECASE))
    return list(set([str(x) for x in found if str(x).strip()]))


def find_urls(text: str) -> List[str]:
    return list(set(re.findall(r"https?://\S+|www\.\S+", text, flags=re.IGNORECASE)))


def find_phones(text: str) -> List[str]:
    return list(set(re.findall(r"\+?\d[\d\s().-]{7,}\d", text)))


def score_intents(subject: str, body: str) -> Tuple[Dict[str, int], Dict[str, List[str]]]:
    text = (subject + "\n" + body).lower()
    scores = {k: 0 for k in INTENT_RULES.keys()}
    evidence = {k: [] for k in INTENT_RULES.keys()}

    for intent, rule in INTENT_RULES.items():
        hits = []
        for term in rule["terms"]:
            if term.lower() in text:
                hits.append(term)
        if hits:
            scores[intent] += rule["weight"] * len(set(hits))
            evidence[intent] = sorted(set(hits))

    return scores, evidence


def extract_features(email: Email) -> Dict:
    domain = extract_email_domain(email.sender) or ""
    sender_is_free = domain in FREE_DOMAINS if domain else True

    text = f"{email.subject}\n{email.body}"

    return {
        "sender_domain": domain,
        "sender_is_free_domain": sender_is_free,
        "mentions_roles": contains_any(text, ROLE_TERMS),
        "role_hits": count_any(text, ROLE_TERMS),
        "mentions_urgency": contains_any(text, URGENCY_TERMS),
        "urgency_hits": count_any(text, URGENCY_TERMS),
        "money_mentions": find_money(text),
        "urls": find_urls(text),
        "phones": find_phones(text),
        "length": len(text),
    }


def decide_action(email: Email) -> Dict:
    scores, intent_evidence = score_intents(email.subject, email.body)
    features = extract_features(email)

    support_like = scores.get("SUPPORT", 0) >= 1
    security_like = scores.get("SECURITY", 0) > 0
    strong_security_terms = ["breach", "hack", "phishing", "wire transfer", "bank details", "datos bancarios", "transferencia"]
    text_all = (email.subject + "\n" + email.body).lower()
    has_strong_security = any(t in text_all for t in strong_security_terms)

    if support_like and security_like and not has_strong_security:
        scores["SECURITY"] = 0

    strategic_risk = 0.0
    strategic_risk += scores.get("M_AND_A", 0) * 1.2
    strategic_risk += (4 if features["mentions_roles"] else 0)
    strategic_risk += (2 if features["mentions_urgency"] else 0)
    strategic_risk += (3 if features["money_mentions"] else 0)

    operational_risk = 0.0
    operational_risk += scores.get("SECURITY", 0) * 1.3
    operational_risk += scores.get("LEGAL", 0) * 1.1

    trust_penalty = 0.0
    if features["sender_is_free_domain"]:
        trust_penalty += 2
    if len(features["urls"]) >= 2:
        trust_penalty += 2
    if len(features["phones"]) >= 1 and scores.get("SECURITY", 0) > 0:
        trust_penalty += 2

    total_risk = strategic_risk + operational_risk + trust_penalty

    if scores.get("SECURITY", 0) >= 10 and trust_penalty >= 3:
        action = "BLOCK"
    elif scores.get("M_AND_A", 0) >= 5 or scores.get("LEGAL", 0) >= 8:
        action = "ESCALATE_HUMAN"
    elif (features["mentions_roles"] and features["mentions_urgency"] and features["money_mentions"]):
        action = "ESCALATE_HUMAN"
    elif total_risk >= 10:
        action = "ESCALATE_HUMAN"
    else:
        action = "AUTO_REPLY"

    return {
        "action": action,
        "risk": round(total_risk, 2),
        "intent_scores": scores,
        "intent_evidence": intent_evidence,
        "features": features
    }


def read_multiline(prompt: str) -> str:
    print(prompt)
    lines = []
    while True:
        line = input()
        if line == "":
            break
        lines.append(line)
    return "\n".join(lines)


def main():
    print("\n=== Email Agent Supervisor — Demo ===\n")
    sender = input("Sender (e.g., john@company.com): ").strip()
    subject = input("Subject: ").strip()
    body = read_multiline("Paste email body (finish with an empty line):")

    email = Email(sender=sender, subject=subject, body=body)
    decision = decide_action(email)

    print("\n--- Decision ---")
    print("Action:", decision["action"])
    print("Risk score:", decision["risk"])

    print("\n--- Intent scores ---")
    for k, v in decision["intent_scores"].items():
        print(f"{k}: {v}")

    print("\n--- Evidence (matched signals) ---")
    for k, ev in decision["intent_evidence"].items():
        if ev:
            print(f"{k}: {ev}")

    print("\n--- Extracted features ---")
    f = decision["features"]
    print("sender_domain:", f["sender_domain"])
    print("sender_is_free_domain:", f["sender_is_free_domain"])
    print("mentions_roles:", f["mentions_roles"])
    print("mentions_urgency:", f["mentions_urgency"])
    print("money_mentions:", f["money_mentions"])
    print("urls:", f["urls"])
    print("phones:", f["phones"])


if __name__ == "__main__":
    main()
