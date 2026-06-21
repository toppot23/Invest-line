import os
import requests
import feedparser
from google import genai

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
LINE_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_USER_ID = os.environ.get('LINE_USER_ID')

# วิธีการเชื่อมต่อ AI แบบใหม่
client = genai.Client(api_key=GEMINI_API_KEY)

rss_feeds = {
    "US_and_Macro": "https://finance.yahoo.com/news/rssindex",
    "Crypto": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Thai_Business": "https://www.thansettakij.com/rss/finance",
    "Gold": "https://www.kitco.com/rss/source/kitco-news-all.xml"
}

print("กำลังดึงข้อมูลข่าว...")
news_data = ""
for category, url in rss_feeds.items():
    try:
        feed = feedparser.parse(url)
        news_data += f"\n--- {category} ---\n"
        for entry in feed.entries[:5]:
            news_data += f"- {entry.title}\n"
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการดึง {category}: {e}")

print("กำลังส่งให้ AI สรุป...")
prompt = f"""
คุณคือนักวิเคราะห์การลงทุนมืออาชีพ สรุปข่าวการลงทุนรายวันจากข้อมูลที่ให้มาให้อ่านง่าย กระชับ แบ่งเป็น 5 หัวข้อ:
1. 🇺🇸 หุ้น US (สรุปภาพรวมตลาด, Sector, หุ้นที่น่าสนใจ)
2. 🇹🇭 หุ้นไทย (ประเด็นหลัก, กลุ่มอุตสาหกรรมที่เป็นกระแส)
3. 🥇 ทองคำ (ทิศทางราคาล่าสุด และปัจจัยหลัก)
4. ₿ คริปโตเคอร์เรนซี (ภาพรวมเหรียญหลัก, ข่าวสำคัญ)
5. 🌍 ภาพรวมเศรษฐกิจ (อสังหาฯ, ดอกเบี้ย)

กฎ:
- ใช้ Bullet points (-) 
- **เน้นตัวหนา** ชื่อหุ้น ตัวเลข
- ถ้าไม่มีข้อมูลให้เขียน "ไม่มีประเด็นสำคัญในรอบวัน"

ข้อมูลข่าว:
{news_data}
"""

try:
    # วิธีสั่งให้ AI जनरेट ข้อความแบบใหม่ (ใช้โมเดล gemini-2.5-flash ซึ่งเป็นตัวล่าสุด)
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
    'messages': [{'type': 'text', 'text': f"☀️ สรุปข่าวการลงทุน\n\n{summary_text}"}]
}

resp = requests.post(url, headers=headers, json=data)
if resp.status_code == 200:
    print("✅ ส่งข้อความเข้า LINE สำเร็จ!")
else:
    print(f"❌ เกิดข้อผิดพลาดในการส่ง LINE: {resp.text}")
