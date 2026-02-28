from __future__ import annotations

from app.schemas import AssetJobCreateRequest
from app.services.scene_planner import PlannedScene, ScenePlanResult

PROMPT_VERSION = "storyboard_dynamic_scene_v1_ko_realistic_v2"
FRAME_COUNT = 5


def build_style_bible_block() -> str:
    return (
        "[시리즈 스타일 바이블]\n"
        "5장 이미지가 동일한 아트 디렉션을 유지한다.\n"
        "실사 기반 시네마틱 스타일, 인물 피부/의복/배경 질감이 사진처럼 자연스럽게 보이도록 구성.\n"
        "배경 그래픽도 평면 일러스트가 아니라 실사형 3D 오브젝트/실제 공간 조명처럼 표현.\n"
        "현대 뉴스룸/다큐 톤, 차분하지만 진지하고 긴장감 있는 분위기.\n"
        "16:9 (640x360), 우측 메인 주체 + 좌측 보조 상징 구성 고정.\n"
        "딥 네이비 + 쿨 그레이 + 뮤트 틸 + 소량의 웜 앰버.\n"
        "은은한 림라이트, 부드러운 그림자, 또렷한 엣지.\n"
        "금지: 국기/국장/군표식/실제지도/랜드마크/로고/워터마크."
    )


def _character_block(character_bible: dict[str, object]) -> str:
    identity = str(character_bible.get("identity", "동일 인물 1인 진행자"))
    age_range = str(character_bible.get("age_range", "20대 후반~30대"))
    face_shape = str(character_bible.get("face_shape", "중간형 얼굴"))
    hair_style = str(character_bible.get("hair_style", "짧고 단정한 헤어"))
    outfit = str(character_bible.get("outfit", "단색 재킷 + 무지 상의"))
    expression_range = str(character_bible.get("expression_range", "침착-긴장"))
    outfit_colors = ", ".join([str(x) for x in character_bible.get("outfit_colors", [])]) or "네이비, 그레이"
    forbidden_changes = ", ".join(
        [str(x) for x in character_bible.get("forbidden_changes", [])]
    ) or "헤어/의상/얼굴형/연령대 변경 금지"
    reference_creator_style = str(
        character_bible.get(
            "reference_creator_style",
            "대본 주제와 관련된 유튜버의 분위기/인상/실루엣을 참고하되 동일 복제는 피함",
        )
    )
    return (
        "[캐릭터 바이블]\n"
        f"정체성: {identity}\n"
        f"연령대: {age_range}\n"
        f"얼굴형: {face_shape}\n"
        f"헤어: {hair_style}\n"
        f"의상: {outfit}\n"
        f"의상색: {outfit_colors}\n"
        f"표정범위: {expression_range}\n"
        f"참조 유튜버 스타일: {reference_creator_style}\n"
        f"변경금지: {forbidden_changes}\n"
        "규칙: 모든 프레임에서 동일 인물 외형을 절대 변경하지 않는다.\n"
        "규칙: 관련 유튜버와 유사한 분위기/체형/스타일을 유지하되 초상은 과도하게 복제하지 않는다."
    )


def build_character_anchor_prompt(scene_plan: ScenePlanResult) -> str:
    return (
        "캐릭터 앵커 이미지 생성.\n"
        "목표: 이후 모든 프레임에서 참조할 기준 인물 1명을 정면 기준으로 선명하게 생성.\n"
        f"{_character_block(scene_plan.character_bible)}\n"
        "구도: 인물은 우측 중앙, 좌측에는 텍스트 없는 추상 상징 2개.\n"
        "카메라: 미디엄 클로즈업, 아이레벨.\n"
        "텍스트규칙: 필요한 경우에만 1~3단어의 짧은 한국어 라벨을 아주 작게 허용.\n"
        "텍스트규칙: 긴 문장/영문 문장/큰 타이포 렌더링 금지.\n"
        f"{build_style_bible_block()}"
    )


def build_grounded_scene_prompt(
    scene: PlannedScene,
    scene_plan: ScenePlanResult,
) -> str:
    left_props = ", ".join(scene.left_props[:3])
    consistency_rules = ", ".join(scene_plan.consistency_rules)
    return (
        f"장면번호: {scene.scene_no}\n"
        f"소스구간: {scene.source_span}\n"
        f"장면목표: {scene.intent}\n"
        f"주체: {scene.subject}\n"
        f"핵심행동: {scene.action}\n"
        f"배경맥락: {scene.location_context}\n"
        f"좌측소품: {left_props}\n"
        f"카메라지시: 샷={scene.camera_shot}, 앵글={scene.camera_angle}\n"
        f"전중후경: {scene.foreground_midground_background}\n"
        f"{_character_block(scene_plan.character_bible)}\n"
        f"[일관성 규칙] {consistency_rules}\n"
        "프레임 생성 규칙: 설명문이 아니라 실제 상황을 한 컷으로 재연한다.\n"
        "텍스트규칙: 설명을 위해 아주 짧은 한국어 텍스트(최대 1~3단어, 한 장면 최대 12자 내)를 소량 허용.\n"
        "텍스트규칙: 영문 문장/긴 문장/큰 자막/과도한 타이포는 금지.\n"
        "금지규칙: 국기/국장/군표식/실지도/랜드마크/브랜드 로고/워터마크 금지.\n"
        "이탈금지: 장면목표 외 사건/인물/사물 추가 금지.\n"
        f"{build_style_bible_block()}"
    )


def build_retry_prompt(base_prompt: str, retry_idx: int) -> str:
    if retry_idx == 0:
        return base_prompt
    if retry_idx == 1:
        return (
            f"{base_prompt}\n"
            "재시도규칙1: 장면 핵심행동과 인물 유사도를 더 명확히, 텍스트는 1~3단어 한국어 라벨만 최소 허용."
        )
    return (
        f"{base_prompt}\n"
        "재시도규칙2: 소품 수를 2개 이하로 축소하고 카메라를 단순화해 이탈을 줄인다."
    )


def build_storyboard_prompts(scene_plan: ScenePlanResult) -> tuple[list[str], list[str]]:
    prompts: list[str] = []
    sources: list[str] = []
    for scene in scene_plan.scenes[:FRAME_COUNT]:
        prompts.append(build_grounded_scene_prompt(scene, scene_plan))
        sources.append(scene.source_span)
    return prompts, sources


def build_thumbnail_prompt(payload: AssetJobCreateRequest, scene_plan: ScenePlanResult) -> str:
    plan = scene_plan.thumbnail_plan
    left_props = ", ".join([str(x) for x in plan.get("left_props", [])][:3])
    title = payload.script.title
    return (
        "썸네일 생성 지시\n"
        f"주제: {title}\n"
        f"장면목표: {plan.get('intent', payload.rationale_block.logic.conclusion)}\n"
        f"주체: {plan.get('subject', '진행자 1인')}\n"
        f"핵심행동: {plan.get('action', '결정 직전의 강한 포즈')}\n"
        f"긴장포인트: {plan.get('tension_point', '충돌 직전 분위기')}\n"
        f"좌측소품: {left_props}\n"
        f"카메라: 샷={plan.get('camera_shot', '클로즈업')}, 앵글={plan.get('camera_angle', '아이레벨')}\n"
        f"{_character_block(scene_plan.character_bible)}\n"
        "목표: CTR 중심의 고대비/강한 시선 유도/긴장감.\n"
        "텍스트규칙: 설명용 짧은 한국어 텍스트 1줄(최대 3단어, 최대 12자)만 허용.\n"
        "텍스트규칙: 영문/긴 문장/과도한 텍스트 노출 금지.\n"
        "금지규칙: 로고/워터마크/국기/국장/군표식/실지도/랜드마크 금지.\n"
        f"{build_style_bible_block()}"
    )


def build_tts_script_ko(payload: AssetJobCreateRequest, max_chars: int = 800) -> str:
    body = [item.line for item in payload.script.body_15_150s[:2]]
    text = " ".join([payload.script.hook_0_15s] + body + [payload.script.closing_150_180s])
    return text.strip()[:max_chars]


def build_storyboard_summary_for_veo(payload: AssetJobCreateRequest, scene_plan: ScenePlanResult) -> str:
    scene_intents = " / ".join([scene.intent for scene in scene_plan.scenes[:FRAME_COUNT]])
    return (
        f"한국어 다큐/뉴스룸 스타일 5초 영상. 주제: {payload.script.title}. "
        f"핵심 흐름: {scene_intents}. "
        "동일 인물 유지, 텍스트 오버레이 없음, 하이 콘트라스트, 차분하지만 긴장감 있는 톤."
    )


def build_production_notes_ko() -> str:
    return (
        "제작 체크리스트\n"
        "1) 5개 장면이 source_span 순서를 따르는지 확인\n"
        "2) 캐릭터 외형(헤어/의상/얼굴형)이 프레임 간 동일한지 확인\n"
        "3) 텍스트/로고/국기/지도/랜드마크 금지 준수 확인\n"
        "4) 썸네일 CTR 톤(긴장감/명암대비/시선유도) 확인\n"
    )


def serialize_scene_plan(scene_plan: ScenePlanResult) -> list[dict[str, str | list[str]]]:
    return [
        {
            "scene_no": str(scene.scene_no),
            "source_span": scene.source_span,
            "intent": scene.intent,
            "action": scene.action,
            "camera_shot": scene.camera_shot,
            "left_props": scene.left_props,
        }
        for scene in scene_plan.scenes[:FRAME_COUNT]
    ]
