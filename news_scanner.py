"""
BREAKING NEWS SCANNER - Separate News Bot
Scans for major news events affecting stocks
"""
import os
import time
import requests
from nsetools import Nse
from datetime import datetime
import re
from xml.etree import ElementTree

os.environ['TZ'] = 'Asia/Kolkata'

# Use SEPARATE bot token for news
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_NEWS_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# Key stocks to track news for
TRACKED_STOCKS = [
    'RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK', 'KOTAKBANK',
    'SBIN', 'ITC', 'TITAN', 'MARUTI', 'SUNPHARMA', 'CIPLA',
    'ADANIPORTS', 'TATASTEEL', 'JSWSTEEL', 'HINDUNILVR',
    'BAJFINANCE', 'POWERGRID', 'NTPC', 'WIPRO', 'TECHM', 'AXISBANK'
]

# High-impact keywords
HIGH_IMPACT = [
    'acquisition', 'merger', 'buyback', 'dividend', 'bonus',
    'split', 'results', 'profit jumps', 'revenue surge',
    'fraud', 'scam', 'investigation', 'penalty', 'fine',
    'ceo resigns', 'arrest', 'default', 'bankruptcy',
    'block deal', 'stake sale', 'takeover', 'ipo',
    'credit rating', 'downgrade', 'upgrade', 'order win',
    'fda approval', 'drug approval', 'recall'
]

def send_to_news_bot(text):
    """Send to separate news bot"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        if len(text) > 3800:
            text = text[:3800] + "\n..."
        resp = requests.post(url, data={
            'chat_id': TELEGRAM_CHAT_ID,
            'text': text,
            'parse_mode': 'HTML'
        }, timeout=10)
        return resp.json().get('ok', False)
    except:
        return False

def scan_breaking_news():
    """Scan for breaking news across all tracked stocks"""
    all_alerts = []
    
    print(f"📰 Scanning news for {len(TRACKED_STOCKS)} stocks...")
    
    for symbol in TRACKED_STOCKS:
        try:
            # Multiple search queries for better coverage
           for query in [
                f"{symbol} stock news today",
                f"{symbol} shares latest",
                f"{symbol} company announcement"
            ]:
                try:
                    url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
                    resp = requests.get(url, timeout=5)
                    root = ElementTree.fromstring(resp.content)
                    
                    for item in root.findall('.//item')[:3]:
                        title = item.find('title').text if item.find('title') is not None else ""
                        pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
                        
                        # Check if high impact
                        title_lower = title.lower()
                        impact_words = []
                        
                        for keyword in HIGH_IMPACT:
                            if keyword in title_lower:
                                impact_words.append(keyword)
                        
                        if impact_words and len(title) > 30:
                            # Get current price
                            try:
                                nse = Nse()
                                q = nse.get_quote(symbol)
                                price = float(q.get('lastPrice', 0)) if q else 0
                                change = float(q.get('pChange', 0)) if q else 0
                            except:
                                price, change = 0, 0
                            
                            all_alerts.append({
                                'symbol': symbol,
                                'price': price,
                                'change': change,
                                'headline': re.sub(r'[^\w\s\-.,%₹$&()]', '', title),
                                'impact': impact_words,
                                'time': pub_date[:25] if pub_date else 'Now'
                            })
                except:
                    pass
            
            time.sleep(0.3)  # Rate limiting
            
        except:
            pass
    
    return all_alerts

def build_news_message(alerts):
    """Build clean news alert message"""
    if not alerts:
        return None
    
    # Remove duplicates
    seen = set()
    unique_alerts = []
    for alert in alerts:
        key = alert['headline'][:80]
        if key not in seen:
            seen.add(key)
            unique_alerts.append(alert)
    
    # Sort by impact (more keywords = more important)
    unique_alerts.sort(key=lambda x: len(x['impact']), reverse=True)
    
    now = datetime.now()
    
    msg = f"📰 <b>BREAKING MARKET NEWS</b>\n"
    msg += f"📅 {now.strftime('%d-%b %I:%M %p')} IST\n"
    msg += f"{'═'*35}\n\n"
    
    msg += f"📊 <b>{len(unique_alerts)} Major Headlines</b>\n"
    msg += f"{'─'*35}\n\n"
    
    for i, alert in enumerate(unique_alerts[:8], 1):
        # Impact level
        if len(alert['impact']) >= 3:
            level = "🔴 HIGH"
        elif len(alert['impact']) >= 2:
            level = "🟠 MEDIUM"
        else:
            level = "🟡 NOTABLE"
        
        # Stock info
        stock_info = ""
        if alert['price'] > 0:
            direction = "📈" if alert['change'] > 0 else "📉"
            stock_info = f" | {direction} ₹{alert['price']:.0f} ({alert['change']:+.1f}%)"
        
        msg += f"<b>{level}</b>\n"
        msg += f"<b>{i}. {alert['symbol']}</b>{stock_info}\n"
        msg += f"📰 {alert['headline'][:150]}\n"
        msg += f"🏷️ Tags: {', '.join(alert['impact'][:3]).title()}\n"
        msg += f"⏰ {alert['time']}\n\n"
    
    msg += f"{'═'*35}\n"
    if len(unique_alerts) > 8:
        msg += f"📌 +{len(unique_alerts)-8} more headlines\n"
    msg += f"📱 <i>News Bot | Auto-Scanner</i>"
    
    return msg

def run_news_scanner():
    """Main news scanner"""
    print("📰 Starting News Scanner...")
    
    alerts = scan_breaking_news()
    
    if alerts:
        msg = build_news_message(alerts)
        if msg and send_to_news_bot(msg):
            print(f"✅ News alert sent! {len(alerts)} headlines")
        else:
            print("❌ Failed to send")
    else:
        print("No breaking news found")
        # Optional: Send "quiet day" message
        # send_to_news_bot("📰 No major breaking news at this hour.")

if __name__ == "__main__":
    run_news_scanner()
