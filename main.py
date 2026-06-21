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
price_context += f"🪙 ทองคำ: ${gold_price:.2f} / ออนซ์\n" if gold_price else "🪙 ทองคำ: ไม่สามารถดึงราคาได้\n"
price_context += f"🛢️ น้ำมัน (WTI): ${oil_price:.2f} / บาร์เรล\n" if oil_price else "🛢️ น้ำมัน: ไม่สามารถดึงราคาได้\n"
price_context += f"₿ Bitcoin: ${btc_price:,.2f}\n" if btc_price else "₿ Bitcoin: ไม่สามารถดึงราคาได้\n"

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

# คำสั่ง AI ให้จัดหน้าตาคลีน มีช่องไฟ และใช้ Emoji สื่อความหมาย
prompt = f"""
สรุปข่าวการลงทุนจากข้อมูลที่ให้มา โดยจัดรูปแบบให้ดูคลีน เป็นระเบียบ มีการเว้นบรรทัดระหว่างย่อหน้าและหัวข้อให้ชัดเจน
ห้ามใช้เครื่องหมายดอกจัน และแฮชแท็ก ในข้อความโดยเด็ดขาด 

ให้ใช้ Emoji ที่เกี่ยวข้องกับเนื้อหาข่าวมานำหน้าแต่ละบรรทัดย่อยแทนการใช้จุดหรือขีด (เช่น 🚀 เทคโนโลยี, 🏥 สุขภาพ, 🏦 ดอกเบี้ย/ธนาคาร, 📉 ตลาดร่วง, 🔋 พลังงาน, 🛍️ ค้าปลีก เป็นต้น)

แบ่งเป็น 6 หมวดหมู่ดังนี้:
1. 🇺🇸 หุ้นสหรัฐ
2. 🇨🇳 หุ้นจีนและฮ่องกง 
3. 🇹🇭 หุ้นไทย 
4. 🥇 ทองคำ และ 🛢️ น้ำมัน (บรรทัดแรกให้สรุปราคาล่าสุดที่แนบให้)
5. ₿ คริปโตเคอร์เรนซี (บรรทัดแรกให้สรุปราคา BTC ล่าสุดที่แนบให้)
6. 🌍 เศรษฐกิจมหภาค 

กฎสำคัญ:
• หากหัวข้อไหนไม่มีข่าว ให้เขียนบรรทัดเดียวสั้นๆ ว่า "ไม่มีประเด็นสำคัญ"
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
    
    # บังคับลบเครื่องหมายดอกจันและแฮชแท็กออกทั้งหมดด้วย Python เพื่อความชัวร์ 100%
    summary_text = summary_text.replace('*', '').replace('#', '')
    
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
