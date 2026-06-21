import os
import requests
import feedparser
import google.generativeai as genai

# 1. โหลด Keys จาก GitHub Secrets
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
LINE_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_USER_ID = os.environ.get('LINE_USER_ID')

genai.configure(api_key=GEMINI_API_KEY)

# 2. แหล่งข้อมูลข่าว (RSS Feeds)
rss_feeds = {
    "US_and_Macro": "https://finance.yahoo.com/news/rssindex",
    "Crypto": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Thai_Business": "https://www.thansettakij.com/rss/finance", # ข่าวการเงินไทย
    "Gold": "https://www.kitco.com/rss/source/kitco-news-all.xml" # ข่าวทองคำ
}

print("กำลังดึงข้อมูลข่าว...")
news_data = ""
for category, url in rss_feeds.items():
    try:
        feed = feedparser.parse(url)
        news_data += f"\n--- {category} ---\n"
        # ดึงแค่ 5 ข่าวล่าสุดต่อหมวดเพื่อไม่ให้ข้อมูลยาวเกินไป
        for entry in feed.entries[:5]:
            news_data += f"- {entry.title}\n"
    except Exception as e:
        print(f"ดึงข้อมูล {category} ไม่สำเร็จ: {e}")

# 3. สร้าง Prompt และส่งให้ Gemini สรุป
print("กำลังส่งให้ AI สรุป...")
prompt = f"""
คุณคือนักวิเคราะห์การลงทุนมืออาชีพ หน้าที่ของคุณคือคัดกรองและสรุปข่าวการลงทุนรายวันจากข้อมูลที่ให้มา เพื่อส่งแจ้งเตือนยามเช้า ให้อ่านง่าย กระชับ ตรงประเด็น และเหมาะกับการอ่านบนแอปพลิเคชัน LINE

กรุณาแบ่งการสรุปออกเป็น 5 หัวข้อตามลำดับดังนี้:
1. 🇺🇸 หุ้น US (สรุปภาพรวมตลาด, Sector, หุ้นที่น่าสนใจ)
2. 🇹🇭 หุ้นไทย (ประเด็นหลัก, กลุ่มอุตสาหกรรมที่เป็นกระแส)
3. 🥇 ทองคำ (ทิศทางราคาล่าสุด และปัจจัยหลัก)
4. ₿ คริปโตเคอร์เรนซี (ภาพรวมเหรียญหลัก, ข่าวสำคัญ)
5. 🌍 ภาพรวมเศรษฐกิจ / Macro (อสังหาฯ, ดอกเบี้ย เน้น US, Asia, ไทย)

กฎในการเขียนสรุป:
- ใช้รูปแบบ Bullet points (-) เพื่อให้กวาดสายตาอ่านได้เร็ว
- **เน้นตัวหนา** (Bold) ที่ชื่อหุ้น ทิกเกอร์ (Ticker) สินทรัพย์ หรือตัวเลขสำคัญต่างๆ
- ใส่ Emoji ประกอบเล็กน้อย
- หากหัวข้อไหนไม่มีข้อมูล ให้เขียนสั้นๆ ว่า "ไม่มีประเด็นสำคัญในรอบวัน"
- สรุปเฉพาะความจริงจากข้อมูลที่ให้มา ห้ามแต่งเติมข้อมูลเองเด็ดขาด

ข้อมูลข่าวสำหรับวันนี้:
{news_data}
"""

try:
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(prompt)
    summary_text = response.text
except Exception as e:
    summary_text = f"เกิดข้อผิดพลาดในการสรุปข่าวจาก AI: {e}"
    print(summary_text)

# 4. ส่งข้อความเข้า LINE Messaging API
print("กำลังส่งข้อความเข้า LINE...")
url = 'https://api.line.me/v2/bot/message/push'
headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {LINE_TOKEN}'
}
data = {
    'to': LINE_USER_ID,
    'messages': [
        {
            'type': 'text',
            'text': f"☀️ สรุปข่าวการลงทุน 9 โมงเช้า\n\n{summary_text}"
        }
    ]
}

response = requests.post(url, headers=headers, json=data)

if response.status_code == 200:
    print("✅ ส่งข้อความเข้า LINE สำเร็จ!")
else:
    print(f"❌ เกิดข้อผิดพลาดในการส่ง LINE: {response.text}")