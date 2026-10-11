# Demo page 작업 handoff

작성: 2026-10-11 KST. 다음 세션은 이 문서를 현재 상태의 기준으로 읽는다.
`TEMPO_DEMO.md`와 원래 영상 handoff에는 과거 구현 설명이 섞여 있다. 아래 최신 사용자 지시가 우선한다.

## 1. 작업 위치와 Git 계약

| 항목 | 값 |
|---|---|
| 작업 폴더 | `/home/always216/ROBOT/anony_repo_tempo_demo` (`/data_fast/home/always216/ROBOT/anony_repo_tempo_demo`와 같은 위치) |
| 원격 | `https://github.com/badeok0716/anony_repo.git` |
| 개인 작업 브랜치 | `hansang/tempo-split-gauge-20261009` |
| 이 문서 작성 직전 구현 commit | `1d754b8966a4ece234db713927e9506428e12d02` |
| 기반 브랜치 | `project-page` |
| 페이지 진입점 | `index.html#inference-time` |

사용자 확정: 앞으로도 개인 브랜치에서 구현·commit·push한다. 중간마다 컨펌을 요구하지 않는다. 최종 컨펌은 마지막에 한 번 받는다. `main` 또는 `project-page`에 직접 push/merge하지 않는다. 최종 merge와 게시 여부는 badeok이 결정한다.

10/11 문서 작업 시작 시 `git status --short`는 빈 출력이었다. 후속 작업 전 다시 확인하고 다른 작업자의 변경을 보존한다.

저장소는 **non-cone sparse checkout**이다. 원래 `static/videos/`, `static/figures/`는 Git에 있지만 현재 checkout에 없다. 로컬 미리보기에서 기존 본문 영상/이미지가 404여도 원격 파일이 삭제된 것은 아니다. 빠진 파일을 임의로 삭제하거나 페이지 링크를 고치지 않는다.

## 2. 사용자가 확정한 화면 방향

- 메인 페이지의 밝은 테마 안에 inference-time 섹션을 둔다. 별도 interactive 페이지를 만들지 않는다. `tempo.html`은 해당 섹션으로 redirect한다.
- 원래 메인 데모 영상과 본문을 유지한다.
- split 비교를 선호한다.
- q50–q90 / q50–q95 / q50–q99를 세 개의 고정 3D 패널로 동시에 보여준다. quantile 선택 버튼과 XY/XZ/YZ 선택은 제거했다.
- 실행 버튼 한 번으로 영상과 3D 점이 동시에 움직이며 **Cup 완료까지** 보여야 한다. 1초~1.2초짜리 시연으로 되돌리지 않는다.
- **v18 B 방식:** 각 runner의 현재 pick/place 구간만 표시한다. 이전 경로를 계속 쌓거나 전체 궤적을 계속 남기지 않는다.
- tempo 그래프, 바늘 속도계, 배속 통계는 제거했다. 사용자가 다시 요청하기 전 복원하지 않는다.
- **잔상은 웹페이지에 넣지 않는다.** 별도 영상으로 만들어 scp 다운로드 후 검토한다.
- 잔상 비교는 기존 split4 panel을 사용하고 **q50 포함 네 패널 모두** 같은 효과를 적용한다. 잔상 수와 진하기를 낮추는 방향이다.
- F1 녹음은 제거했다. 소리는 저음 중심으로 가속할 때 “웅—” 하는 느낌을 원한다. 단순한 고음/얇은 음색과 잡음을 싫어한다. 기존 음색이 청감으로 승인됐다는 근거는 없다.

## 3. 현재 페이지 구현

상단 inference-time 영상: Cup/Towel/Trash task 버튼, v18 split MP4, replay/download, 시계, 선택적으로 켜는 음향과 volume. 영상 자체 playbackRate는 1이다. tempo telemetry는 음향을 구동하는 데 남아 있다.

하단: Cup 전용 q50–q90 / q50–q95 / q50–q99 세 패널. `Run full Cup` 버튼으로 공통 wall clock을 시작한다. 각 패널에서 파란 q50 runner와 해당 quantile runner가 현재 B 구간만 표시한다. 완료한 runner는 끝에 머물며 q50 완료까지 비교가 이어진다.

### 파일 역할

| 파일 | 역할 |
|---|---|
| `index.html` | 기존 메인 페이지 + `#inference-time` 섹션 |
| `static/css/tempo.css` | 밝은 테마, split 및 세 3D 패널 layout |
| `static/js/tempo.js` | task 영상, 음향, 공통 시계, 현재 B 구간 SVG, 동기화 프레임 |
| `static/data/tempo.json` | Cup/Towel/Trash 원본 applied-tempo telemetry 및 소스 정보 |
| `static/data/segment.json` | Cup 전체 measured FK, clip time, 네 clocks, B 구간 boundaries |
| `static/tempo/chunk_atlas.jpg` | Cup 원본 프레임 JPEG atlas; canvas가 시계에 맞는 프레임을 선택 |
| `static/tempo/{cup,towel,trash}_split.mp4` | 기존 v18 split panel 원본 복사본 |
| `tools/export_synced_segment.py` | 로그와 원본 영상에서 전체 Cup 데이터/atlas 생성 |
| `tools/export_tempo_demo.py` | 상단 telemetry export |
| `tools/render_split4_trails.py` | 최신 4-panel 잔상 영상 생성 |
| `tools/serve_demo.py` | localhost HTTP Range 지원 미리보기 서버 |

`tools/export_chunk_demo.py`, `static/data/chunk.json`, `tools/render_gripper_pilot.py`, `static/tempo/cup_trail_pilot.mp4`는 이전 시도에서 남은 파일이다. 현재 화면의 기준으로 사용하지 않는다. `gaugeAngle` 함수나 예전 CSS selector도 일부 남아 있으나 실제 UI는 제거됐다.

## 4. 시계·경로 의미와 구현 차이

원본 영상/로그 handoff: `/home/always216/ROBOT/analysis/tempo_viz_20261004/HANDOFF.md`.
원본 계산/렌더 코드: 같은 디렉터리의 `v01_tempo_clock.py`, `v04_fk.py`, `v19_segments.py`, `v20_split4.py`, `v25_completion.py`.

현재 웹 export는 저장된 q99 Cup 실행의 **measured joint FK 궤적과 촬영 프레임**을 네 시계로 재생한다. q50은 nominal 15 Hz 시계의 이름이며 별도로 저장된 네 번째 모델 출력이 아니다. q90/q95/q99는 저장된 세 log-tempo 채널을 사용한다. q99의 controller 제한이 작동한 곳은 다른 채널에도 해당 기록의 상한을 적용한다. controller를 새로 풀거나 네 번 실제 실행한 결과는 아니다.

소스 rollout stem:
`/storage/always216/ROBOT/tempo_viz_20261004/pc2_logs/20260929/cup_ours_tempo2_demo/v3_20260929_041209`

카메라 JSON:
`/storage/always216/ROBOT/tempo_viz_20261004/cup_041209_camera.json`

현재 웹 시계는 **visible clip 시작 기준**이며 policy 시작 기준 v18 숫자와 다르다.

| clock | 웹 완료 시각 (s) |
|---|---:|
| q50 | 4.220410 |
| q90 | 3.432419 |
| q95 | 3.233075 |
| q99 | 2.897885 |

Cup은 `v25_completion.completion(..., 'cup')`의 두 번째 release 완료까지 export한다. 영상 lag는 0.264362855 s. 원래 v18 policy 시작 기준 q99 완료는 약 3.162 s다. 둘을 혼합해 수치 오류라고 판단하지 않는다.

B 구간은 `v05_zilean2.gripper_events`와 `v19_segments.segments(..., 'B')`를 그대로 사용한다. clip 기준 boundaries는 `[0, 0.488203, 1.414732, 1.943481, 2.763466, 2.897885]`이고 reach/pick1 → carry/place1 → reach/pick2 → carry/place2 → retreat이다. 각 runner가 도달한 source timestamp로 구간을 선택하고 이전 구간을 지운다.

**다음 구현자가 알아야 하는 차이:** 현재 화면의 “chunk”는 실제 한 VLA call의 15-waypoint 예측 chunk가 아니라 measured path의 현재 B 구간이다. 원래 v20 렌더는 현재 B 구간 외에 해당 `plan_id`의 예측 action waypoint도 표시한다. 현재 웹에서는 이 예측 waypoint overlay까지 복제하지 않았다. v18 카메라 `View3D.from_camera` 대신 고정 isometric 투영을 사용한다. 따라서 “원래 v18 렌더를 완전히 그대로 이식했다”라고 설명하면 안 된다. 사용자가 다음 검토에서 원본과 동일한 그림을 요구하면 이 두 차이부터 맞춘다.

atlas 프레임은 30 Hz, geometry는 약 120 Hz다. 영상과 점은 같은 source timestamp를 사용하며, HTML video seek를 반복하는 대신 atlas에서 프레임을 골라 동기화한다.

## 5. 최신 잔상 영상

사용자가 내려받아 검토할 파일:
`/home/always216/ROBOT/analysis/tempo_viz_20261004/cup_split4_trail_light_v5.mp4`

- 원본: `/storage/always216/ROBOT/tempo_viz_20261004/cup_041209_zilean_v18B_split4_panel.mp4`
- 완료 job: `143817`, 로그 `/home/always216/ROBOT/analysis/tempo_viz_20261004/split4_143817.log`
- 1232×482, 30 fps, 184 frames, 약 6.13 s, 약 1.4 MB.
- q50/q90/q95/q99 모든 lane에 같은 설정: 0.10/0.20 s 지연 두 잔상, alpha 0.30/0.18.
- 빨간 손가락의 가장 큰 연결 영역을 찾고 주변 red/dark pixel에 옅은 청록 tint를 입힌다. 현재 빨간 손가락은 원본으로 유지한다.
- 일반 object tracker는 아니다. 색/가림/영상 가장자리 때문에 효과가 일부 프레임에서 빠질 수 있다.
- 원래 영상에 구워진 숫자와 label은 그대로 남아 있다. 웹 그래프·속도계 제거와 별개다.
- 사용자 최종 청감/영상 컨펌은 아직 받지 않았다.

사용자 PC에서 다운로드:

```bash
scp always216@gateway:/home/always216/ROBOT/analysis/tempo_viz_20261004/cup_split4_trail_light_v5.mp4 ~/Downloads/
```

`cup_gripper_trail_v4.mp4`는 이전 2-panel/3잔상 결과라 최신 비교본으로 보내지 않는다.

## 6. 로컬 미리보기와 재생성

```bash
cd /home/always216/ROBOT/anony_repo_tempo_demo
git status --short
git branch --show-current
python3 tools/serve_demo.py --port 8732
```

열기: `http://127.0.0.1:8732/index.html#inference-time`. 원격 gateway라면 로컬 PC에서 SSH port forwarding한다. 기존 서버가 남아 있을 수 있으니 점유 포트를 확인하고 새로운 포트를 고르거나 본인의 정확한 process만 종료한다.

push된 구현 미리보기:
`https://raw.githack.com/badeok0716/anony_repo/1d754b8966a4ece234db713927e9506428e12d02/index.html#inference-time`

raw.githack은 서버에서 Cloudflare 403이 났던 이력이 있다. 로컬 HTTP 미리보기와 별개이며 링크가 사용자 브라우저에서도 항상 열리는지는 보장하지 않는다.

재생성은 compute node의 CPU Slurm job에서 한다. Python 환경:

```bash
export PYTHONPATH=/storage/always216/ROBOT/tempo_viz_20261004/pylib
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=2
cd /home/always216/ROBOT/anony_repo_tempo_demo
/home/always216/miniconda3/bin/python tools/export_synced_segment.py \
  --analysis-dir /home/always216/ROBOT/analysis/tempo_viz_20261004 \
  --stem /storage/always216/ROBOT/tempo_viz_20261004/pc2_logs/20260929/cup_ours_tempo2_demo/v3_20260929_041209 \
  --video static/tempo/cup_context.mp4 \
  --camera /storage/always216/ROBOT/tempo_viz_20261004/cup_041209_camera.json
/home/always216/miniconda3/bin/python tools/render_split4_trails.py \
  /storage/always216/ROBOT/tempo_viz_20261004/cup_041209_zilean_v18B_split4_panel.mp4 \
  /home/always216/ROBOT/analysis/tempo_viz_20261004/cup_split4_trail_light_v5.mp4
```

위 명령은 Slurm wrap 안에서 실행한다. CPU 2개, RAM 4G, 5분 제한으로 충분했다. `rtx3090` partition과 `--exclude=quant,jelly`를 사용했다. GPU 지정은 필요 없다. 로그는 공유되는 자신의 기존 폴더에 둔다. gateway에서 무거운 처리를 직접 실행하지 않는다.

## 7. 검증된 범위와 다음 작업

- 최신 browser check: `/tmp/tempo-demo-browser-20261009/check-v5.cjs`. Node/Playwright는 같은 `/tmp/.../node_modules/` 안에 있다. `/tmp`는 영구 저장소가 아니다.
- Chromium 확인: graph/gauge/trail UI 개수 0, B boundaries 일치, 같은 시각에 각 runner가 서로 다른 현재 phase로 진행, JavaScript page error 없음.
- 스크린샷: `/tmp/tempo-demo-browser-20261009/phase-B-v5.png`. 잔상 확인 이미지: `/tmp/split4trail5.png`.
- 이전 버전에서 전체 Cup 완료·동시 재생·mobile 가로 넘침 없음을 확인했다. 최신 B 수정 후 mobile 전체 항목을 재검증한 기록은 없다.
- 음향은 브라우저에서 초기화됐고, fixed 850 Hz filter·oscillator 5개·volume 40을 확인했다. 서버에 음향 출력 장치가 없어 현재 소리가 사용자 희망에 맞는지는 확인하지 못했다.

후속 작업은 사용자의 실제 화면·음향 리뷰를 반영한다. 요청받지 않은 계기판이나 그래프, trail toggle을 되살리지 않는다. 화면의 기술 설명을 계속 늘리기보다 사용자가 지정한 v18 B의 모습과 동시 재생을 우선한다. 코드 변경 후 관련 화면을 직접 캡처해 확인하고 개인 브랜치에 commit/push한다.
