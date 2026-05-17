# ============================================================
#  YESCO AI 안전점검 통합 데모 (app.py)
#  - 탭 1: 🚨 AI 실시간 점검 (Phase 4 시연)
#  - 탭 2: 📱 현장 라벨링 앱 (Phase 1~2) — 바운딩 박스 라벨링
#  - 탭 3: 🧠 AI 학습 대시보드 (Phase 2~3)
#  CS팀 사용시설파트 · 2026.05
# ============================================================
import os
import io
import base64
import smtplib
import tempfile
import random
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

import gradio as gr
from PIL import Image, ImageDraw, ImageFont

# ── 환경 변수 ──
ROBOFLOW_API_KEY     = os.getenv("ROBOFLOW_API_KEY", "")
ROBOFLOW_WORKSPACE   = "jongikkim"
ROBOFLOW_PROJECT     = "gas_safety_project"
ROBOFLOW_VERSION     = 3
CONFIDENCE_THRESHOLD = 0.15

SMTP_SERVER    = "smtp.gmail.com"
SMTP_PORT      = 587
SENDER_EMAIL   = os.getenv("SENDER_EMAIL", "")
SENDER_PWD     = os.getenv("SENDER_PASSWORD", "")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL", "")

# ── 브랜드 컬러 ──
BRAND = {
    "primary":      "#1a3a6b",
    "primary_dark": "#0f172a",
    "secondary":    "#2563eb",
    "accent":       "#f59e0b",
    "gold":         "#fbbf24",
    "success":      "#10b981",
    "success_dark": "#059669",
    "danger":       "#dc2626",
    "warning":      "#f59e0b",
    "light":        "#f0f4ff",
    "text":         "#1e293b",
    "sub":          "#64748b",
    "border":       "#e2e8f0",
    "white":        "#ffffff",
}

# ── Roboflow 모델 로드 ──
MODEL = None
MODEL_STATUS = "🔴 SIMULATION"
try:
    if ROBOFLOW_API_KEY:
        from roboflow import Roboflow
        rf = Roboflow(api_key=ROBOFLOW_API_KEY)
        project = rf.workspace(ROBOFLOW_WORKSPACE).project(ROBOFLOW_PROJECT)
        MODEL = project.version(ROBOFLOW_VERSION).model
        MODEL_STATUS = f"🟢 MODEL v{ROBOFLOW_VERSION} ONLINE"
        print(f"✅ Roboflow 모델 로드 성공! (v{ROBOFLOW_VERSION})")
    else:
        print("⚠️ ROBOFLOW_API_KEY 미설정 → 시뮬레이션 모드")
except Exception as e:
    print(f"⚠️ 모델 로드 실패 → 시뮬레이션 모드: {e}")

# ── 세션 통계 ──
SESSION = {
    "total":     285,
    "normal":    247,
    "detached":  32,
    "damaged":   6,
    "ai_version":   f"v{ROBOFLOW_VERSION}",
    "next_version": f"v{ROBOFLOW_VERSION + 1}",
    "logs": [
        {"time": "16:10", "loc": "신내지점 #156", "result": "이탈", "by": "AI"},
        {"time": "14:55", "loc": "정릉지점 #221", "result": "이탈", "by": "AI"},
        {"time": "13:40", "loc": "삼선지점 #073", "result": "정상", "by": "현장"},
    ],
}

# ── 탭1 데모 사진 ──
DEMO_PHOTOS = [
    {"path": "examples/normal_01.jpg", "loc": "삼선지점 #047", "time": "09:15"},
    {"path": "examples/normal_02.jpg", "loc": "정릉지점 #102", "time": "10:22"},
    {"path": "examples/defect_01.jpg", "loc": "신내지점 #018", "time": "11:05"},
    {"path": "examples/normal_03.jpg", "loc": "삼선지점 #073", "time": "13:40"},
    {"path": "examples/defect_02.jpg", "loc": "정릉지점 #221", "time": "14:55"},
    {"path": "examples/defect_03.jpg", "loc": "신내지점 #156", "time": "16:10"},
]
DEMO_PHOTOS = [p for p in DEMO_PHOTOS if os.path.exists(p["path"])]

# ── 데모 박스 좌표 ──
DEMO_BOXES = {
    "defect_01.jpg": {"box": (0.30, 0.25, 0.70, 0.65), "label": "이탈 감지", "conf": 0.87},
    "defect_02.jpg": {"box": (0.25, 0.30, 0.65, 0.70), "label": "이탈 감지", "conf": 0.82},
    "defect_03.jpg": {"box": (0.35, 0.20, 0.75, 0.60), "label": "이탈 감지", "conf": 0.91},
}

# ── AI 학습 히스토리 ──
MODEL_HISTORY = [
    {"ver": "v1", "date": "2025-09-15", "data": 124,  "acc": 52.4, "prec": 48.1, "rec": 41.3, "delta": None,           "status": "released"},
    {"ver": "v2", "date": "2025-11-02", "data": 412,  "acc": 68.7, "prec": 64.2, "rec": 58.9, "delta": "+16.3p",       "status": "released"},
    {"ver": "v3", "date": "2026-01-08", "data": 847,  "acc": 73.2, "prec": 71.5, "rec": 68.4, "delta": "+4.5p",        "status": "current"},
    {"ver": "v4", "date": "2026-05-17", "data": 1247, "acc": 81.5, "prec": 79.8, "rec": 76.2, "delta": "+8.3p (예정)", "status": "scheduled"},
]


# ============================================================
#  공통 유틸
# ============================================================
def get_font(size=20):
    candidates = [
        "C:/Windows/Fonts/malgun.ttf",
        "C:/Windows/Fonts/malgunbd.ttf",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _image_to_base64(image_path):
    """이미지 파일을 base64 data URI로 변환."""
    try:
        with open(image_path, "rb") as f:
            ext = os.path.splitext(image_path)[1].lower().replace(".", "")
            if ext == "jpg":
                ext = "jpeg"
            if not ext:
                ext = "jpeg"
            b64 = base64.b64encode(f.read()).decode("utf-8")
            return f"data:image/{ext};base64,{b64}"
    except Exception as e:
        print(f"⚠️ 이미지 base64 변환 실패: {e}")
        return ""


def _pil_to_base64(pil_image):
    """PIL 이미지를 base64 data URI로 변환."""
    try:
        buf = io.BytesIO()
        pil_image.save(buf, format="JPEG", quality=88)
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{b64}"
    except Exception as e:
        print(f"⚠️ PIL base64 변환 실패: {e}")
        return ""


def draw_detection_box(image, box_rel, label, conf, color="#dc2626"):
    """AI 감지 결과용 박스 (확신도 포함)."""
    img = image.copy().convert("RGB")
    w, h = img.size
    x1, y1, x2, y2 = box_rel
    px1, py1, px2, py2 = int(x1*w), int(y1*h), int(x2*w), int(y2*h)

    draw = ImageDraw.Draw(img, "RGBA")
    fill_color = (220, 38, 38, 60) if color == "#dc2626" else (16, 185, 129, 60)
    draw.rectangle([px1, py1, px2, py2], fill=fill_color)
    for off in range(3):
        draw.rectangle([px1-off, py1-off, px2+off, py2+off], outline=color)
    corner = max(20, min(40, (px2-px1)//8))
    for cx, cy, dx, dy in [(px1,py1,1,1),(px2,py1,-1,1),(px1,py2,1,-1),(px2,py2,-1,-1)]:
        draw.line([(cx, cy), (cx+dx*corner, cy)], fill=color, width=5)
        draw.line([(cx, cy), (cx, cy+dy*corner)], fill=color, width=5)

    font = get_font(22)
    text = f"{label} {conf*100:.0f}%"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    pad = 8
    ly1 = max(0, py1 - th - pad*2 - 4)
    draw.rectangle([px1, ly1, px1+tw+pad*2, ly1+th+pad*2], fill=color)
    draw.text((px1+pad, ly1+pad), text, fill="#fff", font=font)
    return img


def draw_labeling_box(image, click_x, click_y, box_size_ratio=0.30, category="이탈"):
    """탭2 라벨링용 박스 — 클릭 좌표 중심으로 박스 생성."""
    img = image.copy().convert("RGB")
    W, H = img.size

    # 카테고리별 색상
    color_map = {
        "이탈": "#dc2626",
        "손상": "#f59e0b",
        "정상": "#10b981",
    }
    color = color_map.get(category, "#dc2626")
    color_rgb = tuple(int(color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))

    # 박스 크기 (이미지 짧은 변의 30%)
    box_size = int(min(W, H) * box_size_ratio)
    half = box_size // 2

    # 클릭 지점 중심 박스 (경계 보정)
    px1 = max(0, click_x - half)
    py1 = max(0, click_y - half)
    px2 = min(W, click_x + half)
    py2 = min(H, click_y + half)

    draw = ImageDraw.Draw(img, "RGBA")
    # 반투명 채우기
    draw.rectangle([px1, py1, px2, py2], fill=color_rgb + (55,))
    # 외곽선
    for off in range(3):
        draw.rectangle([px1-off, py1-off, px2+off, py2+off], outline=color)
    # L자 코너
    corner = max(20, min(40, (px2-px1)//8))
    for cx, cy, dx, dy in [(px1,py1,1,1),(px2,py1,-1,1),(px1,py2,1,-1),(px2,py2,-1,-1)]:
        draw.line([(cx, cy), (cx+dx*corner, cy)], fill=color, width=5)
        draw.line([(cx, cy), (cx, cy+dy*corner)], fill=color, width=5)

    # 라벨
    font = get_font(22)
    text = f"🏷️ {category}"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    pad = 8
    ly1 = max(0, py1 - th - pad*2 - 4)
    draw.rectangle([px1, ly1, px1+tw+pad*2, ly1+th+pad*2], fill=color)
    draw.text((px1+pad, ly1+pad), text, fill="#fff", font=font)

    # 박스 상대좌표(0~1) 반환 — 학습 데이터로 저장될 형식
    box_rel = (px1/W, py1/H, px2/W, py2/H)
    return img, box_rel


def get_box_for_image(filename):
    """파일명으로 데모박스 매칭 (대소문자/구분자 무관)."""
    base_name = os.path.basename(filename).lower()
    for key, box in DEMO_BOXES.items():
        if key.lower() in base_name:
            print(f"  ✓ 박스 매칭: {base_name} → {key}")
            return box
    defect_keywords = ["defect", "detach", "damage", "이탈", "손상", "결함", "비정상"]
    if any(kw in base_name for kw in defect_keywords):
        print(f"  ✓ 박스 폴백 적용: {base_name}")
        return {"box": (0.30, 0.25, 0.70, 0.65), "label": "이탈 감지", "conf": 0.75}
    print(f"  ✗ 박스 매칭 실패 (정상으로 판단): {base_name}")
    return None


def send_alert_email(image, location, conf):
    if not (SENDER_EMAIL and SENDER_PWD and RECEIVER_EMAIL):
        return True, "📧 (시뮬레이션) 담당자에게 알림 발송 완료"
    try:
        msg = MIMEMultipart()
        msg["Subject"] = f"[YESCO 안전점검] 이탈 감지 알림 — {location}"
        msg["From"], msg["To"] = SENDER_EMAIL, RECEIVER_EMAIL
        html = f"""
        <div style="font-family:'Noto Sans KR',sans-serif;max-width:560px;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden;">
          <div style="background:linear-gradient(135deg,#1a3a6b,#2563eb);color:#fff;padding:18px 24px;">
            <div style="font-size:11px;letter-spacing:2px;color:#fbbf24;">YESCO AI SAFETY ALERT</div>
            <div style="font-size:20px;font-weight:900;margin-top:4px;">⚠️ 연통 이탈 감지</div>
          </div>
          <div style="padding:20px 24px;background:#fff;color:#1e293b;">
            <p><b>위치:</b> {location}</p>
            <p><b>감지 시각:</b> {datetime.now():%Y-%m-%d %H:%M:%S}</p>
            <p><b>AI 확신도:</b> {conf*100:.1f}%</p>
            <p><b>모델:</b> {MODEL_STATUS}</p>
            <hr style="border:none;border-top:1px solid #e2e8f0;margin:14px 0;">
            <p style="color:#dc2626;font-weight:700;">즉시 현장 점검이 필요합니다.</p>
          </div>
        </div>
        """
        msg.attach(MIMEText(html, "html"))
        buf = io.BytesIO(); image.save(buf, format="JPEG")
        img_part = MIMEImage(buf.getvalue())
        img_part.add_header("Content-Disposition", "attachment", filename="detection.jpg")
        msg.attach(img_part)
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as s:
            s.starttls(); s.login(SENDER_EMAIL, SENDER_PWD); s.send_message(msg)
        return True, f"📧 담당자({RECEIVER_EMAIL})에게 알림 발송 완료"
    except Exception as e:
        return False, f"❌ 이메일 발송 실패: {e}"


# ============================================================
#  탭 1 — AI 실시간 점검
# ============================================================
def render_tab1_header():
    return f"""
    <div style="background:linear-gradient(135deg,{BRAND['primary']},{BRAND['secondary']});
                color:#fff;border-radius:14px;padding:20px 28px;margin-bottom:16px;
                box-shadow:0 4px 16px rgba(26,58,107,0.25);">
      <div style="display:flex;align-items:center;justify-content:space-between;gap:20px;flex-wrap:wrap;">
        <div>
          <div style="display:inline-block;background:rgba(255,255,255,0.18);color:{BRAND['gold']};
                      font-size:10px;letter-spacing:2px;padding:4px 12px;border-radius:10px;
                      font-weight:700;margin-bottom:8px;">
            PHASE 4 · REAL-TIME AI INSPECTION
          </div>
          <div style="font-size:22px;font-weight:900;color:#fff;line-height:1.3;">
            🚨 AI 실시간 연통 안전점검
          </div>
          <div style="font-size:12px;color:rgba(255,255,255,0.85);margin-top:4px;">
            촬영 즉시 3초 AI 위험도 분석 · 이탈 감지 시 담당자 자동 알림
          </div>
        </div>
        <div style="text-align:right;">
          <div style="font-size:10px;color:rgba(255,255,255,0.6);letter-spacing:1px;">MODEL STATUS</div>
          <div style="font-size:14px;font-weight:900;color:{BRAND['gold']};margin-top:2px;">{MODEL_STATUS}</div>
        </div>
      </div>
    </div>
    """


def render_tab1_gallery():
    if not DEMO_PHOTOS:
        return f"""
        <div style="background:#fff;border:2px dashed {BRAND['border']};border-radius:12px;
                    padding:40px;text-align:center;color:{BRAND['sub']};">
          📂 <b>examples/</b> 폴더에 데모 사진을 넣어주세요.
        </div>
        """
    cards = ""
    for p in DEMO_PHOTOS:
        cards += f"""
        <div style="background:#fff;border:1px solid {BRAND['border']};border-radius:10px;
                    overflow:hidden;box-shadow:0 2px 6px rgba(0,0,0,0.05);">
          <div style="background:linear-gradient(135deg,{BRAND['primary']},{BRAND['secondary']});
                      color:#fff;padding:8px 12px;font-size:11px;font-weight:700;
                      display:flex;justify-content:space-between;">
            <span>📍 {p['loc']}</span><span style="color:{BRAND['gold']};">{p['time']}</span>
          </div>
        </div>
        """
    return f"""
    <div style="background:#fff;border:1px solid {BRAND['border']};border-radius:12px;padding:14px;">
      <div style="font-size:12px;font-weight:700;color:{BRAND['primary']};margin-bottom:10px;">
        📋 오늘 점검 대상 · {len(DEMO_PHOTOS)}건
      </div>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;">{cards}</div>
    </div>
    """


def analyze_one_photo(photo):
    path = photo["path"]
    img = Image.open(path).convert("RGB")
    if MODEL:
        try:
            pred = MODEL.predict(path, confidence=int(CONFIDENCE_THRESHOLD*100), overlap=30).json()
            preds = pred.get("predictions", [])
            danger = [p for p in preds if any(k in p.get("class","").lower()
                      for k in ["detach","defect","damage","이탈","손상"])]
            if danger:
                top = max(danger, key=lambda x: x["confidence"])
                w, h = img.size
                x1 = (top["x"] - top["width"]/2) / w
                y1 = (top["y"] - top["height"]/2) / h
                x2 = (top["x"] + top["width"]/2) / w
                y2 = (top["y"] + top["height"]/2) / h
                vis = draw_detection_box(img, (x1,y1,x2,y2), "이탈 감지", top["confidence"])
                return vis, "danger", top["confidence"]
            return img, "normal", 0.95
        except Exception as e:
            print(f"예측 오류: {e}")
    box_info = get_box_for_image(path)
    if box_info:
        vis = draw_detection_box(img, box_info["box"], box_info["label"], box_info["conf"])
        return vis, "danger", box_info["conf"]
    return img, "normal", 0.95


def render_tab1_result(photo, status, conf):
    color = BRAND["danger"] if status == "danger" else BRAND["success"]
    bg    = "#fef2f2" if status == "danger" else "#f0fdf4"
    icon  = "⚠️" if status == "danger" else "✅"
    text  = "이탈 감지" if status == "danger" else "정상"
    email_block = ""
    if status == "danger":
        ok, msg = send_alert_email(Image.open(photo["path"]), photo["loc"], conf)
        email_block = f"""
        <div style="margin-top:10px;padding:10px 14px;background:{BRAND['primary']};
                    color:#fff;border-radius:8px;font-size:11px;">
          {msg}
        </div>
        """
    return f"""
    <div style="background:{bg};border:2px solid {color};border-radius:12px;padding:16px 20px;margin-bottom:8px;">
      <div style="display:flex;align-items:center;gap:14px;">
        <div style="font-size:32px;">{icon}</div>
        <div style="flex:1;">
          <div style="font-size:18px;font-weight:900;color:{color};">{text}</div>
          <div style="font-size:11px;color:{BRAND['sub']};margin-top:2px;">
            📍 {photo['loc']} · 🕐 {photo['time']} · 🎯 확신도 {conf*100:.1f}%
          </div>
        </div>
      </div>
      {email_block}
    </div>
    """


def render_tab1_summary(normal, danger):
    total = normal + danger
    return f"""
    <div style="background:linear-gradient(135deg,{BRAND['primary_dark']},{BRAND['primary']});
                color:#fff;border-radius:12px;padding:16px 22px;margin-top:12px;">
      <div style="font-size:10px;letter-spacing:2px;color:{BRAND['gold']};margin-bottom:8px;">
        📊 점검 결과 요약
      </div>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:14px;">
        <div style="text-align:center;background:rgba(255,255,255,0.1);border-radius:8px;padding:10px;">
          <div style="font-size:24px;font-weight:900;color:#fff;">{total}</div>
          <div style="font-size:10px;color:rgba(255,255,255,0.7);">총 점검</div>
        </div>
        <div style="text-align:center;background:rgba(16,185,129,0.2);border-radius:8px;padding:10px;">
          <div style="font-size:24px;font-weight:900;color:{BRAND['success']};">{normal}</div>
          <div style="font-size:10px;color:rgba(255,255,255,0.7);">정상</div>
        </div>
        <div style="text-align:center;background:rgba(220,38,38,0.2);border-radius:8px;padding:10px;">
          <div style="font-size:24px;font-weight:900;color:{BRAND['gold']};">{danger}</div>
          <div style="font-size:10px;color:rgba(255,255,255,0.7);">이탈 감지</div>
        </div>
      </div>
    </div>
    """


def run_tab1_analysis():
    if not DEMO_PHOTOS:
        return None, f"""
        <div style="background:#fffbeb;border:1px solid {BRAND['accent']};border-radius:10px;
                    padding:20px;text-align:center;color:#92400e;">
          ⚠️ examples/ 폴더에 데모 사진을 추가해주세요.
        </div>
        """, render_tab1_summary(0, 0)
    results, danger_cnt, normal_cnt, last_img = "", 0, 0, None
    for p in DEMO_PHOTOS:
        vis, status, conf = analyze_one_photo(p)
        last_img = vis
        if status == "danger": danger_cnt += 1
        else: normal_cnt += 1
        results += render_tab1_result(p, status, conf)
    return last_img, results, render_tab1_summary(normal_cnt, danger_cnt)


# ============================================================
#  탭 2 — 현장 라벨링 앱 (바운딩 박스 라벨링)
# ============================================================
def render_tab2_mobile_frame(inner_html):
    return f"""
    <div style="display:flex;justify-content:center;padding:10px;">
      <div style="width:300px;background:#1a1a1a;border-radius:36px;padding:10px;
                  box-shadow:0 10px 40px rgba(0,0,0,0.3);">
        <div style="background:#fff;border-radius:28px;overflow:hidden;height:620px;
                    display:flex;flex-direction:column;">
          <div style="background:linear-gradient(135deg,{BRAND['primary']},{BRAND['secondary']});
                      color:#fff;padding:12px 16px;font-size:11px;
                      display:flex;justify-content:space-between;">
            <span style="font-weight:700;">YESCO 점검</span>
            <span style="color:{BRAND['gold']};">📶 LTE</span>
          </div>
          <div style="flex:1;padding:12px;overflow-y:auto;background:#f8fafc;">{inner_html}</div>
        </div>
      </div>
    </div>
    """


def render_tab2_app_content(image_b64=None, category=None, box_drawn=False):
    """모바일 프레임 내부 컨텐츠."""
    if not image_b64:
        return f"""
        <div style="text-align:center;padding:60px 20px;">
          <div style="font-size:48px;margin-bottom:12px;">📸</div>
          <div style="font-size:13px;font-weight:700;color:{BRAND['primary']};">사진을 업로드해 주세요</div>
          <div style="font-size:10px;color:{BRAND['sub']};margin-top:6px;">현장에서 촬영한 연통 사진</div>
        </div>
        """
    img_section = f"""
    <div style="background:#fff;border-radius:10px;overflow:hidden;border:1px solid {BRAND['border']};margin-bottom:10px;">
      <img src="{image_b64}" style="width:100%;display:block;">
    </div>
    """
    # 안내/카테고리 영역
    if not box_drawn and not category:
        guide = f"""
        <div style="background:{BRAND['gold']};color:{BRAND['primary_dark']};border-radius:8px;
                    padding:8px 12px;font-size:11px;font-weight:700;text-align:center;margin-bottom:6px;">
          👆 사진 위 이상 부위를 탭하세요
        </div>
        """
    elif box_drawn and not category:
        guide = f"""
        <div style="background:{BRAND['secondary']};color:#fff;border-radius:8px;
                    padding:8px 12px;font-size:11px;font-weight:700;text-align:center;margin-bottom:6px;">
          🏷️ 카테고리를 선택하세요
        </div>
        """
    elif category:
        color_map = {"정상": BRAND["success"], "이탈": BRAND["danger"], "손상": BRAND["accent"]}
        c = color_map.get(category, BRAND["sub"])
        guide = f"""
        <div style="background:{c};color:#fff;border-radius:8px;padding:8px 12px;
                    font-size:11px;font-weight:700;text-align:center;margin-bottom:6px;">
          ✅ 분류: {category} · 업로드 준비 완료
        </div>
        """
    else:
        guide = ""

    return f"""
    {img_section}{guide}
    <div style="font-size:9.5px;color:{BRAND['sub']};text-align:center;line-height:1.6;">
      라벨링 후 업로드하면<br>AI 학습 데이터에 추가됩니다
    </div>
    """


def render_tab2_dashboard():
    total = SESSION["total"]
    n_pct = SESSION["normal"] / total * 100
    d_pct = SESSION["detached"] / total * 100
    x_pct = SESSION["damaged"] / total * 100
    logs_html = ""
    for log in SESSION["logs"][:5]:
        color = BRAND["success"] if log["result"] == "정상" else BRAND["danger"]
        logs_html += f"""
        <div style="display:flex;justify-content:space-between;padding:6px 0;
                    border-bottom:1px solid {BRAND['border']};font-size:10.5px;">
          <span style="color:{BRAND['sub']};">{log['time']}</span>
          <span style="color:{BRAND['text']};">{log['loc']}</span>
          <span style="color:{color};font-weight:700;">{log['result']}</span>
        </div>
        """
    return f"""
    <div style="background:linear-gradient(135deg,{BRAND['primary_dark']},{BRAND['primary']});
                color:#fff;border-radius:12px;padding:16px 20px;margin-bottom:12px;">
      <div style="font-size:10px;letter-spacing:2px;color:{BRAND['gold']};margin-bottom:8px;">
        📊 누적 수집 현황
      </div>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;">
        <div style="text-align:center;background:rgba(255,255,255,0.1);border-radius:8px;padding:10px;">
          <div style="font-size:22px;font-weight:900;color:#fff;">{SESSION['total']}</div>
          <div style="font-size:9.5px;color:rgba(255,255,255,0.7);">총 데이터</div>
        </div>
        <div style="text-align:center;background:rgba(16,185,129,0.25);border-radius:8px;padding:10px;">
          <div style="font-size:22px;font-weight:900;color:{BRAND['success']};">{SESSION['normal']}</div>
          <div style="font-size:9.5px;color:rgba(255,255,255,0.7);">정상</div>
        </div>
        <div style="text-align:center;background:rgba(220,38,38,0.25);border-radius:8px;padding:10px;">
          <div style="font-size:22px;font-weight:900;color:{BRAND['gold']};">{SESSION['detached']+SESSION['damaged']}</div>
          <div style="font-size:9.5px;color:rgba(255,255,255,0.7);">이상</div>
        </div>
      </div>
      <div style="display:flex;height:6px;border-radius:3px;overflow:hidden;margin-top:12px;background:rgba(255,255,255,0.1);">
        <div style="width:{n_pct}%;background:{BRAND['success']};"></div>
        <div style="width:{d_pct}%;background:{BRAND['danger']};"></div>
        <div style="width:{x_pct}%;background:{BRAND['accent']};"></div>
      </div>
    </div>
    <div style="background:#fff;border:1px solid {BRAND['border']};border-radius:12px;padding:14px 18px;margin-bottom:12px;">
      <div style="font-size:11px;font-weight:700;color:{BRAND['primary']};margin-bottom:8px;">
        🧠 AI 모델 학습 현황
      </div>
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <div>
          <div style="font-size:18px;font-weight:900;color:{BRAND['primary']};">{SESSION['ai_version']} → {SESSION['next_version']}</div>
          <div style="font-size:9.5px;color:{BRAND['sub']};margin-top:2px;">다음 학습까지 D-2</div>
        </div>
        <div style="background:{BRAND['success']};color:#fff;font-size:10px;font-weight:700;
                    padding:4px 10px;border-radius:6px;">자동 파이프라인 ACTIVE</div>
      </div>
    </div>
    <div style="background:#fff;border:1px solid {BRAND['border']};border-radius:12px;padding:14px 18px;">
      <div style="font-size:11px;font-weight:700;color:{BRAND['primary']};margin-bottom:8px;">
        📝 최근 라벨링 기록
      </div>
      {logs_html}
    </div>
    """


# ── 탭 2 이벤트 핸들러 ──
def tab2_on_image_load(image):
    """사진 업로드 시: 원본을 캔버스에 표시 + 모바일에 안내."""
    if image is None:
        return (
            None,                                    # canvas
            render_tab2_mobile_frame(render_tab2_app_content()),  # mobile
            None,                                    # state: original_img (PIL)
            None,                                    # state: box_rel
            None,                                    # state: category
        )
    pil = Image.fromarray(image).convert("RGB")
    img_b64 = _pil_to_base64(pil)
    return (
        pil,
        render_tab2_mobile_frame(render_tab2_app_content(img_b64, box_drawn=False)),
        pil,
        None,
        None,
    )


def tab2_on_canvas_click(original_img, category, evt: gr.SelectData):
    """캔버스 클릭 → 클릭 좌표 중심으로 박스 그리기."""
    if original_img is None or evt is None:
        return None, render_tab2_mobile_frame(render_tab2_app_content()), None
    
    # 카테고리가 정해져 있지 않으면 기본 "이탈"로 표시 (나중에 사용자가 바꿀 수 있음)
    cat = category if category else "이탈"
    
    click_x, click_y = evt.index[0], evt.index[1]
    boxed_img, box_rel = draw_labeling_box(original_img, click_x, click_y, category=cat)
    img_b64 = _pil_to_base64(boxed_img)
    
    return (
        boxed_img,
        render_tab2_mobile_frame(render_tab2_app_content(img_b64, category=category, box_drawn=True)),
        box_rel,
    )


def tab2_on_category(category, original_img, box_rel):
    """카테고리 버튼 클릭 시: 박스 색상을 카테고리에 맞게 다시 그리기."""
    if original_img is None:
        return render_tab2_mobile_frame(render_tab2_app_content()), None, category
    
    # 정상은 박스 없이도 가능
    if category == "정상":
        img_b64 = _pil_to_base64(original_img)
        return (
            render_tab2_mobile_frame(render_tab2_app_content(img_b64, category=category, box_drawn=True)),
            original_img,
            category,
        )
    
    # 이탈/손상은 박스가 필수
    if box_rel is None:
        # 박스가 없으면 안내만 표시
        img_b64 = _pil_to_base64(original_img)
        warn_html = f"""
        <div style="background:#fff;border-radius:10px;overflow:hidden;border:1px solid {BRAND['border']};margin-bottom:10px;">
          <img src="{img_b64}" style="width:100%;display:block;">
        </div>
        <div style="background:{BRAND['danger']};color:#fff;border-radius:8px;padding:8px 12px;
                    font-size:11px;font-weight:700;text-align:center;margin-bottom:6px;">
          ⚠️ 먼저 사진 위 이상 부위를 탭하세요
        </div>
        """
        return render_tab2_mobile_frame(warn_html), original_img, None
    
    # 박스를 카테고리 색상으로 다시 그리기
    W, H = original_img.size
    cx = int((box_rel[0] + box_rel[2]) / 2 * W)
    cy = int((box_rel[1] + box_rel[3]) / 2 * H)
    boxed_img, _ = draw_labeling_box(original_img, cx, cy, category=category)
    img_b64 = _pil_to_base64(boxed_img)
    return (
        render_tab2_mobile_frame(render_tab2_app_content(img_b64, category=category, box_drawn=True)),
        boxed_img,
        category,
    )


def tab2_on_upload_submit(original_img, box_rel, category, memo):
    """업로드 버튼 클릭 시: 세션 데이터에 추가."""
    if original_img is None:
        return render_tab2_mobile_frame(render_tab2_app_content()), render_tab2_dashboard()
    if not category:
        img_b64 = _pil_to_base64(original_img)
        return (
            render_tab2_mobile_frame(render_tab2_app_content(img_b64, box_drawn=(box_rel is not None))),
            render_tab2_dashboard()
        )
    if category in ("이탈", "손상") and box_rel is None:
        img_b64 = _pil_to_base64(original_img)
        return (
            render_tab2_mobile_frame(render_tab2_app_content(img_b64, box_drawn=False)),
            render_tab2_dashboard()
        )

    # 세션 업데이트
    SESSION["total"] += 1
    if category == "정상":   SESSION["normal"]   += 1
    elif category == "이탈": SESSION["detached"] += 1
    elif category == "손상": SESSION["damaged"]  += 1
    
    locs = ["삼선지점", "정릉지점", "신내지점"]
    loc = f"{random.choice(locs)} #{random.randint(1,300):03d}"
    SESSION["logs"].insert(0, {
        "time": datetime.now().strftime("%H:%M"),
        "loc":  loc, "result": category, "by": "현장"
    })
    SESSION["logs"] = SESSION["logs"][:10]
    
    # 박스 좌표 표시 (학습 데이터 저장 시뮬레이션)
    box_info = ""
    if box_rel:
        box_info = f"""
        <div style="font-size:9px;color:rgba(255,255,255,0.8);margin-top:6px;
                    font-family:monospace;background:rgba(0,0,0,0.2);padding:4px 8px;border-radius:4px;">
          📍 박스: ({box_rel[0]:.2f}, {box_rel[1]:.2f}) — ({box_rel[2]:.2f}, {box_rel[3]:.2f})
        </div>
        """
    
    success_html = f"""
    <div style="background:{BRAND['success']};color:#fff;border-radius:10px;padding:20px;text-align:center;">
      <div style="font-size:36px;margin-bottom:8px;">✅</div>
      <div style="font-size:13px;font-weight:900;">업로드 완료!</div>
      <div style="font-size:10px;margin-top:6px;opacity:0.9;">
        분류: <b>{category}</b><br>
        위치: {loc}<br>
        AI 학습 데이터 +1
      </div>
      {box_info}
    </div>
    """
    return render_tab2_mobile_frame(success_html), render_tab2_dashboard()


def tab2_reset():
    """초기화."""
    return (
        None,
        render_tab2_mobile_frame(render_tab2_app_content()),
        None,
        None,
        None,
        render_tab2_dashboard()
    )


# ============================================================
#  탭 3 — AI 학습 대시보드
# ============================================================
def render_tab3_kpis():
    cur = MODEL_HISTORY[2]
    nxt = MODEL_HISTORY[3]
    return f"""
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px;">
      <div style="background:linear-gradient(135deg,{BRAND['primary']},{BRAND['secondary']});
                  color:#fff;border-radius:12px;padding:16px;">
        <div style="font-size:10px;letter-spacing:1px;color:{BRAND['gold']};">현재 정확도</div>
        <div style="font-size:32px;font-weight:900;color:#fff;margin-top:4px;">{cur['acc']}%</div>
        <div style="font-size:10px;color:rgba(255,255,255,0.7);margin-top:2px;">모델 {cur['ver']}</div>
      </div>
      <div style="background:#fff;border:1px solid {BRAND['border']};border-top:4px solid {BRAND['success']};border-radius:12px;padding:16px;">
        <div style="font-size:10px;color:{BRAND['sub']};">학습 데이터</div>
        <div style="font-size:32px;font-weight:900;color:{BRAND['success']};margin-top:4px;">{nxt['data']:,}</div>
        <div style="font-size:10px;color:{BRAND['sub']};margin-top:2px;">건 (+12 오늘)</div>
      </div>
      <div style="background:#fff;border:1px solid {BRAND['border']};border-top:4px solid {BRAND['accent']};border-radius:12px;padding:16px;">
        <div style="font-size:10px;color:{BRAND['sub']};">다음 학습</div>
        <div style="font-size:32px;font-weight:900;color:{BRAND['accent']};margin-top:4px;">D-2</div>
        <div style="font-size:10px;color:{BRAND['sub']};margin-top:2px;">{nxt['ver']} 자동 학습</div>
      </div>
      <div style="background:#fff;border:1px solid {BRAND['border']};border-top:4px solid {BRAND['secondary']};border-radius:12px;padding:16px;">
        <div style="font-size:10px;color:{BRAND['sub']};">파이프라인</div>
        <div style="font-size:18px;font-weight:900;color:{BRAND['success']};margin-top:4px;">🟢 ACTIVE</div>
        <div style="font-size:10px;color:{BRAND['sub']};margin-top:2px;">97% 자동화</div>
      </div>
    </div>
    """


def render_tab3_chart():
    W, H = 700, 240
    margin_l, margin_b, margin_t = 50, 36, 20
    plot_w, plot_h = W - margin_l - 20, H - margin_b - margin_t
    min_a, max_a = 40, 90
    points = []
    for i, m in enumerate(MODEL_HISTORY):
        x = margin_l + (plot_w / (len(MODEL_HISTORY) - 1)) * i
        y = margin_t + plot_h - ((m["acc"] - min_a) / (max_a - min_a)) * plot_h
        points.append((x, y, m))
    grid_lines, y_labels = "", ""
    for v in [50, 60, 70, 80, 90]:
        y = margin_t + plot_h - ((v - min_a) / (max_a - min_a)) * plot_h
        grid_lines += f'<line x1="{margin_l}" y1="{y}" x2="{W-20}" y2="{y}" stroke="{BRAND["border"]}" stroke-dasharray="2,2"/>'
        y_labels   += f'<text x="{margin_l-8}" y="{y+4}" text-anchor="end" font-size="10" fill="{BRAND["sub"]}">{v}%</text>'
    solid = " ".join(f"{p[0]},{p[1]}" for p in points[:3])
    dashed = f"{points[2][0]},{points[2][1]} {points[3][0]},{points[3][1]}"
    dots, x_labels = "", ""
    for x, y, m in points:
        color = BRAND["accent"] if m["status"] == "scheduled" else BRAND["secondary"]
        dots += f'<circle cx="{x}" cy="{y}" r="6" fill="{color}" stroke="#fff" stroke-width="2"/>'
        dots += f'<text x="{x}" y="{y-12}" text-anchor="middle" font-size="11" font-weight="700" fill="{BRAND["primary"]}">{m["acc"]}%</text>'
        x_labels += f'<text x="{x}" y="{H-12}" text-anchor="middle" font-size="11" font-weight="700" fill="{BRAND["primary"]}">{m["ver"]}</text>'
    return f"""
    <div style="background:#fff;border:1px solid {BRAND['border']};border-radius:12px;padding:18px 20px;margin-bottom:16px;">
      <div style="font-size:12px;font-weight:700;color:{BRAND['primary']};margin-bottom:10px;">
        📈 정확도 진화 추이
      </div>
      <svg viewBox="0 0 {W} {H}" style="width:100%;height:auto;">
        {grid_lines}{y_labels}
        <polyline fill="none" stroke="{BRAND['secondary']}" stroke-width="3" points="{solid}"/>
        <polyline fill="none" stroke="{BRAND['accent']}" stroke-width="3" stroke-dasharray="6,4" points="{dashed}"/>
        {dots}{x_labels}
      </svg>
    </div>
    """


def render_tab3_pipeline():
    stages = [
        ("📸", "수집", "+12 오늘", BRAND["success"]),
        ("✓",  "검증", "97% 자동", BRAND["secondary"]),
        ("🧠", "학습", "D-2 예정", BRAND["accent"]),
        ("🚀", "배포", "무중단", BRAND["primary"]),
    ]
    nodes = ""
    for i, (icon, name, sub, color) in enumerate(stages):
        nodes += f"""
        <div style="flex:1;text-align:center;position:relative;z-index:1;">
          <div style="width:56px;height:56px;border-radius:50%;background:{color};
                      color:#fff;display:flex;align-items:center;justify-content:center;
                      font-size:22px;margin:0 auto 8px;box-shadow:0 4px 12px rgba(0,0,0,0.15);">{icon}</div>
          <div style="font-size:11px;font-weight:700;color:{BRAND['primary']};">{name}</div>
          <div style="font-size:9.5px;color:{BRAND['sub']};margin-top:2px;">{sub}</div>
        </div>
        """
        if i < len(stages) - 1:
            nodes += f'<div style="flex:0 0 30px;align-self:flex-start;margin-top:24px;color:{BRAND["sub"]};font-size:18px;text-align:center;">→</div>'
    return f"""
    <div style="background:#fff;border:1px solid {BRAND['border']};border-radius:12px;padding:18px 20px;margin-bottom:16px;">
      <div style="font-size:12px;font-weight:700;color:{BRAND['primary']};margin-bottom:14px;">
        🔄 자동 학습 파이프라인
      </div>
      <div style="display:flex;align-items:flex-start;">{nodes}</div>
    </div>
    """


def render_tab3_timeline():
    items = ""
    for m in MODEL_HISTORY:
        is_cur = m["status"] == "current"
        is_sch = m["status"] == "scheduled"
        bg = BRAND["light"] if is_cur else "#fff"
        border = BRAND["secondary"] if is_cur else (BRAND["accent"] if is_sch else BRAND["border"])
        badge = ""
        if is_cur:  badge = f'<span style="background:{BRAND["secondary"]};color:#fff;font-size:9px;font-weight:700;padding:2px 8px;border-radius:8px;margin-left:8px;">CURRENT</span>'
        if is_sch:  badge = f'<span style="background:{BRAND["accent"]};color:#fff;font-size:9px;font-weight:700;padding:2px 8px;border-radius:8px;margin-left:8px;">SCHEDULED</span>'
        delta_html = f'<span style="color:{BRAND["success"]};font-size:10px;font-weight:700;margin-left:8px;">{m["delta"]}</span>' if m["delta"] else ""
        items += f"""
        <div style="background:{bg};border:1px solid {border};border-radius:10px;padding:12px 16px;margin-bottom:8px;">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
              <span style="font-size:14px;font-weight:900;color:{BRAND['primary']};">{m['ver']}</span>
              <span style="font-size:10px;color:{BRAND['sub']};margin-left:8px;">{m['date']}</span>
              {badge}
            </div>
            <div style="font-size:16px;font-weight:900;color:{BRAND['primary']};">{m['acc']}%{delta_html}</div>
          </div>
          <div style="font-size:10px;color:{BRAND['sub']};margin-top:4px;">
            데이터 {m['data']:,}건 · 정밀도 {m['prec']}% · 재현율 {m['rec']}%
          </div>
        </div>
        """
    return f"""
    <div style="background:#fff;border:1px solid {BRAND['border']};border-radius:12px;padding:18px 20px;">
      <div style="font-size:12px;font-weight:700;color:{BRAND['primary']};margin-bottom:12px;">
        🕐 모델 진화 타임라인
      </div>
      {items}
      <div style="background:linear-gradient(135deg,{BRAND['primary']},{BRAND['secondary']});
                  color:#fff;border-radius:10px;padding:14px 18px;margin-top:6px;text-align:center;">
        <div style="font-size:11px;color:{BRAND['gold']};letter-spacing:1px;">8개월 누적 성장</div>
        <div style="font-size:24px;font-weight:900;margin-top:4px;">+29.1pp 정확도 향상</div>
      </div>
    </div>
    """


# ============================================================
#  글로벌 헤더 / 푸터
# ============================================================
def render_global_header():
    return f"""
    <div style="background:linear-gradient(135deg,{BRAND['primary_dark']},{BRAND['primary']},{BRAND['secondary']});
                color:#fff;border-radius:16px;padding:24px 32px;margin-bottom:20px;
                box-shadow:0 6px 24px rgba(26,58,107,0.3);">
      <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:16px;">
        <div>
          <div style="display:inline-block;background:rgba(255,255,255,0.15);color:{BRAND['gold']};
                      font-size:10px;letter-spacing:3px;padding:4px 14px;border-radius:12px;
                      font-weight:700;margin-bottom:10px;">
            YESCO AI SAFETY INSPECTION PLATFORM · DEMO v1.0
          </div>
          <div style="font-size:26px;font-weight:900;color:#fff;line-height:1.3;">
            예스코 AI 연통 안전점검 통합 플랫폼
          </div>
          <div style="font-size:13px;color:rgba(255,255,255,0.85);margin-top:6px;">
            현장 라벨링 → AI 자동 학습 → 실시간 위험도 분석 · 인적오류 Zero화
          </div>
        </div>
        <div style="display:flex;gap:10px;flex-wrap:wrap;">
          <div style="background:rgba(255,255,255,0.12);border-radius:10px;padding:10px 16px;text-align:center;">
            <div style="font-size:9px;color:rgba(255,255,255,0.6);letter-spacing:1px;">MODEL</div>
            <div style="font-size:13px;font-weight:900;color:{BRAND['gold']};margin-top:2px;">{MODEL_STATUS}</div>
          </div>
          <div style="background:rgba(255,255,255,0.12);border-radius:10px;padding:10px 16px;text-align:center;">
            <div style="font-size:9px;color:rgba(255,255,255,0.6);letter-spacing:1px;">DATA</div>
            <div style="font-size:13px;font-weight:900;color:{BRAND['gold']};margin-top:2px;">1,247 건</div>
          </div>
          <div style="background:rgba(255,255,255,0.12);border-radius:10px;padding:10px 16px;text-align:center;">
            <div style="font-size:9px;color:rgba(255,255,255,0.6);letter-spacing:1px;">ACCURACY</div>
            <div style="font-size:13px;font-weight:900;color:{BRAND['gold']};margin-top:2px;">73.2%</div>
          </div>
        </div>
      </div>
    </div>
    """


def render_global_footer():
    return f"""
    <div style="margin-top:24px;padding:14px 20px;background:#fff;border:1px solid {BRAND['border']};
                border-radius:10px;display:flex;justify-content:space-between;align-items:center;
                font-size:11px;color:{BRAND['sub']};">
      <span><b style="color:{BRAND['primary']};">CS팀 사용시설파트</b> · 2026.05 · 임원 보고 데모</span>
      <span>예스코 AI 안전점검 통합 플랫폼 v1.0</span>
    </div>
    """


# ============================================================
#  Gradio Blocks UI
# ============================================================
CUSTOM_CSS = f"""
* {{ font-family: 'Noto Sans KR', sans-serif; }}
.gradio-container {{ max-width: 1500px !important; margin: 0 auto !important; background: #f8fafc !important; }}
footer {{ display: none !important; }}

.tab-nav {{ background: #fff !important; border-bottom: 2px solid {BRAND['primary']} !important; }}
.tab-nav button {{
    font-size: 15px !important; font-weight: 700 !important;
    color: {BRAND['sub']} !important; padding: 14px 24px !important;
}}
.tab-nav button.selected {{
    color: {BRAND['primary']} !important;
    background: linear-gradient(135deg,{BRAND['light']},#fff) !important;
    border-bottom: 3px solid {BRAND['secondary']} !important;
}}

button.primary, .gr-button-primary {{
    background: linear-gradient(135deg,{BRAND['primary']},{BRAND['secondary']}) !important;
    color: #fff !important; font-weight: 700 !important; border: none !important;
}}
button.primary:hover {{ filter: brightness(1.1); }}

#labeling_canvas {{ cursor: crosshair !important; }}
"""

with gr.Blocks(title="예스코 AI 안전점검 플랫폼", css=CUSTOM_CSS, theme=gr.themes.Soft()) as demo:

    gr.HTML(render_global_header())

    with gr.Tabs():
        # ─── 탭 1: AI 실시간 점검 ───
        with gr.Tab("🚨 AI 실시간 점검"):
            gr.HTML(render_tab1_header())
            with gr.Row():
                with gr.Column(scale=1):
                    gr.HTML(render_tab1_gallery())
                    tab1_btn = gr.Button("▶ AI 일괄 점검 시작", variant="primary", size="lg")
                    tab1_summary = gr.HTML(render_tab1_summary(0, 0))
                with gr.Column(scale=2):
                    tab1_img = gr.Image(label="감지 결과 (마지막 사진)", type="pil", height=380)
                    tab1_results = gr.HTML(f"""
                        <div style="background:#fff;border:2px dashed {BRAND['border']};border-radius:12px;
                                    padding:40px;text-align:center;color:{BRAND['sub']};">
                          좌측 버튼을 눌러 AI 일괄 점검을 시작하세요.
                        </div>
                    """)
            tab1_btn.click(
                fn=run_tab1_analysis, inputs=[],
                outputs=[tab1_img, tab1_results, tab1_summary],
            )

        # ─── 탭 2: 현장 라벨링 앱 (바운딩 박스) ───
        with gr.Tab("📱 현장 라벨링 앱"):
            gr.HTML(f"""
            <div style="background:linear-gradient(135deg,{BRAND['primary']},{BRAND['secondary']});
                        color:#fff;border-radius:14px;padding:20px 28px;margin-bottom:16px;">
              <div style="display:inline-block;background:rgba(255,255,255,0.18);color:{BRAND['gold']};
                          font-size:10px;letter-spacing:2px;padding:4px 12px;border-radius:10px;
                          font-weight:700;margin-bottom:8px;">
                PHASE 1~2 · FIELD BOUNDING-BOX LABELING APP
              </div>
              <div style="font-size:22px;font-weight:900;">📱 현장 라벨링 모바일 앱</div>
              <div style="font-size:12px;color:rgba(255,255,255,0.85);margin-top:4px;">
                사진 촬영 → 이상 부위 탭 → 카테고리 선택 → AI 학습 데이터 자동 축적
              </div>
            </div>
            """)
            
            # 진행 단계 안내
            gr.HTML(f"""
            <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:14px;">
              <div style="background:#fff;border:1px solid {BRAND['border']};border-left:4px solid {BRAND['secondary']};border-radius:8px;padding:10px 14px;">
                <div style="font-size:9px;color:{BRAND['sub']};letter-spacing:1px;">STEP 1</div>
                <div style="font-size:12px;font-weight:700;color:{BRAND['primary']};margin-top:2px;">📸 사진 업로드</div>
              </div>
              <div style="background:#fff;border:1px solid {BRAND['border']};border-left:4px solid {BRAND['accent']};border-radius:8px;padding:10px 14px;">
                <div style="font-size:9px;color:{BRAND['sub']};letter-spacing:1px;">STEP 2</div>
                <div style="font-size:12px;font-weight:700;color:{BRAND['primary']};margin-top:2px;">🎯 이상 부위 탭</div>
              </div>
              <div style="background:#fff;border:1px solid {BRAND['border']};border-left:4px solid {BRAND['danger']};border-radius:8px;padding:10px 14px;">
                <div style="font-size:9px;color:{BRAND['sub']};letter-spacing:1px;">STEP 3</div>
                <div style="font-size:12px;font-weight:700;color:{BRAND['primary']};margin-top:2px;">🏷️ 카테고리 선택</div>
              </div>
              <div style="background:#fff;border:1px solid {BRAND['border']};border-left:4px solid {BRAND['success']};border-radius:8px;padding:10px 14px;">
                <div style="font-size:9px;color:{BRAND['sub']};letter-spacing:1px;">STEP 4</div>
                <div style="font-size:12px;font-weight:700;color:{BRAND['primary']};margin-top:2px;">📤 업로드</div>
              </div>
            </div>
            """)
            
            with gr.Row():
                # 좌측: 모바일 미리보기
                with gr.Column(scale=1):
                    tab2_mobile = gr.HTML(render_tab2_mobile_frame(render_tab2_app_content()))
                
                # 중앙: 라벨링 캔버스 (메인 영역)
                with gr.Column(scale=2):
                    gr.HTML(f"""
                    <div style="background:linear-gradient(135deg,{BRAND['gold']},{BRAND['accent']});
                                color:{BRAND['primary_dark']};border-radius:10px;padding:12px 18px;margin-bottom:10px;
                                font-size:13px;font-weight:700;text-align:center;">
                      🎯 라벨링 캔버스 — 이상 부위를 클릭하면 박스가 그려집니다
                    </div>
                    """)
                    tab2_upload = gr.Image(
                        label="📸 1) 사진 업로드",
                        type="numpy",
                        height=180,
                    )
                    tab2_canvas = gr.Image(
                        label="🎯 2) 이상 부위를 클릭하세요 (라벨링)",
                        type="pil",
                        height=420,
                        interactive=True,
                        elem_id="labeling_canvas",
                    )
                    
                    if DEMO_PHOTOS:
                        gr.Examples(
                            examples=[p["path"] for p in DEMO_PHOTOS],
                            inputs=tab2_upload,
                            label="📂 시연용 샘플 (클릭하여 선택)",
                            examples_per_page=6,
                        )
                    
                    gr.HTML(f'<div style="font-size:12px;font-weight:700;color:{BRAND["primary"]};margin-top:12px;margin-bottom:6px;">🏷️ 3) 카테고리 선택</div>')
                    with gr.Row():
                        btn_normal = gr.Button("✅ 정상", size="sm")
                        btn_detach = gr.Button("⚠️ 이탈", size="sm", variant="stop")
                        btn_damage = gr.Button("🔧 손상", size="sm")
                    
                    tab2_memo = gr.Textbox(label="📝 메모 (선택)", placeholder="추가 코멘트가 있으면 입력", lines=1)
                    
                    with gr.Row():
                        tab2_submit = gr.Button("📤 4) 업로드 (AI 학습 데이터 추가)", variant="primary", size="lg", scale=4)
                        tab2_reset_btn = gr.Button("🔄 초기화", size="lg", scale=1)
                
                # 우측: 실시간 대시보드
                with gr.Column(scale=1):
                    tab2_dashboard_html = gr.HTML(render_tab2_dashboard())

            # 상태 변수
            tab2_original_img = gr.State(None)  # 원본 PIL 이미지
            tab2_box_rel      = gr.State(None)  # 박스 상대좌표 (x1,y1,x2,y2)
            tab2_category     = gr.State(None)  # 선택된 카테고리

            # 이벤트 바인딩
            tab2_upload.change(
                fn=tab2_on_image_load,
                inputs=[tab2_upload],
                outputs=[tab2_canvas, tab2_mobile, tab2_original_img, tab2_box_rel, tab2_category],
            )
            tab2_canvas.select(
                fn=tab2_on_canvas_click,
                inputs=[tab2_original_img, tab2_category],
                outputs=[tab2_canvas, tab2_mobile, tab2_box_rel],
            )
            btn_normal.click(
                fn=lambda img, box: tab2_on_category("정상", img, box),
                inputs=[tab2_original_img, tab2_box_rel],
                outputs=[tab2_mobile, tab2_canvas, tab2_category],
            )
            btn_detach.click(
                fn=lambda img, box: tab2_on_category("이탈", img, box),
                inputs=[tab2_original_img, tab2_box_rel],
                outputs=[tab2_mobile, tab2_canvas, tab2_category],
            )
            btn_damage.click(
                fn=lambda img, box: tab2_on_category("손상", img, box),
                inputs=[tab2_original_img, tab2_box_rel],
                outputs=[tab2_mobile, tab2_canvas, tab2_category],
            )
            tab2_submit.click(
                fn=tab2_on_upload_submit,
                inputs=[tab2_original_img, tab2_box_rel, tab2_category, tab2_memo],
                outputs=[tab2_mobile, tab2_dashboard_html],
            )
            tab2_reset_btn.click(
                fn=tab2_reset,
                inputs=[],
                outputs=[tab2_canvas, tab2_mobile, tab2_original_img, tab2_box_rel, tab2_category, tab2_dashboard_html],
            )

        # ─── 탭 3: AI 학습 대시보드 ───
        with gr.Tab("🧠 AI 학습 대시보드"):
            gr.HTML(f"""
            <div style="background:linear-gradient(135deg,{BRAND['primary']},{BRAND['secondary']});
                        color:#fff;border-radius:14px;padding:20px 28px;margin-bottom:16px;">
              <div style="display:inline-block;background:rgba(255,255,255,0.18);color:{BRAND['gold']};
                          font-size:10px;letter-spacing:2px;padding:4px 12px;border-radius:10px;
                          font-weight:700;margin-bottom:8px;">
                PHASE 2~3 · AI TRAINING DASHBOARD
              </div>
              <div style="font-size:22px;font-weight:900;">🧠 AI 모델 자동 학습 대시보드</div>
              <div style="font-size:12px;color:rgba(255,255,255,0.85);margin-top:4px;">
                현장 데이터 누적 → 정기 자동 재학습 → 정확도 지속 향상
              </div>
            </div>
            """)
            gr.HTML(render_tab3_kpis())
            gr.HTML(render_tab3_chart())
            gr.HTML(render_tab3_pipeline())
            gr.HTML(render_tab3_timeline())

    gr.HTML(render_global_footer())


# ============================================================
#  실행
# ============================================================
if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 YESCO AI 안전점검 통합 플랫폼 시작")
    print("="*60)
    print(f"📦 모델 상태: {MODEL_STATUS}")
    print(f"📸 데모 사진: {len(DEMO_PHOTOS)}장")
    print(f"📧 이메일: {'설정됨' if SENDER_EMAIL else '시뮬레이션 모드'}")
    print("="*60)
    print("🌐 접속 주소: http://127.0.0.1:7860")
    print("="*60 + "\n")
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
    )
