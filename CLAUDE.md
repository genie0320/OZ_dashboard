# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

건강보험 청구(claim) 대시보드. 주상병이 I10(고혈압)·E11(2형 당뇨)·E78(이상지질혈증)인 청구만 대상으로 한다. 한국어 UI/데이터. git 저장소 아님, 테스트·린트 설정 없음.

## Commands

```bash
python build.py                                  # template.html + Supabase URL/anon key -> dist/dashboard.html, preview.html, 루트 index.html(GitHub Pages: main 브랜치 / , https://genie0320.github.io/OZ_dashboard/). 배포는 build 후 index.html 커밋·push
python tools/load_supabase.py                    # data/*.csv -> Supabase 적재 (재실행 가능, 전체 삭제 후 재적재)
npx supabase db push                             # supabase/migrations 적용 (link 완료, project ref: hdjfvciwzkbeynkdxiwh)
python -m http.server 8765 --directory dist      # 미리보기 (.claude/launch.json 의 "dashboard")
```

Docker 없음 → 로컬 Supabase 불가, 항상 클라우드 프로젝트 대상. `python-psycopg` 불필요(적재는 service_role 키로 REST 호출, 키는 CLI 에서 받아 메모리에서만 사용). build.py 는 env `SUPABASE_URL`/`SUPABASE_ANON_KEY` 가 없으면 CLI 에서 anon 키를 받는다.

## Architecture

Supabase(Postgres) 를 데이터 소스로 쓰는 단일 HTML 대시보드.

- `supabase/migrations/`: 스키마 + RLS(전 테이블 anon/authenticated SELECT 허용, 쓰기 정책 없음). 이관 테이블은 sido_code, sick_master, drug_ingredient, patient, institution, claim, claim_rx 뿐이며 claim 은 I10/E11/E78 주상병만 적재한다.
- `tools/load_supabase.py`: 적재 스크립트. 코드 컬럼은 전부 text(앞자리 0 보존), 빈 문자열은 NULL 로 들어간다.
- `template.html`: CSS + 바닐라 JS, 차트는 직접 그린 SVG. `loadData()` 가 `supabase-js`(CDN)로 7개 테이블을 1000행씩 페이지네이션해 읽고 **정수 인덱스로 압축한 `DATA`** 를 만든 뒤, 기존 렌더링 IIFE 에 넘긴다. 이후 필터링·집계는 모두 브라우저에서 한다(`pass()` → `render()`).
- `DATA.cols`(`mon,grp,sick,sex,age,sido,quint,cl,reg,aid,inst,pt,amt,ins`) 가 `rows` 컬럼 순서를 정의하고 템플릿은 이름→인덱스 맵 `C` 로 참조한다. `loadData()` 의 `rows` 생성 순서를 바꾸면 `cols` 와 템플릿을 같이 바꿔야 한다. `rx` 는 `[claim 행 인덱스, 성분 인덱스, 금액]`.
- `tools/build_static_legacy.py`, `tools/template_static_legacy.html`: 이전 CSV 내장 방식 원본(참고용). `loadData()` 출력이 이것의 DATA 와 12개 키 모두 동일함을 확인했다.

### 데이터 규칙 (loadData)

- 청구월 `mon` 은 2024-01 기준 0부터의 월 오프셋이다 (`recu_fr_dd` 기준).
- 연령대는 `recu_fr_dd` 연도 − `birth_yr` 로 계산해 6개 구간으로 나눈다.
- `ins` = `insup_tp_cd == "5"` 플래그(1/0).
- 성분명은 `(as ...)` 접미사를 제거하고 `(성분명, class_no)` 로 중복 제거한다. `drug_ingredient.csv` 에 `gnl_cd` 중복이 있어 첫 행만 사용한다.
- `CLASS_NAMES` 에 없는 약효분류는 코드 그대로 노출된다.
- CSV 코드 컬럼(`"01"`, `"031"` 등)은 앞자리 0 때문에 문자열로 다뤄야 한다.
- 사용되지 않는 CSV: `claim_sick`, `code_table`, `hospital_open`.

## 주의

- JS 객체는 `"11"` 같은 숫자형 문자열 키를 재정렬한다. 순서가 의미 있는 코드 맵(`CL_NAMES`)은 `Map` 을 쓴다.
- `prem_quintile` 은 빈 값이 존재한다(DB 에서는 NULL, DATA 에서는 `""`).
- anon key 는 공개용이라 dist 에 들어가도 되지만 service_role 키는 절대 넣지 않는다. 읽기가 anon 공개이므로 공개 범위를 좁힐 때는 RLS 정책을 `authenticated` 로 바꾸고 로그인 UI 를 추가해야 한다.
