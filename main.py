from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import pdfplumber, re, io
from typing import List

app = FastAPI(title="Alpaca Tax Analyzer")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

MONTH_MAP = {
    "JANUARY":1,"FEBRUARY":2,"MARCH":3,"APRIL":4,"MAY":5,"JUNE":6,
    "JULY":7,"AUGUST":8,"SEPTEMBER":9,"OCTOBER":10,"NOVEMBER":11,"DECEMBER":12
}

def pn(s):
    try: return float(s.replace(",","").replace(" ",""))
    except: return 0.0

def parse_pdf(content: bytes) -> dict:
    r = dict(period=None,year=None,month=None,month_num=None,
             additions=0.0,subtractions=0.0,ending_cash=0.0,total_market_value=0.0,
             dividend_period=0.0,dividend_ytd=0.0,
             st_gain_period=0.0,st_loss_period=0.0,st_net_period=0.0,
             lt_gain_period=0.0,lt_loss_period=0.0,lt_net_period=0.0,
             st_gain_ytd=0.0,st_loss_ytd=0.0,st_net_ytd=0.0,
             lt_gain_ytd=0.0,lt_loss_ytd=0.0,lt_net_ytd=0.0,
             withholding_tax_period=0.0,total_net_period=0.0,total_net_ytd=0.0)
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        txt = "\n".join(p.extract_text() or "" for p in pdf.pages)
    lines = txt.split("\n")
    for ln in lines:
        m = re.search(r"Period\s+([A-Z]+)\s*[-]\s*(\d{4})", ln, re.I)
        if m:
            mo,yr = m.group(1).upper(), int(m.group(2))
            r.update(period=f"{mo} {yr}",year=yr,month=mo,month_num=MONTH_MAP.get(mo,0)); break
    for ln in lines:
        ns = re.findall(r"-?[\d,]+\.?\d*", ln)
        if "Addition" in ln and "Cash" not in ln and ns: r["additions"] = pn(ns[0])
        elif "Subtraction" in ln and ns: r["subtractions"] = pn(ns[0])
        elif "Ending Value" in ln and ns: r["ending_cash"] = pn(ns[-1])
        elif "Total Market Value" in ln and ns: r["total_market_value"] = pn(ns[-1])
    in_inc = False
    for ln in lines:
        if "Income Summary" in ln: in_inc = True; continue
        if in_inc and re.match(r"\s*Dividend", ln):
            ns = re.findall(r"-?[\d,]+\.?\d*", ln)
            if len(ns)>=2: r["dividend_period"]=pn(ns[0]); r["dividend_ytd"]=pn(ns[1])
            in_inc = False
    in_g, st_done = False, False
    for ln in lines:
        if "Realized GainLoss" in ln or "Realized Gain" in ln: in_g=True; continue
        if not in_g: continue
        ns = re.findall(r"-?[\d,]+\.?\d*", ln)
        if re.search(r"Short\s+Term\s+Gain",ln,re.I) and len(ns)>=2:
            r["st_gain_period"]=pn(ns[0]); r["st_gain_ytd"]=pn(ns[1])
        elif re.search(r"^\s*Loss",ln) and not st_done and len(ns)>=2:
            r["st_loss_period"]=pn(ns[0]); r["st_loss_ytd"]=pn(ns[1])
        elif re.search(r"^\s*Net",ln) and not st_done and len(ns)>=2:
            r["st_net_period"]=pn(ns[0]); r["st_net_ytd"]=pn(ns[1]); st_done=True
        elif re.search(r"Long\s+Term\s+Gain",ln,re.I) and len(ns)>=2:
            r["lt_gain_period"]=pn(ns[0]); r["lt_gain_ytd"]=pn(ns[1])
        elif re.search(r"^\s*Loss",ln) and st_done and len(ns)>=2:
            r["lt_loss_period"]=pn(ns[0]); r["lt_loss_ytd"]=pn(ns[1])
        elif re.search(r"^\s*Net",ln) and st_done and len(ns)>=2:
            r["lt_net_period"]=pn(ns[0]); r["lt_net_ytd"]=pn(ns[1]); in_g=False
    wt = 0.0
    for ln in lines:
        if "NRA Withheld" in ln or "AdjNRA" in ln:
            ns = re.findall(r"-[\d,]+\.?\d*", ln)
            if ns: wt += abs(pn(ns[0]))
    r["withholding_tax_period"] = wt
    r["total_net_period"] = r["st_net_period"] + r["lt_net_period"]
    r["total_net_ytd"]    = r["st_net_ytd"]    + r["lt_net_ytd"]
    return r

@app.post("/api/upload")
async def upload(files: List[UploadFile] = File(...)):
    ok, err = [], []
    for f in files:
        try:
            d = parse_pdf(await f.read())
            if d["year"] and d["month_num"]: ok.append(d)
            else: err.append({"file": f.filename, "msg": "Période non détectée"})
        except Exception as e: err.append({"file": f.filename, "msg": str(e)})
    return {"statements": ok, "errors": err}
