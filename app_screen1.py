"""
예스코 AI 안전 점검 플랫폼 - 현장 라벨링 앱
임원 보고 데모 v1.0

스토리: "현장 작업자가 사진을 찍는 것만으로도 AI 학습 데이터가 쌓이고,
        AI는 점점 똑똑해져서 인적 오류를 백업한다"
"""

import gradio as gr
import os
import json
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# ============================================================
# 🔧 설정
# ============================================================

# 데모 시작 시점의 가짜 누적 데이터 (그럴듯한 숫자)
INITIAL_STATS = {
    "total": 285,
    "normal": 247,
    "defect": 32,
    "damage": 6,
    "ai_version": "v3",
    "next_version": "v4",
    "days_to_next_training": 2,
}

# 세션 상태
SESSION = {
    "stats": INITIAL_STATS.copy(),
    "recent_logs": [
        {"time": "14:23", "type": "defect", "msg": "이탈 의심 발견 - 정릉지점 #047"},
        {"time": "11:05", "type": "normal", "msg": "정상 점검 완료 - 삼선지점 #102"},
        {"time": "09:42", "type": "damage", "msg": "손상 의심 발견 - 신내지점 #018"},
    ],
}

# 시연용 사진의 박스 좌표 (이미지 비율 기준: 0~1)
# 사진을 보고 박스를 어디에 그릴지 미리 정해둠
DEMO_BOXES = {
    "defect_01": {"x": 0.55, "y": 0.25, "w": 0.30, "h": 0.30, "label": "연통 이탈"},
    "defect_02": {"x": 0.50, "y": 0.30, "w": 0.35, "h": 0.25, "label": "연통 이탈"},
    "defect_03": {"x": 0.60, "y": 0.20, "w": 0.25, "h": 0.35, "label": "연통 이탈"},
}

# 브랜드 컬러
BRAND = {
    "primary": "#0057A0",
    "primary_dark": "#003D73",
    "primary_light": "#E8F1FB",
    "success": "#10B981",
    "danger": "#EF4444",
    "warning": "#F59E0B",
    "ios_bg": "#F2F2F7",
    "ios_card": "#FFFFFF",
}

# ============================================================
# 🖼️ 이미지에 박스 그리기
# ============================================================

def draw_demo_box(image, box_info, color=(239, 68, 68)):
    """이미지 위에 라벨링 박스를 그림"""
    if image is None or box_info is None:
        return image
    
    img = image.copy().convert("RGB")
    W, H = img.size
    
    # 비율 좌표를 픽셀로 변환
    x1 = int(box_info["x"] * W)
    y1 = int(box_info["y"] * H)
    x2 = int((box_info["x"] + box_info["w"]) * W)
    y2 = int((box_info["y"] + box_info["h"]) * H)
    
    draw = ImageDraw.Draw(img, "RGBA")
    
    # 반투명 채우기
    draw.rectangle([x1, y1, x2, y2], fill=color + (50,))
    
    # 외곽선
    for i in range(4):
        draw.rectangle([x1-i, y1-i, x2+i, y2+i], outline=color, width=1)
    
    # 모서리 강조 (L자 모양)
    corner_len = min(30, (x2-x1)//4)
    cw = 5  # 모서리 두께
    # 좌상
    draw.rectangle([x1, y1, x1+corner_len, y1+cw], fill=color)
    draw.rectangle([x1, y1, x1+cw, y1+corner_len], fill=color)
    # 우상
    draw.rectangle([x2-corner_len, y1, x2, y1+cw], fill=color)
    draw.rectangle([x2-cw, y1, x2, y1+corner_len], fill=color)
    # 좌하
    draw.rectangle([x1, y2-cw, x1+corner_len, y2], fill=color)
    draw.rectangle([x1, y2-corner_len, x1+cw, y2], fill=color)
    # 우하
    draw.rectangle([x2-corner_len, y2-cw, x2, y2], fill=color)
    draw.rectangle([x2-cw, y2-corner_len, x2, y2], fill=color)
    
    # 라벨 텍스트
    try:
        font = ImageFont.truetype("malgun.ttf", 22)
    except:
        try:
            font = ImageFont.truetype("arial.ttf", 22)
        except:
            font = ImageFont.load_default()
    
    label = box_info.get("label", "")
    if label:
        bbox = draw.textbbox((0, 0), label, font=font)
        lw = bbox[2] - bbox[0] + 16
        lh = bbox[3] - bbox[1] + 10
        draw.rectangle([x1, y1 - lh, x1 + lw, y1], fill=color)
        draw.text((x1 + 8, y1 - lh + 4), label, fill="white", font=font)
    
    return img

def get_box_for_image(image_path):
    """파일명을 보고 미리 정의된 박스 좌표를 찾음"""
    if not image_path:
        return None
    fname = os.path.basename(str(image_path)).lower()
    for key, box in DEMO_BOXES.items():
        if key in fname:
            return box
    # 기본값 (이미지 중앙에 박스)
    return {"x": 0.35, "y": 0.30, "w": 0.30, "h": 0.30, "label": "연통 이탈"}

# ============================================================
# 📱 모바일 프레임 HTML
# ============================================================

def render_mobile_frame_html(content_html):
    """iPhone 스타일 모바일 프레임 안에 콘텐츠를 표시"""
    now_time = datetime.now().strftime("%H:%M")
    
    return f"""
    <div style="display:flex;justify-content:center;padding:20px 0;">
        <div style="
            width: 360px;
            background: #1a1a1a;
            border-radius: 50px;
            padding: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3), 0 0 0 2px #2a2a2a;
            position: relative;
        ">
            <div style="
                background: {BRAND['ios_bg']};
                border-radius: 40px;
                overflow: hidden;
                min-height: 680px;
                position: relative;
            ">
                <!-- 노치 -->
                <div style="
                    position: absolute;
                    top: 0;
                    left: 50%;
                    transform: translateX(-50%);
                    width: 120px;
                    height: 28px;
                    background: #1a1a1a;
                    border-radius: 0 0 18px 18px;
                    z-index: 100;
                "></div>
                
                <!-- 상태바 -->
                <div style="
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 14px 28px 4px;
                    font-size: 13px;
                    font-weight: 600;
                    color: #000;
                ">
                    <span>{now_time}</span>
                    <span style="display:flex;gap:5px;align-items:center;">
                        <span style="font-size:11px;">●●●●</span>
                        <span>📶</span>
                        <span>🔋</span>
                    </span>
                </div>
                
                <!-- 앱 헤더 -->
                <div style="
                    background: linear-gradient(135deg, {BRAND['primary']}, {BRAND['primary_dark']});
                    padding: 16px 20px 14px;
                    color: white;
                    margin-top: 4px;
                ">
                    <div style="font-size:11px;opacity:0.85;letter-spacing:1.5px;font-weight:600;">YESCO FIELD APP</div>
                    <div style="font-size:18px;font-weight:700;margin-top:2px;">현장 점검 라벨링</div>
                    <div style="font-size:11px;opacity:0.8;margin-top:4px;">👤 김코디 · 정릉지점</div>
                </div>
                
                <!-- 콘텐츠 영역 -->
                <div style="padding: 16px 18px;">
                    {content_html}
                </div>
                
                <!-- 홈 인디케이터 -->
                <div style="
                    position: absolute;
                    bottom: 8px;
                    left: 50%;
                    transform: translateX(-50%);
                    width: 120px;
                    height: 4px;
                    background: #000;
                    border-radius: 2px;
                    opacity: 0.3;
                "></div>
            </div>
        </div>
    </div>
    """

def render_app_content(image=None, label_status="waiting", category=None, memo=""):
    """앱 내부 콘텐츠 HTML"""
    
    # 이미지 영역
    if image is None:
        image_area = f"""
        <div style="
            background: white;
            border: 2px dashed #D1D5DB;
            border-radius: 16px;
            height: 200px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            color: #9CA3AF;
        ">
            <div style="font-size:36px;margin-bottom:6px;">📷</div>
            <div style="font-size:13px;font-weight:600;">사진을 업로드하세요</div>
            <div style="font-size:11px;margin-top:2px;">보일러 연통이 잘 보이도록</div>
        </div>
        """
    else:
        import base64
        from io import BytesIO
        buf = BytesIO()
        img_rgb = image.convert("RGB") if image.mode != "RGB" else image
        # 모바일에 맞게 리사이즈
        img_rgb.thumbnail((600, 600))
        img_rgb.save(buf, format="JPEG", quality=85)
        img_b64 = base64.b64encode(buf.getvalue()).decode()
        
        image_area = f"""
        <div style="
            background: black;
            border-radius: 16px;
            overflow: hidden;
            max-height: 240px;
            display: flex;
            justify-content: center;
            align-items: center;
        ">
            <img src="data:image/jpeg;base64,{img_b64}" 
                 style="max-width:100%;max-height:240px;object-fit:contain;" />
        </div>
        """
    
    # 상태 메시지
    if label_status == "waiting":
        status_box = ""
    elif label_status == "labeled":
        cat_label = {"normal": "정상", "defect": "연통 이탈", "damage": "손상"}.get(category, category)
        cat_color = {"normal": BRAND["success"], "defect": BRAND["danger"], "damage": BRAND["warning"]}.get(category, BRAND["primary"])
        status_box = f"""
        <div style="
            background: {cat_color}15;
            border-left: 3px solid {cat_color};
            border-radius: 8px;
            padding: 10px 12px;
            margin-top: 10px;
            font-size: 12px;
        ">
            <div style="color:{cat_color};font-weight:700;">📍 라벨링 완료</div>
            <div style="color:#374151;margin-top:2px;">분류: <b>{cat_label}</b></div>
            {f'<div style="color:#6B7280;margin-top:2px;">메모: {memo}</div>' if memo else ''}
        </div>
        """
    elif label_status == "uploaded":
        cat_label = {"normal": "정상", "defect": "연통 이탈", "damage": "손상"}.get(category, category)
        cat_color = {"normal": BRAND["success"], "defect": BRAND["danger"], "damage": BRAND["warning"]}.get(category, BRAND["primary"])
        status_box = f"""
        <div style="
            background: linear-gradient(135deg, #ECFDF5, #D1FAE5);
            border-radius: 10px;
            padding: 12px;
            margin-top: 10px;
            font-size: 12px;
        ">
            <div style="color:#065F46;font-weight:700;font-size:13px;">✅ 업로드 완료</div>
            <div style="color:#047857;margin-top:4px;line-height:1.5;">
                • 분류: <b>{cat_label}</b><br>
                • AI 학습 데이터에 추가됨<br>
                {'• 담당자에게 알림 발송됨' if category != 'normal' else '• 정상 기록으로 저장됨'}
            </div>
        </div>
        """
    
    return image_area + status_box

# ============================================================
# 📊 대시보드 렌더링
# ============================================================

def render_dashboard():
    s = SESSION["stats"]
    total = s["total"]
    normal_pct = (s["normal"] / total * 100) if total > 0 else 0
    defect_pct = (s["defect"] / total * 100) if total > 0 else 0
    damage_pct = (s["damage"] / total * 100) if total > 0 else 0
    
    # 최근 로그
    log_items = ""
    log_colors = {"normal": BRAND["success"], "defect": BRAND["danger"], "damage": BRAND["warning"]}
    log_icons = {"normal": "✓", "defect": "⚠", "damage": "⚡"}
    for log in SESSION["recent_logs"][:5]:
        c = log_colors.get(log["type"], BRAND["primary"])
        ic = log_icons.get(log["type"], "•")
        log_items += f"""
        <div style="display:flex;align-items:center;gap:10px;padding:10px 0;border-bottom:1px solid #F3F4F6;">
            <div style="width:28px;height:28px;background:{c}15;border-radius:8px;
                        display:flex;align-items:center;justify-content:center;
                        color:{c};font-weight:bold;font-size:14px;">{ic}</div>
            <div style="flex:1;">
                <div style="font-size:13px;color:#374151;">{log['msg']}</div>
                <div style="font-size:11px;color:#9CA3AF;margin-top:1px;">🕐 {log['time']}</div>
            </div>
        </div>
        """
    
    return f"""
    <div style="display:flex;flex-direction:column;gap:14px;">
        
        <!-- 누적 점검 카드 -->
        <div style="background:white;border-radius:14px;padding:20px;
                    box-shadow:0 2px 12px rgba(0,0,0,0.04);border:1px solid #F3F4F6;">
            <div style="display:flex;justify-content:space-between;align-items:baseline;">
                <div style="font-size:12px;color:#6B7280;font-weight:700;letter-spacing:0.5px;">📊 누적 수집 데이터</div>
                <div style="font-size:11px;color:{BRAND['success']};font-weight:600;">● LIVE</div>
            </div>
            <div style="font-size:38px;font-weight:800;color:{BRAND['primary_dark']};margin:6px 0;">
                {total:,}<span style="font-size:16px;color:#9CA3AF;font-weight:500;"> 건</span>
            </div>
            
            <!-- 분포 차트 -->
            <div style="display:flex;height:8px;border-radius:4px;overflow:hidden;margin-top:8px;background:#F3F4F6;">
                <div style="width:{normal_pct}%;background:{BRAND['success']};"></div>
                <div style="width:{defect_pct}%;background:{BRAND['danger']};"></div>
                <div style="width:{damage_pct}%;background:{BRAND['warning']};"></div>
            </div>
            
            <div style="display:flex;justify-content:space-between;margin-top:10px;font-size:11px;">
                <div><span style="color:{BRAND['success']};font-weight:700;">●</span> 정상 <b>{s['normal']:,}</b></div>
                <div><span style="color:{BRAND['danger']};font-weight:700;">●</span> 이탈 <b>{s['defect']:,}</b></div>
                <div><span style="color:{BRAND['warning']};font-weight:700;">●</span> 손상 <b>{s['damage']:,}</b></div>
            </div>
        </div>
        
        <!-- AI 모델 카드 -->
        <div style="background:linear-gradient(135deg,{BRAND['primary']},{BRAND['primary_dark']});
                    border-radius:14px;padding:18px;color:white;
                    box-shadow:0 4px 14px rgba(0,87,160,0.3);">
            <div style="font-size:11px;opacity:0.85;letter-spacing:0.5px;font-weight:600;">🤖 AI 모델 상태</div>
            <div style="display:flex;align-items:center;gap:10px;margin-top:8px;">
                <div style="font-size:24px;font-weight:800;">{s['ai_version']}</div>
                <div style="font-size:14px;opacity:0.8;">→</div>
                <div style="font-size:18px;font-weight:700;opacity:0.9;">{s['next_version']}</div>
                <div style="margin-left:auto;background:rgba(255,255,255,0.2);padding:4px 10px;
                            border-radius:6px;font-size:11px;font-weight:600;">
                    D-{s['days_to_next_training']}
                </div>
            </div>
            <div style="font-size:12px;opacity:0.85;margin-top:8px;">
                다음 재학습 시 정확도 +3.2% 향상 예상
            </div>
        </div>
        
        <!-- 최근 알림 -->
        <div style="background:white;border-radius:14px;padding:16px 20px;
                    box-shadow:0 2px 12px rgba(0,0,0,0.04);border:1px solid #F3F4F6;">
            <div style="font-size:12px;color:#6B7280;font-weight:700;letter-spacing:0.5px;margin-bottom:6px;">
                📋 최근 점검 기록
            </div>
            {log_items}
        </div>
        
    </div>
    """

# ============================================================
# 🔄 메인 핸들러
# ============================================================

def on_image_upload(image, source_path=None):
    """사진 업로드 시 — 모바일 프레임 갱신"""
    if image is None:
        content = render_app_content()
        return render_mobile_frame_html(content), None, gr.update(visible=False), gr.update(visible=False)
    
    # 박스가 자동으로 그려진 이미지를 함께 만들어둠 (실제 화면엔 라벨링 단계에서 표시)
    content = render_app_content(image=image, label_status="waiting")
    return render_mobile_frame_html(content), image, gr.update(visible=True), gr.update(visible=False)

def on_label_apply(image, category, source_path):
    """라벨링 버튼 클릭 — 이미지 위에 박스 그리기"""
    if image is None:
        return render_mobile_frame_html(render_app_content()), gr.update(visible=False)
    
    # 카테고리별 색상
    color_map = {
        "defect": (239, 68, 68),      # 빨강
        "damage": (245, 158, 11),     # 주황
        "normal": (16, 185, 129),     # 초록
    }
    color = color_map.get(category, (239, 68, 68))
    
    # 이미지에 박스 그리기 (정상 외의 경우)
    if category != "normal":
        box = get_box_for_image(source_path) if source_path else {"x": 0.35, "y": 0.30, "w": 0.30, "h": 0.30, "label": {"defect":"연통 이탈", "damage":"손상"}[category]}
        box = {**box, "label": {"defect":"연통 이탈", "damage":"손상"}[category]}
        labeled_img = draw_demo_box(image, box, color=color)
    else:
        labeled_img = image
    
    content = render_app_content(image=labeled_img, label_status="labeled", category=category)
    return render_mobile_frame_html(content), gr.update(visible=True)

def on_upload_submit(image, category, memo, source_path):
    """업로드 버튼 클릭 — 통계 증가 + 완료 메시지"""
    if image is None or category is None:
        return render_mobile_frame_html(render_app_content()), render_dashboard()
    
    # 통계 업데이트
    SESSION["stats"]["total"] += 1
    SESSION["stats"][category] = SESSION["stats"].get(category, 0) + 1
    
    # 로그 추가
    now = datetime.now().strftime("%H:%M")
    locations = ["정릉지점", "삼선지점", "신내지점", "마포지점", "용산지점"]
    import random
    location = random.choice(locations)
    case_num = random.randint(100, 999)
    
    msg_map = {
        "normal": f"정상 점검 완료 - {location} #{case_num}",
        "defect": f"이탈 의심 발견 - {location} #{case_num}",
        "damage": f"손상 의심 발견 - {location} #{case_num}",
    }
    SESSION["recent_logs"].insert(0, {
        "time": now,
        "type": category,
        "msg": msg_map.get(category, "점검 완료"),
    })
    SESSION["recent_logs"] = SESSION["recent_logs"][:10]
    
    # 박스 표시된 이미지 유지
    color_map = {"defect": (239, 68, 68), "damage": (245, 158, 11), "normal": (16, 185, 129)}
    if category != "normal":
        box = get_box_for_image(source_path) if source_path else {"x": 0.35, "y": 0.30, "w": 0.30, "h": 0.30}
        box = {**box, "label": {"defect":"연통 이탈", "damage":"손상"}[category]}
        labeled_img = draw_demo_box(image, box, color=color_map[category])
    else:
        labeled_img = image
    
    content = render_app_content(image=labeled_img, label_status="uploaded", category=category, memo=memo)
    return render_mobile_frame_html(content), render_dashboard()

def reset_app():
    """초기화 - 새 사진을 위해"""
    return (
        render_mobile_frame_html(render_app_content()),
        None,
        None,
        "",
        gr.update(visible=False),
        gr.update(visible=False),
    )

# ============================================================
# 🖥️ Gradio UI
# ============================================================

custom_css = f"""
.gradio-container {{
    background: linear-gradient(180deg, #EEF2F7 0%, #E0E7EF 100%) !important;
    font-family: 'Pretendard', 'Malgun Gothic', -apple-system, sans-serif !important;
    max-width: 1400px !important;
    margin: auto !important;
}}
.header-banner {{
    background: linear-gradient(135deg, {BRAND['primary']} 0%, {BRAND['primary_dark']} 100%);
    border-radius: 18px;
    padding: 24px 32px;
    color: white;
    box-shadow: 0 8px 30px rgba(0, 87, 160, 0.2);
    margin-bottom: 18px;
}}
.demo-section-title {{
    color: {BRAND['primary_dark']};
    font-weight: 800;
    font-size: 14px;
    letter-spacing: 0.5px;
    margin-bottom: 6px;
}}
.btn-category button {{
    border-radius: 10px !important;
    font-weight: 700 !important;
    padding: 10px !important;
    font-size: 13px !important;
}}
"""

example_files = [
    ["examples/normal_01.jpg"],
    ["examples/normal_02.jpg"],
    ["examples/normal_03.jpg"],
    ["examples/defect_01.jpg"],
    ["examples/defect_02.jpg"],
    ["examples/defect_03.jpg"],
]
# 존재하는 파일만 필터링
example_files = [e for e in example_files if os.path.exists(e[0])]

with gr.Blocks(title="예스코 현장 라벨링 앱", css=custom_css, theme=gr.themes.Soft(
    primary_hue="blue", neutral_hue="slate"
)) as demo:
    
    # ── 헤더 ──
    gr.HTML(f"""
    <div class="header-banner">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:14px;">
            <div>
                <div style="font-size:11px;letter-spacing:2.5px;opacity:0.85;font-weight:700;">
                    YESCO · AI SAFETY PLATFORM
                </div>
                <h1 style="margin:6px 0 6px;font-size:26px;font-weight:800;letter-spacing:-0.5px;">
                    📱 현장 라벨링 앱 데모
                </h1>
                <p style="margin:0;opacity:0.85;font-size:13px;">
                    현장 작업자의 점검 사진이 곧 AI 학습 데이터가 되는 자가성장형 안전 플랫폼
                </p>
            </div>
            <div style="text-align:right;">
                <div style="background:rgba(255,255,255,0.18);padding:6px 14px;border-radius:8px;
                            font-size:11px;font-weight:600;backdrop-filter:blur(10px);display:inline-block;">
                    🟢 DEMO MODE
                </div>
                <div style="margin-top:6px;font-size:11px;opacity:0.7;">Field Labeling App v1.0</div>
            </div>
        </div>
    </div>
    """)
    
    # 상태 저장용 (현재 이미지, 원본 경로)
    current_image = gr.State(value=None)
    current_path = gr.State(value=None)
    
    with gr.Row():
        # ── 왼쪽: 모바일 앱 시연 ──
        with gr.Column(scale=5):
            gr.HTML('<div class="demo-section-title">📱 현장 작업자 화면 (모바일 앱)</div>')
            mobile_view = gr.HTML(render_mobile_frame_html(render_app_content()))
        
        # ── 가운데: 컨트롤 패널 ──
        with gr.Column(scale=4):
            gr.HTML('<div class="demo-section-title">🎮 시연 컨트롤</div>')
            
            with gr.Group():
                gr.Markdown("**① 사진 업로드**")
                image_input = gr.Image(
                    type="pil",
                    label="현장 사진",
                    height=200,
                    sources=["upload"],
                )
                
                if example_files:
                    gr.Examples(
                        examples=example_files,
                        inputs=image_input,
                        label="📁 시연용 샘플 사진 (클릭)",
                        examples_per_page=6,
                    )
                else:
                    gr.HTML(f"""
                    <div style="padding:10px;background:{BRAND['warning']}15;
                                border-left:3px solid {BRAND['warning']};border-radius:6px;
                                font-size:12px;color:#92400E;">
                        ℹ️ examples/ 폴더에 시연용 사진을 넣으면 여기 표시됩니다
                    </div>
                    """)
            
            with gr.Group(visible=False) as label_group:
                gr.Markdown("**② 카테고리 선택 (탭 한번으로 라벨링)**")
                with gr.Row(elem_classes="btn-category"):
                    btn_normal = gr.Button("✓ 정상", variant="secondary")
                    btn_defect = gr.Button("⚠ 연통 이탈", variant="stop")
                    btn_damage = gr.Button("⚡ 손상", variant="secondary")
            
            with gr.Group(visible=False) as upload_group:
                gr.Markdown("**③ 메모 및 업로드**")
                memo_input = gr.Textbox(
                    label="메모 (선택)",
                    placeholder="예: 상부 연결부 5cm 이격",
                    lines=1,
                )
                submit_btn = gr.Button("📤 업로드 및 학습 데이터로 등록", variant="primary", size="lg")
            
            reset_btn = gr.Button("🔄 다음 점검 시작", size="sm")
        
        # ── 오른쪽: 실시간 대시보드 ──
        with gr.Column(scale=5):
            gr.HTML('<div class="demo-section-title">📊 실시간 시스템 현황</div>')
            dashboard = gr.HTML(render_dashboard())
    
    # 선택된 카테고리 저장
    selected_category = gr.State(value=None)
    
    # ── 이벤트 핸들러 ──
    
    # 이미지 업로드 시
    image_input.change(
        fn=on_image_upload,
        inputs=[image_input],
        outputs=[mobile_view, current_image, label_group, upload_group],
    )
    
    # 카테고리 버튼들
    def select_category(image, cat, path):
        mobile_html, upload_visible = on_label_apply(image, cat, path)
        return mobile_html, cat, upload_visible
    
    btn_normal.click(
        fn=lambda img, p: select_category(img, "normal", p),
        inputs=[current_image, current_path],
        outputs=[mobile_view, selected_category, upload_group],
    )
    btn_defect.click(
        fn=lambda img, p: select_category(img, "defect", p),
        inputs=[current_image, current_path],
        outputs=[mobile_view, selected_category, upload_group],
    )
    btn_damage.click(
        fn=lambda img, p: select_category(img, "damage", p),
        inputs=[current_image, current_path],
        outputs=[mobile_view, selected_category, upload_group],
    )
    
    # 업로드
    submit_btn.click(
        fn=on_upload_submit,
        inputs=[current_image, selected_category, memo_input, current_path],
        outputs=[mobile_view, dashboard],
    )
    
    # 리셋
    reset_btn.click(
        fn=reset_app,
        outputs=[mobile_view, current_image, selected_category, memo_input, label_group, upload_group],
    )
    
    # 푸터
    gr.HTML(f"""
    <div style="margin-top:20px;padding:18px;background:white;border-radius:12px;
                border:1px solid #E5E7EB;text-align:center;">
        <div style="font-size:12px;color:#6B7280;line-height:1.7;">
            💡 <b>시연 흐름:</b> 
            ① 사진 업로드 → ② 카테고리 선택 (자동 박스 표시) → ③ 메모 작성 후 업로드 → ④ 대시보드에 실시간 반영
        </div>
        <div style="font-size:11px;color:#9CA3AF;margin-top:8px;">
            © 2026 YESCO AI Safety Platform · Field Labeling Demo v1.0
        </div>
    </div>
    """)

# ============================================================
# 🚀 실행
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("📱 예스코 현장 라벨링 앱 데모 v1.0")
    print("=" * 60)
    print("📡 http://127.0.0.1:7860 에서 접속하세요")
    print(f"📁 examples/ 폴더에 시연용 사진을 넣어주세요")
    print("=" * 60)
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
