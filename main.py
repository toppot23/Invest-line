import os
import requests
import feedparser
import yfinance as yf
from google import genai

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
LINE_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_USER_ID = os.environ.get('LINE_USER_ID')

client = genai.Client(api_key=GEMINI_API_KEY)

# ฟังก์ชันดึงราคาที่ปลอดภัย (รองรับวันหยุด/วันเสาร์-อาทิตย์)
def fetch_ticker_price(symbol):
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="5d")
        if not hist.empty:
            return hist['Close'].iloc[-1]
        return None
    except Exception as e:
        print(f"ไม่สามารถดึงราคาสำหรับ {symbol} ได้: {e}")
        return None

print("กำลังดึงข้อมูลราคาล่าสุด...")
gold_price = fetch_ticker_price("GC=F")   
oil_price = fetch_ticker_price("CL=F")    
btc_price = fetch_ticker_price("BTC-USD")  

price_context = "[ราคาตลาดโลกล่าสุด]\n"
price_context += f"- ทองคำ (Gold Spot): ${gold_price:.2f} ต่อออนซ์\n" if gold_price else "- ทองคำ (Gold Spot): ไม่สามารถดึงราคาได้\n"
price_context += f"- น้ำมัน (WTI Crude Oil): ${oil_price:.2f} ต่อบาร์เรล\n" if oil_price else "- น้ำมัน (WTI Crude Oil): ไม่สามารถดึงราคาได้\n"
price_context += f"- Bitcoin (BTC): ${btc_price:,.2f}\n" if btc_price else "- Bitcoin (BTC): ไม่สามารถดึงราคาได้\n"

# เพิ่มแหล่งข่าวจากฝั่งเอเชียและจีนเพื่อความครอบคลุม
rss_feeds = {
    "US_Macro_and_Forex": "https://finance.yahoo.com/news/rssindex",
    "China_and_Asia_Markets": "https://www.cnbc.com/id/19832390/device/rss/rss.html", # ข่าวตลาดหุ้นเอเชียและจีนจาก CNBC
    "Crypto": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Thai_Business": "https://www.prachachat.net/finance/feed",
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

print("กำลังส่งให้ AI สรุป...")
prompt = f"""
คุณคือนักวิเคราะห์การลงทุนมืออาชีพ สรุปข่าวการลงทุนรายวันจากข้อมูลข่าวและข้อมูลราคาล่าสุดที่ให้มา ให้อ่านง่าย กระชับ เหมาะกับการอ่านบน LINE โดยแบ่งเป็นหมวดหมู่ดังนี้:

1. 🇺🇸 หุ้น US (สรุปภาพรวมตลาด, Sector เด่น เช่น Tech, AI, Healthcare และหุ้นหรือกลุ่ม ETF ที่น่าสนใจ)
2. 🇨🇳 หุ้นจีนและฮ่องกง (สรุปภาพรวมตลาดทั้งแผ่นดินใหญ่ CSI300 และฮ่องกง Hang Seng แบ่งตาม Sector ที่โดดเด่น และเจาะจงหุ้นรายตัวหรือ ETF ที่น่าสนใจ)
3. 🇹🇭 หุ้นไทย (ประเด็นหลักที่กระทบตลาดวันนี้, กลุ่มอุตสาหกรรมที่เป็นกระแส)
4. 🥇 ทองคำ และ 🛢️ น้ำมัน (ระบุราคาล่าสุดจากข้อมูลที่แนบให้ชัดเจน และสรุปปัจจัยหลักที่ขับเคลื่อนราคา)
5. ₿ คริปโตเคอร์เรนซี (ระบุราคา BTC ปัจจุบันจากข้อมูลที่แนบให้ชัดเจน และสรุปภาพรวมเหรียญหลัก ข่าวสำคัญ)
6. 💵 ค่าเงินดอลลาร์ และ 🌍 เศรษฐกิจมหภาค (อัปเดตดัชนีดอลลาร์ ดอกเบี้ย นโยบายการเงิน และอสังหาริมทรัพย์ เน้น US, Asia, ไทย)

กฎในการสรุป:
- ใช้รูปแบบ Bullet points (-) เพื่อความรวดเร็วในการอ่าน
- **เน้นตัวหนา** ที่ราคาตัวเลข ดัชนี ชื่อหุ้น หรือทิศทางสำคัญ เช่น ราคาล่าสุด หรือคำว่า **พุ่งขึ้น** / **ดิ่งลง**
- ห้ามตัดหัวข้อราคาล่าสุดออกเด็ดขาด ให้นำข้อมูลราคาไปใส่ให้ตรงหมวด
- สรุปตามข้อเท็จจริง ห้ามคาดเดาตัวเลขราคาเอาเอง

ข้อมูลราคาล่าสุดสำหรับใช้อ้างอิง:
{price_context}

ข้อมูลข่าวสารสำหรับวันนี้:
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

print("กำลังส่งข้อความเข้า LINE...")
url = 'https://api.line.me/v2/bot/message/push'
headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {LINE_TOKEN}'
}
data = {
    'to': LINE_USER_ID,
    'messages': [{'type': 'text', 'text': f"☀️ สรุปข่าวและราคาลงทุนยามเช้า\n\n{summary_text}"}]
}

resp = requests.post(url, headers=headers, json=data)
if resp.status_code == 200:
    print("✅ ส่งข้อความเข้า LINE สำเร็จ!")
else:
    print(f"❌ เกิดข้อผิดพลาดในการส่ง LINE: {resp.text}")
