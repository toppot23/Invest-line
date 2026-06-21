import os
import requests
import feedparser
import yfinance as yf
from google import genai

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
LINE_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_USER_ID = os.environ.get('LINE_USER_ID')

client = genai.Client(api_key=GEMINI_API_KEY)

# 1. ฟังก์ชันดึงราคาตลาดโลก
def fetch_ticker_price(symbol):
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="5d")
        if not hist.empty:
            return hist['Close'].iloc[-1]
        return None
    except Exception:
        return None

# 2. ฟังก์ชันดึงราคาน้ำมันขายปลีกในประเทศไทย
def fetch_thai_oil_prices():
    try:
        feed_url = "https://www.bangchak.co.id/th/oilprice-rss"
        feed = feedparser.parse(feed_url)
        
        gasohol95 = None
        diesel = None
        update_date = ""
        
        if feed.entries:
            update_date = feed.entries[0].get('updated', '').split('T')[0]
            if not update_date:
                update_date = feed.entries[0].get('published', '')
                
            for entry in feed.entries:
                title = entry.title.lower()
                if "gasohol 95" in title or "แก๊สโซฮอล์ 95" in title:
                    gasohol95 = entry.summary
                elif "diesel" in title or "ดีเซล" in title:
                    if "premium" not in title and "พรีเมียม" not in title:
                        diesel = entry.summary
                        
        return gasohol95, diesel, update_date
    except Exception:
        return None, None, ""

print("กำลังดึงข้อมูลราคาล่าสุด...")
gold_price = fetch_ticker_price("GC=F")   
oil_wti = fetch_ticker_price("CL=F")    
btc_price = fetch_ticker_price("BTC-USD")  
th_gas95, th_diesel, th_oil_date = fetch_thai_oil_prices()

price_context = "ราคาตลาดล่าสุด\n"
price_context += f"• ทองคำโลก: ${gold_price:.2f} / ออนซ์\n" if gold_price else ""
price_context += f"• น้ำมันดิบโลก (WTI): ${oil_wti:.2f} / บาร์เรล\n" if oil_wti else ""
price_context += f"• Bitcoin: ${btc_price:,.2f}\n" if btc_price else ""

if th_gas95 or th_diesel:
    price_context += f"\n[ราคาน้ำมันขายปลีกในไทย (บาท/ลิตร) อัปเดตวันที่: {th_oil_date}]\n"
    if th_gas95: price_context += f"• แก๊สโซฮอล์ 95: {th_gas95} บาท\n"
    if th_diesel: price_context += f"• ดีเซล: {th_diesel} บาท\n"

# 3. ดึงข้อมูลข่าวสาร
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

# 4. ส่งคำสั่งให้ Gemini สรุป
prompt = f"""
สรุปข่าวการลงทุนจากข้อมูลที่ให้มา โดยจัดรูปแบบให้ดูคลีน เป็นระเบียบ มีการเว้นบรรทัดระหว่างย่อหน้าและหัวข้อให้ชัดเจน
ห้ามใช้เครื่องหมายดอกจัน และแฮชแท็ก ในข้อความโดยเด็ดขาด 

ให้ใช้ Emoji ที่เกี่ยวข้องกับเนื้อหาข่าวมานำหน้าแต่ละบรรทัดย่อยแทนการใช้จุดหรือขีด 

แบ่งเป็น 6 หมวดหมู่ดังนี้:
1. 🇺🇸 หุ้นสหรัฐ (ภาพรวม, Sector เด่น, หุ้นที่น่าสนใจ)
2. 🇨🇳 หุ้นจีนและฮ่องกง (ภาพรวมตลาด, กลุ่มอุตสาหกรรม, หุ้นเด่น)
3. 🇹🇭 หุ้นไทย (ประเด็นหลักที่กระทบตลาดวันนี้)
4. 🥇 ทองคำ และ 🛢️ น้ำมัน (บรรทัดแรกให้ใส่ราคาและทิศทางทองคำโลก น้ำมันดิบโลก และราคาน้ำมันขายปลีกในไทย แก๊สโซฮอล์ 95 และดีเซล พร้อมระบุวันที่อัปเดตที่แนบมาให้ชัดเจน จากนั้นสรุปข่าวที่เกี่ยวข้อง)
5. ₿ คริปโตเคอร์เรนซี (บรรทัดแรกให้สรุปราคา BTC ล่าสุด และสรุปข่าวสารสำคัญ)
6. 🌍 เศรษฐกิจมหภาค (ดอกเบี้ย ค่าเงิน นโยบายการเงินทั่วโลก)

กฎสำคัญ:
• หากหัวข้อไหนไม่มีข่าว ให้เขียนบรรทัดเดียวสั้นๆ ว่า "ไม่มีประเด็นสำคัญ"
• สรุปกระชับ ไม่ต้องเกริ่นนำ ไม่ต้องมีคำลงท้าย

ข้อมูลราคา:
{price_context}

ข้อมูลข่าวสำหรับวันนี้:
{news_data}
"""

try:
    # เปลี่ยนมาใช้รุ่น 3.5 Flash ตามที่ต้องการครับ
    response = client.models.generate_content(
        model='gemini-3.5-flash',
        contents=prompt,
    )
    summary_text = response.text
    summary_text = summary_text.replace('*', '').replace('#', '')
except Exception as e:
    summary_text = f"เกิดข้อผิดพลาด: {e}"

# 5. ส่งข้อมูลเข้า LINE
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
