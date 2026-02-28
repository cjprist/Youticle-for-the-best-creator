# Youticle for the best creator

Youticle은 유튜브 댓글 데이터를 바탕으로, 다음 영상의 주제와 대본, 썸네일/프레임까지 빠르게 도출하는 크리에이터 지원 도구입니다.

## 프로덕트 배경

- 많은 크리에이터가 "무엇을 만들어야 조회수가 나오는지"를 감(직관)에 의존합니다.
- 댓글에는 시청자 수요가 분명히 있는데, 이를 체계적으로 읽고 다음 콘텐츠로 연결하는 과정이 어렵고 시간이 오래 걸립니다.
- 특히 영상 주제 선정과 대본 작성, 썸네일 방향 정리는 반복적이지만 비용이 큰 작업입니다.

## 해결하려는 문제

- 댓글 데이터가 쌓여도 인사이트가 구조화되지 않아 실행 가능한 전략으로 이어지지 않는 문제
- "근거 없는 다음 영상 기획"으로 인한 실패 리스크
- 분석/기획/제작 초기 단계(대본, 썸네일 컨셉)까지 이어지는 워크플로우 단절

## 제품 목적

- 채널 핸들 입력만으로 최신 영상/댓글을 수집하고, 다음 영상 기획까지 연결합니다.
- 인사이트를 `근거(댓글) -> 해석(인과) -> 결론(다음 영상 전략)` 구조로 제시합니다.
- 선택한 signal을 기반으로 대본과 스토리보드(썸네일/프레임)를 자동 생성해 제작 리드타임을 단축합니다.

## 사용자 흐름

1. 채널 핸들(또는 URL) 입력
2. 최근 영상 댓글 수집
3. Signal 분석 생성
4. Signal 선택 후 스크립트 생성
5. Storyboard job으로 썸네일/프레임 생성

## 시스템 구성

- `backend-strategy` (`8000`)
  - 댓글 수집, signal 분석, 스크립트 생성
  - FastAPI
- `backend-generation` (`8001`)
  - storyboard 파이프라인(썸네일/프레임/프리뷰 영상 등)
  - FastAPI
- `frontend` (`3000`)
  - Next.js 기반 UI
  - 채널 입력 -> 분석 -> 대본 -> 생성 결과 확인

## 디렉터리

```text
.
├─ backend-strategy/
├─ backend-generation/
├─ frontend/
├─ docker-compose.yml
├─ docker-compose.team.example.yml
└─ .env.example
```

## 빠른 실행

1. 환경변수 파일 생성
```bash
cp .env.example .env
```

2. 인증 파일 준비
- `./.secrets/strategy-sa.json`
- `./.secrets/generation-sa.json`

3. 실행
```bash
docker compose up --build
```

4. 접속
- Frontend: `http://localhost:3000`
- Strategy API: `http://localhost:8000`
- Generation API: `http://localhost:8001`

## 주요 API

### Strategy (`8000`)
- `POST /api/v1/strategy/youtube/comments`
- `POST /api/v1/strategy/signals/from-comments`
- `POST /api/v1/strategy/scripts/from-signal`

### Generation (`8001`)
- `POST /api/assets/jobs/storyboard`
- `POST /api/assets/jobs/storyboard-to-video`
- `GET /api/assets/jobs/{job_id}`
- `GET /api/assets/jobs/{job_id}/result`

## AI API 사용 현황

- 상세 문서: [AI_API_USAGE.md](./AI_API_USAGE.md)
- 포함 내용:
  - backend-strategy/backend-generation에서 사용하는 AI API 및 모델
  - 인증/환경변수 기준
  - 프론트엔드 API 호출 경로

## 협업 규칙

- 브랜치 예시
  - `feat/strategy-*`
  - `feat/generation-*`
  - `feat/frontend-*`
- 환경변수는 `.env` 로컬 사용, 공유는 `.env.example` 기준 유지

## 비즈니스 모델 (초안)

### 고객 세그먼트

- 1인/소규모 유튜브 크리에이터 (핵심)
- 크리에이터 팀/스튜디오
- 다채널 운영 에이전시 및 브랜드 콘텐츠팀

### 핵심 가치 제안

- 댓글 기반 인사이트로 다음 영상 전략을 빠르게 도출
- 채널 소유자 관점 대본 생성으로 실행 가능성 강화
- 채널 지식 검색(영상 내용 재활용)으로 기획 비용 절감
- 기획 리드타임 단축 + 성과 개선(조회수/CTR/유지율)

### 수익 모델

1. 구독형 SaaS
- Free: 체험용 제한 기능
- Pro: 개인 크리에이터용 핵심 기능
- Team: 협업/권한/히스토리
- Agency: 다채널 운영 최적화

2. 사용량 기반 과금(Overage)
- 스크립트/인사이트/검색 요청량 초과 시 종량 과금
- 고비용 생성(이미지/영상)은 크레딧 차감

3. 부가 매출
- 월간 전략 리포트(리뷰형 서비스)
- 템플릿/프레임워크 패키지
- API/화이트라벨(B2B)

### 플랜/가격 프레임 (가설)

- Free: 0원
- Pro: 월 29~59 USD
- Team: 월 99~299 USD
- Agency: 월 499 USD+ (채널 수/사용량 기반 커스텀)

### 핵심 KPI

- 무료 -> 유료 전환율
- 월간 활성 채널 수
- 채널당 생성 작업 수(인사이트/대본/생성 파이프라인)
- 추천 주제 채택률
- 3개월 리텐션
- ARPU(고객당 평균 매출)

### 초기 Go-To-Market

- 크리에이터 커뮤니티 베타 운영
- "내 채널 무료 진단" 리드 획득
- 성공 사례(시간 절감/성과 개선) 공개
- 보이스 학습/채널 지식 검색 기능을 유료 전환 포인트로 설계

## 향후 계획 (Roadmap)

### Phase 1: 댓글 인사이트 고도화 (단기)

- 댓글 신호 품질 향상(근거 -> 해석 -> 결론 일관성 강화)
- 채널 소유자 관점 문체 고정(전략/대본 전 구간)
- 인사이트 결과의 재현성과 평가 지표 정립

### Phase 2: 채널 콘텐츠 학습 레이어 (핵심)

- 채널 영상 자막/설명/메타데이터 수집 파이프라인 구축
- 채널 고유 말투/구조/CTA를 반영한 `voice profile` 생성
- 기존 영상 지식 기반 semantic search(영상 + 타임스탬프) 제공

### Phase 3: 대본 생성 강화

- 입력: 댓글 인사이트 + 채널 지식 + voice profile
- 출력: 동일 스키마 유지, 채널 뉘앙스 일치도 향상
- 과거 영상 중복 주제 회피 및 시리즈형 후속 콘텐츠 추천

### Phase 4: 전략-제작 연결 자동화

- 다음 영상 전략 -> 대본 -> 스토리보드(썸네일/프레임) 원클릭 연결
- 실행 우선순위(예상 성과/제작 난이도/준비 시간) 자동 제시
- 주간 전략 리포트와 댓글 운영 보조(중요 댓글 추천/답변 초안) 제공
