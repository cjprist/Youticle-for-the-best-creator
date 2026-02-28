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

## 협업 규칙

- 브랜치 예시
  - `feat/strategy-*`
  - `feat/generation-*`
  - `feat/frontend-*`
- 환경변수는 `.env` 로컬 사용, 공유는 `.env.example` 기준 유지
