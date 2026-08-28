import json
import os
import shutil
import smtplib
import ssl
import tempfile
import uuid
import zipfile
from datetime import date, datetime, timedelta
from email.message import EmailMessage
from io import BytesIO
from pathlib import Path

import streamlit as st
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


APP_NAME = "Mein Handwerksassistent"
APP_VERSION = "5.3 Nordwerk Cloud"

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
BACKUP_DIR = BASE_DIR / "backups"

KUNDEN_DATEI = DATA_DIR / "kunden.json"
ANGEBOTE_DATEI = DATA_DIR / "angebote.json"
FIRMA_DATEI = DATA_DIR / "firma.json"
EINSTELLUNGEN_DATEI = DATA_DIR / "einstellungen.json"
LEADS_DATEI = DATA_DIR / "leads.json"
VORLAGEN_DATEI = DATA_DIR / "vorlagen.json"
RECHNUNGEN_DATEI = DATA_DIR / "rechnungen.json"

STATUS = ["Entwurf", "Gesendet", "Angenommen", "Abgelehnt"]
RECHNUNGS_STATUS = ["Offen", "Bezahlt", "Storniert"]
LEAD_STATUS = ["Neu", "Kontaktiert", "Angebot erstellt", "Gewonnen", "Verloren"]
POSITIONSTYPEN = ["Leistung", "Material"]
EINHEITEN = ["Stk.", "Std.", "m²", "m", "lfm", "kg", "Pauschal"]

LEISTUNGSBEREICHE = [
    "Badezimmer", "Küche", "Dach", "Fenster", "Renovierung",
    "Sanierung", "Trockenbau", "Bodenbeläge", "Malerarbeiten",
    "Elektroarbeiten", "Heizung / Sanitär",
    "Allgemeine Handwerksleistung", "Sonstiges",
]

STANDARD_FIRMA = {
    "name": "Nordwerk Handwerk & Sanierung",
    "inhaber": "Daniel Hartmann",
    "strasse": "Werkstraße 18",
    "plz": "30159",
    "ort": "Hannover",
    "telefon": "0511 000000",
    "email": "kontakt@nordwerk-beispiel.de",
    "website": "www.nordwerk-beispiel.de",
    "steuernummer": "",
    "ust_id": "",
    "bank": "",
    "iban": "",
    "bic": "",
    "abschluss_text": "Vielen Dank für Ihr Vertrauen. Wir freuen uns auf die Zusammenarbeit.",
}

STANDARD_EINSTELLUNGEN = {
    "mwst": 19.0,
    "zahlungsziel": 14,
    "gueltigkeit": 30,
    "erinnerung_nach_tagen": 3,
    "zweite_erinnerung_nach_tagen": 7,
    "auto_rechnung": True,
    "smtp_host": "",
    "smtp_port": 587,
    "smtp_user": "",
    "smtp_sender": "",
    "smtp_tls": True,
}

STANDARD_VORLAGEN = [
    {
        "id": "VOR-000001",
        "name": "Badezimmer Basis",
        "leistungsbereich": "Badezimmer",
        "positionen": [
            {
                "typ": "Leistung",
                "name": "Demontage und Vorbereitung",
                "beschreibung": "Rückbau vorhandener Bauteile und Vorbereitung der Arbeitsfläche.",
                "menge": 1.0,
                "einheit": "Pauschal",
                "preis": 650.0,
            },
            {
                "typ": "Leistung",
                "name": "Montage- und Sanierungsarbeiten",
                "beschreibung": "Ausführung der vereinbarten Handwerksarbeiten.",
                "menge": 16.0,
                "einheit": "Std.",
                "preis": 62.0,
            },
        ],
        "kundennotiz": "Ausführung nach gemeinsamer Terminabstimmung. Änderungen des Leistungsumfangs werden vorab abgestimmt.",
    }
]


st.set_page_config(
    page_title=APP_NAME,
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
:root{
  --bg:#f6f8fc;
  --surface:#ffffff;
  --surface-soft:#f8fafc;
  --border:#e5eaf2;
  --text:#0f172a;
  --muted:#64748b;
  --navy:#081a33;
  --navy2:#0b2344;
  --blue:#1769ff;
  --blue2:#2d7dff;
  --green:#16a34a;
  --orange:#f59e0b;
  --purple:#6d5dfc;
}

html, body, .stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"]{
  background:var(--bg)!important;
  color:var(--text)!important;
}

.block-container{
  max-width:1380px;
  padding-top:1.4rem;
  padding-bottom:4rem;
  padding-left:1.7rem;
  padding-right:1.7rem;
}

h1,h2,h3,h4,h5,h6{
  color:var(--text)!important;
  letter-spacing:-.025em;
}

p, span, label, div{
  text-rendering:optimizeLegibility;
}

/* SIDEBAR */
[data-testid="stSidebar"]{
  background:
    radial-gradient(circle at 20% 10%, rgba(59,130,246,.08), transparent 24%),
    linear-gradient(180deg,var(--navy) 0%,var(--navy2) 100%)!important;
  border-right:1px solid rgba(255,255,255,.05);
}

[data-testid="stSidebar"] [data-testid="stSidebarContent"]{
  padding-top:1rem;
}

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] small{
  color:#f8fafc!important;
}

[data-testid="stSidebar"] hr{
  border-color:rgba(255,255,255,.09)!important;
}

[data-testid="stSidebar"] .stButton>button{
  width:100%;
  min-height:46px;
  justify-content:flex-start;
  background:transparent!important;
  color:#eef4ff!important;
  border:1px solid transparent!important;
  border-radius:12px!important;
  padding:.55rem .85rem!important;
  font-weight:650!important;
  box-shadow:none!important;
  transition:.16s ease;
}

[data-testid="stSidebar"] .stButton>button:hover{
  background:rgba(255,255,255,.07)!important;
  border-color:rgba(255,255,255,.06)!important;
  transform:translateY(-1px);
}

[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"]{
  background:linear-gradient(135deg,var(--blue),var(--blue2))!important;
  color:#fff!important;
  border-color:rgba(255,255,255,.1)!important;
  box-shadow:0 8px 20px rgba(23,105,255,.28)!important;
}

[data-testid="stSidebar"] button *{
  color:inherit!important;
}

/* HERO */
.hero-pro{
  position:relative;
  overflow:hidden;
  border-radius:24px;
  padding:30px 34px;
  margin:0 0 26px 0;
  background:
    radial-gradient(circle at 78% 20%,rgba(255,255,255,.55),transparent 18%),
    linear-gradient(135deg,#eef5ff 0%,#e8f1ff 46%,#dceaff 100%);
  border:1px solid #d9e6fb;
  box-shadow:0 16px 38px rgba(15,23,42,.06);
}

.hero-pro:after{
  content:"";
  position:absolute;
  right:34px;
  top:24px;
  width:210px;
  height:120px;
  border-radius:28px;
  background:
    linear-gradient(135deg,rgba(23,105,255,.12),rgba(59,130,246,.04));
  transform:skewX(-8deg);
}

.hero-eyebrow{
  display:inline-flex;
  align-items:center;
  justify-content:center;
  width:54px;
  height:54px;
  border-radius:16px;
  background:#fff;
  border:1px solid #dce7f8;
  box-shadow:0 8px 22px rgba(37,99,235,.10);
  font-size:1.45rem;
  margin-bottom:14px;
}

.hero-pro h1{
  margin:0;
  font-size:2rem;
  line-height:1.1;
  font-weight:800;
  color:#0b1f3a!important;
}

.hero-pro p{
  margin:12px 0 0;
  color:#334155!important;
  font-size:1rem;
  max-width:720px;
  line-height:1.55;
}

/* KPI CARDS */
.kpi-grid{
  display:grid;
  grid-template-columns:repeat(5,minmax(0,1fr));
  gap:14px;
  margin-bottom:22px;
}

.kpi-card{
  background:#fff;
  border:1px solid var(--border);
  border-radius:18px;
  padding:16px 16px 14px;
  min-height:132px;
  box-shadow:0 8px 24px rgba(15,23,42,.045);
}

.kpi-icon{
  width:44px;
  height:44px;
  border-radius:50%;
  display:flex;
  align-items:center;
  justify-content:center;
  font-size:1.1rem;
  margin-bottom:12px;
}

.kpi-icon.blue{background:#e9f2ff;color:#1769ff}
.kpi-icon.purple{background:#f0edff;color:#6d5dfc}
.kpi-icon.green{background:#eaf8ef;color:#16a34a}
.kpi-icon.orange{background:#fff3e1;color:#f59e0b}

.kpi-title{
  color:#24324a!important;
  font-size:.82rem;
  font-weight:700;
  min-height:38px;
}

.kpi-number{
  color:#0f172a!important;
  font-size:1.12rem;
  line-height:1.25;
  font-weight:800;
  margin:8px 0 6px;
  letter-spacing:-.025em;
  word-break:normal;
}

.kpi-sub{
  color:#7a889d!important;
  font-size:.74rem;
  line-height:1.35;
}

/* SECTION CARDS */
.panel{
  background:#fff;
  border:1px solid var(--border);
  border-radius:18px;
  padding:22px 24px;
  box-shadow:0 8px 24px rgba(15,23,42,.04);
}

.panel-title{
  display:flex;
  align-items:center;
  gap:10px;
  font-weight:800;
  font-size:1.02rem;
  color:#172033!important;
  margin-bottom:16px;
}

.activity-row{
  display:grid;
  grid-template-columns:1fr auto;
  gap:18px;
  align-items:center;
  padding:16px 0;
  border-top:1px solid #edf1f6;
}

.activity-row:first-of-type{
  border-top:none;
}

.activity-main{
  display:flex;
  gap:12px;
  align-items:flex-start;
}

.activity-icon{
  width:38px;
  height:38px;
  border-radius:50%;
  display:flex;
  align-items:center;
  justify-content:center;
  background:#edf6ff;
  color:#1769ff;
  flex:0 0 auto;
}

.activity-name{
  font-size:.9rem;
  color:#172033!important;
  font-weight:700;
  margin-bottom:3px;
}

.activity-meta{
  font-size:.72rem;
  color:#8793a5!important;
}

.status-pill{
  display:inline-flex;
  align-items:center;
  padding:5px 10px;
  border-radius:999px;
  font-size:.7rem;
  font-weight:750;
  white-space:nowrap;
}
.status-pill.green{background:#eaf8ef;color:#15803d}
.status-pill.blue{background:#eaf2ff;color:#1d4ed8}
.status-pill.orange{background:#fff4e6;color:#b45309}
.status-pill.red{background:#fef2f2;color:#b91c1c}

.automation-item{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:14px;
  padding:13px 0;
  border-top:1px solid #edf1f6;
}

.automation-item:first-of-type{border-top:none}

.automation-left{
  display:flex;
  align-items:center;
  gap:12px;
  color:#1f2937!important;
  font-size:.87rem;
  font-weight:650;
}

.auto-icon{
  width:36px;
  height:36px;
  border-radius:50%;
  display:flex;
  align-items:center;
  justify-content:center;
  background:#eef5ff;
  color:#1769ff;
}

.auto-badge{
  padding:5px 12px;
  border-radius:999px;
  background:#eaf8ef;
  color:#15803d!important;
  font-size:.72rem;
  font-weight:800;
}

.note-box{
  margin-top:18px;
  background:#f3f7ff;
  border:1px solid #d9e6fb;
  color:#36506f!important;
  border-radius:12px;
  padding:13px 14px;
  font-size:.75rem;
  line-height:1.45;
}

/* General Streamlit widgets */
[data-testid="stMetric"]{
  background:#fff!important;
  border:1px solid var(--border)!important;
  border-radius:16px!important;
  padding:14px 16px!important;
  box-shadow:0 6px 18px rgba(15,23,42,.04);
}

[data-testid="stMetricValue"]{
  font-size:1.35rem!important;
  line-height:1.25!important;
}

[data-testid="stMetricLabel"]{
  font-size:.78rem!important;
}

div[data-testid="stVerticalBlockBorderWrapper"]{
  background:#fff!important;
  border-color:var(--border)!important;
  border-radius:16px!important;
}

.stButton>button,.stDownloadButton>button{
  min-height:42px;
  border-radius:11px!important;
  font-weight:700!important;
}

[data-testid="stMain"] button[data-testid="stBaseButton-primary"]{
  background:linear-gradient(135deg,var(--blue),var(--blue2))!important;
  color:#fff!important;
  border-color:var(--blue)!important;
}

[data-baseweb="input"]>div,
[data-baseweb="textarea"]>div,
[data-baseweb="select"]>div,
.stTextInput input,
.stTextArea textarea,
.stNumberInput input{
  background:#fff!important;
  color:var(--text)!important;
  border-color:#d9e1ec!important;
}

hr{border-color:#e7ebf2!important}

/* Existing status */
.status{
  display:inline-flex;
  padding:5px 10px;
  border-radius:999px;
  font-size:.72rem;
  font-weight:750;
  border:1px solid transparent;
}
.status-entwurf,.status-neu{background:#f1f5f9;color:#475569!important;border-color:#e2e8f0}
.status-gesendet,.status-kontaktiert{background:#eff6ff;color:#1d4ed8!important;border-color:#bfdbfe}
.status-angenommen,.status-gewonnen,.status-bezahlt{background:#f0fdf4;color:#15803d!important;border-color:#bbf7d0}
.status-abgelehnt,.status-verloren,.status-storniert,.status-überfällig{background:#fef2f2;color:#b91c1c!important;border-color:#fecaca}
.status-ausstehend,.status-offen,.status-angebot-erstellt,.status-offene-rechnung{background:#fff7ed;color:#b45309!important;border-color:#fed7aa}

/* Customer portal */
.portal-head{
  background:#fff;
  border:1px solid var(--border);
  border-radius:22px;
  padding:28px;
  box-shadow:0 12px 32px rgba(15,23,42,.06);
}

.portal-price{
  font-size:2rem;
  font-weight:800;
  letter-spacing:-.035em;
  color:#0f172a!important;
}

@media(max-width:1180px){
  .kpi-grid{grid-template-columns:repeat(3,minmax(0,1fr))}
}

@media(max-width:800px){
  .block-container{padding-left:1rem;padding-right:1rem}
  .kpi-grid{grid-template-columns:1fr 1fr}
  .hero-pro{padding:22px}
  .hero-pro h1{font-size:1.55rem}
  .hero-pro:after{display:none}
}

@media(max-width:560px){
  .kpi-grid{grid-template-columns:1fr}
}
</style>
""", unsafe_allow_html=True)


def copy_json(value):
    return json.loads(json.dumps(value, ensure_ascii=False))


def atomic_save(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.stem}_", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def load_json(path: Path, default):
    if not path.exists():
        atomic_save(path, default)
        return copy_json(default)
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError, TypeError):
        return copy_json(default)


def migrate_old_file(filename, target, default):
    target.parent.mkdir(parents=True, exist_ok=True)
    old = BASE_DIR / filename
    if not target.exists():
        if old.exists():
            try:
                shutil.copy2(old, target)
            except OSError:
                atomic_save(target, default)
        else:
            atomic_save(target, default)


for fn, target, default in [
    ("kunden.json", KUNDEN_DATEI, []),
    ("angebote.json", ANGEBOTE_DATEI, []),
    ("firma.json", FIRMA_DATEI, STANDARD_FIRMA),
    ("einstellungen.json", EINSTELLUNGEN_DATEI, STANDARD_EINSTELLUNGEN),
]:
    migrate_old_file(fn, target, default)

kunden = load_json(KUNDEN_DATEI, [])
angebote = load_json(ANGEBOTE_DATEI, [])
firma = load_json(FIRMA_DATEI, STANDARD_FIRMA)
einstellungen = load_json(EINSTELLUNGEN_DATEI, STANDARD_EINSTELLUNGEN)
leads = load_json(LEADS_DATEI, [])
vorlagen = load_json(VORLAGEN_DATEI, STANDARD_VORLAGEN)
rechnungen = load_json(RECHNUNGEN_DATEI, [])

for k, v in STANDARD_FIRMA.items():
    firma.setdefault(k, v)
for k, v in STANDARD_EINSTELLUNGEN.items():
    einstellungen.setdefault(k, v)

# Migration: Ein früherer Teststand konnte versehentlich 19,19 % speichern.
# Nur genau dieser bekannte Altwert wird auf 19,0 % korrigiert.
mwst_migration_geaendert = False
try:
    if abs(float(einstellungen.get("mwst", 19.0)) - 19.19) < 0.0001:
        einstellungen["mwst"] = 19.0
        mwst_migration_geaendert = True
except (TypeError, ValueError):
    pass
for _angebot in angebote:
    try:
        if abs(float(_angebot.get("mwst_satz", 19.0)) - 19.19) < 0.0001:
            _angebot["mwst_satz"] = 19.0
            mwst_migration_geaendert = True
    except (TypeError, ValueError):
        pass
if mwst_migration_geaendert:
    atomic_save(EINSTELLUNGEN_DATEI, einstellungen)
    atomic_save(ANGEBOTE_DATEI, angebote)


def html_clean(value):
    """Entfernt führende Einrückung, damit Streamlit HTML nicht als Codeblock anzeigt."""
    import textwrap
    return textwrap.dedent(str(value)).strip()


def text(v):
    return str(v or "").strip()


def number(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def euro(v):
    return f"{number(v):,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def iso_now():
    return datetime.now().isoformat(timespec="seconds")


def parse_iso(raw):
    try:
        return datetime.fromisoformat(text(raw))
    except ValueError:
        return None


def valid_email(v):
    v = text(v)
    return not v or ("@" in v and "." in v.rsplit("@", 1)[-1])


def status_html(status):
    s = text(status).lower().replace(" ", "-")
    return f'<span class="status status-{s}">{text(status)}</span>'


def next_id(items, prefix, key="id"):
    vals = []
    for item in items:
        raw = text(item.get(key))
        if raw.startswith(prefix):
            try:
                vals.append(int(raw[len(prefix):]))
            except ValueError:
                pass
    return f"{prefix}{max(vals, default=0)+1:06d}"


def kunde_id_neu():
    return next_id(kunden, "KUN-")


def angebot_id_neu():
    return next_id(angebote, "ANG-ID-")


def lead_id_neu():
    return next_id(leads, "LEAD-")


def vorlage_id_neu():
    return next_id(vorlagen, "VOR-")


def rechnung_id_neu():
    return next_id(rechnungen, "RE-ID-")


def angebotsnummer_neu():
    prefix = f"ANG-{date.today():%Y%m%d}-"
    vals = []
    for a in angebote:
        raw = text(a.get("angebotsnummer"))
        if raw.startswith(prefix):
            try:
                vals.append(int(raw.rsplit("-", 1)[1]))
            except (ValueError, IndexError):
                pass
    return f"{prefix}{max(vals, default=0)+1:03d}"


def rechnungsnummer_neu():
    prefix = f"RE-{date.today():%Y%m%d}-"
    vals = []
    for r in rechnungen:
        raw = text(r.get("rechnungsnummer"))
        if raw.startswith(prefix):
            try:
                vals.append(int(raw.rsplit("-", 1)[1]))
            except (ValueError, IndexError):
                pass
    return f"{prefix}{max(vals, default=0)+1:03d}"


def kunde_finden(i):
    return next((x for x in kunden if x.get("id") == i), None)


def kunde_nach_name(n):
    target = text(n).casefold()
    return next((x for x in kunden if text(x.get("name")).casefold() == target), None)


def angebot_finden(i):
    return next((x for x in angebote if x.get("id") == i), None)


def rechnung_finden(i):
    return next((x for x in rechnungen if x.get("id") == i), None)


def lead_finden(i):
    return next((x for x in leads if x.get("id") == i), None)


def vorlage_finden(i):
    return next((x for x in vorlagen if x.get("id") == i), None)


def portal_angebot(token):
    return next((a for a in angebote if text(a.get("portal_token")) == text(token)), None)


def ensure_portal_token(a):
    if not text(a.get("portal_token")):
        a["portal_token"] = uuid.uuid4().hex
    return a["portal_token"]


def angebotswerte(a):
    positionen = sum(
        number(p.get("menge")) * number(p.get("preis"))
        for p in a.get("positionen", []) if isinstance(p, dict)
    )
    material = number(a.get("materialkosten"))
    arbeit = number(a.get("arbeitsstunden")) * number(a.get("stundensatz"))
    anfahrt = number(a.get("anfahrt"))
    zwischen = positionen + material + arbeit + anfahrt
    rp = max(0.0, min(100.0, number(a.get("rabatt_prozent"))))
    re = max(0.0, number(a.get("rabatt_euro")))
    rabatt = min(zwischen, zwischen * rp / 100 + re)
    netto = zwischen - rabatt
    mwst_satz = number(a.get("mwst_satz"), number(einstellungen.get("mwst"), 19.0))
    mwst = netto * mwst_satz / 100
    return {
        "positionen": positionen, "material": material, "arbeit": arbeit,
        "anfahrt": anfahrt, "zwischen": zwischen, "rabatt": rabatt,
        "netto": netto, "mwst": mwst, "brutto": netto + mwst,
        "mwst_satz": mwst_satz,
    }


def rechnungswerte(r):
    netto = number(r.get("netto"))
    mwst = number(r.get("mwst"))
    brutto = number(r.get("brutto"))
    return netto, mwst, brutto


def kunden_angebote(k):
    kid = k.get("id")
    n = text(k.get("name")).casefold()
    return [a for a in angebote if a.get("kunden_id") == kid or text(a.get("kundenname")).casefold() == n]


def angebot_gueltig_bis(a):
    tage = int(number(a.get("gueltigkeit_tage"), number(einstellungen.get("gueltigkeit"), 30)))
    try:
        d = datetime.strptime(text(a.get("datum")), "%d.%m.%Y").date()
    except ValueError:
        d = date.today()
    return (d + timedelta(days=tage)).strftime("%d.%m.%Y")


def save_all():
    atomic_save(KUNDEN_DATEI, kunden)
    atomic_save(ANGEBOTE_DATEI, angebote)
    atomic_save(FIRMA_DATEI, firma)
    atomic_save(EINSTELLUNGEN_DATEI, einstellungen)
    atomic_save(LEADS_DATEI, leads)
    atomic_save(VORLAGEN_DATEI, vorlagen)
    atomic_save(RECHNUNGEN_DATEI, rechnungen)


def navigate(page, **state):
    st.session_state.page = page
    for k, v in state.items():
        st.session_state[k] = v
    st.rerun()


def make_backup():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    target = BACKUP_DIR / datetime.now().strftime("backup_%Y%m%d_%H%M%S")
    target.mkdir(exist_ok=True)
    for path in [
        KUNDEN_DATEI, ANGEBOTE_DATEI, FIRMA_DATEI, EINSTELLUNGEN_DATEI,
        LEADS_DATEI, VORLAGEN_DATEI, RECHNUNGEN_DATEI
    ]:
        if path.exists():
            shutil.copy2(path, target / path.name)
    return target


def export_zip_bytes():
    b = BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        for path in [
            KUNDEN_DATEI, ANGEBOTE_DATEI, FIRMA_DATEI, EINSTELLUNGEN_DATEI,
            LEADS_DATEI, VORLAGEN_DATEI, RECHNUNGEN_DATEI
        ]:
            if path.exists():
                z.writestr(path.name, path.read_bytes())
    return b.getvalue()



def secret_value(name, default=""):
    try:
        return str(st.secrets.get(name, default)).strip()
    except Exception:
        return str(default).strip()


def cloud_gmail_address():
    return secret_value("GMAIL_ADDRESS", text(einstellungen.get("smtp_sender")))


def smtp_password():
    return secret_value("GMAIL_APP_PASSWORD", os.getenv("HANDWERK_SMTP_PASSWORD", ""))


def smtp_ready():
    address = cloud_gmail_address()
    return all([
        address,
        smtp_password(),
    ])


def email_senden(empfaenger, betreff, inhalt, pdf_bytes=None, pdf_name=None):
    empfaenger = text(empfaenger)

    if not smtp_ready():
        return False, "SMTP ist noch nicht vollständig eingerichtet. Bitte zuerst die E-Mail-Einstellungen prüfen."

    if not empfaenger:
        return False, "Es ist keine Empfänger-E-Mail-Adresse eingetragen."

    if not valid_email(empfaenger):
        return False, f"Die Empfänger-E-Mail-Adresse '{empfaenger}' ist ungültig."

    sender = text(einstellungen.get("smtp_sender"))
    if not valid_email(sender):
        return False, "Die Absender-E-Mail-Adresse in den SMTP-Einstellungen ist ungültig."

    try:
        msg = EmailMessage()
        msg["From"] = sender
        msg["To"] = empfaenger
        msg["Subject"] = text(betreff)
        msg.set_content(text(inhalt))

        if pdf_bytes and pdf_name:
            msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf", filename=pdf_name)

        host = "smtp.gmail.com"
        port = 587
        user = cloud_gmail_address()
        pwd = smtp_password()

        if einstellungen.get("smtp_tls", True):
            context = ssl.create_default_context()
            with smtplib.SMTP(host, port, timeout=25) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(user, pwd)
                server.send_message(msg)
        else:
            with smtplib.SMTP_SSL(host, port, timeout=25) as server:
                server.login(user, pwd)
                server.send_message(msg)

        return True, f"E-Mail wurde erfolgreich an {empfaenger} versendet."
    except smtplib.SMTPAuthenticationError:
        return False, "Gmail hat Benutzername oder App-Passwort abgelehnt. Bitte SMTP-Benutzer und App-Passwort prüfen."
    except smtplib.SMTPRecipientsRefused:
        return False, "Gmail hat die Empfängeradresse abgelehnt. Bitte die Kunden-E-Mail-Adresse prüfen."
    except smtplib.SMTPException as exc:
        return False, f"SMTP-Fehler beim Versand: {exc}"
    except Exception as exc:
        return False, f"E-Mail konnte nicht versendet werden: {exc}"


def rechnung_aus_angebot(a):
    existing = next((r for r in rechnungen if r.get("angebot_id") == a.get("id") and r.get("status") != "Storniert"), None)
    if existing:
        return existing

    v = angebotswerte(a)
    zahlungsziel = int(number(a.get("zahlungsziel"), number(einstellungen.get("zahlungsziel"), 14)))
    faellig = date.today() + timedelta(days=zahlungsziel)

    r = {
        "id": rechnung_id_neu(),
        "rechnungsnummer": rechnungsnummer_neu(),
        "angebot_id": a.get("id"),
        "angebotsnummer": a.get("angebotsnummer"),
        "kunden_id": a.get("kunden_id"),
        "kundenname": a.get("kundenname"),
        "kundenadresse": a.get("kundenadresse"),
        "kunden_email": a.get("kunden_email"),
        "datum": date.today().strftime("%d.%m.%Y"),
        "faellig_am": faellig.strftime("%d.%m.%Y"),
        "status": "Offen",
        "netto": v["netto"],
        "mwst": v["mwst"],
        "brutto": v["brutto"],
        "mwst_satz": v["mwst_satz"],
        "positionen": copy_json(a.get("positionen", [])),
        "erstellt_am": iso_now(),
        "bezahlt_am": "",
    }
    rechnungen.append(r)
    atomic_save(RECHNUNGEN_DATEI, rechnungen)
    return r


def angebot_angenommen(a):
    a["status"] = "Angenommen"
    a["kundenentscheidung_am"] = iso_now()
    a["geaendert_am"] = iso_now()
    if einstellungen.get("auto_rechnung", True):
        rechnung_aus_angebot(a)
    save_all()


def faellige_erinnerungen():
    due = []
    now = datetime.now()
    d1 = int(number(einstellungen.get("erinnerung_nach_tagen"), 3))
    d2 = int(number(einstellungen.get("zweite_erinnerung_nach_tagen"), 7))

    for a in angebote:
        if a.get("status") != "Gesendet":
            continue
        sent = parse_iso(a.get("gesendet_am"))
        if not sent:
            continue
        days = (now.date() - sent.date()).days
        r1 = bool(a.get("erinnerung_1_am"))
        r2 = bool(a.get("erinnerung_2_am"))

        if days >= d2 and not r2:
            due.append((a, 2))
        elif days >= d1 and not r1:
            due.append((a, 1))
    return due



def erinnerungsstatus(a):
    if a.get("status") != "Gesendet":
        return "Keine Erinnerung erforderlich"

    sent = parse_iso(a.get("gesendet_am"))
    if not sent:
        return "Versanddatum fehlt"

    heute = datetime.now().date()
    tage = (heute - sent.date()).days
    d1 = int(number(einstellungen.get("erinnerung_nach_tagen"), 3))
    d2 = int(number(einstellungen.get("zweite_erinnerung_nach_tagen"), 7))

    if a.get("erinnerung_2_am"):
        return "2. Erinnerung gesendet"
    if a.get("erinnerung_1_am"):
        rest = max(d2 - tage, 0)
        return f"1. Erinnerung gesendet · 2. in {rest} Tag(en)"
    if tage >= d2:
        return "2. Erinnerung fällig"
    if tage >= d1:
        return "1. Erinnerung fällig"

    rest = max(d1 - tage, 0)
    return f"1. Erinnerung in {rest} Tag(en)"


def erinnerung_email_text(a, stufe):
    name = text(a.get("kundenname")) or "Kundin/Kunde"
    nummer = text(a.get("angebotsnummer"))
    firma_name = text(firma.get("name")) or APP_NAME
    gueltig = angebot_gueltig_bis(a)
    portal = f"https://b8xurr8vrkyquv5zmwdzk3.streamlit.app/?portal={text(a.get('portal_token'))}"

    if stufe == 1:
        betreff = f"Freundliche Erinnerung zu Ihrem Angebot {nummer}"
        inhalt = (
            f"Guten Tag {name},\\n\\n"
            f"vor einigen Tagen haben wir Ihnen unser Angebot {nummer} zugesendet. "
            f"Wir möchten freundlich nachfragen, ob Sie noch Fragen haben oder weitere Informationen benötigen.\\n\\n"
            f"Das Angebot ist aktuell bis {gueltig} gültig.\\n\\n"
            f"Kundenportal: {portal}\\n\\n"
            f"Im Anhang finden Sie das Angebot erneut als PDF.\\n\\n"
            f"Freundliche Grüße\\n{firma_name}"
        )
    else:
        betreff = f"2. Erinnerung zu Ihrem Angebot {nummer}"
        inhalt = (
            f"Guten Tag {name},\\n\\n"
            f"wir möchten Sie noch einmal an unser Angebot {nummer} erinnern. "
            f"Falls Sie das Projekt weiterhin planen, stehen wir gern für Rückfragen oder Anpassungen zur Verfügung.\\n\\n"
            f"Das Angebot ist aktuell bis {gueltig} gültig.\\n\\n"
            f"Kundenportal: {portal}\\n\\n"
            f"Das Angebots-PDF finden Sie erneut im Anhang.\\n\\n"
            f"Freundliche Grüße\\n{firma_name}"
        )

    return betreff, inhalt



def rechnung_email_text(r):
    name = text(r.get("kundenname")) or "Kundin/Kunde"
    nummer = text(r.get("rechnungsnummer"))
    firma_name = text(firma.get("name")) or APP_NAME
    faellig = text(r.get("faellig_am"))
    return (
        f"Rechnung {nummer} – {firma_name}",
        (
            f"Guten Tag {name},\n\n"
            f"vielen Dank für Ihren Auftrag. Im Anhang erhalten Sie unsere Rechnung {nummer} "
            f"als PDF.\n\n"
            f"Rechnungsbetrag: {euro(r.get('brutto'))}\n"
            f"Fällig am: {faellig}\n\n"
            f"Bitte verwenden Sie bei der Zahlung die Rechnungsnummer {nummer} als Verwendungszweck.\n\n"
            f"Freundliche Grüße\n{firma_name}"
        ),
    )


def pdf_erstellen(a, dokument_typ="Angebot"):
    b = BytesIO()
    doc = SimpleDocTemplate(
        b, pagesize=A4, leftMargin=18*mm, rightMargin=18*mm,
        topMargin=18*mm, bottomMargin=19*mm,
        title=f"{dokument_typ} {text(a.get('angebotsnummer') or a.get('rechnungsnummer'))}",
        author=text(firma.get("name")) or APP_NAME,
    )
    ss = getSampleStyleSheet()
    navy = colors.HexColor("#0F172A")
    blue = colors.HexColor("#2563EB")
    muted = colors.HexColor("#64748B")
    light = colors.HexColor("#F8FAFC")
    border = colors.HexColor("#E2E8F0")
    body = ParagraphStyle("body", parent=ss["BodyText"], fontName="Helvetica", fontSize=8.5, leading=11.5, textColor=navy)
    small = ParagraphStyle("small", parent=body, fontSize=7.5, leading=9.5, textColor=muted)
    title = ParagraphStyle("title", parent=ss["Title"], fontName="Helvetica-Bold", fontSize=21, leading=24, textColor=navy)
    right = ParagraphStyle("right", parent=body, alignment=TA_RIGHT)
    bold_right = ParagraphStyle("boldright", parent=right, fontName="Helvetica-Bold")
    total = ParagraphStyle("total", parent=right, fontName="Helvetica-Bold", fontSize=12, leading=15)

    if dokument_typ == "Rechnung":
        netto, mwst, brutto = rechnungswerte(a)
        values = {"netto": netto, "mwst": mwst, "brutto": brutto, "mwst_satz": number(a.get("mwst_satz"), 19)}
        doc_no = text(a.get("rechnungsnummer"))
        datum = text(a.get("datum"))
    else:
        values = angebotswerte(a)
        doc_no = text(a.get("angebotsnummer"))
        datum = text(a.get("datum"))

    story = []
    firmenadresse = " · ".join(x for x in [text(firma.get("strasse")), f"{text(firma.get('plz'))} {text(firma.get('ort'))}".strip()] if x)
    kontakt = " · ".join(x for x in [text(firma.get("telefon")), text(firma.get("email")), text(firma.get("website"))] if x)

    header = Table([[
        [Paragraph(text(firma.get("name")) or "Handwerksbetrieb", title), Paragraph(firmenadresse, small), Paragraph(kontakt, small)],
        [Paragraph(dokument_typ.upper(), ParagraphStyle("doc", parent=title, alignment=TA_RIGHT, textColor=blue, fontSize=19)),
         Paragraph(f"<b>{doc_no}</b>", right), Paragraph(f"Datum: {datum}", small)]
    ]], colWidths=[105*mm, 65*mm])
    header.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "TOP")]))
    story += [header, Spacer(1, 7*mm)]

    customer = Table([[
        [Paragraph("<b>KUNDE</b>", small), Paragraph(f"<b>{text(a.get('kundenname'))}</b>", body),
         Paragraph(text(a.get("kundenadresse")) or "Keine Adresse angegeben", body),
         Paragraph(text(a.get("kunden_email")), small)],
        [Paragraph("<b>DOKUMENT</b>", small),
         Paragraph(f"<b>{dokument_typ}</b>", body),
         Paragraph(f"Fällig am: {text(a.get('faellig_am'))}" if dokument_typ=="Rechnung" else f"Gültig bis: {angebot_gueltig_bis(a)}", small),
         Paragraph(f"MwSt.: {values['mwst_satz']:g} %", small)]
    ]], colWidths=[105*mm, 65*mm])
    customer.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),light),("BOX",(0,0),(-1,-1),.5,border),
        ("LEFTPADDING",(0,0),(-1,-1),9),("RIGHTPADDING",(0,0),(-1,-1),9),
        ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8)
    ]))
    story += [customer, Spacer(1,8*mm)]

    rows = [[Paragraph("POS.",small),Paragraph("LEISTUNG",small),Paragraph("MENGE",right),Paragraph("EINZELPREIS",right),Paragraph("GESAMT",right)]]
    for i,p in enumerate(a.get("positionen",[]),1):
        q=number(p.get("menge")); pr=number(p.get("preis"))
        name=text(p.get("name"))
        if text(p.get("beschreibung")):
            name += f"<br/><font color='#64748B' size='7'>{text(p.get('beschreibung'))}</font>"
        rows.append([
            Paragraph(str(i),body),Paragraph(name,body),
            Paragraph(f"{q:.2f} {text(p.get('einheit')) or 'Stk.'}",right),
            Paragraph(euro(pr),right),Paragraph(euro(q*pr),bold_right)
        ])
    table=Table(rows,colWidths=[12*mm,76*mm,24*mm,31*mm,37*mm],repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),navy),("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("GRID",(0,0),(-1,-1),.35,border),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,light]),
        ("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5),
        ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6)
    ]))
    story += [table, Spacer(1,6*mm)]

    sr=[["Netto",euro(values["netto"])],[f"MwSt. {values['mwst_satz']:g} %",euro(values["mwst"])],["GESAMT",euro(values["brutto"])]]
    formatted=[[Paragraph(f"<b>{lab}</b>" if lab=="GESAMT" else lab,body),
                Paragraph(val,total if lab=="GESAMT" else right)] for lab,val in sr]
    sm=Table(formatted,colWidths=[62*mm,48*mm],hAlign="RIGHT")
    sm.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-2),light),("BACKGROUND",(0,-1),(-1,-1),colors.HexColor("#EFF6FF")),
        ("BOX",(0,0),(-1,-1),.5,border),("INNERGRID",(0,0),(-1,-2),.25,border),
        ("LEFTPADDING",(0,0),(-1,-1),8),("RIGHTPADDING",(0,0),(-1,-1),8),
        ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6)
    ]))
    story += [sm, Spacer(1,8*mm)]

    if text(firma.get("abschluss_text")) and dokument_typ=="Angebot":
        story.append(Paragraph(text(firma.get("abschluss_text")), body))
    if text(firma.get("iban")):
        story += [Spacer(1,7*mm), Paragraph(
            f"<b>Bankverbindung</b><br/>{text(firma.get('bank'))}<br/>IBAN: {text(firma.get('iban'))} · BIC: {text(firma.get('bic'))}",
            small
        )]

    def footer(canvas, doc_obj):
        canvas.saveState()
        canvas.setStrokeColor(border); canvas.line(18*mm,13*mm,A4[0]-18*mm,13*mm)
        canvas.setFillColor(muted); canvas.setFont("Helvetica",7)
        canvas.drawString(18*mm,8*mm,text(firma.get("name")) or APP_NAME)
        canvas.drawRightString(A4[0]-18*mm,8*mm,f"Seite {doc_obj.page}")
        canvas.restoreState()

    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    b.seek(0)
    return b.getvalue()


for key, value in {
    "page":"dashboard", "offer_id":None, "customer_id":None,
    "lead_id":None, "invoice_id":None
}.items():
    if key not in st.session_state:
        st.session_state[key] = value


# Öffentliche Lead-Erfassung
if text(st.query_params.get("lead","")) == "1":
    st.markdown('<div class="portal-head">', unsafe_allow_html=True)
    st.title("Projektanfrage")
    st.caption(f"{text(firma.get('name'))} · Wir melden uns mit einem passenden Angebot.")
    with st.form("public_lead"):
        c1,c2=st.columns(2)
        name=c1.text_input("Name / Firma *")
        email=c2.text_input("E-Mail *")
        telefon=c1.text_input("Telefon")
        bereich=c2.selectbox("Leistungsbereich",LEISTUNGSBEREICHE)
        adresse=st.text_input("Projektadresse")
        beschreibung=st.text_area("Was soll gemacht werden? *")
        budget=st.number_input("Ungefähres Budget (€)",min_value=0.0,value=0.0)
        if st.form_submit_button("Anfrage senden",type="primary"):
            if not text(name) or not text(email) or not text(beschreibung):
                st.error("Bitte Name, E-Mail und Beschreibung ausfüllen.")
            elif not valid_email(email):
                st.error("Bitte eine gültige E-Mail-Adresse eingeben.")
            else:
                leads.append({
                    "id":lead_id_neu(),"name":text(name),"email":text(email),"telefon":text(telefon),
                    "adresse":text(adresse),"leistungsbereich":text(bereich),"beschreibung":text(beschreibung),
                    "budget":budget,"status":"Neu","erstellt_am":iso_now(),"quelle":"Webformular"
                })
                atomic_save(LEADS_DATEI,leads)
                st.success("Vielen Dank. Ihre Anfrage wurde erfolgreich übermittelt.")
    st.markdown("</div>",unsafe_allow_html=True)
    st.stop()


# Kundenportal
portal_token=text(st.query_params.get("portal",""))
if portal_token:
    a=portal_angebot(portal_token)
    if not a:
        st.error("Dieses Angebot wurde nicht gefunden.")
        st.stop()
    v=angebotswerte(a)
    st.markdown(f"""
    <div class="portal-head">
      <div style="font-size:.8rem;color:#64748b;font-weight:700;">{text(firma.get("name"))}</div>
      <h1 style="margin-bottom:4px;">Angebot {text(a.get("angebotsnummer"))}</h1>
      <div style="color:#64748b;">{text(a.get("leistungsbereich"))} · {text(a.get("kundenname"))}</div>
      <div style="height:20px"></div>
      <div class="portal-price">{euro(v["brutto"])}</div>
      <div style="color:#64748b;font-size:.85rem;">Brutto inkl. {v["mwst_satz"]:g} % MwSt.</div>
      <div style="margin-top:16px;">{status_html(a.get("status","Entwurf"))}</div>
    </div>
    """,unsafe_allow_html=True)
    st.write("")
    st.subheader("Leistungsübersicht")
    for i,p in enumerate(a.get("positionen",[]),1):
        with st.container(border=True):
            c1,c2=st.columns([4,1.3])
            c1.write(f"**{i}. {text(p.get('name'))}**")
            c1.caption(f"{number(p.get('menge')):.2f} {text(p.get('einheit')) or 'Stk.'} × {euro(p.get('preis'))}")
            c2.write(f"**{euro(number(p.get('menge'))*number(p.get('preis')))}**")
    st.write(f"**Gültig bis:** {angebot_gueltig_bis(a)}")
    b1,b2,b3=st.columns(3)
    if b1.button("✅ Angebot annehmen",type="primary",use_container_width=True):
        angebot_angenommen(a)
        st.success("Vielen Dank. Das Angebot wurde angenommen und intern weiterverarbeitet.")
        st.rerun()
    if b2.button("❌ Angebot ablehnen",use_container_width=True):
        a["status"]="Abgelehnt"; a["kundenentscheidung_am"]=iso_now(); save_all(); st.rerun()
    b3.download_button("📥 PDF herunterladen",data=pdf_erstellen(a),file_name=f"{a.get('angebotsnummer')}.pdf",mime="application/pdf",use_container_width=True)
    st.stop()



# ------------------------------------------------------------
# ADMIN-BEREICH SCHÜTZEN
# Kundenportal (?portal=...) und Leadformular (?lead=1) wurden
# bereits oberhalb verarbeitet und bleiben öffentlich.
# ------------------------------------------------------------
admin_password = secret_value("ADMIN_PASSWORD")

if not admin_password:
    st.error(
        "ADMIN_PASSWORD fehlt in den Streamlit-Secrets. "
        "Bitte in Streamlit Community Cloud unter App → Settings → Secrets eintragen."
    )
    st.stop()

if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

if not st.session_state.admin_authenticated:
    st.markdown(
        """
        <div style="
            max-width:520px;margin:8vh auto 24px auto;padding:28px;
            background:#ffffff;border:1px solid #e5eaf2;border-radius:20px;
            box-shadow:0 14px 38px rgba(15,23,42,.08);">
          <div style="font-size:.8rem;color:#64748b;font-weight:700;">NORDWERK</div>
          <h1 style="margin:.35rem 0 .5rem 0;">Admin-Anmeldung</h1>
          <p style="color:#64748b;margin:0;">
            Dieser Bereich ist nur für die interne Verwaltung bestimmt.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("admin_login"):
        password_input = st.text_input("Admin-Passwort", type="password")
        login = st.form_submit_button("Anmelden", type="primary", use_container_width=True)

    if login:
        if password_input == admin_password:
            st.session_state.admin_authenticated = True
            st.rerun()
        else:
            st.error("Falsches Admin-Passwort.")

    st.stop()


with st.sidebar:
    st.markdown("## 🏠 Nordwerk")
    st.caption("Handwerk & Sanierung")
    st.divider()

    nav=[
        ("dashboard","▦  Automatisierungscockpit"),
        ("leads","♙  Leads"),
        ("angebote","▣  Angebote"),
        ("rechnungen","€  Rechnungen"),
        ("kunden","♧  Kunden"),
        ("vorlagen","✉  E-Mail Vorlagen"),
        ("automation","🔔  Erinnerungen"),
        ("dokumente","▤  Dokumente"),
        ("firma","⚙  Einstellungen"),
    ]
    for page,label in nav:
        if st.button(
            label,
            key=f"nav_{page}",
            use_container_width=True,
            type="primary" if st.session_state.page==page else "secondary"
        ):
            navigate(page)

    st.divider()
    st.caption(f"◎ {len(leads)} Leads")
    st.caption(f"👥 {len(kunden)} Kunden")
    st.caption(f"📄 {len(angebote)} Angebote")
    st.caption(f"€ {len(rechnungen)} Rechnungen")


if st.session_state.page=="dashboard":
    offene_angebote=sum(angebotswerte(a)["brutto"] for a in angebote if a.get("status") in ["Entwurf","Gesendet"])
    offene_rechnungen=sum(number(r.get("brutto")) for r in rechnungen if r.get("status")=="Offen")
    umsatz=sum(number(r.get("brutto")) for r in rechnungen if r.get("status")=="Bezahlt")
    neue_leads=sum(l.get("status")=="Neu" for l in leads)
    angenommen=sum(a.get("status")=="Angenommen" for a in angebote)
    offene_rechnungsanzahl=sum(r.get("status")=="Offen" for r in rechnungen)
    bezahlte_rechnungsanzahl=sum(r.get("status")=="Bezahlt" for r in rechnungen)
    ueberfaellige_rechnungsanzahl=0

    for r in rechnungen:
        if r.get("status")!="Offen":
            continue
        try:
            if datetime.strptime(text(r.get("faellig_am")),"%d.%m.%Y").date() < date.today():
                ueberfaellige_rechnungsanzahl += 1
        except ValueError:
            pass

    st.markdown(f"""
    <div class="hero-pro">
      <div class="hero-eyebrow">📈</div>
      <h1>Automatisierungscockpit</h1>
      <p>{text(firma.get("name"))} · Leads → Angebote → Rechnungen → Zahlungen.</p>
    </div>
    """,unsafe_allow_html=True)

    st.markdown(f"""
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-icon purple">👥</div>
        <div class="kpi-title">Neue Leads</div>
        <div class="kpi-number">{neue_leads}</div>
        <div class="kpi-sub">noch nicht bearbeitet</div>
      </div>

      <div class="kpi-card">
        <div class="kpi-icon blue">📄</div>
        <div class="kpi-title">Offene Angebote</div>
        <div class="kpi-number">{euro(offene_angebote)}</div>
        <div class="kpi-sub">Entwurf + Gesendet</div>
      </div>

      <div class="kpi-card">
        <div class="kpi-icon green">✓</div>
        <div class="kpi-title">Angenommen</div>
        <div class="kpi-number">{angenommen}</div>
        <div class="kpi-sub">Aufträge</div>
      </div>

      <div class="kpi-card">
        <div class="kpi-icon orange">🧾</div>
        <div class="kpi-title">Ausstehende Rechnungen</div>
        <div class="kpi-number">{euro(offene_rechnungen)}</div>
        <div class="kpi-sub">{offene_rechnungsanzahl} ausstehend · {ueberfaellige_rechnungsanzahl} überfällig</div>
      </div>

      <div class="kpi-card">
        <div class="kpi-icon green">€</div>
        <div class="kpi-title">Umsatz</div>
        <div class="kpi-number">{euro(umsatz)}</div>
        <div class="kpi-sub">{bezahlte_rechnungsanzahl} bezahlte Rechnung(en)</div>
      </div>
    </div>
    """,unsafe_allow_html=True)

    activity=[]
    for l in leads:
        activity.append((
            text(l.get("erstellt_am")),
            f"Lead {text(l.get('name'))}",
            text(l.get("status")),
            "👥"
        ))
    for a in angebote:
        activity.append((
            text(a.get("geaendert_am") or a.get("gespeichert_am")),
            f"Angebot {text(a.get('angebotsnummer'))}",
            text(a.get("status")),
            "📄"
        ))
    for r in rechnungen:
        activity.append((
            text(r.get("bezahlt_am") or r.get("versendet_am") or r.get("erstellt_am")),
            f"Rechnung {text(r.get('rechnungsnummer'))}",
            text(r.get("status")),
            "🧾"
        ))

    left, right = st.columns([1.45, 1])

    with left:
        st.subheader("📋 Letzte Aktivitäten")

        if not activity:
            with st.container(border=True):
                st.caption("Noch keine Aktivitäten vorhanden.")
        else:
            for raw, title, status, icon in sorted(activity, reverse=True)[:6]:
                with st.container(border=True):
                    c1, c2 = st.columns([4, 1.4])

                    dt = parse_iso(raw)
                    meta = dt.strftime("%d.%m.%Y · %H:%M Uhr") if dt else ""

                    c1.write(f"**{icon} {title}**")
                    if meta:
                        c1.caption(meta)

                    c2.markdown(
                        status_html(status),
                        unsafe_allow_html=True,
                    )

    with right:
        st.subheader("⚙ Automatisierungsstatus")

        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            c1.write("🔔 **Fällige Erinnerungen**")
            c2.write(f"**{len(faellige_erinnerungen())}**")

            st.divider()

            c1, c2 = st.columns([3, 1])
            c1.write("✉️ **SMTP**")
            c2.write("**bereit**" if smtp_ready() else "**nicht bereit**")

            st.divider()

            c1, c2 = st.columns([3, 1])
            c1.write("🤖 **Auto-Rechnung**")
            c2.write(
                "**aktiv**"
                if einstellungen.get("auto_rechnung", True)
                else "**aus**"
            )

            st.info(
                "Automatische Prozesse laufen nur, solange die App erreichbar ist. "
                "Für echten 24/7-Betrieb wird sie später online bereitgestellt."
            )


elif st.session_state.page=="leads":
    st.title("Leads")
    st.caption("Neue Anfragen erfassen und mit wenigen Klicks in Kunden und Angebote umwandeln.")

    st.text_input("Öffentlicher Lead-Link (lokal)",value="https://b8xurr8vrkyquv5zmwdzk3.streamlit.app/?lead=1")

    with st.expander("＋ Lead manuell anlegen"):
        with st.form("lead_new"):
            c1,c2=st.columns(2)
            name=c1.text_input("Name / Firma *")
            email=c2.text_input("E-Mail")
            telefon=c1.text_input("Telefon")
            bereich=c2.selectbox("Leistungsbereich",LEISTUNGSBEREICHE)
            adresse=st.text_input("Adresse")
            beschreibung=st.text_area("Anfrage")
            if st.form_submit_button("Lead speichern",type="primary"):
                if not text(name):
                    st.error("Bitte einen Namen eingeben.")
                else:
                    leads.append({"id":lead_id_neu(),"name":text(name),"email":text(email),"telefon":text(telefon),
                                  "adresse":text(adresse),"leistungsbereich":text(bereich),"beschreibung":text(beschreibung),
                                  "status":"Neu","erstellt_am":iso_now(),"quelle":"Manuell"})
                    atomic_save(LEADS_DATEI,leads); st.rerun()

    q=st.text_input("🔎 Leads suchen")
    for l in [x for x in leads if not text(q) or text(q).casefold() in " ".join([text(x.get("name")),text(x.get("email")),text(x.get("beschreibung"))]).casefold()]:
        with st.container(border=True):
            c1,c2,c3=st.columns([3,2,1.5])
            c1.write(f"**{text(l.get('name'))}**")
            c1.caption(text(l.get("beschreibung"))[:160])
            c2.write(text(l.get("email")) or "—")
            c2.caption(text(l.get("leistungsbereich")))
            c3.markdown(status_html(l.get("status","Neu")),unsafe_allow_html=True)

            b1,b2=st.columns(2)
            if b1.button("Kunde + Angebot erstellen",key=f"lead_convert_{l.get('id')}",use_container_width=True):
                k=kunde_nach_name(l.get("name"))
                if not k:
                    k={"id":kunde_id_neu(),"name":text(l.get("name")),"adresse":text(l.get("adresse")),
                       "telefon":text(l.get("telefon")),"email":text(l.get("email")),"notizen":text(l.get("beschreibung")),
                       "erstellt_am":iso_now(),"geaendert_am":iso_now()}
                    kunden.append(k)
                matching=[v for v in vorlagen if text(v.get("leistungsbereich"))==text(l.get("leistungsbereich"))]
                template=matching[0] if matching else None
                pos=copy_json(template.get("positionen",[])) if template else [{"typ":"Leistung","name":text(l.get("beschreibung")) or "Handwerksleistung","beschreibung":"","menge":1.0,"einheit":"Pauschal","preis":0.0}]
                a={"id":angebot_id_neu(),"angebotsnummer":angebotsnummer_neu(),"datum":date.today().strftime("%d.%m.%Y"),
                   "gespeichert_am":iso_now(),"geaendert_am":iso_now(),"status":"Entwurf","portal_token":uuid.uuid4().hex,
                   "kunden_id":k["id"],"kundenname":k["name"],"kundenadresse":k.get("adresse",""),
                   "kunden_telefon":k.get("telefon",""),"kunden_email":k.get("email",""),
                   "leistungsbereich":text(l.get("leistungsbereich")),"positionen":pos,"materialkosten":0.0,
                   "arbeitsstunden":0.0,"stundensatz":0.0,"anfahrt":0.0,"rabatt_prozent":0.0,"rabatt_euro":0.0,
                   "mwst_satz":number(einstellungen.get("mwst"),19),"zahlungsziel":int(number(einstellungen.get("zahlungsziel"),14)),
                   "gueltigkeit_tage":int(number(einstellungen.get("gueltigkeit"),30)),
                   "kundennotiz":text(template.get("kundennotiz","")) if template else ""}
                angebote.append(a); l["status"]="Angebot erstellt"; l["angebot_id"]=a["id"]; save_all()
                navigate("angebot_detail",offer_id=a["id"])
            ns=b2.selectbox("Status",LEAD_STATUS,index=LEAD_STATUS.index(l.get("status","Neu")) if l.get("status") in LEAD_STATUS else 0,key=f"lead_status_{l.get('id')}")
            if ns!=l.get("status"):
                l["status"]=ns; atomic_save(LEADS_DATEI,leads); st.rerun()


elif st.session_state.page=="kunden":
    st.title("Kunden")
    q=st.text_input("🔎 Kunden suchen")
    for k in [x for x in kunden if not text(q) or text(q).casefold() in " ".join([text(x.get("name")),text(x.get("email")),text(x.get("telefon"))]).casefold()]:
        ko=kunden_angebote(k); value=sum(angebotswerte(a)["brutto"] for a in ko)
        with st.container(border=True):
            c1,c2,c3,c4=st.columns([3,2.5,1.2,1.4])
            c1.write(f"**{text(k.get('name'))}**"); c1.caption(text(k.get("adresse")) or "—")
            c2.write(text(k.get("email")) or "—"); c2.caption(text(k.get("telefon")) or "—")
            c3.metric("Angebote",len(ko)); c4.metric("Wert",euro(value))


elif st.session_state.page=="angebote":
    st.title("Angebote")
    q=st.text_input("🔎 Angebote suchen")
    for a in [x for x in angebote if not text(q) or text(q).casefold() in " ".join([text(x.get("kundenname")),text(x.get("angebotsnummer")),text(x.get("leistungsbereich"))]).casefold()]:
        v=angebotswerte(a)
        with st.container(border=True):
            c1,c2,c3,c4=st.columns([2.3,2.5,1.5,1.5])
            c1.write(f"**{text(a.get('angebotsnummer'))}**"); c1.caption(text(a.get("datum")))
            c2.write(text(a.get("kundenname"))); c2.caption(text(a.get("leistungsbereich")))
            c3.markdown(status_html(a.get("status","Entwurf")),unsafe_allow_html=True)
            c4.write(f"**{euro(v['brutto'])}**")
            b1,b2,b3=st.columns(3)
            if b1.button("Öffnen",key=f"aopen_{a.get('id')}",use_container_width=True):
                navigate("angebot_detail",offer_id=a.get("id"))
            b2.download_button("PDF",data=pdf_erstellen(a),file_name=f"{a.get('angebotsnummer')}.pdf",mime="application/pdf",key=f"apdf_{a.get('id')}",use_container_width=True)
            if b3.button("Als gesendet markieren",key=f"asent_{a.get('id')}",use_container_width=True):
                a["status"]="Gesendet"; a["gesendet_am"]=iso_now(); a["geaendert_am"]=iso_now(); save_all(); st.rerun()


elif st.session_state.page=="angebot_detail":
    a=angebot_finden(st.session_state.offer_id)
    if not a:
        st.error("Angebot nicht gefunden.")
        st.stop()

    ensure_portal_token(a)
    save_all()
    v=angebotswerte(a)

    if st.button("← Angebote"):
        navigate("angebote")

    st.title(text(a.get("angebotsnummer")))
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Netto",euro(v["netto"]))
    c2.metric("MwSt.",euro(v["mwst"]))
    c3.metric("Gesamt",euro(v["brutto"]))
    c4.markdown(status_html(a.get("status","Entwurf")),unsafe_allow_html=True)

    st.subheader("Kundendaten")
    with st.container(border=True):
        c1,c2=st.columns(2)
        c1.write(f"**Kunde:** {text(a.get('kundenname')) or '—'}")
        c1.write(f"**Adresse:** {text(a.get('kundenadresse')) or '—'}")
        c2.write(f"**Telefon:** {text(a.get('kunden_telefon')) or '—'}")
        c2.write(f"**E-Mail:** {text(a.get('kunden_email')) or 'Keine E-Mail eingetragen'}")

    with st.expander("✏️ Kundendaten bearbeiten", expanded=not bool(text(a.get("kunden_email")))):
        with st.form(f"edit_customer_offer_{a.get('id')}"):
            c1,c2=st.columns(2)
            kundenname=c1.text_input("Kundenname *",value=text(a.get("kundenname")))
            kundenemail=c2.text_input("E-Mail",value=text(a.get("kunden_email")))
            kundenadresse=c1.text_input("Adresse",value=text(a.get("kundenadresse")))
            kundentelefon=c2.text_input("Telefon",value=text(a.get("kunden_telefon")))

            if st.form_submit_button("Kundendaten speichern",type="primary"):
                if not text(kundenname):
                    st.error("Bitte einen Kundennamen eingeben.")
                elif text(kundenemail) and not valid_email(kundenemail):
                    st.error("Bitte eine gültige E-Mail-Adresse eingeben.")
                else:
                    old_name=text(a.get("kundenname"))
                    k=kunde_finden(a.get("kunden_id")) or kunde_nach_name(old_name)
                    if not k:
                        k={
                            "id":kunde_id_neu(),
                            "name":text(kundenname),
                            "adresse":text(kundenadresse),
                            "telefon":text(kundentelefon),
                            "email":text(kundenemail),
                            "notizen":"",
                            "erstellt_am":iso_now(),
                            "geaendert_am":iso_now(),
                        }
                        kunden.append(k)
                    else:
                        k.update({
                            "name":text(kundenname),
                            "adresse":text(kundenadresse),
                            "telefon":text(kundentelefon),
                            "email":text(kundenemail),
                            "geaendert_am":iso_now(),
                        })

                    a.update({
                        "kunden_id":k.get("id"),
                        "kundenname":text(kundenname),
                        "kundenadresse":text(kundenadresse),
                        "kunden_telefon":text(kundentelefon),
                        "kunden_email":text(kundenemail),
                        "geaendert_am":iso_now(),
                    })
                    save_all()
                    st.success("Kundendaten wurden gespeichert.")
                    st.rerun()

    st.write(f"**Projekt:** {text(a.get('leistungsbereich'))}")
    if a.get("status") == "Gesendet":
        st.info(f"🔔 Erinnerungsstatus: {erinnerungsstatus(a)}")
    st.text_input("Kundenportal-Link",value=f"https://b8xurr8vrkyquv5zmwdzk3.streamlit.app/?portal={a.get('portal_token')}")

    st.subheader("Positionen")
    for i,p in enumerate(a.get("positionen",[]),1):
        with st.container(border=True):
            x,y=st.columns([4,1.5])
            x.write(f"**{i}. {text(p.get('name'))}**")
            x.caption(text(p.get("beschreibung")))
            y.write(f"**{euro(number(p.get('menge'))*number(p.get('preis')))}**")

    st.divider()
    st.subheader("E-Mail-Versand")

    empfaenger=text(a.get("kunden_email"))
    if not empfaenger:
        st.warning("Für dieses Angebot ist noch keine Kunden-E-Mail-Adresse eingetragen. Öffne oben 'Kundendaten bearbeiten'.")
    elif not valid_email(empfaenger):
        st.error(f"Die Kunden-E-Mail-Adresse '{empfaenger}' ist ungültig. Bitte zuerst korrigieren.")
    else:
        st.info(f"Angebot wird an **{empfaenger}** gesendet.")

    b1,b2,b3,b4=st.columns(4)

    if b1.button("📤 Angebot per E-Mail senden",type="primary",use_container_width=True,disabled=not bool(empfaenger and valid_email(empfaenger))):
        ok,msg=email_senden(
            empfaenger,
            f"Angebot {a.get('angebotsnummer')} – {firma.get('name')}",
            f"Guten Tag {a.get('kundenname')},\n\nanbei erhalten Sie unser Angebot {a.get('angebotsnummer')}.\n\nKundenportal: https://b8xurr8vrkyquv5zmwdzk3.streamlit.app/?portal={a.get('portal_token')}\n\nFreundliche Grüße\n{firma.get('name')}",
            pdf_erstellen(a),
            f"{a.get('angebotsnummer')}.pdf"
        )
        if ok:
            a["status"]="Gesendet"
            a["gesendet_am"]=iso_now()
            a["geaendert_am"]=iso_now()
            save_all()
            st.success(msg)
        else:
            st.error(msg)

    test_empfaenger=cloud_gmail_address()
    if b2.button("🧪 Test-E-Mail + PDF an mich",use_container_width=True,disabled=not bool(test_empfaenger and valid_email(test_empfaenger))):
        ok,msg=email_senden(
            test_empfaenger,
            f"Testangebot {a.get('angebotsnummer')} – {firma.get('name')}",
            f"Hallo,\n\ndies ist eine Test-E-Mail aus {APP_NAME}.\n\nIm Anhang befindet sich das aktuelle Angebots-PDF {a.get('angebotsnummer')}. So werden gleichzeitig Gmail-Versand und PDF-Anhang geprüft.\n\nFreundliche Grüße\n{firma.get('name')}",
            pdf_erstellen(a),
            f"{a.get('angebotsnummer')}.pdf"
        )
        if ok:
            st.success(msg)
        else:
            st.error(msg)

    if b3.button("✅ Intern annehmen",use_container_width=True):
        angebot_angenommen(a)
        st.rerun()

    b4.download_button(
        "📥 PDF",
        data=pdf_erstellen(a),
        file_name=f"{a.get('angebotsnummer')}.pdf",
        mime="application/pdf",
        use_container_width=True
    )

    with st.expander("✏️ Positionen / Preise bearbeiten"):
        with st.form(f"edit_offer_{a.get('id')}"):
            new_positions=[]
            for i,p in enumerate(a.get("positionen",[])):
                x,y,z=st.columns([4,1.4,2])
                name=x.text_input("Leistung",value=text(p.get("name")),key=f"en_{i}")
                qty=y.number_input("Menge",min_value=0.0,value=number(p.get("menge"),1),key=f"eq_{i}")
                price=z.number_input("Preis €",min_value=0.0,value=number(p.get("preis")),key=f"ep_{i}")
                new_positions.append({**p,"name":text(name),"menge":qty,"preis":price})

            material=st.number_input("Material pauschal €",min_value=0.0,value=number(a.get("materialkosten")))
            hours=st.number_input("Arbeitszeit Std.",min_value=0.0,value=number(a.get("arbeitsstunden")))
            rate=st.number_input("Stundensatz €",min_value=0.0,value=number(a.get("stundensatz")))
            travel=st.number_input("Anfahrt €",min_value=0.0,value=number(a.get("anfahrt")))
            tax=st.number_input("MwSt. %",min_value=0.0,max_value=100.0,value=number(a.get("mwst_satz"),19.0),step=1.0)

            if st.form_submit_button("Speichern",type="primary"):
                a.update({
                    "positionen":new_positions,
                    "materialkosten":material,
                    "arbeitsstunden":hours,
                    "stundensatz":rate,
                    "anfahrt":travel,
                    "mwst_satz":tax,
                    "geaendert_am":iso_now()
                })
                save_all()
                st.rerun()

elif st.session_state.page=="vorlagen":
    st.title("Angebotsvorlagen")
    st.caption("Standardleistungen einmal anlegen und später für Leads wiederverwenden.")

    with st.expander("＋ Neue Vorlage"):
        with st.form("tpl_new"):
            name=st.text_input("Vorlagenname *")
            bereich=st.selectbox("Leistungsbereich",LEISTUNGSBEREICHE)
            p1=st.text_input("Standardposition")
            preis=st.number_input("Standardpreis €",min_value=0.0,value=0.0)
            note=st.text_area("Kundenhinweis")
            if st.form_submit_button("Vorlage speichern",type="primary"):
                if not text(name) or not text(p1):
                    st.error("Name und Position sind erforderlich.")
                else:
                    vorlagen.append({"id":vorlage_id_neu(),"name":text(name),"leistungsbereich":text(bereich),
                                     "positionen":[{"typ":"Leistung","name":text(p1),"beschreibung":"","menge":1.0,"einheit":"Pauschal","preis":preis}],
                                     "kundennotiz":text(note)})
                    atomic_save(VORLAGEN_DATEI,vorlagen); st.rerun()

    for v in vorlagen:
        with st.container(border=True):
            c1,c2,c3=st.columns([3,2,1])
            c1.write(f"**{text(v.get('name'))}**"); c1.caption(text(v.get("leistungsbereich")))
            c2.write(f"{len(v.get('positionen',[]))} Position(en)")
            if c3.button("Löschen",key=f"vdel_{v.get('id')}"):
                vorlagen[:] = [x for x in vorlagen if x.get("id")!=v.get("id")]
                atomic_save(VORLAGEN_DATEI,vorlagen); st.rerun()


elif st.session_state.page=="rechnungen":
    st.title("Rechnungen")
    st.caption("Angenommene Angebote werden automatisch zu Rechnungen. Versand und Zahlung werden hier nachverfolgt.")

    offen = sum(number(r.get("brutto")) for r in rechnungen if r.get("status") == "Offen")
    bezahlt = sum(number(r.get("brutto")) for r in rechnungen if r.get("status") == "Bezahlt")
    ueberfaellig = 0
    heute = date.today()
    for r in rechnungen:
        if r.get("status") != "Offen":
            continue
        try:
            if datetime.strptime(text(r.get("faellig_am")), "%d.%m.%Y").date() < heute:
                ueberfaellig += 1
        except ValueError:
            pass

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rechnungen", len(rechnungen))
    c2.metric("Ausstehende Beträge", euro(offen))
    c3.metric("Bezahlter Umsatz", euro(bezahlt))
    c4.metric("Überfällig", ueberfaellig)

    if bezahlt > 0:
        st.success(f"💰 Bereits verbuchter Umsatz: {euro(bezahlt)}")
    if offen > 0:
        st.info(f"📌 Noch ausstehende Forderungen: {euro(offen)}")

    if not rechnungen:
        st.info("Noch keine Rechnungen vorhanden. Sobald ein Angebot angenommen wird, kann automatisch eine Rechnung entstehen.")

    for r in sorted(rechnungen, key=lambda x: text(x.get("erstellt_am")), reverse=True):
        try:
            faellig_date = datetime.strptime(text(r.get("faellig_am")), "%d.%m.%Y").date()
            is_overdue = r.get("status") == "Offen" and faellig_date < heute
        except ValueError:
            is_overdue = False

        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([2.2, 2.5, 1.5, 1.5])
            c1.write(f"**{text(r.get('rechnungsnummer'))}**")
            c1.caption(f"Rechnung vom {text(r.get('datum'))}")

            c2.write(f"**{text(r.get('kundenname'))}**")
            c2.caption(text(r.get("kunden_email")) or "Keine E-Mail")

            gespeicherter_status = text(r.get("status", "Offen"))
            if is_overdue:
                label = "Überfällig"
            elif gespeicherter_status == "Offen":
                label = "Ausstehend"
            else:
                label = gespeicherter_status
            c3.markdown(status_html(label), unsafe_allow_html=True)
            c3.caption(f"Fällig: {text(r.get('faellig_am'))}")

            c4.write(f"**{euro(r.get('brutto'))}**")

            b1, b2, b3 = st.columns(3)
            b1.download_button(
                "📥 Rechnungs-PDF",
                data=pdf_erstellen(r, "Rechnung"),
                file_name=f"{text(r.get('rechnungsnummer'))}.pdf",
                mime="application/pdf",
                key=f"rpdf_{r.get('id')}",
                use_container_width=True,
            )

            empfaenger = text(r.get("kunden_email"))
            can_send = bool(empfaenger and valid_email(empfaenger) and smtp_ready())
            if b2.button(
                "📤 Rechnung per E-Mail",
                key=f"rsend_{r.get('id')}",
                use_container_width=True,
                disabled=not can_send,
            ):
                betreff, inhalt = rechnung_email_text(r)
                ok, msg = email_senden(
                    empfaenger,
                    betreff,
                    inhalt,
                    pdf_erstellen(r, "Rechnung"),
                    f"{text(r.get('rechnungsnummer'))}.pdf",
                )
                if ok:
                    r["versendet_am"] = iso_now()
                    save_all()
                    st.success("Rechnung wurde mit PDF-Anhang versendet.")
                    st.rerun()
                else:
                    st.error(msg)

            if r.get("status") == "Offen":
                if b3.button(
                    "✅ Als bezahlt markieren",
                    key=f"paid_{r.get('id')}",
                    type="primary",
                    use_container_width=True,
                ):
                    r["status"] = "Bezahlt"
                    r["bezahlt_am"] = iso_now()
                    save_all()
                    st.success("Zahlung wurde verbucht. Das Dashboard wird automatisch aktualisiert.")
                    st.rerun()
            else:
                b3.write("✅ Bezahlt")
                if r.get("bezahlt_am"):
                    bezahlt_dt = parse_iso(r.get("bezahlt_am"))
                    if bezahlt_dt:
                        b3.caption(f"Bezahlt am {bezahlt_dt.strftime('%d.%m.%Y um %H:%M')}")
                    else:
                        b3.caption(text(r.get("bezahlt_am")))

            if r.get("versendet_am"):
                st.caption(f"📧 Rechnung versendet: {text(r.get('versendet_am'))}")
            elif not can_send and not valid_email(empfaenger):
                st.warning("Für den Rechnungsversand fehlt eine gültige Kunden-E-Mail-Adresse.")


elif st.session_state.page=="automation":
    st.title("Automatisierung")
    st.caption("Fällige Erinnerungen, Versandstatus und Nachverfolgung zentral verwalten.")

    due = faellige_erinnerungen()
    erste = sum(stufe == 1 for _, stufe in due)
    zweite = sum(stufe == 2 for _, stufe in due)

    c1, c2, c3 = st.columns(3)
    c1.metric("Heute fällig", len(due))
    c2.metric("1. Erinnerungen", erste)
    c3.metric("2. Erinnerungen", zweite)

    if not smtp_ready():
        st.warning(
            "SMTP ist noch nicht vollständig eingerichtet. "
            "Erinnerungen können erst versendet werden, wenn Gmail/SMTP bereit ist."
        )

    st.divider()
    st.subheader("Heute fällige Erinnerungen")

    if not due:
        st.success("Aktuell ist keine Erinnerung fällig.")

    for a, stage in due:
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([2.4, 2.2, 1.6, 1.5])

            c1.write(f"**{text(a.get('angebotsnummer'))}**")
            c1.caption(text(a.get("kundenname")))

            c2.write(text(a.get("kunden_email")) or "Keine E-Mail")
            c2.caption(erinnerungsstatus(a))

            c3.write(f"**{euro(angebotswerte(a)['brutto'])}**")
            c3.caption(f"Erinnerungsstufe {stage}")

            empfaenger = text(a.get("kunden_email"))
            versand_ok = bool(empfaenger and valid_email(empfaenger) and smtp_ready())

            if c4.button(
                f"Erinnerung {stage} senden",
                key=f"rem_{a.get('id')}_{stage}",
                type="primary",
                use_container_width=True,
                disabled=not versand_ok,
            ):
                marker = f"erinnerung_{stage}_am"

                # Doppelversand verhindern
                if a.get(marker):
                    st.warning("Diese Erinnerung wurde bereits versendet.")
                else:
                    betreff, inhalt = erinnerung_email_text(a, stage)
                    ok, msg = email_senden(
                        empfaenger,
                        betreff,
                        inhalt,
                        pdf_erstellen(a),
                        f"{text(a.get('angebotsnummer'))}.pdf",
                    )

                    if ok:
                        a[marker] = iso_now()
                        a["geaendert_am"] = iso_now()
                        save_all()
                        st.success(f"Erinnerung {stage} wurde mit PDF-Anhang versendet.")
                        st.rerun()
                    else:
                        st.error(msg)

    st.divider()
    st.subheader("Nachverfolgung aller gesendeten Angebote")

    sent_offers = [a for a in angebote if a.get("status") == "Gesendet"]
    sent_offers.sort(key=lambda x: text(x.get("gesendet_am")), reverse=True)

    if not sent_offers:
        st.info("Noch keine offenen gesendeten Angebote vorhanden.")

    for a in sent_offers:
        sent = parse_iso(a.get("gesendet_am"))
        tage = (datetime.now().date() - sent.date()).days if sent else 0

        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([2.3, 2.3, 1.4, 2.0])

            c1.write(f"**{text(a.get('angebotsnummer'))}**")
            c1.caption(text(a.get("kundenname")))

            c2.write(f"Gesendet vor **{tage} Tag(en)**")
            c2.caption(text(a.get("kunden_email")) or "Keine E-Mail")

            c3.write(f"**{euro(angebotswerte(a)['brutto'])}**")

            c4.write(erinnerungsstatus(a))
            if a.get("erinnerung_1_am"):
                c4.caption(f"1. Erinnerung: {text(a.get('erinnerung_1_am'))}")
            if a.get("erinnerung_2_am"):
                c4.caption(f"2. Erinnerung: {text(a.get('erinnerung_2_am'))}")

    st.divider()
    st.info(
        "Die App erkennt Fälligkeiten automatisch. Solange sie nur lokal auf deinem Laptop läuft, "
        "werden E-Mails aber nicht selbstständig verschickt, wenn der Laptop ausgeschaltet ist. "
        "Für echten 24/7-Automatikbetrieb veröffentlichen wir die App später online."
    )

elif st.session_state.page=="dokumente":
    st.title("Dokumente & Backup")
    c1,c2=st.columns(2)
    with c1:
        if st.button("💾 Backup erstellen",type="primary",use_container_width=True):
            target=make_backup(); st.success(f"Backup: {target.name}")
    with c2:
        st.download_button("📦 Datenexport",data=export_zip_bytes(),file_name=f"handwerksassistent_{date.today():%Y%m%d}.zip",mime="application/zip",use_container_width=True)


elif st.session_state.page=="firma":
    st.title("Einstellungen")
    with st.form("settings"):
        c1,c2=st.columns(2)
        name=c1.text_input("Firmenname *",value=text(firma.get("name")))
        inhaber=c2.text_input("Inhaber",value=text(firma.get("inhaber")))
        strasse=c1.text_input("Straße",value=text(firma.get("strasse")))
        plz=c2.text_input("PLZ",value=text(firma.get("plz")))
        ort=c1.text_input("Ort",value=text(firma.get("ort")))
        telefon=c2.text_input("Telefon",value=text(firma.get("telefon")))
        email=c1.text_input("E-Mail",value=text(firma.get("email")))
        website=c2.text_input("Website",value=text(firma.get("website")))
        iban=c1.text_input("IBAN",value=text(firma.get("iban")))
        bic=c2.text_input("BIC",value=text(firma.get("bic")))

        st.subheader("Automatisierung")
        auto_rechnung=st.checkbox("Bei angenommenem Angebot automatisch Rechnung erzeugen",value=bool(einstellungen.get("auto_rechnung",True)))
        d1=st.number_input("1. Erinnerung nach Tagen",min_value=1,value=int(number(einstellungen.get("erinnerung_nach_tagen"),3)))
        d2=st.number_input("2. Erinnerung nach Tagen",min_value=1,value=int(number(einstellungen.get("zweite_erinnerung_nach_tagen"),7)))

        st.subheader("E-Mail / SMTP")
        smtp_host=st.text_input("SMTP Host",value=text(einstellungen.get("smtp_host")))
        smtp_port=st.number_input("SMTP Port",min_value=1,max_value=65535,value=int(number(einstellungen.get("smtp_port"),587)))
        smtp_user=st.text_input("SMTP Benutzer",value=text(einstellungen.get("smtp_user")))
        smtp_sender=st.text_input("Absender-E-Mail",value=text(einstellungen.get("smtp_sender")))
        smtp_tls=st.checkbox("STARTTLS verwenden",value=bool(einstellungen.get("smtp_tls",True)))
        st.caption("Cloud-Version: Gmail-Adresse und App-Passwort werden sicher über Streamlit Secrets gelesen.")

        if st.form_submit_button("Einstellungen speichern",type="primary"):
            firma.update({"name":text(name),"inhaber":text(inhaber),"strasse":text(strasse),"plz":text(plz),"ort":text(ort),
                          "telefon":text(telefon),"email":text(email),"website":text(website),"iban":text(iban),"bic":text(bic)})
            einstellungen.update({"auto_rechnung":auto_rechnung,"erinnerung_nach_tagen":int(d1),"zweite_erinnerung_nach_tagen":int(d2),
                                  "smtp_host":text(smtp_host),"smtp_port":int(smtp_port),"smtp_user":text(smtp_user),
                                  "smtp_sender":text(smtp_sender),"smtp_tls":smtp_tls})
            save_all(); st.success("Gespeichert."); st.rerun()

    st.divider()
    st.subheader("Späterer Ausbau")
    st.warning(
        "Wichtig für die Cloud: Die aktuelle JSON-Datenspeicherung ist für einen ersten Online-Test geeignet, "
        "aber nicht dauerhaft zuverlässig. Für echten 24/7-Betrieb migrieren wir Kunden, Angebote und Rechnungen "
        "als nächsten Schritt in eine persistente Cloud-Datenbank."
    )
    st.info("Online-Zahlung ist vorbereitet, braucht aber einen Zahlungsanbieter wie Stripe oder PayPal. KI-Angebotstexte und Preisvorschläge brauchen später eine API-Anbindung.")
