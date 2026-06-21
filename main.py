import os
import requests
import feedparser
import yfinance as yf
from google import genai

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
LINE_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_USER_ID = os.environ.get('LINE_USER_ID')

client = genai.Client(api_key=GEMINI_API_KEY)

# ดึงราคา
def fetch_ticker_price(symbol):
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="5d")
        if not hist.empty:
            return hist['Close'].iloc[-1]
        return None
    except Exception as e:
        return None

gold_price = fetch_ticker_price("GC=F")   
oil_price = fetch_ticker_price("CL=F")    
btc_price = fetch_ticker_price("BTC-USD")  

price_context = "ราคาตลาดโลกล่าสุด\n"
price_context += f"• ทองคำ: ${gold_price:.2f} ต่อออนซ์\n" if gold_price else "• ทองคำ: ไม่สามารถดึงราคาได้\n"
price_context += f"• น้ำมัน (WTI): ${oil_price:.2f} ต่อบาร์เรล\n" if oil_price else "• น้ำมัน: ไม่สามารถดึงราคาได้\n"
price_context += f"• Bitcoin: ${btc_price:,.2f}\n" if btc_price else "• Bitcoin: ไม่สามารถดึงราคาได้\n"

# ดึงข่าว
rss_feeds = {
    "US_Macro": "https://finance.yahoo.com/news/rssindex",
    "Asia_China": "https://www.cnbc.com/id/19832390/device/rss/rss.html",
    "Crypto": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Thai": "https://www.prachachat.net/finance/feed",
    "Gold": "https://www.kitco.com/rss/source/kitco-news-all.xml"
}

news_data = ""
for category, url in rss_feeds.items():
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:6]:
            news_data += f"- {entry.title}\n"
    except Exception:
        pass

# คำสั่ง AI ให้เขียนแบบสะอาดตา
prompt = f"""
สรุปข่าวการลงทุนจากข้อมูลที่ให้มา โดยใช้รูปแบบที่สะอาดตา อ่านง่ายบนมือถือ มินิมอล ไม่รก
ห้ามใช้สัญลักษณ์ * หรือ # เยอะเกินไป ให้ใช้จุดนำหน้า (•) หรือ Emoji แบบพอดีๆ เพื่อแบ่งหัวข้อ

ให้แบ่งเป็น 6 หมวดหมู่ดังนี้:
1. หุ้นสหรัฐ 🇺🇸 (ภาพรวม, Sector เด่น, หุ้นที่น่าสนใจ)
2. หุ้นจีนและฮ่องกง 🇨🇳 (ภาพรวม CSI300 / Hang Seng, Sector, หุ้นเด่น)
3. หุ้นไทย 🇹🇭 (ประเด็นหลัก, กลุ่มกระแส)
4. ทองคำ และ น้ำมัน ⛽️ (ใส่ราคาล่าสุดไว้บรรทัดแรก และสรุปทิศทางตลาด)
5. คริปโตเคอร์เรนซี ₿ (ใส่ราคา BTC ล่าสุดไว้บรรทัดแรก และสรุปข่าวสำคัญ)
6. เศรษฐกิจมหภาค 🌍 (ดอกเบี้ย ค่าเงิน นโยบาย เน้นสหรัฐฯ เอเชีย และไทย)

กฎสำคัญ:
• หากหัวข้อไหนไม่มีข่าว ให้เขียนว่า "ไม่มีประเด็นสำคัญ"
• สรุปกระชับ ไม่ต้องเกริ่นนำ ไม่ต้องมีคำลงท้าย

ข้อมูลราคา:
{price_context}

ข้อมูลข่าว:
{news_data}
"""

try:
    response = client.models.generate_content(
        model='gemini-3.5-flash',
        contents=prompt,
    )
    summary_text = response.text
except Exception as e:
    summary_text = f"เกิดข้อผิดพลาด: {e}"

# ส่งเข้า LINE
url = 'https://api.line.me/v2/bot/message/push'
headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {LINE_TOKEN}'
}
data = {
    'to': LINE_USER_ID,
    'messages': [{'type': 'text', 'text': f"☀️ อัปเดตตลาดเช้านี้\n\n{summary_text}"}]
}

requests.post(url, headers=headers, json=data)
