-- 대시보드가 사용하는 테이블만 이관 (claim_sick, code_table, hospital_open 제외)
create table sido_code (
  sido_cd   text primary key,
  sido_nm   text not null,
  region_cd text not null,
  region_nm text not null
);

create table sick_master (
  sickcd text primary key,
  krnm   text,
  sicknm text
);

create table drug_ingredient (
  gnl_cd   text primary key,
  form_cd  text,
  form_nm  text,
  gnl_nm   text,
  class_no text,
  route    text,
  strength text,
  unit     text
);

create table patient (
  jid           text primary key,
  sex_tp_cd     text not null,
  birth_yr      integer not null,
  sido_cd       text references sido_code,
  qlf_tp_cd     text,
  prem_quintile text
);

create table institution (
  yid         text primary key,
  cl_cd       text not null,
  region_cd   text not null,
  shw_sbjt_cd text
);

create table claim (
  mid                text primary key,
  jid                text not null references patient,
  yid                text not null references institution,
  insup_tp_cd        text,
  fom_tp_cd          text,
  main_sick          text not null,
  sub_sick           text,
  dgsbjt_cd          text,
  recu_fr_dd         date not null,
  recu_to_dd         date,
  vst_ddcnt          integer,
  recu_ddcnt         integer,
  rvd_rpe_tamt_amt   bigint,
  rvd_slf_brdn_amt   bigint,
  rvd_insup_brdn_amt bigint,
  sopr_yn            text,
  dgrslt_tp_cd       text
);
create index claim_main_sick_idx on claim (main_sick);
create index claim_jid_idx on claim (jid);
create index claim_yid_idx on claim (yid);

create table claim_rx (
  mid                    text not null references claim on delete cascade,
  ln_no                  integer not null,
  gnl_cd                 text not null references drug_ingredient,
  fq1_mdct_qty           numeric,
  dy1_mdct_qty           numeric,
  tot_injc_ddcnt_exec_fq numeric,
  tot_use_qty_or_exec_fq numeric,
  unprc                  numeric,
  amt                    numeric,
  primary key (mid, ln_no)
);
create index claim_rx_gnl_idx on claim_rx (gnl_cd);

-- RLS: 읽기 전용 공개. 환자·청구 데이터이므로 공개 범위 확정 후 authenticated 로 좁힐 수 있다.
do $$
declare t text;
begin
  foreach t in array array['sido_code','sick_master','drug_ingredient','patient','institution','claim','claim_rx']
  loop
    execute format('alter table %I enable row level security', t);
    execute format('create policy "read all" on %I for select to anon, authenticated using (true)', t);
  end loop;
end $$;
