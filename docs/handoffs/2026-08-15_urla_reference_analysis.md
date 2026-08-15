# Handoff — URLA 표준 양식 확보 + 대조 분석 (완료 보고)

> 이 문서는 완료된 세션의 결과를 다음 세션에 전달하는 핸드오프다.
> 이 세션의 범위는 "자료 확보 + 텍스트 대조 + 사실 보고"까지였다.
> **분류/그룹핑 로직은 여전히 미구현이고, 전략도 미결정 상태다** — 이 문서에도 전략 판단은 없다.

## 0. 전제 상태 (이 세션 이전)

- PDF 파싱 파이프라인 완료: `uv run python -m docsplit.parse --data-dir data --out-dir outputs`
  → 페이지별 JSONL(`outputs/parsed/`), 검수용 텍스트(`outputs/inspection/`), 통계(`outputs/stats.md`)
- 관찰 보고서 존재: `outputs/observation_report.md` (원문 발췌 포함이라 **미커밋**) —
  문서별 식별 신호, 헤더/푸터, grouping metadata, shuffled↔원본 매칭(39/39 완전 일치), pkg02 44페이지 훑기
- 도메인 지식 문서: `docs/domain_knowledge.md` (커밋됨)

## 1. 이 세션에서 한 것

1. GSE 공식 URLA blank 양식 확보 (Freddie Mac 자동 + Fannie Mae 수동)
2. 데이터셋 URLA 21페이지(pkg01 11p + pkg02 10p)와 표준 양식 텍스트 대조
   → 텍스트를 STANDARD / RENDERER / FILLED / UNCERTAIN으로 분류
3. Fannie ↔ Freddie 판 교차 대조 (파일·단어·텍스트레이어 수준)
4. `data/` 디렉토리 정리

## 2. 데이터 레이아웃 (현재)

```text
data/                      # reference/ 제외 전부 gitignore
├── packages/              # 셔플 패키지 2개 (01: 39p, 02: 44p) — 파일명 원본 유지
├── ground_truth/          # pkg01 정답 원본 4개 (URLA 11p / Credit 18p / Income 1p / Title 9p)
└── reference/urla/        # 공개 표준 양식 — 커밋 대상 (.gitignore: data/* + !data/reference/)
    ├── SOURCES.md         # 출처 URL·일자·원본 파일명 전부 기록
    ├── freddiemac/        # 7종 (curl로 확보)
    └── fanniemae/         # 동일 7종, 동일 파일명 (Cloudflare 차단 → 사용자 수동 다운로드)
```

- 7종 = URLA 5개 컴포넌트(본체 9p / Additional Borrower 4p / Unmarried Addendum 1p /
  Lender Loan Info 2p / Continuation Sheet 1p) + Instructions + SCIF Form 1103
- 버전: URLA 전부 `Effective 1/2021` (데이터셋과 동일 버전), SCIF `5/2022`
- `input delivery/`는 수령 원본 보존용으로 미변경. PDF 원본·파생물 커밋 금지 정책 유지

## 3. 산출물 위치

| 산출물 | 위치 | 커밋 |
|---|---|---|
| 분석 보고서 (사람용, 핵심) | `docs/analysis/urla_standard_analysis.md` | ✅ |
| 대조 raw 결과 (페이지별 분류, 미해소 라인, 미출현 표준 라인) | `outputs/urla_standard_diff/` | ❌ (원문 포함) |
| 대조 스크립트 (결정론적, 재실행 가능) | `scripts/observe_urla_diff.py` | ✅ |
| 공식 양식 + 출처 기록 | `data/reference/urla/` | ✅ |

대조 방법: 라인 정규화(NFKC, `•`→`·`, dash 통일, 공백 축약, 소문자) 후
정확 일치 → 전문 부분문자열(줄바꿈 재조합) → fuzzy(0.90) 순 매칭. 상세는 스크립트 참조.

## 4. 핵심 사실 (분류 근거로 쓸 수 있는 검증된 사실들)

### 4-1. STANDARD (양 GSE blank에서 확인된 문구 — 렌더러 불문 존재 기대)

- 푸터 세트 (데이터셋 URLA 21/21 페이지에 존재):
  - `Uniform Residential Loan Application` + 컴포넌트별 접미
    (`— Unmarried Addendum` / `— Continuation Sheet` / `— Lender Loan Information` / `— Additional Borrower`)
  - `Freddie Mac Form 65 • Fannie Mae Form 1003` (구분자 표기는 4-3 참조)
  - `Effective 1/2021`
  - `Borrower Name:` (본체 중간 페이지들)
- 상단 식별 블록: `To be completed by the Lender:` / `Lender Loan No./Universal Loan Identifier` / `Agency Case No.`
  (본체 1장, Unmarried Addendum, Lender Loan Info, **SCIF도 동일 블록**)
- 본문: `Section 1:`~`Section 9:` 제목+설명문, `L1.`~`L4.` 제목, 하위 항목 라벨, 법적 고지 단락

### 4-2. RENDERER (이 데이터셋 렌더링에서만 — blank 어디에도 없음)

- 인쇄 코드 4종: `GURLA20S`, `GURLA20_S`, `(POD)`, `0718` (전 21페이지 푸터)
- **페이지 번호 `N of 11`/`N of 10` 전체** — 공식 blank에는 페이지 번호가 아예 없음.
  분모는 패키지 구성(Continuation Sheet 유무)에 따라 변동
- 페이지 분할: 본체 blank 9p ↔ 데이터셋 7p (섹션↔페이지 대응이 렌더러 재량)
- California Civil Code 1812.30(j) 고지 (pkg01 Continuation Sheet) — GSE 표준 아닌 템플릿 삽입 문구
- 알려진 외부 사례: Calyx는 같은 자리에 `Calyx Form - URLA_1.frm (04/2020)` 형태

### 4-3. 렌더러 간 미세 표기 차이 (실증됨)

- 푸터 구분자: 양 GSE blank `Form 65  •  Form 1003` (U+2022, 공백2) ↔ 데이터셋 `Form 65 · Form 1003` (U+00B7, 공백1)
  → **바이트 단위 완전 일치 매칭은 발행처/렌더러 간에 깨진다**
- Section 6 철자: 양 GSE 본체 blank `Acknowledgments` ↔ 데이터셋 `Acknowledgements`
  (GSE 문서끼리도 갈림: Additional Borrower blank는 `Acknowledgements`)
- 같은 표준 문구의 줄바꿈/라인 구성이 발행처마다 다름:
  Freddie blank 기준 미해소였던 9개 라인(예: `Balloon / Balloon Term`, `Currently serving on active duty …` 융합 라인)이
  Fannie blank 텍스트 레이어에서는 데이터셋과 동일 라인으로 존재 → 표준 세트를 양쪽 합산해야 커버됨

### 4-4. Fannie ↔ Freddie 차이 (교차 검증 결과)

- **표준 문구 차이 0** (bag-of-words 검증). Additional Borrower·Unmarried·Continuation 3종은 배포 파일이 **바이트 동일**
- 차이는 전부 텍스트 레이어 아티팩트: Fannie 본체의 `SIGN` 토큰 3개, Freddie Lender의 `0.00` 노출,
  Freddie SCIF의 `pr ovided`(단어 분절)
- Instructions만 Fannie 소장본이 Revised 11/2024로 더 최신 (양식 자체는 Effective 1/2021 유지)

### 4-5. 대조 수치

- 데이터셋 URLA 21페이지: 페이지당 STANDARD(+~) 비율 약 70–95%
- 미해소 라인 111건 (거의 전부 입력값·라벨+값 융합·페이지번호·CA 고지) → `outputs/urla_standard_diff/unmatched_distinct.txt`
- blank에만 있고 데이터셋에 없는 표준 라인 51건 (Additional Borrower 미사용분 + 선택지 안내 목록 생략
  — 예: Section 1e의 income source 열거 16종을 이 렌더러는 렌더링하지 않음) → `standard_lines_not_seen.txt`
- SCIF 텍스트는 데이터셋 6개 PDF 어디에도 없음 (향후 등장 대비 식별 문구는 분석 보고서 §9)

## 5. 다음 세션 참고사항

- 분류/그룹핑/순서복원 로직: **한 줄도 구현되지 않음** (일관되게 범위 밖이었음)
- 전략 논의·제안도 의도적으로 전부 배제되어 있음 — 위 사실들에서 전략을 도출하는 것은 다음 단계의 몫
- 재현: 대조 재실행은 `uv run python scripts/observe_urla_diff.py`, 파싱 재실행은
  `uv run python -m docsplit.parse --data-dir data --out-dir outputs` (reference/는 자동 제외)
- 상세 근거가 필요하면: `docs/analysis/urla_standard_analysis.md` (§1~§10) → `outputs/urla_standard_diff/` (raw) 순으로 볼 것
