"""data/*.csv -> dist/dashboard.html (I10 / E11 / E78 claim dashboard).

claim 중 주상병(main_sick)이 I10·E11·E78 로 시작하는 건만 추려 행 단위로 내장하고,
집계는 브라우저에서 필터에 맞춰 다시 계산한다.
"""
import csv, json, re, collections, pathlib

ROOT = pathlib.Path(__file__).parent
D = ROOT / "data"


def read(name):
    with open(D / f"{name}.csv", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


GROUPS = [("I10", "고혈압"), ("E11", "2형 당뇨"), ("E78", "이상지질혈증")]
AGE_BANDS = ["40세 미만", "40대", "50대", "60대", "70대", "80세 이상"]
CL_NAMES = {"01": "상급종합병원", "11": "종합병원", "21": "병원", "31": "의원"}
CLASS_NAMES = {"214": "혈압강하제", "218": "고지혈증용제", "219": "기타 순환계용약", "396": "당뇨병용제"}


def age_band(age):
    for i, edge in enumerate((40, 50, 60, 70, 80)):
        if age < edge:
            return i
    return 5


claims = [r for r in read("claim") if r["main_sick"][:3] in dict(GROUPS)]
patients = {r["jid"]: r for r in read("patient")}
insts = {r["yid"]: r for r in read("institution")}
sidos = read("sido_code")
sick_nm = {}
for r in read("sick_master"):
    sick_nm.setdefault(r["sickcd"], r["krnm"])

sido_idx = {s["sido_cd"]: i for i, s in enumerate(sidos)}
region_names = {}
for s in sidos:
    region_names[s["region_cd"]] = s["region_nm"]

sick_codes = sorted({r["main_sick"] for r in claims})
jids = sorted({r["jid"] for r in claims})
yids = sorted({r["yid"] for r in claims}, key=int)
jid_i = {j: i for i, j in enumerate(jids)}
yid_i = {y: i for i, y in enumerate(yids)}
cl_codes = list(CL_NAMES)
reg_codes = sorted(region_names)
quint = sorted({patients[j]["prem_quintile"] for j in jids})

# 성분
ing = {}
for r in read("drug_ingredient"):
    ing.setdefault(r["gnl_cd"], r)
mids = {r["mid"]: i for i, r in enumerate(claims)}
ing_names, ing_class, ing_i = [], [], {}
rx = []
for r in read("claim_rx"):
    if r["mid"] not in mids:
        continue
    d = ing[r["gnl_cd"]]
    name = re.sub(r"\s*\(as [^)]*\)", "", d["gnl_nm"]).strip()
    key = (name, d["class_no"])
    if key not in ing_i:
        ing_i[key] = len(ing_names)
        ing_names.append(name)
        ing_class.append(d["class_no"])
    rx.append([mids[r["mid"]], ing_i[key], int(float(r["amt"] or 0))])

rows = []
for r in claims:
    p = patients[r["jid"]]
    yr = int(r["recu_fr_dd"][:4])
    mon = (yr - 2024) * 12 + int(r["recu_fr_dd"][5:7]) - 1
    g = [k for k, _ in GROUPS].index(r["main_sick"][:3])
    inst = insts[r["yid"]]
    rows.append([
        mon, g, sick_codes.index(r["main_sick"]), int(p["sex_tp_cd"]),
        age_band(yr - int(p["birth_yr"])), sido_idx[p["sido_cd"]], quint.index(p["prem_quintile"]),
        cl_codes.index(inst["cl_cd"]), reg_codes.index(inst["region_cd"]), int(r["insup_tp_cd"] == "5"),
        yid_i[r["yid"]], jid_i[r["jid"]],
        int(r["rvd_rpe_tamt_amt"]), int(r["rvd_insup_brdn_amt"]),
    ])

data = {
    "groups": [{"code": c, "name": n} for c, n in GROUPS],
    "sick": [{"code": c, "name": sick_nm.get(c, c)} for c in sick_codes],
    "ageBands": AGE_BANDS,
    "sido": [{"code": s["sido_cd"], "name": s["sido_nm"], "region": region_names[s["region_cd"]]} for s in sidos],
    "quint": quint,
    "cl": [{"code": c, "name": CL_NAMES[c]} for c in cl_codes],
    "regions": [region_names[c] for c in reg_codes],
    "yids": yids,
    "ing": [{"name": n, "cls": c, "clsName": CLASS_NAMES.get(c, c)} for n, c in zip(ing_names, ing_class)],
    "cols": "mon,grp,sick,sex,age,sido,quint,cl,reg,aid,inst,pt,amt,ins".split(","),
    "rows": rows,
    "rx": rx,
}

tpl = (ROOT / "template.html").read_text(encoding="utf-8")
out = tpl.replace("__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
(ROOT / "dist").mkdir(exist_ok=True)
(ROOT / "dist" / "dashboard.html").write_text(out, encoding="utf-8")
(ROOT / "dist" / "preview.html").write_text('<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">' + out, encoding="utf-8")
print(len(rows), "claims,", len(jids), "patients,", len(yids), "institutions,", len(rx), "rx lines,", len(ing_names), "ingredients,", len(out) // 1024, "KB")
print(data["ing"], quint)
