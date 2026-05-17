"""
예스코 AI 백업 검사 시스템 - 화면 ③
임원 보고 데모 v1.0

스토리: "코디가 '정상'으로 분류한 사진을 AI가 다시 한번 검토하여
        인적 오류로 인한 안전 사고를 예방한다"
"""

import gradio as gr
import os
import smtplib
import base64
import time
from io import BytesIO
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from PIL import Image, ImageDraw, ImageFont

# ============================================================
# 🔧 설정
# ============================================================

# 시뮬레이션: 이 사진에서만 AI가 이상을 감지함
TRAP_IMAGES = ["defect_01", "defect_02", "defect_03"]

# 이메일 설정 (환경변수에서 가져옴, 없으면 발송 스킵)
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL", "c600595@lsyesco.co.kr")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# 시연용 사진 6장과 메타데이터
DEMO_PHOTOS = [
    {"path": "examples/normal_01.jpg", "location": "강남지점 #047", "time": "09:15"},
    {"path": "examples/normal_02.jpg", "location": "송파지점 #102", "time": "10:22"},
    {"path": "examples/defect_01.jpg", "location": "강서지점 #018", "time": "11:05"},  # ⚠ 함정
    {"path": "examples/normal_03.jpg", "location": "마포지점 #073", "time": "13:40"},
    {"path": "examples/defect_02.jpg", "location": "용산지점 #221", "time": "14:55"},
    {"path": "examples/defect_03.jpg", "location": "서초지점 #156", "time": "16:10"},
]

# 박스 좌표 (화면 ①과 동일)
DEMO_BOXES = {
    "defect_01": {"x": 0.55, "y": 0.25, "w": 0.30, "h": 0.30, "label": "연통 이탈"},
    "defect_02": {"x": 0.50, "y": 0.30, "w": 0.35, "h": 0.25, "label": "연통 이탈"},
    "defect_03": {"x": 0.60, "y": 0.20, "w": 0.25, "h": 0.35, "label": "연통 이탈"},
}

BRAND = {
    "primary": "#0057A0",
    "primary_dark": "#003D73",
    "primary_light": "#E8F1FB",
    "success": "#10B981",
    "danger": "#EF4444",
    "warning": "#F59E0B",
}

# ============================================================
# 🖼️ 이미지 유틸
# ============================================================

def image_to_base64(image, max_size=400, quality=80):
    """PIL 이미지를 base64 문자열로 (HTML 임베드용)"""
    if image is None:
        return ""
    img = image.copy().convert("RGB")
    img.thumbnail((max_size, max_size))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return base64.b64encode(buf.getvalue()).decode()

def file_to_base64(path, max_size=400, quality=80):
    """파일 경로 → base64"""
    if not os.path.exists(path):
        return None
    img = Image.open(path)
    return image_to_base64(img, max_size, quality)

def draw_detection_box(image, box_info, color=(239, 68, 68)):
    """탐지 박스 그리기 (화면 ①과 동일 스타일)"""
    if image is None or box_info is None:
        return image
    img = image.copy().convert("RGB")
    W, H = img.size
    
    x1 = int(box_info["x"] * W)
    y1 = int(box_info["y"] * H)
    x2 = int((box_info["x"] + box_info["w"]) * W)
    y2 = int((box_info["y"] + box_info["h"]) * H)
    
    draw = ImageDraw.Draw(img, "RGBA")
    draw.rectangle([x1, y1, x2, y2], fill=color + (50,))
    
    for i in range(4):
        draw.rectangle([x1-i, y1-i, x2+i, y2+i], outline=color, width=1)
    
    corner_len = min(40, (x2-x1)//4)
    cw = 6
    for cx, cy, dx, dy in [(x1, y1, 1, 1), (x2, y1, -1, 1), (x1, y2, 1, -1), (x2, y2, -1, -1)]:
        draw.rectangle([cx if dx>0 else cx-corner_len, cy if dy>0 else cy-cw, 
                       cx+corner_len if dx>0 else cx, cy+cw if dy>0 else cy], fill=color)
        draw.rectangle([cx if dx>0 else cx-cw, cy if dy>0 else cy-corner_len,
                       cx+cw if dx>0 else cx, cy+corner_len if dy>0 else cy], fill=color)
    
    try:
        font = ImageFont.truetype("malgun.ttf", 24)
    except:
        try:
            font = ImageFont.truetype("arial.ttf", 24)
        except:
            font = ImageFont.load_default()
    
    label = box_info.get("label", "")
    if label:
        bbox = draw.textbbox((0, 0), label, font=font)
        lw = bbox[2] - bbox[0] + 18
        lh = bbox[3] - bbox[1] + 12
        draw.rectangle([x1, y1 - lh, x1 + lw, y1], fill=color)
        draw.text((x1 + 9, y1 - lh + 5), label, fill="white", font=font)
    
    return img

# ============================================================
# 📧 이메일 발송
# ============================================================

def send_alert_email(image_with_box, photo_info, confidence):
    """이상 감지 시 담당자에게 메일 발송"""
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        return False, "이메일 미설정 (환경변수 확인)"
    
    try:
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = RECEIVER_EMAIL
        msg["Subject"] = f"[예스코 AI] 🚨 인적 오류 백업 검사 - 이상 감지 ({photo_info['location']})"
        
        body = f"""
        <html><body style="font-family:'Malgun Gothic',sans-serif;background:#F3F4F6;padding:20px;">
            <div style="max-width:600px;margin:auto;background:white;border-radius:12px;overflow:hidden;
                        box-shadow:0 4px 12px rgba(0,0,0,0.08);">
                <div style="background:linear-gradient(135deg,#0057A0,#003D73);padding:24px;color:white;">
                    <h1 style="margin:0;font-size:22px;">🛡️ AI 백업 검사 알림</h1>
                    <p style="margin:6px 0 0;opacity:0.9;font-size:13px;">코디 보고에서 누락된 이상을 AI가 발견했습니다</p>
                </div>
                <div style="padding:24px;">
                    <div style="background:#FEF2F2;border-left:4px solid #EF4444;padding:14px;border-radius:6px;margin-bottom:16px;">
                        <strong style="color:#991B1B;font-size:15px;">⚠️ 인적 오류 가능성 감지</strong>
                        <p style="margin:6px 0 0;color:#7F1D1D;font-size:13px;">
                            현장 점검자가 '정상'으로 보고했으나, AI는 연통 이탈 징후를 감지했습니다.
                        </p>
                    </div>
                    <table style="width:100%;border-collapse:collapse;">
                        <tr><td style="padding:8px 0;color:#6B7280;width:130px;">감지 일시</td>
                            <td style="padding:8px 0;font-weight:600;">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td></tr>
                        <tr><td style="padding:8px 0;color:#6B7280;">현장 위치</td>
                            <td style="padding:8px 0;font-weight:600;">{photo_info['location']}</td></tr>
                        <tr><td style="padding:8px 0;color:#6B7280;">현장 점검 시각</td>
                            <td style="padding:8px 0;">{photo_info['time']}</td></tr>
                        <tr><td style="padding:8px 0;color:#6B7280;">AI 신뢰도</td>
                            <td style="padding:8px 0;color:#EF4444;font-weight:700;">{confidence}%</td></tr>
                        <tr><td style="padding:8px 0;color:#6B7280;">조치 권고</td>
                            <td style="padding:8px 0;color:#991B1B;font-weight:600;">즉시 현장 재방문 점검 필요</td></tr>
                    </table>
                </div>
                <div style="padding:14px;background:#F9FAFB;text-align:center;color:#9CA3AF;font-size:11px;">
                    본 메일은 예스코 AI 백업 검사 시스템에서 자동 발송되었습니다.
                </div>
            </div>
        </body></html>
        """
        msg.attach(MIMEText(body, "html"))
        
        if image_with_box:
            buf = BytesIO()
            img_send = image_with_box.convert("RGB") if image_with_box.mode != "RGB" else image_with_box
            img_send.save(buf, format="JPEG", quality=75)
            attachment = MIMEImage(buf.getvalue(), name=f"detection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
            msg.attach(attachment)
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        
        return True, "이메일 발송 완료"
    except Exception as e:
        return False, f"이메일 발송 실패: {str(e)}"

# ============================================================
# 🎨 화면 렌더링
# ============================================================

def render_photo_grid(highlighted_idx=None, analyzing=False, found_idx=None):
    """6장 사진 그리드"""
    cards = ""
    for idx, photo in enumerate(DEMO_PHOTOS):
        b64 = file_to_base64(photo["path"], max_size=300)
        if not b64:
            img_html = f"""<div style="background:#E5E7EB;height:120px;display:flex;
                          align-items:center;justify-content:center;color:#9CA3AF;font-size:12px;">
                          이미지 없음<br>{photo['path']}</div>"""
        else:
            img_html = f'<img src="data:image/jpeg;base64,{b64}" style="width:100%;height:120px;object-fit:cover;display:block;">'
        
        # 상태별 스타일
        border = "1px solid #E5E7EB"
        overlay = ""
        badge = f'<div style="position:absolute;top:6px;right:6px;background:rgba(16,185,129,0.95);color:white;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:700;">정상보고</div>'
        
        if analyzing and (highlighted_idx is None or idx <= highlighted_idx):
            border = f"2px solid {BRAND['primary']}"
            overlay = f"""<div style="position:absolute;top:0;left:0;right:0;bottom:0;
                        background:rgba(0,87,160,0.15);display:flex;align-items:center;justify-content:center;">
                        <div style="background:white;padding:4px 10px;border-radius:12px;
                        font-size:11px;color:{BRAND['primary']};font-weight:700;">✓ 분석완료</div></div>"""
        
        if found_idx is not None and idx == found_idx:
            border = f"3px solid {BRAND['danger']}"
            overlay = f"""<div style="position:absolute;top:0;left:0;right:0;bottom:0;
                        background:rgba(239,68,68,0.25);display:flex;align-items:center;justify-content:center;">
                        <div style="background:{BRAND['danger']};color:white;padding:6px 14px;border-radius:20px;
                        font-size:13px;font-weight:800;box-shadow:0 4px 12px rgba(239,68,68,0.4);">
                        ⚠️ 이상 감지!</div></div>"""
            badge = f'<div style="position:absolute;top:6px;right:6px;background:{BRAND["danger"]};color:white;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:700;">AI 재검토</div>'
        
        cards += f"""
        <div style="position:relative;border-radius:10px;overflow:hidden;border:{border};
                    box-shadow:0 2px 8px rgba(0,0,0,0.05);background:white;transition:all 0.3s;">
            {img_html}
            {badge}
            {overlay}
            <div style="padding:8px 10px;background:white;">
                <div style="font-size:11px;font-weight:700;color:#374151;">{photo['location']}</div>
                <div style="font-size:10px;color:#9CA3AF;margin-top:1px;">🕐 {photo['time']}</div>
            </div>
        </div>
        """
    
    return f"""
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;">
        {cards}
    </div>
    """

def render_inspector_card():
    """점검자 보고서 헤더"""
    return f"""
    <div style="background:white;border-radius:14px;padding:18px 22px;border:1px solid #E5E7EB;
                box-shadow:0 2px 10px rgba(0,0,0,0.04);margin-bottom:14px;">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
            <div style="display:flex;align-items:center;gap:14px;">
                <div style="width:48px;height:48px;border-radius:50%;background:linear-gradient(135deg,{BRAND['primary']},{BRAND['primary_dark']});
                            display:flex;align-items:center;justify-content:center;color:white;font-weight:700;font-size:18px;">
                    김코
                </div>
                <div>
                    <div style="font-size:15px;font-weight:700;color:#111827;">김코디 점검자 · 강남권역</div>
                    <div style="font-size:12px;color:#6B7280;margin-top:2px;">📅 {datetime.now().strftime('%Y년 %m월 %d일')} 점검 보고</div>
                </div>
            </div>
            <div style="display:flex;gap:18px;">
                <div style="text-align:center;">
                    <div style="font-size:11px;color:#6B7280;font-weight:600;">점검 완료</div>
                    <div style="font-size:22px;font-weight:800;color:{BRAND['primary']};">{len(DEMO_PHOTOS)}</div>
                </div>
                <div style="text-align:center;">
                    <div style="font-size:11px;color:#6B7280;font-weight:600;">정상 보고</div>
                    <div style="font-size:22px;font-weight:800;color:{BRAND['success']};">{len(DEMO_PHOTOS)}</div>
                </div>
                <div style="text-align:center;">
                    <div style="font-size:11px;color:#6B7280;font-weight:600;">이상 보고</div>
                    <div style="font-size:22px;font-weight:800;color:#9CA3AF;">0</div>
                </div>
            </div>
        </div>
    </div>
    """

def render_initial_result():
    return f"""
    <div style="background:white;border-radius:14px;padding:30px;text-align:center;
                border:2px dashed #D1D5DB;color:#9CA3AF;">
        <div style="font-size:36px;margin-bottom:8px;">🤖</div>
        <div style="font-size:14px;font-weight:600;color:#6B7280;">AI 백업 검사 대기 중</div>
        <div style="font-size:12px;margin-top:4px;">'AI 백업 검사 시작' 버튼을 클릭하세요</div>
    </div>
    """

def render_analyzing_status(progress, current_idx):
    return f"""
    <div style="background:white;border-radius:14px;padding:24px;border:1px solid #E5E7EB;
                box-shadow:0 2px 10px rgba(0,0,0,0.04);">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;">
            <div style="width:40px;height:40px;border-radius:10px;background:{BRAND['primary_light']};
                        display:flex;align-items:center;justify-content:center;font-size:20px;">🤖</div>
            <div>
                <div style="font-size:15px;font-weight:700;color:#111827;">AI 분석 진행 중...</div>
                <div style="font-size:12px;color:#6B7280;">사진 {current_idx+1}/{len(DEMO_PHOTOS)} 검토 중</div>
            </div>
        </div>
        <div style="background:#F3F4F6;border-radius:999px;height:10px;overflow:hidden;">
            <div style="background:linear-gradient(90deg,{BRAND['primary']},{BRAND['primary_dark']});
                        width:{progress}%;height:100%;border-radius:999px;transition:width 0.3s;
                        box-shadow:0 0 10px {BRAND['primary']}66;"></div>
        </div>
        <div style="text-align:center;font-size:12px;color:#6B7280;margin-top:8px;font-weight:600;">
            {progress}% 완료
        </div>
    </div>
    """

def render_detection_result(found_photo, found_idx, confidence, email_status):
    """이상 감지 결과 카드"""
    # 박스 그린 이미지
    fname_key = os.path.splitext(os.path.basename(found_photo["path"]))[0]
    box = DEMO_BOXES.get(fname_key, {"x": 0.4, "y": 0.3, "w": 0.3, "h": 0.3, "label": "연통 이탈"})
    
    if os.path.exists(found_photo["path"]):
        img = Image.open(found_photo["path"])
        img_with_box = draw_detection_box(img, box)
        b64 = image_to_base64(img_with_box, max_size=500, quality=85)
        img_html = f'<img src="data:image/jpeg;base64,{b64}" style="width:100%;border-radius:10px;display:block;">'
    else:
        img_html = '<div style="background:#E5E7EB;height:200px;border-radius:10px;"></div>'
    
    email_icon = "✅" if email_status[0] else "⚠️"
    email_color = BRAND["success"] if email_status[0] else BRAND["warning"]
    
    ticket_no = f"TK-{datetime.now().strftime('%Y%m%d')}-{found_idx+1:04d}"
    
    return f"""
    <div style="background:white;border-radius:14px;padding:22px;border:1px solid #E5E7EB;
                box-shadow:0 4px 16px rgba(0,0,0,0.06);">
        <div style="background:linear-gradient(135deg,#FEF2F2,#FEE2E2);border-radius:10px;padding:14px;margin-bottom:16px;">
            <div style="display:flex;align-items:center;gap:10px;">
                <div style="font-size:28px;">🚨</div>
                <div>
                    <div style="font-size:18px;font-weight:800;color:#991B1B;">
                        {len(DEMO_PHOTOS)}건 중 <span style="font-size:24px;">1건</span>에서 이상 감지!
                    </div>
                    <div style="font-size:12px;color:#7F1D1D;margin-top:2px;">
                        현장 점검자가 누락한 이상을 AI가 발견했습니다
                    </div>
                </div>
            </div>
        </div>
        
        {img_html}
        
        <div style="margin-top:14px;display:grid;grid-template-columns:1fr 1fr;gap:10px;">
            <div style="padding:10px;background:#F9FAFB;border-radius:8px;">
                <div style="font-size:10px;color:#6B7280;font-weight:700;letter-spacing:0.5px;">감지 클래스</div>
                <div style="font-size:14px;font-weight:700;color:{BRAND['danger']};margin-top:2px;">연통 이탈</div>
            </div>
            <div style="padding:10px;background:#F9FAFB;border-radius:8px;">
                <div style="font-size:10px;color:#6B7280;font-weight:700;letter-spacing:0.5px;">AI 신뢰도</div>
                <div style="font-size:14px;font-weight:700;color:{BRAND['danger']};margin-top:2px;">{confidence}%</div>
            </div>
            <div style="padding:10px;background:#F9FAFB;border-radius:8px;">
                <div style="font-size:10px;color:#6B7280;font-weight:700;letter-spacing:0.5px;">현장 위치</div>
                <div style="font-size:14px;font-weight:700;color:#374151;margin-top:2px;">{found_photo['location']}</div>
            </div>
            <div style="padding:10px;background:#F9FAFB;border-radius:8px;">
                <div style="font-size:10px;color:#6B7280;font-weight:700;letter-spacing:0.5px;">점검자 보고</div>
                <div style="font-size:14px;font-weight:700;color:{BRAND['warning']};margin-top:2px;">정상으로 보고</div>
            </div>
        </div>
        
        <div style="margin-top:14px;padding:14px;background:linear-gradient(135deg,#ECFDF5,#D1FAE5);border-radius:10px;">
            <div style="font-size:12px;font-weight:700;color:#065F46;margin-bottom:8px;">⚡ 자동 조치 수행 완료</div>
            <div style="display:flex;flex-direction:column;gap:6px;">
                <div style="display:flex;align-items:center;gap:8px;font-size:13px;color:#047857;">
                    <span style="color:{email_color};font-weight:700;">{email_icon}</span>
                    <span><b>담당자 이메일 발송</b> · {email_status[1]}</span>
                </div>
                <div style="display:flex;align-items:center;gap:8px;font-size:13px;color:#047857;">
                    <span style="color:{BRAND['success']};font-weight:700;">✅</span>
                    <span><b>재점검 티켓 자동 생성</b> · #{ticket_no}</span>
                </div>
                <div style="display:flex;align-items:center;gap:8px;font-size:13px;color:#047857;">
                    <span style="color:{BRAND['success']};font-weight:700;">✅</span>
                    <span><b>AI 학습 데이터에 추가</b> · 다음 재학습 반영</span>
                </div>
            </div>
        </div>
    </div>
    """

def render_phase2_preview():
    """Phase 2 실시간 어드바이스 미리보기"""
    # 첫 번째 defect 이미지로 박스 그린 시뮬레이션
    sample_path = "examples/defect_01.jpg"
    if os.path.exists(sample_path):
        img = Image.open(sample_path)
        box = DEMO_BOXES.get("defect_01", {"x": 0.55, "y": 0.25, "w": 0.30, "h": 0.30, "label": "연통 이탈 의심"})
        img_with_box = draw_detection_box(img, box)
        b64 = image_to_base64(img_with_box, max_size=350, quality=80)
        camera_view = f'<img src="data:image/jpeg;base64,{b64}" style="width:100%;display:block;">'
    else:
        camera_view = '<div style="background:#1a1a1a;height:280px;display:flex;align-items:center;justify-content:center;color:white;font-size:13px;">카메라 시뮬레이션 영역</div>'
    
    return f"""
    <div style="background:linear-gradient(135deg,#1e293b,#0f172a);border-radius:16px;padding:24px;
                color:white;box-shadow:0 8px 24px rgba(0,0,0,0.2);">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
            <div>
                <div style="font-size:11px;letter-spacing:1.5px;opacity:0.7;font-weight:600;">PHASE 2 · COMING SOON</div>
                <div style="font-size:20px;font-weight:800;margin-top:4px;">🔮 실시간 카메라 어드바이스</div>
                <div style="font-size:12px;opacity:0.7;margin-top:4px;">현장에서 사진 찍는 순간, AI가 즉시 이상을 알려줍니다</div>
            </div>
            <div style="background:rgba(239,68,68,0.2);color:#FCA5A5;padding:6px 12px;border-radius:8px;
                        font-size:11px;font-weight:700;letter-spacing:0.5px;animation:pulse 2s infinite;">
                ● LIVE PREVIEW
            </div>
        </div>
        
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:18px;align-items:center;">
            <!-- 카메라 뷰 -->
            <div style="position:relative;border-radius:12px;overflow:hidden;background:#000;
                        border:3px solid rgba(239,68,68,0.5);box-shadow:0 0 20px rgba(239,68,68,0.3);">
                {camera_view}
                <div style="position:absolute;top:10px;left:10px;background:rgba(0,0,0,0.6);color:white;
                            padding:4px 10px;border-radius:6px;font-size:11px;backdrop-filter:blur(10px);">
                    📹 LIVE · 1080p
                </div>
                <div style="position:absolute;bottom:10px;right:10px;background:rgba(239,68,68,0.9);color:white;
                            padding:6px 12px;border-radius:8px;font-size:12px;font-weight:700;">
                    ⚠️ 이탈 감지 87%
                </div>
            </div>
            
            <!-- 안내 메시지 -->
            <div>
                <div style="background:rgba(239,68,68,0.15);border-left:3px solid #EF4444;
                            padding:14px;border-radius:8px;margin-bottom:12px;">
                    <div style="font-size:14px;font-weight:800;color:#FCA5A5;">📢 AI 실시간 알림</div>
                    <div style="font-size:13px;color:#FECACA;margin-top:6px;line-height:1.5;">
                        "연통 상부에서 이탈 징후가 감지되었습니다. 
                        가까이서 한 번 더 촬영해주세요."
                    </div>
                </div>
                
                <div style="display:flex;flex-direction:column;gap:8px;">
                    <div style="display:flex;align-items:center;gap:8px;font-size:12px;opacity:0.85;">
                        <span style="color:#34D399;">✓</span> 촬영과 동시에 분석
                    </div>
                    <div style="display:flex;align-items:center;gap:8px;font-size:12px;opacity:0.85;">
                        <span style="color:#34D399;">✓</span> 음성 안내 지원
                    </div>
                    <div style="display:flex;align-items:center;gap:8px;font-size:12px;opacity:0.85;">
                        <span style="color:#34D399;">✓</span> 오프라인 작동 (Edge AI)
                    </div>
                    <div style="display:flex;align-items:center;gap:8px;font-size:12px;opacity:0.85;">
                        <span style="color:#34D399;">✓</span> 점검 누락 ZERO
                    </div>
                </div>
            </div>
        </div>
        
        <div style="margin-top:18px;padding:12px;background:rgba(255,255,255,0.05);border-radius:10px;
                    text-align:center;font-size:12px;opacity:0.8;">
            💡 <b>예상 출시:</b> 2026년 3분기 · 모바일 앱 통합 배포
        </div>
    </div>
    
    <style>
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}
    </style>
    """

# ============================================================
# 🔄 핸들러
# ============================================================

def start_ai_inspection():
    """AI 백업 검사 시작 - 진행 시뮬레이션 + 결과"""
    # 단계별로 yield해서 실시간 진행 효과
    
    # 1단계: 분석 시작
    for i in range(len(DEMO_PHOTOS)):
        progress = int((i+1) / len(DEMO_PHOTOS) * 100)
        grid = render_photo_grid(highlighted_idx=i, analyzing=True)
        status = render_analyzing_status(progress, i)
        yield grid, status
        time.sleep(0.6)  # 시연 효과
    
    # 2단계: 함정 사진 찾기
    found_idx = None
    found_photo = None
    for idx, photo in enumerate(DEMO_PHOTOS):
        fname_key = os.path.splitext(os.path.basename(photo["path"]))[0]
        if fname_key in TRAP_IMAGES:
            found_idx = idx
            found_photo = photo
            break
    
    if found_idx is None:
        # 함정 사진 없으면 그냥 정상
        yield render_photo_grid(analyzing=True, highlighted_idx=len(DEMO_PHOTOS)-1), f"""
        <div style="background:#ECFDF5;border-radius:12px;padding:20px;text-align:center;">
            <div style="font-size:36px;">✅</div>
            <div style="font-size:16px;font-weight:700;color:#065F46;margin-top:6px;">전체 정상</div>
            <div style="font-size:12px;color:#047857;margin-top:4px;">{len(DEMO_PHOTOS)}장 모두 정상으로 확인됨</div>
        </div>
        """
        return
    
    # 3단계: 이상 감지 표시
    grid = render_photo_grid(analyzing=True, found_idx=found_idx, highlighted_idx=len(DEMO_PHOTOS)-1)
    
    # 4단계: 이메일 발송
    fname_key = os.path.splitext(os.path.basename(found_photo["path"]))[0]
    box = DEMO_BOXES.get(fname_key, {"x": 0.4, "y": 0.3, "w": 0.3, "h": 0.3, "label": "연통 이탈"})
    img = Image.open(found_photo["path"])
    img_with_box = draw_detection_box(img, box)
    confidence = 87
    
    email_status = send_alert_email(img_with_box, found_photo, confidence)
    
    # 5단계: 최종 결과
    result_html = render_detection_result(found_photo, found_idx, confidence, email_status)
    yield grid, result_html

def reset_inspection():
    return render_photo_grid(), render_initial_result()

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
.section-title {{
    color: {BRAND['primary_dark']};
    font-weight: 800;
    font-size: 14px;
    letter-spacing: 0.5px;
    margin: 14px 0 8px;
}}
button.primary {{
    background: linear-gradient(135deg, {BRAND['primary']}, {BRAND['primary_dark']}) !important;
    border: none !important;
    font-weight: 700 !important;
}}
"""

with gr.Blocks(title="AI 백업 검사 시스템", css=custom_css, theme=gr.themes.Soft(
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
                    🛡️ AI 백업 검사 시스템
                </h1>
                <p style="margin:0;opacity:0.85;font-size:13px;">
                    현장 점검자가 놓친 이상을 AI가 발견하여 인적 오류로 인한 안전 사고를 예방합니다
                </p>
            </div>
            <div style="text-align:right;">
                <div style="background:rgba(255,255,255,0.18);padding:6px 14px;border-radius:8px;
                            font-size:11px;font-weight:600;display:inline-block;">
                    🟢 DEMO MODE
                </div>
                <div style="margin-top:6px;font-size:11px;opacity:0.7;">Backup Inspection v1.0</div>
            </div>
        </div>
    </div>
    """)
    
    # 점검자 보고서
    gr.HTML(render_inspector_card())
    
    with gr.Row():
        with gr.Column(scale=6):
            gr.HTML('<div class="section-title">📋 점검자가 보고한 사진 (전체 정상 보고)</div>')
            photo_grid = gr.HTML(render_photo_grid())
            
            with gr.Row():
                start_btn = gr.Button("🤖 AI 백업 검사 시작", variant="primary", size="lg", scale=3)
                reset_btn = gr.Button("🔄 초기화", size="lg", scale=1)
        
        with gr.Column(scale=5):
            gr.HTML('<div class="section-title">🔍 AI 분석 결과</div>')
            result_panel = gr.HTML(render_initial_result())
    
    # Phase 2 미리보기
    gr.HTML('<div class="section-title" style="margin-top:24px;">🔮 다음 단계: 실시간 어드바이스 (개발 중)</div>')
    gr.HTML(render_phase2_preview())
    
    # 푸터
    gr.HTML(f"""
    <div style="margin-top:20px;padding:18px;background:white;border-radius:12px;
                border:1px solid #E5E7EB;text-align:center;">
        <div style="font-size:12px;color:#6B7280;line-height:1.7;">
            💡 <b>시연 흐름:</b> 
            ① 코디 정상 보고 확인 → ② AI 백업 검사 시작 → ③ 누락된 이상 감지 → ④ 자동 메일 + 티켓 생성
        </div>
        <div style="font-size:11px;color:#9CA3AF;margin-top:8px;">
            © 2026 YESCO AI Safety Platform · Backup Inspection Demo v1.0
        </div>
    </div>
    """)
    
    # 이벤트
    start_btn.click(
        fn=start_ai_inspection,
        outputs=[photo_grid, result_panel],
    )
    
    reset_btn.click(
        fn=reset_inspection,
        outputs=[photo_grid, result_panel],
    )

if __name__ == "__main__":
    print("=" * 60)
    print("🛡️ 예스코 AI 백업 검사 시스템 v1.0")
    print("=" * 60)
    print("📡 http://127.0.0.1:7861 에서 접속하세요")
    print("=" * 60)
    demo.launch(server_name="0.0.0.0", server_port=7861, share=False)
