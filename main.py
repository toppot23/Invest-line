import os
import sys
import requests
import feedparser
import yfinance as yf
from datetime import datetime
import xml.etree.ElementTree as ET
from google import genai
import pytz

# ตั้งค่า API Keys จาก GitHub Secrets
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
LINE_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_USER_ID = os.environ.get('LINE_USER_ID')

client = genai.Client(api_key=GEMINI_API_KEY)

# ตั้งเวลาไทยสำหรับแสดงในหัวข้อ
tz_thai = pytz.timezone('Asia/Bangkok')
now_thai = datetime.now(tz_thai)
current_time_str = now_thai.strftime("%d/%m/%Y %H:%M น.")

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

# 2. ฟังก์ชันดึงราคาน้ำมันขายปลีกในไทย
def fetch_thai_oil_prices():
    gasohol95 = None
    diesel = None
    update_date = ""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    # แผน A: ดึงจาก API
    try:
        res = requests.get("https://api.chnwt.dev/thai-oil-api/latest", headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            prices = data.get('response', {}).get('stations', {}).get('ptt', {})
            update_date = data.get('response', {}).get('date', '')
            
            if 'gasohol_95' in prices:
                gasohol95 = str(prices['gasohol_95'].get('price', ''))
            if 'diesel' in prices:
                diesel = str(prices['diesel'].get('price', ''))
                
            if gasohol95 and diesel:
                return gasohol95, diesel, update_date
    except Exception:
        pass

    # แผน B: ดึงจากระบบ ปตท. สำรอง
    try:
        url = "https://orapiweb.pttor.com/oilservice/OilPrice.asmx/CurrentOilPrice?Language=en"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            inner_root = ET.fromstring(root.text)
            
            for item in inner_root.findall('DataAccess'):
                prod = item.find('PRODUCT')
                price = item.find('PRICE')
                date_val = item.find('PRICE_DATE')
                
                if prod is not None and price is not None and price.text:
                    p_name = prod.text.lower()
                    
                    if not update_date and date_val is not None:
                        update_date = date_val.text.split(' ')[0]
                        
                    if "gasohol 95" in p_name and "premium" not in p_name and "super" not in p_name:
                        gasohol95 = price.text
                    elif "diesel" in p_name and "premium" not in p_name and "super" not in p_name:
                        diesel = price.text
                        
            if gasohol95 or diesel:
                return gasohol95, diesel, update_date
    except Exception:
        pass

    return gasohol95, diesel, update_date

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
    price_context += f"\n[ราคาน้ำมันขายปลีกไทย อัปเดตวันที่: {th_oil_date}]\n"
    if th_gas95: price_context += f"• แก๊สโซฮอล์ 95: {th_gas95} บาท/ลิตร\n"
    if th_diesel: price_context += f"• ดีเซล: {th_diesel} บาท/ลิตร\n"

# 3. ดึงข้อมูลข่าวสารจากคลังข่าวหลัก
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
        for entry in feed.entries[:10]: # ดึงแค่ 10 ข่าวต่อหมวดเพื่อไม่ให้ข้อความยาวเกินไป
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
3. 🇹🇭 หุ้นไทย (ประเด็นหลักที่กระทบตลาดล่าสุด)
4. 🥇 ทองคำ และ 🛢️ น้ำมัน (บรรทัดแรกให้นำข้อมูล ราคาตลาดล่าสุด และ ราคาน้ำมันขายปลีกไทย ที่แนบให้ไปใส่ให้ครบถ้วน จากนั้นสรุปข่าวที่เกี่ยวข้อง)
5. ₿ คริปโตเคอร์เรนซี (บรรทัดแรกให้สรุปราคา BTC ล่าสุด และสรุปข่าวสารสำคัญ)
6. 🌍 เศรษฐกิจมหภาค (ดอกเบี้ย ค่าเงิน นโยบายการเงินทั่วโลก)

กฎสำคัญ:
• ใช้คำทับศัพท์ภาษาอังกฤษสำหรับชื่อบุคคล, บริษัท, หุ้น, กองทุน และศัพท์เฉพาะทางการเงิน/เทคนิคให้มากที่สุด (ไม่ต้องแปลไทย)
• ในกรณีที่ข้อมูลข่าวสารมีน้อย ให้ดึงข่าวสำคัญของวันก่อนหน้ามาสรุปแทน
• สรุปเนื้อหาให้สั้นและกระชับที่สุด (หมวดละไม่เกิน 3-4 บรรทัด) เพื่อไม่ให้ข้อความยาวเกิน 5000 ตัวอักษร 
• สรุปเข้าเรื่องทันที ไม่ต้องมีคำเกริ่นนำ ไม่ต้องมีคำลงท้าย

ข้อมูลอ้างอิงราคา:
{price_context}

ข้อมูลข่าวสำหรับวันนี้และวันก่อนหน้า:
{news_data}
"""

try:
    print("กำลังส่งข้อมูลให้ Gemini สรุป...")
    # ใช้โมเดล gemini-3.5-flash ตามที่คุณต้องการ
    response = client.models.generate_content(
        model='gemini-3.5-flash',
        contents=prompt,
    )
    summary_text = response.text
    # กรองสัญลักษณ์ที่อาจหลุดมาออก
    summary_text = summary_text.replace('*', '').replace('#', '')
except Exception as e:
    summary_text = f"เกิดข้อผิดพลาดในการสรุปข่าว: {e}"

# 5. ประกอบข้อความและตรวจสอบความยาวก่อนส่งเข้า LINE
final_message = f"☀️ อัปเดตตลาดล่าสุด\n({current_time_str})\n\n{summary_text}"

# ดักความยาวข้อความไม่ให้เกินลิมิต 5000 ตัวอักษรของ LINE API
if len(final_message) > 4950:
    final_message = final_message[:4950] + "\n...(ข้อความยาวเกินไป)"

print("กำลังส่งข้อความเข้า LINE...")
url = 'https://api.line.me/v2/bot/message/push'
headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {LINE_TOKEN}'
}
data = {
    'to': LINE_USER_ID,
    'messages': [{'type': 'text', 'text': final_message}]
}

response_line = requests.post(url, headers=headers, json=data)

if response_line.status_code == 200:
    print("✅ ส่งข้อความเข้า LINE สำเร็จ!")
else:
    print(f"❌ ส่ง LINE ไม่สำเร็จ! Error Code: {response_line.status_code}")
    print(f"สาเหตุจาก LINE API: {response_line.text}")
    # บังคับให้ระบบแจ้งเตือนว่าทำงานผิดพลาดเพื่อเตือนเข้า LINE อีกช่องทาง
    sys.exit(1)
