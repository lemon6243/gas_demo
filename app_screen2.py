"""
예스코 AI 학습 대시보드 - 화면 ②
임원 보고 데모 v1.0

스토리: "현장에서 쌓인 데이터로 AI는 매주 재학습되며,
        시간이 갈수록 시스템 가치가 커진다"
"""

import gradio as gr
from datetime import datetime, timedelta

# ============================================================
# 🔧 설정 - 모델 버전별 데이터
# ============================================================

# 버전별 진화 히스토리 (그럴듯한 수치)
MODEL_HISTORY = [
    {
        "version": "v1",
        "date": "2025-09-15",
        "data_count": 124,
        "accuracy": 52.4,
        "precision": 48.1,
        "recall": 41.3,
        "status": "released",
        "highlight": "초기 모델 출시",
        "improvement": None,
    },
    {
        "version": "v2",
        "date": "2025-11-02",
        "data_count": 412,
        "accuracy": 68.7,
        "precision": 64.2,
        "recall": 58.9,
        "status": "released",
        "highlight": "삼선/정릉 권역 데이터 추가",
        "improvement": "+16.3%p",
    },
    {
        "version": "v3",
        "date": "2026-01-08",
        "data_count": 847,
        "accuracy": 73.2,
        "precision": 71.5,
        "recall": 68.4,
        "status": "current",
        "highlight": "신내 권역 확장 + 야간 촬영 데이터 보강",
        "improvement": "+4.5%p",
    },
    {
        "version": "v4",
        "date": "2026-05-17",
        "data_count": 1247,
        "accuracy": 81.5,
        "precision": 79.8,
        "recall": 76.2,
        "status": "scheduled",
        "highlight": "백업 검사 피드백 자동 반영 (예정)",
        "improvement": "+8.3%p (예상)",
    },
]

# 현재 KPI
KPI = {
    "current_version": "v3",
    "current_accuracy": 73.2,
    "total_data": 1247,
    "data_today": 12,
    "data_this_week": 47,
    "next_version": "v4",
    "days_to_training": 2,
    "expected_accuracy": 81.5,
    "auto_pipeline_status": "active",
}

BRAND = {
    "primary": "#0057A0",
    "primary_dark": "#003D73",
    "primary_light": "#E8F1FB",
    "success": "#10B981",
    "danger": "#EF4444",
    "warning": "#F59E0B",
    "purple": "#8B5CF6",
}

# ============================================================
# 📊 KPI 카드 렌더링
# ============================================================

def render_kpi_cards():
    """상단 4개 KPI 카드"""
    return f"""
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:20px;">
        
        <!-- 현재 정확도 -->
        <div style="background:white;border-radius:14px;padding:18px;border:1px solid #F3F4F6;
                    box-shadow:0 2px 12px rgba(0,0,0,0.04);position:relative;overflow:hidden;">
            <div style="position:absolute;top:0;right:0;width:80px;height:80px;
                        background:radial-gradient(circle,{BRAND['success']}20,transparent 70%);"></div>
            <div style="font-size:11px;color:#6B7280;font-weight:700;letter-spacing:0.5px;">📈 현재 정확도</div>
            <div style="display:flex;align-items:baseline;gap:4px;margin-top:8px;">
                <span style="font-size:34px;font-weight:800;color:{BRAND['primary_dark']};">{KPI['current_accuracy']}</span>
                <span style="font-size:16px;color:#9CA3AF;font-weight:600;">%</span>
            </div>
            <div style="display:flex;align-items:center;gap:4px;margin-top:4px;">
                <span style="font-size:11px;color:{BRAND['success']};font-weight:700;">▲ +4.5%p</span>
                <span style="font-size:11px;color:#9CA3AF;">vs 이전 버전</span>
            </div>
        </div>
        
        <!-- 누적 학습 데이터 -->
        <div style="background:white;border-radius:14px;padding:18px;border:1px solid #F3F4F6;
                    box-shadow:0 2px 12px rgba(0,0,0,0.04);position:relative;overflow:hidden;">
            <div style="position:absolute;top:0;right:0;width:80px;height:80px;
                        background:radial-gradient(circle,{BRAND['primary']}20,transparent 70%);"></div>
            <div style="font-size:11px;color:#6B7280;font-weight:700;letter-spacing:0.5px;">📦 누적 학습 데이터</div>
            <div style="display:flex;align-items:baseline;gap:4px;margin-top:8px;">
                <span style="font-size:34px;font-weight:800;color:{BRAND['primary_dark']};">{KPI['total_data']:,}</span>
                <span style="font-size:16px;color:#9CA3AF;font-weight:600;">건</span>
            </div>
            <div style="display:flex;align-items:center;gap:4px;margin-top:4px;">
                <span style="font-size:11px;color:{BRAND['success']};font-weight:700;">+{KPI['data_today']}</span>
                <span style="font-size:11px;color:#9CA3AF;">오늘 / +{KPI['data_this_week']} 이번 주</span>
            </div>
        </div>
        
        <!-- 다음 재학습 -->
        <div style="background:linear-gradient(135deg,{BRAND['primary']},{BRAND['primary_dark']});
                    border-radius:14px;padding:18px;color:white;
                    box-shadow:0 4px 14px rgba(0,87,160,0.3);position:relative;overflow:hidden;">
            <div style="position:absolute;top:-20px;right:-20px;width:100px;height:100px;
                        background:radial-gradient(circle,rgba(255,255,255,0.15),transparent 70%);"></div>
            <div style="font-size:11px;opacity:0.85;font-weight:700;letter-spacing:0.5px;">⏰ 다음 재학습</div>
            <div style="display:flex;align-items:baseline;gap:4px;margin-top:8px;">
                <span style="font-size:34px;font-weight:800;">D-{KPI['days_to_training']}</span>
            </div>
            <div style="display:flex;align-items:center;gap:6px;margin-top:4px;">
                <span style="background:rgba(255,255,255,0.2);padding:2px 8px;border-radius:5px;
                            font-size:10px;font-weight:700;">🤖 자동</span>
                <span style="font-size:11px;opacity:0.85;">예상 정확도 {KPI['expected_accuracy']}%</span>
            </div>
        </div>
        
        <!-- 자동 파이프라인 상태 -->
        <div style="background:white;border-radius:14px;padding:18px;border:1px solid #F3F4F6;
                    box-shadow:0 2px 12px rgba(0,0,0,0.04);position:relative;overflow:hidden;">
            <div style="position:absolute;top:0;right:0;width:80px;height:80px;
                        background:radial-gradient(circle,{BRAND['success']}20,transparent 70%);"></div>
            <div style="font-size:11px;color:#6B7280;font-weight:700;letter-spacing:0.5px;">⚙️ 학습 파이프라인</div>
            <div style="display:flex;align-items:center;gap:8px;margin-top:10px;">
                <div style="width:10px;height:10px;border-radius:50%;background:{BRAND['success']};
                            box-shadow:0 0 8px {BRAND['success']};animation:pulse 2s infinite;"></div>
                <span style="font-size:18px;font-weight:800;color:{BRAND['success']};">ACTIVE</span>
            </div>
            <div style="font-size:11px;color:#9CA3AF;margin-top:6px;">전자동 운영 중 · 무중단</div>
        </div>
        
    </div>
    <style>
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; transform: scale(1); }}
            50% {{ opacity: 0.6; transform: scale(1.2); }}
        }}
    </style>
    """

# ============================================================
# 📈 정확도 추이 차트 (SVG로 직접 그리기)
# ============================================================

def render_accuracy_chart():
    """버전별 정확도 우상향 곡선 - SVG"""
    
    # 차트 영역 설정
    W, H = 720, 320
    padding_left, padding_right = 60, 30
    padding_top, padding_bottom = 40, 60
    chart_w = W - padding_left - padding_right
    chart_h = H - padding_top - padding_bottom
    
    # 데이터
    versions = MODEL_HISTORY
    n = len(versions)
    max_acc = 100
    min_acc = 30
    
    # 좌표 계산
    points = []
    for i, v in enumerate(versions):
        x = padding_left + (chart_w * i / (n - 1))
        y = padding_top + chart_h - (chart_h * (v["accuracy"] - min_acc) / (max_acc - min_acc))
        points.append((x, y, v))
    
    # 그리드 라인 (수평)
    grid_lines = ""
    for pct in [40, 50, 60, 70, 80, 90]:
        y = padding_top + chart_h - (chart_h * (pct - min_acc) / (max_acc - min_acc))
        grid_lines += f"""
        <line x1="{padding_left}" y1="{y}" x2="{W - padding_right}" y2="{y}"
              stroke="#F3F4F6" stroke-width="1" stroke-dasharray="3,3"/>
        <text x="{padding_left - 10}" y="{y + 4}" text-anchor="end"
              font-size="11" fill="#9CA3AF" font-weight="600">{pct}%</text>
        """
    
    # 영역 채우기 (그라데이션)
    area_points = " ".join([f"{x},{y}" for x, y, _ in points])
    area_path = f"M {padding_left},{padding_top + chart_h} L {area_points} L {W - padding_right},{padding_top + chart_h} Z"
    
    # 선 (실선 부분: released + current / 점선 부분: scheduled)
    solid_points = []
    dashed_points = []
    for i, (x, y, v) in enumerate(points):
        if v["status"] == "scheduled":
            if i > 0:
                # 이전 점과 이번 점 사이는 점선
                dashed_points.append((points[i-1][0], points[i-1][1]))
                dashed_points.append((x, y))
        else:
            solid_points.append((x, y))
    
    solid_line = ""
    if len(solid_points) >= 2:
        d = f"M {solid_points[0][0]},{solid_points[0][1]}"
        for x, y in solid_points[1:]:
            d += f" L {x},{y}"
        solid_line = f'<path d="{d}" stroke="{BRAND["primary"]}" stroke-width="3.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
    
    dashed_line = ""
    if len(dashed_points) >= 2:
        for i in range(0, len(dashed_points), 2):
            if i + 1 < len(dashed_points):
                x1, y1 = dashed_points[i]
                x2, y2 = dashed_points[i+1]
                dashed_line += f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{BRAND["primary"]}" stroke-width="3" stroke-dasharray="6,5" stroke-linecap="round" opacity="0.6"/>'
    
    # 점과 라벨
    dots_and_labels = ""
    for i, (x, y, v) in enumerate(points):
        is_current = v["status"] == "current"
        is_scheduled = v["status"] == "scheduled"
        
        if is_scheduled:
            dot_color = BRAND["purple"]
            ring_size = 8
        elif is_current:
            dot_color = BRAND["danger"]
            ring_size = 10
        else:
            dot_color = BRAND["primary"]
            ring_size = 7
        
        # 외곽 링 (현재 버전 강조)
        if is_current:
            dots_and_labels += f"""
            <circle cx="{x}" cy="{y}" r="14" fill="{dot_color}" opacity="0.2">
                <animate attributeName="r" values="14;20;14" dur="2s" repeatCount="indefinite"/>
                <animate attributeName="opacity" values="0.3;0;0.3" dur="2s" repeatCount="indefinite"/>
            </circle>
            """
        
        # 본체 점
        dots_and_labels += f"""
        <circle cx="{x}" cy="{y}" r="{ring_size}" fill="white" stroke="{dot_color}" stroke-width="3"/>
        <circle cx="{x}" cy="{y}" r="{ring_size - 4}" fill="{dot_color}"/>
        """
        
        # 정확도 라벨 (점 위에)
        acc_text_y = y - 20 if y > 80 else y + 30
        acc_color = dot_color
        dots_and_labels += f"""
        <text x="{x}" y="{acc_text_y}" text-anchor="middle"
              font-size="14" font-weight="800" fill="{acc_color}">{v['accuracy']}%</text>
        """
        
        # 버전 라벨 (X축)
        version_y = padding_top + chart_h + 22
        date_y = padding_top + chart_h + 38
        ver_color = BRAND["danger"] if is_current else (BRAND["purple"] if is_scheduled else "#374151")
        
        status_badge = ""
        if is_current:
            status_badge = f'<text x="{x}" y="{padding_top + chart_h + 52}" text-anchor="middle" font-size="9" font-weight="700" fill="{BRAND["danger"]}">● 현재</text>'
        elif is_scheduled:
            status_badge = f'<text x="{x}" y="{padding_top + chart_h + 52}" text-anchor="middle" font-size="9" font-weight="700" fill="{BRAND["purple"]}">⏰ 예정</text>'
        
        dots_and_labels += f"""
        <text x="{x}" y="{version_y}" text-anchor="middle"
              font-size="14" font-weight="800" fill="{ver_color}">{v['version']}</text>
        <text x="{x}" y="{date_y}" text-anchor="middle"
              font-size="10" fill="#9CA3AF">{v['date'][5:]}</text>
        {status_badge}
        """
    
    svg = f"""
    <svg viewBox="0 0 {W} {H}" style="width:100%;height:auto;max-height:380px;">
        <defs>
            <linearGradient id="areaGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stop-color="{BRAND['primary']}" stop-opacity="0.25"/>
                <stop offset="100%" stop-color="{BRAND['primary']}" stop-opacity="0"/>
            </linearGradient>
        </defs>
        
        <!-- 그리드 -->
        {grid_lines}
        
        <!-- 면적 -->
        <path d="{area_path}" fill="url(#areaGradient)"/>
        
        <!-- 선 -->
        {solid_line}
        {dashed_line}
        
        <!-- 점과 라벨 -->
        {dots_and_labels}
    </svg>
    """
    
    return f"""
    <div style="background:white;border-radius:16px;padding:24px;border:1px solid #F3F4F6;
                box-shadow:0 4px 16px rgba(0,0,0,0.04);">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;flex-wrap:wrap;gap:10px;">
            <div>
                <div style="font-size:18px;font-weight:800;color:#111827;">📈 AI 모델 정확도 진화</div>
                <div style="font-size:12px;color:#6B7280;margin-top:2px;">현장 데이터가 쌓일수록 정확도가 우상향합니다</div>
            </div>
            <div style="display:flex;gap:14px;font-size:11px;color:#6B7280;font-weight:600;">
                <div style="display:flex;align-items:center;gap:5px;">
                    <span style="width:10px;height:10px;border-radius:50%;background:{BRAND['primary']};"></span>
                    완료 버전
                </div>
                <div style="display:flex;align-items:center;gap:5px;">
                    <span style="width:10px;height:10px;border-radius:50%;background:{BRAND['danger']};"></span>
                    현재 버전
                </div>
                <div style="display:flex;align-items:center;gap:5px;">
                    <span style="width:10px;height:10px;border-radius:50%;background:{BRAND['purple']};"></span>
                    예정 버전
                </div>
            </div>
        </div>
        {svg}
    </div>
    """

# ============================================================
# 🔄 자동 파이프라인 다이어그램
# ============================================================

def render_pipeline():
    """수집 → 검수 → 학습 → 배포 흐름"""
    steps = [
        {"icon": "📸", "title": "데이터 수집", "desc": "현장 점검 사진 자동 업로드", "metric": f"+{KPI['data_today']}/일"},
        {"icon": "✅", "title": "자동 검수", "desc": "AI 사전 라벨링 + 사람 검토", "metric": "97% 자동화"},
        {"icon": "🤖", "title": "모델 재학습", "desc": "주 1회 자동 트리거", "metric": f"D-{KPI['days_to_training']}"},
        {"icon": "🚀", "title": "무중단 배포", "desc": "성능 검증 후 자동 배포", "metric": "Zero Downtime"},
    ]
    
    step_html = ""
    for i, step in enumerate(steps):
        is_last = i == len(steps) - 1
        arrow = "" if is_last else f"""
        <div style="display:flex;align-items:center;color:{BRAND['primary']};font-size:20px;font-weight:bold;
                    flex:0 0 24px;justify-content:center;">→</div>
        """
        step_html += f"""
        <div style="flex:1;background:white;border-radius:12px;padding:16px;border:1px solid #F3F4F6;
                    box-shadow:0 2px 8px rgba(0,0,0,0.03);text-align:center;position:relative;">
            <div style="font-size:32px;margin-bottom:8px;">{step['icon']}</div>
            <div style="font-size:13px;font-weight:800;color:#111827;">{step['title']}</div>
            <div style="font-size:11px;color:#6B7280;margin-top:4px;line-height:1.4;">{step['desc']}</div>
            <div style="margin-top:10px;display:inline-block;background:{BRAND['primary_light']};
                        color:{BRAND['primary_dark']};padding:3px 10px;border-radius:6px;
                        font-size:11px;font-weight:700;">{step['metric']}</div>
        </div>
        {arrow}
        """
    
    return f"""
    <div style="background:linear-gradient(135deg,#F0F9FF,#E0F2FE);border-radius:16px;padding:20px;
                border:1px solid #BAE6FD;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
            <div>
                <div style="font-size:16px;font-weight:800;color:{BRAND['primary_dark']};">⚙️ 자동 재학습 파이프라인</div>
                <div style="font-size:12px;color:#6B7280;margin-top:2px;">사람 개입 없이 전 과정이 자동으로 진행됩니다</div>
            </div>
            <div style="background:white;padding:6px 12px;border-radius:8px;font-size:11px;font-weight:700;
                        color:{BRAND['success']};border:1px solid {BRAND['success']}40;">
                ● 실시간 가동 중
            </div>
        </div>
        <div style="display:flex;align-items:stretch;gap:8px;">
            {step_html}
        </div>
    </div>
    """

# ============================================================
# 📜 진화 타임라인
# ============================================================

def render_timeline():
    """모델 버전별 상세 히스토리"""
    items = ""
    for i, v in enumerate(MODEL_HISTORY):
        is_current = v["status"] == "current"
        is_scheduled = v["status"] == "scheduled"
        is_last = i == len(MODEL_HISTORY) - 1
        
        if is_scheduled:
            dot_color = BRAND["purple"]
            bg_color = "#F5F3FF"
            status_label = '<span style="background:#EDE9FE;color:#6B21A8;padding:2px 8px;border-radius:5px;font-size:10px;font-weight:700;">PLANNED</span>'
        elif is_current:
            dot_color = BRAND["danger"]
            bg_color = "#FEF2F2"
            status_label = '<span style="background:#FEE2E2;color:#991B1B;padding:2px 8px;border-radius:5px;font-size:10px;font-weight:700;">CURRENT</span>'
        else:
            dot_color = BRAND["success"]
            bg_color = "#F0FDF4"
            status_label = '<span style="background:#D1FAE5;color:#065F46;padding:2px 8px;border-radius:5px;font-size:10px;font-weight:700;">RELEASED</span>'
        
        improvement_html = ""
        if v["improvement"]:
            color = BRAND["purple"] if is_scheduled else BRAND["success"]
            improvement_html = f"""
            <div style="display:inline-flex;align-items:center;gap:4px;background:{color}15;
                        color:{color};padding:3px 10px;border-radius:6px;font-size:11px;font-weight:700;">
                ▲ {v['improvement']}
            </div>
            """
        
        line = "" if is_last else f"""
        <div style="position:absolute;left:23px;top:48px;bottom:-16px;width:2px;background:#E5E7EB;"></div>
        """
        
        items += f"""
        <div style="position:relative;display:flex;gap:18px;padding-bottom:16px;">
            {line}
            <div style="flex:0 0 48px;height:48px;border-radius:50%;background:white;
                        border:3px solid {dot_color};display:flex;align-items:center;justify-content:center;
                        font-weight:800;color:{dot_color};font-size:14px;z-index:1;">
                {v['version']}
            </div>
            <div style="flex:1;background:{bg_color};border-radius:12px;padding:14px 16px;
                        border:1px solid {dot_color}30;">
                <div style="display:flex;justify-content:space-between;align-items:start;flex-wrap:wrap;gap:8px;">
                    <div>
                        <div style="display:flex;align-items:center;gap:8px;">
                            <span style="font-size:14px;font-weight:800;color:#111827;">{v['highlight']}</span>
                            {status_label}
                        </div>
                        <div style="font-size:12px;color:#6B7280;margin-top:3px;">📅 {v['date']} · 📦 학습 데이터 {v['data_count']:,}건</div>
                    </div>
                    {improvement_html}
                </div>
                <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:10px;">
                    <div style="background:white;border-radius:6px;padding:6px 10px;border:1px solid #F3F4F6;">
                        <div style="font-size:9px;color:#9CA3AF;font-weight:700;">정확도</div>
                        <div style="font-size:14px;font-weight:800;color:{dot_color};">{v['accuracy']}%</div>
                    </div>
                    <div style="background:white;border-radius:6px;padding:6px 10px;border:1px solid #F3F4F6;">
                        <div style="font-size:9px;color:#9CA3AF;font-weight:700;">Precision</div>
                        <div style="font-size:14px;font-weight:800;color:#374151;">{v['precision']}%</div>
                    </div>
                    <div style="background:white;border-radius:6px;padding:6px 10px;border:1px solid #F3F4F6;">
                        <div style="font-size:9px;color:#9CA3AF;font-weight:700;">Recall</div>
                        <div style="font-size:14px;font-weight:800;color:#374151;">{v['recall']}%</div>
                    </div>
                </div>
            </div>
        </div>
        """
    
    return f"""
    <div style="background:white;border-radius:16px;padding:24px;border:1px solid #F3F4F6;
                box-shadow:0 4px 16px rgba(0,0,0,0.04);">
        <div style="font-size:18px;font-weight:800;color:#111827;margin-bottom:4px;">📜 모델 진화 타임라인</div>
        <div style="font-size:12px;color:#6B7280;margin-bottom:18px;">버전별 성능 변화와 주요 개선 사항</div>
        {items}
    </div>
    """

# ============================================================
# 🖥️ Gradio UI
# ============================================================

custom_css = f"""
.gradio-container {{
    background: linear-gradient(180deg, #EEF2F7 0%, #E0E7EF 100%) !important;
    font-family: 'Pretendard', 'Malgun Gothic', -apple-system, sans-serif !important;
    max-width: 1500px !important;
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
"""

with gr.Blocks(title="AI 학습 대시보드", css=custom_css, theme=gr.themes.Soft(
    primary_hue="blue", neutral_hue="slate"
)) as demo:
    
    # 헤더
    gr.HTML(f"""
    <div class="header-banner">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:14px;">
            <div>
                <div style="font-size:11px;letter-spacing:2.5px;opacity:0.85;font-weight:700;">
                    YESCO · AI SAFETY PLATFORM
                </div>
                <h1 style="margin:6px 0 6px;font-size:26px;font-weight:800;letter-spacing:-0.5px;">
                    🤖 AI 학습 대시보드
                </h1>
                <p style="margin:0;opacity:0.85;font-size:13px;">
                    현장 데이터가 쌓일수록 AI는 점점 똑똑해집니다 — 시스템의 가치는 시간이 갈수록 커집니다
                </p>
            </div>
            <div style="text-align:right;">
                <div style="background:rgba(255,255,255,0.18);padding:6px 14px;border-radius:8px;
                            font-size:11px;font-weight:600;display:inline-block;">
                    🟢 LIVE MONITORING
                </div>
                <div style="margin-top:6px;font-size:11px;opacity:0.7;">AI Training Dashboard v1.0</div>
            </div>
        </div>
    </div>
    """)
    
    # KPI 카드
    gr.HTML(render_kpi_cards())
    
    # 정확도 추이 차트 + 파이프라인
    with gr.Row():
        with gr.Column(scale=7):
            gr.HTML(render_accuracy_chart())
        with gr.Column(scale=5):
            gr.HTML(render_pipeline())
    
    # 타임라인
    gr.HTML('<div style="margin-top:20px;"></div>')
    gr.HTML(render_timeline())
    
    # 푸터
    gr.HTML(f"""
    <div style="margin-top:20px;padding:20px;background:linear-gradient(135deg,{BRAND['primary_dark']},{BRAND['primary']});
                border-radius:14px;color:white;">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:14px;">
            <div>
                <div style="font-size:14px;font-weight:800;">💡 핵심 인사이트</div>
                <div style="font-size:12px;opacity:0.9;margin-top:6px;line-height:1.6;">
                    초기 v1 (52.4%) → 현재 v3 (73.2%) → 차기 v4 (81.5% 예상)<br>
                    <b>8개월간 정확도 +29.1%p 향상</b> · 현장 데이터 누적이 만든 자동 성장
                </div>
            </div>
            <div style="text-align:right;font-size:11px;opacity:0.7;">
                © 2026 YESCO AI Safety Platform<br>
                AI Training Dashboard v1.0
            </div>
        </div>
    </div>
    """)

if __name__ == "__main__":
    print("=" * 60)
    print("🤖 예스코 AI 학습 대시보드 v1.0")
    print("=" * 60)
    print("📡 http://127.0.0.1:7862 에서 접속하세요")
    print("=" * 60)
    demo.launch(server_name="0.0.0.0", server_port=7862, share=False)
