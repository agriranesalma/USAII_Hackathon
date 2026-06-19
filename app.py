import json
import os
import re
import time
import uuid
import urllib.error
import urllib.request
from html import escape as html_escape
from typing import Any, Dict, List, Optional

import streamlit as st

# Config
st.set_page_config(page_title="First Gen Compass", page_icon="🧭", layout="centered")

NVIDIA_BASE_URL    = "https://integrate.api.nvidia.com/v1"
NVIDIA_MODEL       = "meta/llama-3.3-70b-instruct"

SCENARIOS = [
    ("Scholarship lost",              "Financial aid is reduced or disappears."),
    ("Family cannot support",         "No extra family money or backup."),
    ("Housing costs rise",            "Rent and living costs are higher than expected."),
    ("Need part-time work",           "You must earn while studying."),
    ("Family emergency",              "You may need to pause or travel back home."),
    ("Internship offer arrives",      "A good internship becomes available."),
    ("Graduate school becomes goal",  "You might want to continue beyond the degree."),
]

# Design system
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,700&display=swap');

/* ── Base ── */
:root {
  --bg-deep:   #050d17;
  --bg-mid:    #081525;
  --surface:   rgba(255,255,255,0.042);
  --surface-hover: rgba(255,255,255,0.07);
  --border:    rgba(255,255,255,0.08);
  --border-hi: rgba(255,255,255,0.14);
  --txt:       #eef2f9;
  --txt-dim:   rgba(238,242,249,0.60);
  --txt-dimmer:rgba(238,242,249,0.38);
  --blue:      #5a9eff;
  --blue-glow: rgba(90,158,255,0.18);
  --emerald:   #34d399;
  --amber:     #fbbf24;
  --rose:      #f87171;
  --violet:    #a78bfa;
  --r:         18px;
}
.stApp {
  background:
    radial-gradient(ellipse 80% 40% at 15% -5%,  rgba(90,120,255,0.13) 0%, transparent 55%),
    radial-gradient(ellipse 60% 30% at 85%  5%,  rgba(249,176,92,0.09) 0%, transparent 50%),
    radial-gradient(ellipse 50% 50% at 50% 100%, rgba(52,211,153,0.05) 0%, transparent 60%),
    linear-gradient(170deg, #050d17 0%, #081525 100%);
  color: var(--txt);
  font-family: 'Inter', sans-serif;
  font-size: 15px;
}
.block-container { padding-top: 2.6rem; padding-bottom: 3rem; max-width: 1280px; }
footer { visibility:hidden; height:0; }
h1,h2,h3,h4 { font-family:'Fraunces',serif !important; letter-spacing:-0.025em; }
a { color: var(--blue); }

/* ── Streamlit overrides ── */
div[data-testid="stSlider"] label,
.stTextInput label, .stTextArea label,
.stSelectbox label, .stMultiSelect label {
  color: var(--txt-dim) !important; font-size:0.82rem !important;
  letter-spacing: 0.04em; text-transform: uppercase;
}
.stTextInput input, .stTextArea textarea, .stSelectbox select {
  background: rgba(255,255,255,0.04) !important;
  border: 1px solid var(--border-hi) !important;
  border-radius: 12px !important;
  color: var(--txt) !important;
}
div[data-testid="stCheckbox"] label { color: var(--txt) !important; font-size: 0.88rem !important; }
.stButton button[kind="primary"] {
  background: linear-gradient(135deg, #3b82f6, #6366f1) !important;
  border: none !important; border-radius: 12px !important;
  font-weight: 700 !important; letter-spacing: 0.02em !important;
  padding: 0.65rem 1.4rem !important;
  box-shadow: 0 4px 24px rgba(99,102,241,0.35) !important;
  transition: transform 0.15s, box-shadow 0.15s !important;
}
.stButton button[kind="primary"]:hover {
  transform: translateY(-1px) !important;
  box-shadow: 0 6px 32px rgba(99,102,241,0.50) !important;
}
.stButton button:not([kind="primary"]) {
  background: var(--surface) !important;
  border: 1px solid var(--border-hi) !important;
  border-radius: 10px !important;
  color: var(--txt-dim) !important;
}
div[data-testid="stDivider"] { opacity:0.18; }

/* ── Hero ── */
.hero {
  position: relative; overflow: hidden;
  padding: 2.4rem 2.6rem 2.2rem;
  border: 1px solid var(--border-hi);
  border-radius: 28px;
  background: linear-gradient(135deg, rgba(90,158,255,0.10), rgba(255,255,255,0.03));
  box-shadow: 0 0 0 1px rgba(90,158,255,0.08), 0 24px 80px rgba(0,0,0,0.35);
  margin-bottom: 1.8rem;
}
.hero::before {
  content:''; position:absolute; inset:0; border-radius:28px;
  background: radial-gradient(ellipse 60% 80% at 100% 0%, rgba(90,158,255,0.08), transparent);
  pointer-events:none;
}
.hero-eyebrow {
  display:inline-flex; align-items:center; gap:0.45rem;
  font-size:0.72rem; font-weight:700; letter-spacing:0.14em;
  text-transform:uppercase; color: var(--blue);
  padding: 0.3rem 0.7rem; border-radius: 999px;
  background: rgba(90,158,255,0.12); border: 1px solid rgba(90,158,255,0.22);
  margin-bottom: 1rem;
}
.hero-title {
  font-size: clamp(2rem, 4vw, 2.9rem);
  font-weight: 700; line-height: 1.12;
  color: var(--txt); margin: 0 0 0.65rem;
}
.hero-title em { font-style:normal; color: var(--blue); }
.hero-sub { color: var(--txt-dim); font-size:1.05rem; line-height:1.65; max-width:680px; margin:0 0 1.2rem; }
.hero-chips { display:flex; flex-wrap:wrap; gap:0.5rem; }
.hero-chip {
  font-size:0.78rem; font-weight:500; padding:0.32rem 0.75rem;
  border-radius:999px; background:rgba(255,255,255,0.05);
  border:1px solid var(--border); color:var(--txt-dim);
}
.hero-chip b { color: var(--txt); }

/* ── Section header ── */
.section-label {
  display:flex; align-items:center; gap:0.6rem;
  margin: 2rem 0 0.6rem; font-size:0.72rem;
  font-weight:700; letter-spacing:0.12em; text-transform:uppercase;
  color: var(--txt-dimmer);
}
.section-label::after {
  content:''; flex:1; height:1px; background:var(--border);
}

/* ── Option input card ── */
.opt-card {
  padding: 1.2rem 1.4rem; margin-bottom: 1rem;
  border-radius: 20px;
  background: rgba(255,255,255,0.03);
  border: 1px solid var(--border-hi);
  box-shadow: 0 4px 20px rgba(0,0,0,0.18);
  transition: border-color 0.2s;
}
.opt-card:hover { border-color: rgba(90,158,255,0.25); }

/* ── Metric chip ── */
.mc {
  padding: 0.9rem 1rem 0.85rem;
  border-radius: 14px;
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--border);
  position: relative; overflow: hidden;
  transition: border-color 0.2s;
}
.mc:hover { border-color: var(--border-hi); }
.mc-label {
  font-size: 0.68rem; font-weight:600; letter-spacing:0.09em;
  text-transform:uppercase; color:var(--txt-dimmer);
}
.mc-value {
  font-size: 1.45rem; font-weight:800; line-height:1;
  margin: 0.3rem 0 0.55rem; color:var(--txt);
}
.mc-bar {
  height: 5px; border-radius:999px; overflow:hidden;
  background: rgba(255,255,255,0.07);
}
.mc-fill { display:block; height:100%; border-radius:999px; }
.mc-tag {
  position:absolute; top:0.75rem; right:0.85rem;
  font-size:0.6rem; font-weight:700; letter-spacing:0.08em;
  text-transform:uppercase; opacity:0.6;
}

/* ── Listbox ── */
.lb {
  padding: 1.1rem 1.2rem; border-radius: 16px; height:100%;
  background: rgba(255,255,255,0.03);
  border: 1px solid var(--border);
}
.lb-header {
  display:flex; align-items:center; gap:0.5rem;
  font-size: 0.72rem; font-weight:700; letter-spacing:0.1em;
  text-transform:uppercase; color:var(--txt-dimmer);
  margin-bottom:0.75rem; padding-bottom:0.65rem;
  border-bottom: 1px solid var(--border);
}
.lb-icon { font-size:0.95rem; }
.lb ul { margin:0; padding:0; list-style:none; }
.lb li {
  display:flex; gap:0.55rem; align-items:flex-start;
  padding: 0.42rem 0; color:var(--txt-dim); font-size:0.88rem;
  line-height:1.55; border-bottom:1px solid rgba(255,255,255,0.04);
}
.lb li:last-child { border-bottom:none; }
.lb li::before {
  content:'›'; color:var(--blue); font-weight:700;
  flex-shrink:0; margin-top:0.02rem; opacity:0.7;
}

/* ── Timeline ── */
.tl-wrap { position:relative; padding: 0.5rem 0; }
.tl-row {
  display:grid; grid-template-columns: 2.2rem 1fr; gap:0 1rem;
  margin-bottom: 0.1rem; position:relative;
}
.tl-node-col { display:flex; flex-direction:column; align-items:center; }
.tl-dot {
  width:2.2rem; height:2.2rem; border-radius:50%; flex-shrink:0;
  display:flex; align-items:center; justify-content:center;
  font-size:0.7rem; font-weight:800; color:#fff; z-index:1;
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  box-shadow: 0 0 0 3px rgba(59,130,246,0.18);
}
.tl-connector {
  width:2px; flex:1; min-height:1rem;
  background: linear-gradient(to bottom, rgba(99,102,241,0.35), rgba(99,102,241,0.08));
  margin: 3px 0;
}
.tl-content {
  padding: 0.75rem 1rem 0.9rem;
  background: rgba(255,255,255,0.03);
  border: 1px solid var(--border);
  border-radius: 14px; margin-bottom: 0.6rem;
}
.tl-stage {
  font-size:0.68rem; font-weight:700; letter-spacing:0.1em;
  text-transform:uppercase; color:var(--blue); margin-bottom:0.25rem;
}
.tl-text { color:var(--txt-dim); font-size:0.88rem; line-height:1.55; }

/* ── Option result card ── */
.opt-result {
  margin-bottom: 1.4rem;
  border: 1px solid var(--border-hi);
  border-radius: 24px; overflow:hidden;
}
.opt-result-head {
  padding: 1.4rem 1.6rem 1.2rem;
  background: linear-gradient(160deg, rgba(90,158,255,0.08), rgba(255,255,255,0.02));
  border-bottom: 1px solid var(--border);
  display:flex; align-items:flex-start; justify-content:space-between; gap:1rem;
}
.opt-result-name {
  font-family:'Fraunces',serif; font-size:1.55rem;
  font-weight:700; letter-spacing:-0.02em; color:var(--txt);
  margin:0 0 0.3rem;
}
.opt-result-summary { color:var(--txt-dim); font-size:0.93rem; line-height:1.6; max-width:680px; }
.opt-result-body { padding: 1.4rem 1.6rem; }

/* ── Comparison panel ── */
.cmp-panel {
  padding: 1.3rem 1.5rem; border-radius: 20px;
  background: linear-gradient(160deg, rgba(90,158,255,0.07), rgba(255,255,255,0.02));
  border: 1px solid rgba(90,158,255,0.18);
  margin-bottom: 1rem;
}
.cmp-panel-label {
  font-size:0.68rem; font-weight:700; letter-spacing:0.12em;
  text-transform:uppercase; color:var(--blue); margin-bottom:0.5rem;
}
.cmp-panel-text { color:var(--txt-dim); font-size:0.92rem; line-height:1.65; }

/* ── Scenario badge ── */
.sc-card {
  padding: 0.85rem 1rem; border-radius:14px; margin-bottom:0.6rem;
  background:rgba(251,191,36,0.06); border:1px solid rgba(251,191,36,0.18);
}
.sc-name { font-weight:700; font-size:0.88rem; color:var(--amber); }
.sc-text { color:var(--txt-dim); font-size:0.84rem; margin-top:0.2rem; line-height:1.5; }

/* ── Stress-test result ── */
.stress-panel {
  padding: 1rem 1.2rem; border-radius:14px; margin-top:1rem;
  background: rgba(167,139,250,0.07); border:1px solid rgba(167,139,250,0.2);
  display:flex; align-items:center; gap:1rem;
}
.stress-icon {
  font-size:1.5rem; flex-shrink:0; line-height:1;
}
.stress-label { font-size:0.7rem; font-weight:700; letter-spacing:0.08em; text-transform:uppercase; color:var(--violet); margin-bottom:0.25rem; }
.stress-delta { font-size:0.92rem; font-weight:500; color:var(--txt-dim); line-height:1.5; }

/* ── Empty state ── */
.empty-state {
  padding: 3rem 2rem; text-align:center;
  border: 1px dashed var(--border-hi); border-radius:24px;
  background: rgba(255,255,255,0.02);
}
.empty-state-icon { font-size:2.8rem; margin-bottom:0.8rem; }
.empty-state-title { font-family:'Fraunces',serif; font-size:1.4rem; margin-bottom:0.4rem; }
.empty-state-text { color:var(--txt-dim); max-width:460px; margin:0 auto; font-size:0.92rem; line-height:1.6; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# Session state
def new_option(n: int) -> Dict[str, str]:
    return {"id": uuid.uuid4().hex[:8], "name": f"Option {n}", "details": "", "gut_take": ""}

_DEFAULT_PROFILE = {
    "name": "", "context_note": "", "risk_tolerance": 5,
    "financial_pressure": 5, "family_support": 5, "home_location": "",
}
for _k, _v in _DEFAULT_PROFILE.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v
if "options"          not in st.session_state: st.session_state.options          = [new_option(1), new_option(2)]
if "engine_result"    not in st.session_state: st.session_state.engine_result    = None
if "show_results"     not in st.session_state: st.session_state.show_results     = False
if "scenario_checks"  not in st.session_state: st.session_state.scenario_checks  = {n: False for n, _ in SCENARIOS}

def profile() -> Dict[str, Any]:
    return {k: st.session_state[k] for k in _DEFAULT_PROFILE}

# API
def get_api_key() -> str:
    try:
        for k in ("NVIDIA_API_KEY", "nvidia_api_key", "api_key"):
            if k in st.secrets:
                v = str(st.secrets[k]).strip()
                if v: return v
    except Exception:
        pass
    return os.getenv("NVIDIA_API_KEY", "").strip()

def nvidia_post(payload: Dict[str, Any], timeout: int = 90, retries: int = 3) -> Dict[str, Any]:
    key = get_api_key()
    if not key:
        raise RuntimeError("No NVIDIA API key configured.")
    url  = f"{NVIDIA_BASE_URL.rstrip('/')}/chat/completions"
    body = json.dumps(payload).encode()
    hdrs = {"Authorization": f"Bearer {key}", "Content-Type": "application/json",
            "Accept": "application/json", "User-Agent": "FirstGenCompass/2.1"}
    last: Optional[Exception] = None
    for attempt in range(retries):
        req = urllib.request.Request(url, data=body, headers=hdrs, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", errors="replace"))
        except urllib.error.HTTPError as e:
            detail = ""
            try: detail = e.read().decode("utf-8", errors="replace")
            except Exception: pass
            if e.code in (408,425,429,500,502,503,504) and attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1)); last = RuntimeError(f"HTTP {e.code}"); continue
            raise RuntimeError(f"NVIDIA HTTP {e.code}: {detail[:800] or e.reason}") from e
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1)); last = e; continue
            raise RuntimeError(f"API call failed: {e}") from e
    raise RuntimeError(f"Exhausted retries: {last}")

def llm(messages: List[Dict], *, temperature: float = 0.15, max_tokens: int = 2800) -> str:
    data = nvidia_post({"model": NVIDIA_MODEL, "messages": messages,
                        "temperature": temperature, "top_p": 0.9,
                        "max_tokens": max_tokens, "stream": False})
    try:
        c0 = data["choices"][0]
        txt = (c0.get("message") or {}).get("content") or c0.get("text", "")
        if isinstance(txt, str) and txt.strip(): return txt
    except Exception: pass
    raise RuntimeError(f"No text in response: {data}")

# Utilities
def parse_json(text: str) -> Optional[Any]:
    if not text: return None
    s = text.strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\s*```$", "", s)
    for cand in [s, s[s.find("{"):s.rfind("}")+1] if "{" in s else ""]:
        if cand:
            try: return json.loads(cand)
            except Exception: pass
    return None

def clip(values: List[str], limit: int = 4) -> List[str]:
    return [str(v).strip() for v in (values or []) if str(v).strip()][:limit]

def coerce(value: Any, default: float = 5.0) -> float:
    if value is None: return float(default)
    if isinstance(value, (int, float)): return float(value)
    if isinstance(value, dict):
        for k in ("score","value","rating","amount"):
            if k in value: return coerce(value[k], default)
        return float(default)
    if isinstance(value, list):
        ns = [coerce(v, None) for v in value]
        ns = [n for n in ns if n is not None]
        return round(sum(ns)/len(ns), 1) if ns else float(default)
    if isinstance(value, str):
        m = re.search(r"(\d+(?:\.\d+)?)", value)
        if m:
            try: return float(m.group(1))
            except Exception: pass
    return float(default)

def clamp(v: float) -> float: return round(max(0.0, min(10.0, v)), 1)

def default_timeline(name: str = "", details: str = "") -> List[Dict[str, str]]:
    t = f"{name} {details}".lower()
    if any(k in t for k in ["community college","two-year","2-year","transfer"]):
        beats = [("Apply","Submit application and check registration."),
                 ("Financial aid","Confirm tuition, books, transit costs after aid."),
                 ("Schedule","Plan around work, commuting, and class times."),
                 ("First semester","Learn advising, support services, and transfer rules."),
                 ("Transfer planning","Map credits early if a four-year move is likely."),
                 ("Next step","Decide whether to transfer, work, or continue locally.")]
    elif any(k in t for k in ["abroad","international","relocat"]):
        beats = [("Apply","Compare deadlines, visa paperwork, and entry requirements."),
                 ("Financial aid","Check tuition, deposits, travel, and first-month costs."),
                 ("Housing","Secure room, transport, and arrival logistics."),
                 ("Move / settle in","Handle paperwork, orientation, and basic routines."),
                 ("First semester","Learn local systems, campus norms, and support channels."),
                 ("Internships","Start earlier — location changes what's available."),
                 ("Graduation","Check whether you can stay, leave, or convert to work status.")]
    else:
        beats = [("Apply","Submit applications and gather documents."),
                 ("Financial aid","Confirm the real cost after aid, loans, and fees."),
                 ("Housing","Check residence, commute, and living expenses."),
                 ("First semester","Learn the academic and social system fast."),
                 ("Internship search","Start applying earlier than you think."),
                 ("Graduation","Decide whether this path opens or narrows options."),
                 ("First job","Translate the degree into the first role.")]
    return [{"stage": s, "what_happens": w} for s, w in beats]

_STALE_FILLER_RE = re.compile(
    r"covid|pandemic|coronavirus|post-covid|unprecedented times|remote learning shift",
    re.IGNORECASE
)

def _drop_stale_filler(items: List[str]) -> List[str]:
    return [s for s in items if not _STALE_FILLER_RE.search(s)]

def normalize(opt: Dict[str, Any]) -> Dict[str, Any]:
    o = dict(opt)
    for key in ["hidden_costs","hidden_benefits","opportunity_costs","first_gen_insights","unknowns","questions_to_investigate"]:
        val = o.get(key, [])
        if isinstance(val, list):   items = [str(x).strip() for x in val if str(x).strip()]
        elif isinstance(val, str):  items = [s.strip() for s in re.split(r"[\n;•]+", val) if s.strip()]
        else:                       items = []
        items = _drop_stale_filler(items)
        o[key] = items
    if not o["unknowns"]:
        o["unknowns"] = ["Exact costs, support systems, and timelines need direct verification with the school."]
    tl, timeline = o.get("timeline", []), []
    if isinstance(tl, list):
        for item in tl:
            if isinstance(item, dict):
                s = str(item.get("stage","")).strip(); w = str(item.get("what_happens","")).strip()
                if s or w: timeline.append({"stage": s or "Stage", "what_happens": w or "—"})
    if not timeline: timeline = default_timeline(o.get("name",""), o.get("details",""))
    o["timeline"] = timeline
    for key in ["flexibility","recovery_difficulty","confidence_level","financial_risk",
                "salary_potential","career_flexibility","path_change_ease","networking",
                "family_support_required","mental_workload","bureaucracy","time_commitment","geographic_mobility"]:
        o[key] = clamp(coerce(o.get(key, 5)))
    o["summary"] = str(o.get("summary") or "Analysis pending.")
    return o

def heuristic(prof: Dict[str, Any], opt: Dict[str, Any]) -> Dict[str, Any]:
    txt = f"{opt.get('name','')} {opt.get('details','')} {prof.get('context_note','')} {prof.get('home_location','')}".lower()
    def bmp(v, a): return max(0.0, min(10.0, v + a))
    fr=5.;sp=5.;cf=5.;pce=5.;nw=5.;fsr=5.;mw=5.;bu=5.;tc=5.;gm=5.;fl=5.;rd=5.;cl=5.
    hc,hb,oc,fgi,un,qi=[],[],[],[],[],[]
    if any(w in txt for w in ["abroad","overseas","international","out of state","relocat"]):
        fr=bmp(fr,2);gm=bmp(gm,3);fsr=bmp(fsr,2);bu=bmp(bu,1)
        hc.append("Relocation, visa, deposit, and first-month setup costs.")
        qi.append("Can I cover relocation, deposits, and first month of living without help?")
    if any(w in txt for w in ["scholarship","funded","financial aid","full ride","stipend"]):
        fr=bmp(fr,-2); hb.append("The real net cost may be much lower than the sticker price.")
    if any(w in txt for w in ["loan","debt","expensive","private","elite","prestigious"]):
        fr=bmp(fr,3); hc.append("Debt and living costs often stack beyond the headline price.")
    if any(w in txt for w in ["community college","local","commute","live at home","public"]):
        fr=bmp(fr,-1);fl=bmp(fl,1);pce=bmp(pce,1);fsr=bmp(fsr,-2)
        hb.append("Proximity reduces logistics, travel cost, and emotional load.")
    if not hc:  hc  = ["Costs beyond tuition — books, transport, housing, activity fees."]
    if not hb:  hb  = ["There may be an opening here not obvious from the name alone."]
    if not oc:  oc  = ["Choosing this means giving up some alternative stability or flexibility."]
    if not fgi: fgi = ["This path may include unwritten rules that experienced families navigate early."]
    if not un:  un  = ["Exact costs, support systems, and timelines need verification."]
    if not qi:  qi  = ["What is the hardest part of this path you cannot tell from the brochure?"]
    return normalize({**opt, "hidden_costs":hc,"hidden_benefits":hb,"opportunity_costs":oc,
        "first_gen_insights":fgi,"unknowns":un,"questions_to_investigate":qi,
        "timeline":default_timeline(opt.get("name",""), opt.get("details","")),
        "financial_risk":fr,"salary_potential":sp,"career_flexibility":cf,"path_change_ease":pce,
        "networking":nw,"family_support_required":fsr,"mental_workload":mw,"bureaucracy":bu,
        "time_commitment":tc,"geographic_mobility":gm,"flexibility":fl,"recovery_difficulty":rd,
        "confidence_level":cl,"summary":"Keyword estimate — AI unavailable."})

# Scoring
def weights(prof: Dict[str, Any]) -> Dict[str, float]:
    risk = float(prof.get("risk_tolerance", 5))
    money = float(prof.get("financial_pressure", 5))
    support = float(prof.get("family_support", 5))
    return {"financial_risk": 10-risk, "salary_potential":5., "career_flexibility":6.,
            "path_change_ease": risk, "networking":5., "family_support_required":10-support,
            "mental_workload": money, "bureaucracy":4., "time_commitment":4.,
            "geographic_mobility":4., "flexibility": risk, "recovery_difficulty":10-risk, "confidence_level":4.}

def score(opt: Dict[str, Any], w: Dict[str, float]) -> float:
    pos = {"salary_potential":opt["salary_potential"],"career_flexibility":opt["career_flexibility"],
           "path_change_ease":opt["path_change_ease"],"networking":opt["networking"],
           "flexibility":opt["flexibility"],"confidence_level":opt["confidence_level"]}
    neg = {"financial_risk":10-opt["financial_risk"],"family_support_required":10-opt["family_support_required"],
           "mental_workload":10-opt["mental_workload"],"bureaucracy":10-opt["bureaucracy"],
           "time_commitment":10-opt["time_commitment"],"geographic_mobility":10-opt["geographic_mobility"],
           "recovery_difficulty":10-opt["recovery_difficulty"]}
    total=wsum=0.0
    for k,v in {**pos,**neg}.items():
        wt=w.get(k,1.); total+=wt*v; wsum+=wt
    return round(total/max(wsum,1.),1)

def apply_scenarios(opt: Dict[str, Any], scenarios: List[str]) -> Dict[str, Any]:
    a = dict(opt)
    for s in scenarios:
        if s == "Scholarship lost":
            a["financial_risk"]=min(10,a["financial_risk"]+3); a["confidence_level"]=max(0,a["confidence_level"]-1)
        elif s == "Family cannot support":
            a["family_support_required"]=min(10,a["family_support_required"]+3); a["mental_workload"]=min(10,a["mental_workload"]+1)
        elif s == "Housing costs rise":
            a["financial_risk"]=min(10,a["financial_risk"]+2); a["time_commitment"]=min(10,a["time_commitment"]+1)
        elif s == "Need part-time work":
            a["time_commitment"]=min(10,a["time_commitment"]+2); a["mental_workload"]=min(10,a["mental_workload"]+2)
        elif s == "Family emergency":
            a["path_change_ease"]=max(0,a["path_change_ease"]-1); a["recovery_difficulty"]=min(10,a["recovery_difficulty"]+2)
        elif s == "Internship offer arrives":
            a["networking"]=min(10,a["networking"]+2); a["salary_potential"]=min(10,a["salary_potential"]+1)
        elif s == "Graduate school becomes goal":
            a["career_flexibility"]=min(10,a["career_flexibility"]+1); a["confidence_level"]=min(10,a["confidence_level"]+1)
    return a

def active_scenarios() -> List[str]:
    return [n for n,_ in SCENARIOS if st.session_state.scenario_checks.get(n)]

_METRIC_LABELS = {
    "financial_risk": "financial risk", "salary_potential": "salary potential",
    "career_flexibility": "career flexibility", "path_change_ease": "path-change ease",
    "networking": "networking", "family_support_required": "family support needed",
    "mental_workload": "mental workload", "bureaucracy": "bureaucracy",
    "time_commitment": "time commitment", "geographic_mobility": "geographic mobility",
    "flexibility": "flexibility", "recovery_difficulty": "recovery difficulty",
    "confidence_level": "confidence in the path",
}
_BAD_WHEN_UP = {"financial_risk","family_support_required","mental_workload","bureaucracy",
                "time_commitment","geographic_mobility","recovery_difficulty"}

def scenario_impact_text(opt: Dict[str, Any], scenarios: List[str]) -> str:
    """Describe, in plain language, which metrics shift for this option under the
    selected scenarios — no numeric score."""
    before = opt
    after  = apply_scenarios(opt, scenarios)
    ups, downs = [], []
    for key, label in _METRIC_LABELS.items():
        b, a = before.get(key, 5), after.get(key, 5)
        if a == b: continue
        worse = (a > b) if key in _BAD_WHEN_UP else (a < b)
        (downs if worse else ups).append(label)
    if not ups and not downs:
        return "This option is largely unaffected by the scenario(s) you selected."
    parts = []
    if downs: parts.append(f"raises {', '.join(downs)}")
    if ups:   parts.append(f"reduces {', '.join(ups)}")
    return "Under the selected scenario(s), this option " + " and ".join(parts) + "."

# AI prompt
def build_prompt(prof: Dict[str, Any], opts: List[Dict[str, Any]]) -> str:
    ctx = {"risk_tolerance_0_to_10": prof.get("risk_tolerance"),
           "financial_pressure_0_to_10": prof.get("financial_pressure"),
           "family_support_0_to_10": prof.get("family_support"),
           "home_location": prof.get("home_location") or "not specified",
           "extra_context": prof.get("context_note") or "none",
           "active_scenarios": active_scenarios()}
    opts_block = ""
    for i, o in enumerate(opts, 1):
        opts_block += f"\nOption {i}:\n  name: {o['name']}\n  student notes: {o.get('details','none')}\n  gut take: {o.get('gut_take','none')}\n"
    return f"""You are an expert college advisor with deep knowledge of US universities, international institutions, living costs, financial aid, and career outcomes.

=== CRITICAL RULES ===
1. USE YOUR TRAINING KNOWLEDGE. "UCLA" = UC system, LA, ~$14k in-state + ~$20k living, ~$44k out-of-state total, massive entertainment/tech alumni network, quarter system. "MIT" = Cambridge MA, ~$60k tuition, elite networking, crushing workload. "Community college" = $1-3k/yr, flexible, transfer pathway. USE THIS KNOWLEDGE.
2. NEVER output 5 as a default score. Every number must reflect your actual knowledge. Scores of 5 are only correct if you genuinely judge something average.
3. DIFFERENTIATE MEANINGFULLY. UCLA vs community college must look completely different in the output.
4. Return ONLY valid JSON. No preamble, markdown, or text outside the JSON.
5. NEVER mention COVID-19, the pandemic, "unprecedented times," or other stale 2020-2022-era uncertainty as an "unknown." That period has long passed and is not a live risk factor. Every "unknown" must be a concrete, present-day uncertainty specific to this student and this option (e.g. "Whether this major's funding model changes before you graduate," "How your specific financial aid package is recalculated after year one") — never generic disclaimers about the future being unpredictable.

=== SCORING SCALE ===
financial_risk:         0=fully funded/free, 3=very affordable, 5=~$25k/yr total, 7=$40-60k/yr, 9=extreme debt, 10=financial catastrophe
salary_potential:       0=very low earnings path, 5=median, 7=above average, 9=elite field
networking:             0=no alumni/connections, 5=average, 8=strong industry ties, 10=elite placement (MIT/Stanford level)
family_support_required:0=fully self-sufficient, 5=moderate logistics need, 10=totally dependent on family money/help
mental_workload:        0=very light, 5=normal college, 8=demanding, 10=med/law school intensity
bureaucracy:            0=simple, 5=normal paperwork, 8=CSS+FAFSA+visa+housing lottery, 10=nightmare
geographic_mobility:    0=stay home, 5=different city, 7=different state, 10=international relocation
recovery_difficulty:    0=trivial to leave/pivot, 5=moderate friction, 10=very hard to recover (debt+niche+relocation)
career_flexibility:     0=locked into one role, 10=opens many career paths
path_change_ease:       0=nearly impossible to switch, 10=very easy to transfer or pivot
flexibility:            0=rigid fixed schedule, 10=fully flexible
confidence_level:       0=very unclear path, 10=extremely well-mapped outcomes

=== STUDENT PROFILE ===
{json.dumps(ctx, ensure_ascii=False, indent=2)}

=== OPTIONS ===
{opts_block}

Return ONLY this JSON object:
{{
  "comparison": {{
    "biggest_tradeoff": "one paragraph naming each option directly and explaining the core tension",
    "what_first_gen_students_miss": ["specific insight about THESE options","second","third"],
    "questions_to_research": ["specific question for financial aid office","another","third"]
  }},
  "options": [
    {{
      "name": "<exactly match input name>",
      "summary": "2 sentences: what this path really is and what it truly costs",
      "hidden_costs": ["specific cost with dollar amount if possible","another"],
      "hidden_benefits": ["specific benefit unique to this institution","another"],
      "opportunity_costs": ["what you concretely give up vs the other option(s)"],
      "first_gen_insights": ["specific unwritten rule at this institution","another","third"],
      "timeline": [
        {{"stage":"Apply","what_happens":"specific deadlines and essay requirements for this school"}},
        {{"stage":"Financial aid","what_happens":"specific aid process and deadlines for this school"}},
        {{"stage":"Housing","what_happens":"specific housing costs in this city/campus"}},
        {{"stage":"First semester","what_happens":"what the academic environment is like here specifically"}},
        {{"stage":"Internships","what_happens":"how recruiting works from this school"}},
        {{"stage":"Graduation","what_happens":"placement rates and alumni network access at this school"}}
      ],
      "unknowns": ["something genuinely uncertain for this student"],
      "questions_to_investigate": ["specific question to ask this school","another"],
      "financial_risk": <0-10, DO NOT default to 5>,
      "salary_potential": <0-10>,
      "career_flexibility": <0-10>,
      "path_change_ease": <0-10>,
      "networking": <0-10>,
      "family_support_required": <0-10>,
      "mental_workload": <0-10>,
      "bureaucracy": <0-10>,
      "time_commitment": <0-10>,
      "geographic_mobility": <0-10>,
      "flexibility": <0-10>,
      "recovery_difficulty": <0-10>,
      "confidence_level": <0-10>
    }}
  ]
}}"""

def fallback_comparison(opts: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not opts:
        return {"biggest_tradeoff":"Not enough information to compare yet.",
                "what_first_gen_students_miss":["The real net cost — not tuition alone.",
                    "Unwritten networking expectations.","How hard it is to leave mid-path."],
                "questions_to_research":["What is the net price after aid for your income bracket?",
                    "What if aid changes after year one?","How easy is it to transfer or pause?"]}
    lo = min(opts, key=lambda o: o["financial_risk"])
    hi = max(opts, key=lambda o: o["salary_potential"]+o["networking"])
    tradeoff = (f"{lo['name']} carries lower financial risk, while {hi['name']} offers stronger upside — but likely asks more upfront."
                if lo["name"] != hi["name"] else "The options are closer than they appear on the surface.")
    return {"biggest_tradeoff": tradeoff,
            "what_first_gen_students_miss":["Total cost of attendance including housing, books, transport — not tuition alone.",
                "Unwritten networking expectations that experienced families navigate from day one.",
                "How hard it is to leave, transfer, or recover if the plan changes."],
            "questions_to_research":["What does the net price calculator show for your family income?",
                "What happens to your aid if your family situation changes after year one?",
                "How easy is it to switch programs, transfer, or pause if needed?"]}

# Engine
NUMERIC_KEYS = ["flexibility","recovery_difficulty","confidence_level","financial_risk",
                "salary_potential","career_flexibility","path_change_ease","networking",
                "family_support_required","mental_workload","bureaucracy","time_commitment","geographic_mobility"]
TEXT_KEYS    = ["summary","hidden_costs","hidden_benefits","opportunity_costs",
                "first_gen_insights","timeline","unknowns","questions_to_investigate"]

def run_engine(prof: Dict[str, Any], opts: List[Dict[str, Any]]) -> Dict[str, Any]:
    try:
        raw = llm([
            {"role":"system","content":"You are a college advisor with encyclopedic knowledge of real institutions, their costs, aid policies, and career outcomes. Return only valid JSON. Never default any score to 5."},
            {"role":"user","content":build_prompt(prof, opts)},
        ])
        data = parse_json(raw)
        if not isinstance(data, dict): raise RuntimeError("No JSON object.")
        ai_opts = data.get("options", [])
        if not isinstance(ai_opts, list) or not ai_opts: raise RuntimeError("Empty options.")

        by_name: Dict[str, Dict] = {}
        for ao in ai_opts:
            if isinstance(ao, dict):
                by_name[str(ao.get("name","")).strip().lower()] = ao

        merged = []
        for src in opts:
            sk = src.get("name","").strip().lower()
            ai = by_name.get(sk)
            if ai is None:
                for k,v in by_name.items():
                    ws = sk.split()
                    if ws and (ws[0] in k or k.split()[0] in sk): ai = v; break
            if ai is None:
                merged.append(heuristic(prof, src)); continue

            row: Dict[str, Any] = {"id":src.get("id",uuid.uuid4().hex[:8]),
                                   "name":src["name"],"details":src.get("details",""),"gut_take":src.get("gut_take","")}
            for key in TEXT_KEYS:
                v = ai.get(key)
                if v not in (None, "", []): row[key] = v
            for key in NUMERIC_KEYS:
                rv = ai.get(key)
                if rv is not None: row[key] = clamp(coerce(rv))
            merged.append(normalize(row))

        # Sanity: if all financial_risk scores are exactly 5.0, override with heuristics
        if len(merged) >= 2 and len({o.get("financial_risk",5) for o in merged}) == 1:
            for i,(m,src) in enumerate(zip(merged, opts)):
                h = heuristic(prof, src)
                for key in NUMERIC_KEYS:
                    if m.get(key, 5.0) == 5.0: m[key] = h.get(key, 5.0)

        comp_raw = data.get("comparison", {})
        if not isinstance(comp_raw, dict): comp_raw = {}
        fb = fallback_comparison(merged)
        comparison = {
            "biggest_tradeoff": str(comp_raw.get("biggest_tradeoff") or fb["biggest_tradeoff"]),
            "what_first_gen_students_miss": clip(comp_raw.get("what_first_gen_students_miss") or fb["what_first_gen_students_miss"], 5),
            "questions_to_research": clip(comp_raw.get("questions_to_research") or fb["questions_to_research"], 5),
        }
        return {"options": merged, "comparison": comparison, "used_ai": True}

    except Exception as e:
        st.warning(f"AI unavailable ({e}) — showing keyword estimates.")
        fb_opts = [heuristic(prof, o) for o in opts]
        return {"options": fb_opts, "comparison": fallback_comparison(fb_opts), "used_ai": False}

# Rendering
_POSITIVE_KEYS = {"salary_potential","networking","career_flexibility","flexibility","confidence_level","path_change_ease"}

def _bar_color(key: str, val: float) -> str:
    if key in _POSITIVE_KEYS:
        if val >= 7: return "linear-gradient(90deg, #059669, #34d399)"
        if val >= 4: return "linear-gradient(90deg, #0d9488, #5eead4)"
        return "linear-gradient(90deg, #1e40af, #60a5fa)"
    else:
        if val >= 7: return "linear-gradient(90deg, #dc2626, #f87171)"
        if val >= 4: return "linear-gradient(90deg, #b45309, #fbbf24)"
        return "linear-gradient(90deg, #059669, #34d399)"

def _risk_tag(key: str) -> str:
    if key in _POSITIVE_KEYS: return "UPSIDE"
    return "RISK"

def metric_chip(label: str, key: str, val: float) -> str:
    color = _bar_color(key, val)
    tag   = _risk_tag(key)
    return (f'<div class="mc">'
            f'<div class="mc-label">{html_escape(label)}</div>'
            f'<div class="mc-value">{val:.1f}</div>'
            f'<div class="mc-bar"><span class="mc-fill" style="width:{val*10:.0f}%;background:{color}"></span></div>'
            f'<div class="mc-tag">{tag}</div>'
            f'</div>')

_LB_ICONS = {
    "Hidden costs":              ("💸", "rgba(248,113,113,0.10)", "rgba(248,113,113,0.22)"),
    "Hidden benefits":           ("✨", "rgba(52,211,153,0.10)",  "rgba(52,211,153,0.22)"),
    "Opportunity costs":         ("⚖️", "rgba(251,191,36,0.10)",  "rgba(251,191,36,0.22)"),
    "First-generation insights": ("🧭", "rgba(90,158,255,0.10)",  "rgba(90,158,255,0.22)"),
    "Unknowns":                  ("❓", "rgba(167,139,250,0.10)", "rgba(167,139,250,0.22)"),
    "Questions to investigate":  ("🔍", "rgba(94,234,212,0.10)",  "rgba(94,234,212,0.22)"),
}

def render_listbox(title: str, items: List[str]) -> str:
    icon, bg, border = _LB_ICONS.get(title, ("›", "rgba(255,255,255,0.03)", "rgba(255,255,255,0.08)"))
    if not items: items = ["—"]
    lis = "".join(f"<li>{html_escape(i)}</li>" for i in items)
    return (f'<div class="lb" style="background:{bg};border-color:{border};">'
            f'<div class="lb-header"><span class="lb-icon">{icon}</span>{html_escape(title)}</div>'
            f'<ul>{lis}</ul></div>')

def render_timeline(opt: Dict[str, Any]) -> str:
    stages = opt.get("timeline") or []
    rows = []
    for i, s in enumerate(stages):
        last = i == len(stages) - 1
        connector = "" if last else '<div class="tl-connector"></div>'
        rows.append(
            f'<div class="tl-row">'
            f'<div class="tl-node-col"><div class="tl-dot">{i+1}</div>{connector}</div>'
            f'<div class="tl-content" style="align-self:start">'
            f'<div class="tl-stage">{html_escape(s.get("stage","Stage"))}</div>'
            f'<div class="tl-text">{html_escape(s.get("what_happens",""))}</div>'
            f'</div></div>'
        )
    return f'<div class="tl-wrap">{"".join(rows)}</div>'

def render_map_svg(prof: Dict[str, Any], opts: List[Dict[str, Any]]) -> str:
    n = max(len(opts), 1)
    cw, ch, gap = 320, 240, 40
    width   = max(1100, n * (cw + gap) + 140)
    height  = 740
    cx      = width // 2
    ry, py, cy2 = 56, 150, 268

    def e(s): return html_escape(str(s))
    def t(x, y, txt, sz=13, fw=500, col="#EEF2F9", anchor="middle", ff="Inter"):
        return (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" fill="{col}" '
                f'font-size="{sz}" font-weight="{fw}" font-family="{ff}">{e(txt)}</text>')

    out = [f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" xmlns="http://www.w3.org/2000/svg">']
    out.append("""<defs>
      <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stop-color="#050d17"/><stop offset="100%" stop-color="#081525"/>
      </linearGradient>
      <linearGradient id="card" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#f1f5fb"/><stop offset="100%" stop-color="#dde5f4"/>
      </linearGradient>
      <linearGradient id="bar" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0%" stop-color="#3b82f6"/><stop offset="100%" stop-color="#6366f1"/>
      </linearGradient>
      <filter id="sh"><feDropShadow dx="0" dy="14" stdDeviation="18" flood-color="#000" flood-opacity="0.4"/></filter>
      <filter id="glow"><feGaussianBlur stdDeviation="6" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
      <style>
        .ln{stroke-dasharray:900;stroke-dashoffset:900;animation:draw 1.2s ease-out forwards}
        .cd{opacity:0;animation:rise .65s ease-out forwards}
        @keyframes draw{to{stroke-dashoffset:0}}
        @keyframes rise{from{opacity:0;transform:translateY(18px)}to{opacity:1;transform:translateY(0)}}
      </style>
    </defs>""")
    out.append(f'<rect width="{width}" height="{height}" fill="url(#bg)"/>')
    out.append(f'<circle cx="{cx}" cy="{ry+18}" r="28" fill="rgba(90,158,255,0.15)" filter="url(#glow)"/>')
    out.append(f'<circle cx="{cx}" cy="{ry+18}" r="8" fill="#5a9eff"/>')
    out.append(t(cx, ry-4, "YOU ARE HERE", 10, 700, "#5a9eff"))
    out.append(t(cx, ry+44, prof.get("name") or "This decision", 22, 700, "#EEF2F9", ff="Fraunces"))
    out.append(t(cx, py, "Which path to take", 13, 600, "rgba(238,242,249,0.55)"))
    out.append(f'<line x1="{cx}" y1="{ry+50}" x2="{cx}" y2="{py-10}" stroke="rgba(90,158,255,0.25)" stroke-width="1.5" stroke-dasharray="4,3"/>')

    sx = cx - ((n-1)*(cw+gap))/2
    mkeys  = ["financial_risk","salary_potential","networking","recovery_difficulty"]
    mlabels = ["Financial risk","Salary potential","Networking","Recovery diff."]
    mcols  = ["#f87171","#34d399","#60a5fa","#fbbf24"]
    mhigh_bad = [True, False, False, True]

    for i, opt in enumerate(opts):
        x   = sx + i*(cw+gap)
        mid = x + cw/2
        d   = 0.13*i
        out.append(f'<path class="ln" d="M{cx:.0f} {py+16} Q{cx:.0f} {cy2-48} {mid:.0f} {cy2-12}" '
                   f'fill="none" stroke="rgba(90,158,255,0.20)" stroke-width="1.5" style="animation-delay:{d:.2f}s"/>')
        g = [f'<g class="cd" style="animation-delay:{d+0.38:.2f}s">']
        g.append(f'<rect x="{x:.1f}" y="{cy2}" width="{cw}" height="{ch}" rx="22" '
                 f'fill="url(#card)" stroke="rgba(90,158,255,0.14)" stroke-width="1" filter="url(#sh)"/>')
        g.append(t(mid, cy2+30, opt["name"], 16, 800, "#0f172a", ff="Fraunces"))
        summary = str(opt.get("summary",""))[:58]
        g.append(t(mid, cy2+50, summary, 10, 400, "#475569"))
        base_y = cy2+74
        for j,(mk,ml,mc,hi_bad) in enumerate(zip(mkeys,mlabels,mcols,mhigh_bad)):
            dy = base_y + j*38
            val = coerce(opt.get(mk, 5))
            bar_col = mc if not hi_bad else ("#34d399" if val < 4 else ("#fbbf24" if val < 7 else "#f87171"))
            g.append(t(x+16, dy, ml, 8, 600, "#475569", anchor="start"))
            g.append(t(x+cw-16, dy, f"{val:.1f}", 10, 700, "#0f172a", anchor="end"))
            g.append(f'<rect x="{x+16:.1f}" y="{dy+6:.1f}" width="{cw-32}" height="6" rx="999" fill="rgba(15,23,42,0.12)"/>')
            g.append(f'<rect x="{x+16:.1f}" y="{dy+6:.1f}" width="{val/10*(cw-32):.1f}" height="6" rx="999" fill="{bar_col}"/>')
        g.append("</g>")
        out.append("".join(g))
    out.append("</svg>")
    return "".join(out)

# UI — Hero
st.markdown("""
<div class="hero">
  <div class="hero-eyebrow">🧭 First Gen Compass</div>
  <h1 class="hero-title">See the <em>hidden realities</em><br>before you decide.</h1>
  <p class="hero-sub">
    The AI draws on real knowledge of specific colleges, cities, costs, and career paths —
    not generic defaults. No verdicts. No "best choice." Just a clearer map of what each
    path truly asks from you.
  </p>
  <div class="hero-chips">
    <span class="hero-chip"><b>Real college data</b> — not guesses</span>
    <span class="hero-chip"><b>Color-coded risk</b> at a glance</span>
    <span class="hero-chip"><b>Step-by-step timeline</b></span>
    <span class="hero-chip"><b>Scenario stress-test</b></span>
    <span class="hero-chip"><b>First-gen specific</b> insights</span>
  </div>
</div>
""", unsafe_allow_html=True)

# API key status
if not get_api_key():
    st.warning(
        "No NVIDIA API key configured. Add `NVIDIA_API_KEY` to this app's "
        "Streamlit secrets (Settings → Secrets) to enable AI reasoning. "
        "Without it, results fall back to keyword-based estimates."
    )

# Profile
st.markdown('<div class="section-label">Your situation</div>', unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)
with c1:
    st.session_state["name"]         = st.text_input("Your name (optional)",    value=st.session_state["name"],         placeholder="For the map label")
with c2:
    st.session_state["context_note"] = st.text_input("One-line context",         value=st.session_state["context_note"], placeholder="e.g. first in family to study abroad")
with c3:
    st.session_state["home_location"]= st.text_input("Home city / country",      value=st.session_state["home_location"],placeholder="e.g. Rabat, Morocco")

s1, s2, s3 = st.columns(3)
with s1: st.session_state["risk_tolerance"]    = st.slider("Risk tolerance",           0, 10, int(st.session_state["risk_tolerance"]))
with s2: st.session_state["financial_pressure"]= st.slider("Financial pressure",       0, 10, int(st.session_state["financial_pressure"]))
with s3: st.session_state["family_support"]    = st.slider("Family support / guidance",0, 10, int(st.session_state["family_support"]))
st.caption("These sliders weight the scores toward what matters most in your situation.")

# Scenarios
st.markdown('<div class="section-label">Scenario stress-test</div>', unsafe_allow_html=True)
scols = st.columns(4)
for i, (name, desc) in enumerate(SCENARIOS):
    with scols[i % 4]:
        st.session_state.scenario_checks[name] = st.checkbox(name, value=st.session_state.scenario_checks[name], help=desc)

st.divider()

# Option inputs
st.markdown('<div class="section-label">Your options</div>', unsafe_allow_html=True)
ac, rc = st.columns([1, 1])
with ac:
    if st.button("＋ Add option", use_container_width=True):
        st.session_state.options.append(new_option(len(st.session_state.options)+1))
with rc:
    if st.button("↺ Start over", use_container_width=True):
        for k in ["options","engine_result","show_results"]:
            st.session_state[k] = [new_option(1), new_option(2)] if k == "options" else (None if k == "engine_result" else False)
        st.rerun()

for opt in list(st.session_state.options):
    oid = opt["id"]
    st.markdown('<div class="opt-card">', unsafe_allow_html=True)
    h1, h2 = st.columns([5, 1])
    with h1:
        opt["name"] = st.text_input("Option name", value=opt["name"], key=f"n_{oid}", label_visibility="collapsed",
                                    placeholder="e.g. UCLA, MIT, Local community college, Coding bootcamp…")
    with h2:
        if st.button("Remove", key=f"rm_{oid}", use_container_width=True) and len(st.session_state.options) > 2:
            st.session_state.options = [o for o in st.session_state.options if o["id"] != oid]
            st.session_state.engine_result = None; st.session_state.show_results = False; st.rerun()
    opt["details"]  = st.text_area("Details", value=opt.get("details",""), key=f"d_{oid}",
                                   label_visibility="collapsed", height=80,
                                   placeholder="Optional extra context — cost, location, major, situation. Just a school name works too.")
    opt["gut_take"] = st.text_input("Gut take", value=opt.get("gut_take",""), key=f"g_{oid}",
                                    placeholder="Your intuition — the AI will engage with it, not override it.")
    st.markdown('</div>', unsafe_allow_html=True)

if st.button("🗺️  Chart the paths", type="primary", use_container_width=True):
    with st.spinner("AI is reasoning about your specific options — usually 15-25 seconds…"):
        prof = profile()
        result = run_engine(prof, st.session_state.options)
    st.session_state.engine_result = result
    st.session_state.show_results  = True

st.divider()

# Results
if st.session_state.show_results and st.session_state.engine_result:
    result = st.session_state.engine_result
    ranked = list(result["options"])
    act    = active_scenarios()
    prof   = profile()
    w      = weights(prof)

    if result.get("used_ai"):
        st.success("✓ AI reasoning used — scores reflect real knowledge of these specific institutions and paths.")
    else:
        st.warning("Showing keyword-based estimates — AI was unavailable. Add your NVIDIA API key for accurate scores.")

    # Map
    st.markdown('<div class="section-label">Decision map</div>', unsafe_allow_html=True)
    st.caption("Visual ranks are not a recommendation — they show the structure of the trade-off given your profile.")
    st.components.v1.html(render_map_svg(prof, ranked), height=740, scrolling=True)

    # Comparison
    st.markdown('<div class="section-label">Comparison</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="cmp-panel"><div class="cmp-panel-label">Biggest trade-off</div>'
        f'<div class="cmp-panel-text">{html_escape(result["comparison"]["biggest_tradeoff"])}</div></div>',
        unsafe_allow_html=True)

    cc1, cc2, cc3 = st.columns(3)
    with cc1:
        st.markdown(render_listbox("First-generation insights",
                                   result["comparison"]["what_first_gen_students_miss"]), unsafe_allow_html=True)
    with cc2:
        st.markdown(render_listbox("Questions to research",
                                   result["comparison"]["questions_to_research"]), unsafe_allow_html=True)
    with cc3:
        if act:
            IMPACT_MAP = {
                "Scholarship lost":             "Financial risk spikes — the most cost-exposed path feels it first.",
                "Family cannot support":        "The path leaning on family logistics becomes much harder.",
                "Housing costs rise":           "Living cost buffer shrinks; most expensive option is most exposed.",
                "Need part-time work":          "Time pressure and mental load increase significantly.",
                "Family emergency":             "Recovery difficulty rises and path-change ease drops.",
                "Internship offer arrives":     "Networking and salary upside become more decisive.",
                "Graduate school becomes goal": "Long-term flexibility and career credentials matter more.",
            }
            for s in act:
                worst, worst_d = "—", 0.0
                for o in ranked:
                    d = round(score(apply_scenarios(o,[s]),w) - score(o,w), 1)
                    if abs(d) >= abs(worst_d): worst_d = d; worst = o["name"]
                dt = f"{'+' if worst_d > 0 else ''}{worst_d:.1f}"
                st.markdown(
                    f'<div class="sc-card"><div class="sc-name">{html_escape(s)}</div>'
                    f'<div class="sc-text">{html_escape(IMPACT_MAP.get(s,"The scenario shifts the risk balance."))} '
                    f'Most exposed: <b>{html_escape(worst)}</b> ({html_escape(dt)} pts)</div></div>',
                    unsafe_allow_html=True)
        else:
            st.markdown(render_listbox("Unknowns",[
                "Toggle scenarios above to stress-test which path breaks first.",
                "Each scenario shows the most exposed option and the score shift."]), unsafe_allow_html=True)

    # Per-option breakdown
    st.markdown('<div class="section-label">Option-by-option breakdown</div>', unsafe_allow_html=True)

    for opt in ranked:
        st.markdown(
            f'<div class="opt-result">'
            f'<div class="opt-result-head">'
            f'<div><div class="opt-result-name">{html_escape(opt["name"])}</div>'
            f'<div class="opt-result-summary">{html_escape(opt.get("summary",""))}</div></div>'
            f'</div><div class="opt-result-body">',
            unsafe_allow_html=True)

        m1,m2,m3,m4 = st.columns(4)
        with m1:
            st.markdown(metric_chip("Financial risk",      "financial_risk",      opt["financial_risk"]),      unsafe_allow_html=True)
            st.markdown(metric_chip("Salary potential",    "salary_potential",    opt["salary_potential"]),    unsafe_allow_html=True)
        with m2:
            st.markdown(metric_chip("Career flexibility",  "career_flexibility",  opt["career_flexibility"]),  unsafe_allow_html=True)
            st.markdown(metric_chip("Path-change ease",    "path_change_ease",    opt["path_change_ease"]),    unsafe_allow_html=True)
        with m3:
            st.markdown(metric_chip("Networking",          "networking",          opt["networking"]),          unsafe_allow_html=True)
            st.markdown(metric_chip("Family support req.", "family_support_required", opt["family_support_required"]), unsafe_allow_html=True)
        with m4:
            st.markdown(metric_chip("Mental workload",     "mental_workload",     opt["mental_workload"]),     unsafe_allow_html=True)
            st.markdown(metric_chip("Recovery difficulty", "recovery_difficulty", opt["recovery_difficulty"]), unsafe_allow_html=True)

        st.markdown("<div style='height:1.1rem'></div>", unsafe_allow_html=True)

        la, lb, lc = st.columns(3)
        with la: st.markdown(render_listbox("Hidden costs",             opt["hidden_costs"]),             unsafe_allow_html=True)
        with lb: st.markdown(render_listbox("Hidden benefits",          opt["hidden_benefits"]),          unsafe_allow_html=True)
        with lc: st.markdown(render_listbox("Opportunity costs",        opt["opportunity_costs"]),        unsafe_allow_html=True)

        st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)

        ld, le, lf = st.columns(3)
        with ld: st.markdown(render_listbox("First-generation insights",opt["first_gen_insights"]),       unsafe_allow_html=True)
        with le: st.markdown(render_listbox("Unknowns",                 opt["unknowns"]),                 unsafe_allow_html=True)
        with lf: st.markdown(render_listbox("Questions to investigate", opt["questions_to_investigate"]), unsafe_allow_html=True)

        st.markdown("<div style='height:1.1rem'></div>", unsafe_allow_html=True)

        st.markdown("**Step-by-step timeline**", unsafe_allow_html=True)
        st.components.v1.html(
            f"<style>*{{box-sizing:border-box;font-family:'Inter',sans-serif}}"
            f".tl-wrap{{padding:0.5rem 0}}"
            f".tl-row{{display:grid;grid-template-columns:2.4rem 1fr;gap:0 0.9rem;margin-bottom:0}}"
            f".tl-node-col{{display:flex;flex-direction:column;align-items:center}}"
            f".tl-dot{{width:2.2rem;height:2.2rem;border-radius:50%;background:linear-gradient(135deg,#3b82f6,#6366f1);"
            f"display:flex;align-items:center;justify-content:center;font-size:0.7rem;font-weight:800;color:#fff;"
            f"box-shadow:0 0 0 3px rgba(59,130,246,0.18);flex-shrink:0}}"
            f".tl-connector{{width:2px;flex:1;min-height:0.8rem;background:linear-gradient(to bottom,rgba(99,102,241,0.4),rgba(99,102,241,0.08));margin:2px 0}}"
            f".tl-content{{background:rgba(248,250,252,0.06);border:1px solid rgba(255,255,255,0.09);"
            f"border-radius:14px;padding:0.7rem 1rem 0.8rem;margin-bottom:0.55rem;color:#cdd6e8}}"
            f".tl-stage{{font-size:0.66rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;"
            f"color:#60a5fa;margin-bottom:0.2rem}}"
            f".tl-text{{font-size:0.86rem;line-height:1.55;color:rgba(205,214,232,0.82)}}</style>"
            + render_timeline(opt),
            height=max(280, len(opt.get("timeline",[])) * 88), scrolling=False)

        if act:
            impact_text = scenario_impact_text(opt, act)
            st.markdown(
                f'<div class="stress-panel">'
                f'<div class="stress-icon">⚖️</div>'
                f'<div><div class="stress-label">Under your selected scenario(s)</div>'
                f'<div class="stress-delta">{html_escape(impact_text)}</div>'
                f'</div></div>', unsafe_allow_html=True)
            
        st.markdown("</div></div>", unsafe_allow_html=True)
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="empty-state">
      <div class="empty-state-icon">🗺️</div>
      <div class="empty-state-title">Your map will appear here</div>
      <div class="empty-state-text">
        Enter any college names, paths, or options above and click <b>Chart the paths</b>.
        Just a name is enough — the AI already knows UCLA, MIT, community colleges, and thousands more.
      </div>
    </div>""", unsafe_allow_html=True)
