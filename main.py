import os
import requests
import feedparser
import yfinance as yf
from google import genai

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
LINE_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_USER_ID = os.environ.get('LINE_USER_ID')

client = genai.Client(api_key=GEMINI_API_KEY)

# 1. ดึงราคาสินทรัพย์แบบเรียลไทม์จากตลาดโลก
print("กำลังดึงข้อมูลราคาล่าสุด...")
try:
    gold_price = yf.Ticker("GC=F").history(period="1d")['Close'].iloc[-1]
    oil_price = yf.Ticker("CL=F").history(period="1d")['Close'].iloc[-1]
    btc_price = yf.Ticker("BTC-USD").history(period="1d")['Close'].iloc[-1]
    
    price_context = f"""
    [ราคาตลาดโลกปัจจุบัน]
    - ทองคำ (Gold Spot): ${gold_price:.2f} ต่อออนซ์
    - น้ำมัน (WTI Crude Oil): ${oil_price:.2f} ต่อบาร์เรล
    - Bitcoin (BTC): ${btc_price:,.2f}
    """
except Exception as e:
    price_context = "- ไม่สามารถดึงข้อมูลราคาเรียลไทม์ได้ชั่วคราว ให้เน้นสรุปจากเนื้อหาข่าวแทน"
    print(f"Error fetching prices: {e}")

# 2. ดึงข้อมูลข่าวจาก RSS Feeds
rss_feeds = {
    "US_Macro_and_Forex": "https://finance.yahoo.com/news/rssindex",
    "Crypto": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Thai_Business": "https://www.thansettakij.com/rss/finance",
    "Gold_and_Commodities": "https://www.kitco.com/rss/source/kitco-news-all.xml"
}

print("กำลังดึงข้อมูลเนื้อหาข่าว...")
news_data = ""
for category, url in rss_feeds.items():
    try:
        feed = feedparser.parse(url)
        news_data += f"\n--- {category} ---\n"
        for entry in feed.entries[:6]:
            news_data += f"- {entry.title}\n"
    except Exception as e:
        pass

# 3. ส่งข้อมูลทั้งหมดให้ Gemini สรุปผล
print("กำลังส่งให้ AI สรุป...")
prompt = f"""
คุณคือนักวิเคราะห์การลงทุนมืออาชีพ สรุปข่าวการลงทุนรายวันจากข้อมูลข่าวและข้อมูลราคาล่าสุดที่ให้มา ให้อ่านง่าย กระชับ เหมาะกับการอ่านบน LINE โดยแบ่งเป็นหมวดหมู่ดังนี้:

1. 🇺🇸 หุ้น US (สรุปภาพรวมตลาด, Sector เด่น, หุ้นหรือกลุ่ม ETF ที่น่าสนใจ)
2. 🇹🇭 หุ้นไทย (ประเด็นหลักที่กระทบตลาดวันนี้, กลุ่มอุตสาหกรรมที่เป็นกระแส)
3. 🥇 ทองคำ และ 🛢️ น้ำมัน (ระบุราคาล่าสุดจากข้อมูลตลาดโลกที่แนบให้ และสรุปปัจจัยหลักที่ขับเคลื่อนราคา)
4. ₿ คริปโตเคอร์เรนซี (ระบุราคา BTC ล่าสุดจากข้อมูลตลาดโลกที่แนบให้ และสรุปภาพรวมเหรียญหลัก ข่าวสำคัญ)
5. 💵 ค่าเงินดอลลาร์ และ 🌍 เศรษฐกิจมหภาค (อัปเดตดัชนีดอลลาร์ ดอกเบี้ย นโยบายการเงิน และอสังหาริมทรัพย์ เน้น US, Asia, ไทย)

กฎในการสรุป:
- ใช้รูปแบบ Bullet points (-) เพื่อความรวดเร็วในการอ่าน
- **เน้นตัวหนา** ที่ราคาตัวเลข ดัชนี ชื่อหุ้น หรือทิศทางสำคัญ
- นำข้อมูลราคาล่าสุดไปแสดงในหมวดหมู่ที่ถูกต้องให้ชัดเจน
- สรุปตามข้อเท็จจริง ห้ามคาดเดาตัวเลขราคาเองเด็ดขาด

ข้อมูลอ้างอิงสำหรับวันนี้:
{price_context}

ข้อมูลข่าวสาร:
{news_data}
"""

try:
    response = client.models.generate_content(
        model='gemini-3.5-flash',
        contents=prompt,
    )
    summary_text = response.text
except Exception as e:
    summary_text = f"เกิดข้อผิดพลาดในการสรุปข่าว: {e}"

# 4. ส่งเข้า LINE Messaging API
print("กำลังส่งข้อความเข้า LINE...")
url = 'https://api.line.me/v2/bot/message/push'
headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {LINE_TOKEN}'
}
data = {
    'to': LINE_USER_ID,
    'messages': [{'type': 'text', 'text': f"☀️ สรุปข่าวและราคาทุนยามเช้า\n\n{summary_text}"}]
}

resp = requests.post(url, headers=headers, json=data)
if resp.status_code == 200:
    print("✅ ส่งข้อความเข้า LINE สำเร็จ!")
else:
    print(f"❌ เกิดข้อผิดพลาดในการส่ง LINE: {resp.text}")
