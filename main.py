import os
import requests
import feedparser
from google import genai

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
LINE_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_USER_ID = os.environ.get('LINE_USER_ID')

# เชื่อมต่อกับ Gemini API
client = genai.Client(api_key=GEMINI_API_KEY)

# แหล่งข้อมูลข่าว (RSS Feeds) ที่ครอบคลุมทั้งหุ้น คริปโต ทองคำ น้ำมัน และอัตราแลกเปลี่ยน
rss_feeds = {
    "US_Macro_and_Forex": "https://finance.yahoo.com/news/rssindex", # ข่าวเศรษฐกิจโลก อัตราแลกเปลี่ยน และน้ำมัน
    "Crypto": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Thai_Business": "https://www.thansettakij.com/rss/finance",
    "Gold_and_Commodities": "https://www.kitco.com/rss/source/kitco-news-all.xml"
}

print("กำลังดึงข้อมูลข่าว...")
news_data = ""
for category, url in rss_feeds.items():
    try:
        feed = feedparser.parse(url)
        news_data += f"\n--- {category} ---\n"
        for entry in feed.entries[:6]: # ดึง 6 ข่าวล่าสุดต่อหมวดเพื่อให้ครอบคลุมน้ำมันและดอลลาร์
            news_data += f"- {entry.title}\n"
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการดึง {category}: {e}")

print("กำลังส่งให้ AI สรุป...")
prompt = f"""
คุณคือนักวิเคราะห์การลงทุนมืออาชีพ สรุปข่าวการลงทุนรายวันจากข้อมูลที่ให้มาให้อ่านง่าย กระชับ เหมาะกับการอ่านบน LINE โดยแบ่งเป็นหมวดหมู่ดังนี้:

1. 🇺🇸 หุ้น US (สรุปภาพรวมตลาด, Sector เด่น, หุ้นหรือกลุ่ม ETF ที่น่าสนใจ)
2. 🇹🇭 หุ้นไทย (ประเด็นหลักที่กระทบตลาดวันนี้, กลุ่มอุตสาหกรรมที่เป็นกระแส)
3. 🥇 ทองคำ และ 🛢️ น้ำมัน (ทิศทางราคาล่าสุด ปัจจัยหลักที่ขับเคลื่อนราคาพลังงานและโลหะมีค่า)
4. ₿ คริปโตเคอร์เรนซี (ภาพรวมเหรียญหลัก และแนวโน้มที่น่าสนใจ)
5. 💵 ค่าเงินดอลลาร์ และ 🌍 เศรษฐกิจมหภาค (อัปเดตดัชนีดอลลาร์ ดอกเบี้ย นโยบายการเงิน และอสังหาริมทรัพย์ เน้น US, Asia, ไทย)

กฎในการสรุป:
- ใช้รูปแบบ Bullet points (-) เพื่อความรวดเร็วในการอ่าน
- **เน้นตัวหนา** ที่ชื่อหุ้น ตัวเลขสำคัญ ดัชนีค่าเงิน หรือทิศทางราคา (เช่น **พุ่งขึ้น**, **ดิ่งลง**)
- หากหัวข้อไหนไม่มีประเด็นสำคัญในรอบวัน ให้เขียนว่า "ไม่มีประเด็นสำคัญในรอบวัน"
- สรุปเฉพาะความจริงจากข้อมูล ห้ามแต่งเติมตัวเลขเองเด็ดขาด

ข้อมูลข่าวสำหรับวันนี้:
{news_data}
"""

try:
    # ใช้โมเดล gemini-3.5-flash ตามต้องการ
    response = client.models.generate_content(
        model='gemini-3.5-flash',
        contents=prompt,
    )
    summary_text = response.text
except Exception as e:
    summary_text = f"เกิดข้อผิดพลาดในการสรุปข่าว: {e}"
    print(summary_text)

print("กำลังส่งข้อความเข้า LINE...")
url = 'https://api.line.me/v2/bot/message/push'
headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {LINE_TOKEN}'
}
data = {
    'to': LINE_USER_ID,
    'messages': [{'type': 'text', 'text': f"☀️ สรุปข่าวการลงทุนยามเช้า\n\n{summary_text}"}]
}

resp = requests.post(url, headers=headers, json=data)
if resp.status_code == 200:
    print("✅ ส่งข้อความเข้า LINE สำเร็จ!")
else:
    print(f"❌ เกิดข้อผิดพลาดในการส่ง LINE: {resp.text}")
