"""template.html -> dist/dashboard.html, preview.html, docs/index.html (GitHub Pages). 데이터는 브라우저가 Supabase 에서 직접 읽는다.

URL/anon key 는 env(SUPABASE_URL, SUPABASE_ANON_KEY)가 없으면 supabase CLI(link 완료 상태)에서 받는다.
CSV -> Supabase 적재는 tools/load_supabase.py. 구 정적 빌드는 tools/build_static_legacy.py.
"""
import json, os, pathlib, subprocess

ROOT = pathlib.Path(__file__).parent


def config():
    url, key = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_ANON_KEY")
    if url and key:
        return url, key
    ref = (ROOT / "supabase/.temp/project-ref").read_text().strip()
    keys = json.loads(subprocess.run(f"npx supabase projects api-keys --project-ref {ref} -o json",
                                     shell=True, capture_output=True, text=True, check=True).stdout)
    return f"https://{ref}.supabase.co", next(k["api_key"] for k in keys if k["name"] == "anon")


url, key = config()
out = (ROOT / "template.html").read_text(encoding="utf-8").replace("__SUPABASE_URL__", url).replace("__SUPABASE_ANON_KEY__", key)
(ROOT / "dist").mkdir(exist_ok=True)
(ROOT / "dist" / "dashboard.html").write_text(out, encoding="utf-8")
(ROOT / "docs").mkdir(exist_ok=True)
(ROOT / "docs" / "index.html").write_text(out, encoding="utf-8")  # GitHub Pages (main /docs)
(ROOT / "dist" / "preview.html").write_text(out, encoding="utf-8")
print("built dist/dashboard.html", len(out) // 1024, "KB ->", url)
