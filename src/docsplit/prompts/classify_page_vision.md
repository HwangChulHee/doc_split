<!--
[스텁] — 이번 범위에서는 사용하지 않는다 (핸드오프 §3: pkg02 이미지 페이지 적용 시 사용).
목적: 텍스트 0자(스캔) 페이지를 렌더링 이미지로 유형 판정한다 (DEFER_VLM 경로).
입력변수(예정):
  <<candidate_types>>  후보 유형명 목록
  (+ 이미지는 vision 입력으로 별도 첨부)
출력스키마(예정): {"type": str|null, "evidence": [str]}
근거문서: docs/classification/urla.md §3-3 (텍스트 없음 → DEFER_VLM)
-->

(미구현 — DEFER_VLM 페이지는 현재 미판정으로 기록된다)
