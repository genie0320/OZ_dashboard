"""data/*.csv -> Supabase(Postgres) 적재. 대시보드 대상(I10/E11/E78 주상병) 청구만 올린다.

사용: python tools/load_supabase.py   (supabase link + login 완료 상태)
service_role 키는 CLI 에서 받아 메모리에서만 사용한다. 재실행 가능(FK 역순 삭제 후 재적재).
"""
import csv, json, pathlib, subprocess, urllib.request

D = pathlib.Path(__file__).resolve().parent.parent / "data"
PREFIXES = ("I10", "E11", "E78")


def read(name):
    with open(D / f"{name}.csv", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def nul(v):
    return v if v != "" else None


claims = [r for r in read("claim") if r["main_sick"][:3] in PREFIXES]
mids = {r["mid"] for r in claims}
jids = {r["jid"] for r in claims}
yids = {r["yid"] for r in claims}
rx = [r for r in read("claim_rx") if r["mid"] in mids]
gnl = {r["gnl_cd"] for r in rx}

def first_unique(rows, key):
    seen, out = set(), []
    for r in rows:
        if r[key] not in seen:
            seen.add(r[key]); out.append(r)
    return out

TABLES = [
    ("sido_code", read("sido_code")),
    ("sick_master", first_unique(read("sick_master"), "sickcd")),
    ("drug_ingredient", [r for r in first_unique(read("drug_ingredient"), "gnl_cd") if r["gnl_cd"] in gnl]),
    ("patient", [r for r in read("patient") if r["jid"] in jids]),
    ("institution", [r for r in read("institution") if r["yid"] in yids]),
    ("claim", claims),
    ("claim_rx", rx),
]


REF = pathlib.Path(__file__).resolve().parent.parent.joinpath("supabase/.temp/project-ref").read_text().strip()
keys = json.loads(subprocess.run("npx supabase projects api-keys --project-ref %s -o json" % REF,
                                 shell=True, capture_output=True, text=True, check=True).stdout)
KEY = next(k["api_key"] for k in keys if k["name"] == "service_role")
BASE = f"https://{REF}.supabase.co/rest/v1"


def call(method, path, body=None):
    req = urllib.request.Request(BASE + path, method=method, data=body and json.dumps(body).encode(),
                                 headers={"apikey": KEY, "Authorization": "Bearer " + KEY,
                                          "Content-Type": "application/json", "Prefer": "return=minimal"})
    urllib.request.urlopen(req).read()


PK = {"sido_code": "sido_cd", "sick_master": "sickcd", "drug_ingredient": "gnl_cd", "patient": "jid",
      "institution": "yid", "claim": "mid", "claim_rx": "mid"}
COLS = {"sick_master": ["sickcd", "krnm", "sicknm"]}

for table, _ in reversed(TABLES):
    call("DELETE", f"/{table}?{PK[table]}=not.is.null")
for table, rows in TABLES:
    for i in range(0, len(rows), 1000):
        chunk = [{c: nul(r[c]) for c in COLS.get(table, r.keys())} for r in rows[i:i + 1000]]
        call("POST", f"/{table}", chunk)
    print(table, len(rows))
