# Youticle-for-the-best-creator

`docker-compose` 기반 팀 협업 스켈레톤입니다.

## 서비스 구성

- `backend-strategy` (공동작업자, `8000`)
  - 전략 수립 백엔드
  - FastAPI
- `backend-generation` (내 담당, `8001`)
  - Vertex AI 기반 생성 백엔드
  - 텍스트/이미지/비디오/음성 API 뼈대
  - FastAPI + `google-genai`
- `frontend` (`3000`)
  - Next.js
  - 두 백엔드 헬스체크/엔드포인트 연결 기본 화면

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

## 실행 방법

1. 환경변수 파일 생성
```bash
cp .env.example .env
```

2. Vertex 인증 파일 준비
- 전략 백엔드: `./.secrets/strategy-sa.json`
- 생성 백엔드: `./.secrets/generation-sa.json`
- `.gitignore`에 제외됨
 - 현재 리포에 템플릿 JSON이 있으니, GCP에서 받은 실제 서비스계정 JSON 내용으로 전체 교체

3. `.env` 값 입력
- `STRATEGY_GCP_PROJECT_ID`, `STRATEGY_GCP_LOCATION`
- `GENERATION_GCP_PROJECT_ID`, `GENERATION_GCP_LOCATION`

4. 실행
```bash
docker compose up --build
```

## 주요 엔드포인트

### Strategy backend (`http://localhost:8000`)
- `GET /health`
- `POST /api/v1/strategy/plan`
- `POST /api/v1/strategy/next-video-script`

### Generation backend (`http://localhost:8001`)
- `GET /health`
- `POST /api/v1/generation/text`
- `POST /api/v1/generation/image`
- `POST /api/v1/generation/thumbnail/script`
- `POST /api/v1/generation/audio`
- `POST /api/v1/generation/video/jobs`
- `GET /api/v1/generation/video/jobs/{operation_name}`

### Frontend (`http://localhost:3000`)
- 대시보드 기본 페이지

## 협업 규칙 제안

- 공통 브랜치 전략:
  - `feat/strategy-*`
  - `feat/generation-*`
  - `feat/frontend-*`
- 환경변수는 `.env`만 로컬 사용, 공유는 `.env.example` 기준
- 서비스 간 내부 통신은 compose 서비스명 사용
  - 예: `http://backend-strategy:8000`

## 확장 (4번째 컨테이너)

`docker-compose.team.example.yml`에 워커 예시가 들어 있습니다.
필요 시 `docker-compose.yml`에 서비스 블록을 추가해서 확장하세요.
