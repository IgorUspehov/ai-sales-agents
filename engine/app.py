import json
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
PACKS = ROOT / "packs"
app = FastAPI(title="AI Sales Agents")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
LINES = {
    "de": ["Guten Tag. Entscheiden Sie, ob ein neues Gebiet angefangen wird?", "In welcher PLZ haben Sie jetzt freie Kapazitäten? Einen neuen Klienten garantieren wir nicht.", "Ist die Zulassung aktiv?", "Gibt es dort jetzt freie Besuche?", "Was nehmen Sie nicht an?", "Welche Nummer nimmt ab, und welche Ersatznummer bekommt die SMS?", "Wie heisst der Dienst?", "Anfrage aufgenommen. Schriftliche Antwort. Keine Klient-Garantie."],
    "en": ["Hello. Do you decide a new area?", "Which postcode has free capacity now? We do not guarantee a new client.", "Is the licence active?", "Are visits free there now?", "What do you not take?", "Which number answers, and which backup gets the SMS?", "What is the service called?", "Enquiry recorded. Written reply. No client guarantee."],
    "ru": ["Здравствуйте. Вы решаете, открывать ли новый район?", "В каком индексе сейчас есть свободные визиты? Нового клиента не гарантируем.", "Допуск активен?", "Свободные визиты есть сейчас?", "Кого не берёте?", "Какой номер берёт трубку, и какой запасной получает SMS?", "Как называется служба?", "Заявка записана. Ответ письменно. Клиента не гарантируем."],
}
class BuildIn(BaseModel):
    niche: str = "pflegedienst"
    business: str = ""
    city: str = ""
    language: str = "de"
    contact: str = ""
    phone: str = ""
    email: str = ""
    never: str = ""
class TalkIn(BaseModel):
    language: str = "de"
    step: int = 0
    text: str = ""
    card: dict = {}
def load_pack(niche: str) -> dict:
    path = PACKS / niche / "pack.json"
    if not path.exists():
        path = PACKS / "pflegedienst" / "pack.json"
    return json.loads(path.read_text())
def lang(code: str) -> str:
    return code if code in LINES else "de"
@app.get("/health")
def health():
    return {"ok": True}
@app.get("/packs")
def packs():
    return {"packs": [p.name for p in PACKS.iterdir() if (p / "pack.json").exists()]}
@app.post("/build")
def build(body: BuildIn):
    pack = load_pack(body.niche)
    return {"manifest": {"niche": pack["id"], "business": body.business, "city": body.city, "language": lang(body.language), "contact": body.contact, "phone": body.phone, "email": body.email, "never": pack["never"], "price": pack["price"], "setup": pack["setup"], "steps": pack["steps"]}}
@app.post("/talk")
def talk(body: TalkIn):
    code = lang(body.language)
    lines = LINES[code]
    card = dict(body.card)
    text = body.text.lower()
    step = body.step
    if body.text:
        if step == 1: card["area"] = body.text
        elif step == 2: card["licence"] = "no" if any(w in text for w in ("nein", "no", "нет", "ні")) else "yes"
        elif step == 3: card["free_now"] = "no" if any(w in text for w in ("nein", "no", "нет", "ні")) else "yes"
        elif step == 4: card["exclude"] = body.text
        elif step == 5: card["phone"] = body.text
        elif step == 6: card["service"] = body.text
        step = min(step + 1, len(lines) - 1)
    stopped = card.get("licence") == "no" or card.get("free_now") == "no"
    say = lines[step]
    if stopped and code == "de": say = "Ohne Zulassung und freie Besuche starten wir nicht."
    if stopped and code == "ru": say = "Без допуска и свободных визитов не стартуем."
    if stopped and code == "en": say = "Without a licence and free visits we do not start."
    ready = bool(card.get("area") and card.get("phone") and card.get("service") and not stopped)
    return {"say": say, "step": step, "card": card, "ready": ready, "stopped": stopped}
