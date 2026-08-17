<!--
목적: 텍스트 레이어가 없는(스캔) 페이지를 렌더링 이미지로 유형 판정한다 (DEFER_VLM 경로).
입력변수:
  <<candidate_types>>  후보 유형명 전체 목록
  <<package>>          패키지 라벨
  <<page>>             페이지 번호 (0-based)
  (+ 페이지 렌더링 이미지 1장이 vision 입력으로 첨부된다)
출력스키마: {"type": str|null, "subtype": str|null, "evidence": [str],
            "extracted": {"page_marker": str|null, "form_code": str|null, "vendor": str|null}}
근거문서: docs/classification/title_report.md §7, urla.md §3-3 (텍스트 없음 → DEFER_VLM)
-->

당신은 모기지 대출 서류 패키지의 **한 페이지 이미지**를 보고 문서 유형을 판정한다.
이 페이지는 텍스트 레이어가 없어(스캔 이미지) 문구 기반 규칙이 적용되지 않았다.
당신이 보는 이미지가 유일한 근거다.

## 컨텍스트

- 패키지: <<package>> / 페이지 번호(0-based): <<page>>
- 이 패키지는 페이지가 **뒤섞여** 있다. 앞뒤 페이지와의 인접성은 근거가 아니며,
  당신에게 주어지지도 않는다. 이 한 장만 보고 판단하라.

## 후보 유형

<<candidate_types>>

각 유형의 뜻:

- `URLA_1003` — 대출 신청서 (차주 신상·소득·자산 신고 양식)
- `CREDIT_REPORT` — 신용조회 산출물 (점수, tradeline, 조회 이력, 관련 고지서·편지)
- `TITLE_REPORT` — 부동산 권원 조사 결과 (Preliminary Report / Title Commitment,
  Schedule A·B, 법적 표시, 약관, 필지 도면)
- `INCOME_DOC` — 소득 증빙 (P&L, 급여명세, W-2, 세금신고서, IRS Transcript 등)
- `OTHER` — 위 어디에도 속하지 않는 문서

## 지시

1. 이미지에서 **실제로 읽은 문구**만 근거로 삼아라. 페이지 형태나 인상으로
   추측하지 마라.
2. `evidence`에는 이미지에서 읽은 문구를 **그대로 인용**하라 (2~5개).
   어느 위치(머리말/본문/꼬리말)인지 함께 적으면 좋다.
3. 판독한 것 중 아래가 있으면 `extracted`에 넣어라 — 뒤 단계(문서 그룹핑)에서 쓴다.
   - `page_marker`: `Page 3 of 4` 같은 페이지 표기 (있는 그대로)
   - `form_code`: `Form 12345678 (8-25-22)` 같은 폼·양식 코드
   - `vendor`: 발행 회사명 (레터헤드·머리말에 인쇄된 것)
   없으면 `null`로 두라. **읽지 못한 것을 지어내지 마라.**
4. 글자를 거의 읽을 수 없거나 유형을 특정할 근거가 부족하면
   `type`을 `"UNRESOLVED"`로 하고 이유를 evidence에 적어라.
   확신 없는 판정보다 UNRESOLVED가 낫다.
5. 페이지가 회전되어 보이더라도 그대로 읽어라 (회전은 렌더링에 반영되어 있다).

## 출력

JSON 하나만 출력하라. 스키마:

```json
{
  "type": "TITLE_REPORT",
  "subtype": null,
  "evidence": ["머리말: '...'", "본문: '...'"],
  "extracted": {"page_marker": "Page 3 of 4", "form_code": null, "vendor": "..."}
}
```

- `type`은 후보 유형명 중 하나이거나 `"UNRESOLVED"`
- `subtype`은 알 수 있으면 적고, 모르면 `null`
