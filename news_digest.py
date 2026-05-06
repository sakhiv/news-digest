#!/usr/bin/env python3
import json, re, time, os
from datetime import datetime, timezone, timedelta
import feedparser
import requests

SCRIPT_DIR      = os.path.dirname(os.path.abspath(__file__))
RECIPIENT_EMAIL = "sakhi@scrabbleinc.in"
SENDER_EMAIL    = "hiring@scrabbleinc.in"
RESEND_API_KEY  = os.environ["RESEND_API_KEY"]

RSS_FEEDS = [
    "https://inc42.com/feed/",
    "https://yourstory.com/feed",
    "https://entrackr.com/feed/",
    "https://www.vccircle.com/feed",
    "https://economictimes.indiatimes.com/tech/startups/rssfeeds/78570550.cms",
    "https://www.business-standard.com/rss/companies-101.rss",
    "https://www.livemint.com/rss/companies",
    "https://news.google.com/rss/search?q=India+startup+funding&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=India+venture+capital+investment&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=India+startup+funding+round&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=India+PE+VC+deal&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=India+startup+acquisition+merger&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=India+startup+unicorn&hl=en-IN&gl=IN&ceid=IN:en",
]

def load_json(filename):
    with open(os.path.join(SCRIPT_DIR, "data", filename)) as f:
        return json.load(f)

def clean_list(lst, min_len=4):
    return sorted(set(
        name.strip() for name in lst if name and len(name.strip()) >= min_len
    ), key=lambda x: -len(x))

def find_matches(text, entity_list):
    text_lower = text.lower()
    matches = []
    for name in entity_list:
        pattern = r'(?<!\w)' + re.escape(name.lower()) + r'(?!\w)'
        if re.search(pattern, text_lower):
            matches.append(name)
    return matches

def fetch_articles(hours=24):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    articles, seen = [], set()
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url, request_headers={'User-Agent': 'Mozilla/5.0'})
            for entry in feed.entries:
                pub = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    try:
                        pub = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                    except Exception:
                        pass
                if pub and pub < cutoff:
                    continue
                link = entry.get('link', '')
                if link in seen:
                    continue
                seen.add(link)
                articles.append({
                    'title':   entry.get('title', ''),
                    'summary': re.sub('<[^>]+>', '', entry.get('summary', '')),
                    'link':    link,
                    'source':  feed.feed.get('title', url),
                    'pub':     pub.strftime('%d %b %Y %H:%M UTC') if pub else 'Unknown date'
                })
        except Exception as e:
            print(f"  [WARN] {url}: {e}")
        time.sleep(0.3)
    return articles

def build_hits(articles, entity_list):
    hits = []
    for article in articles:
        matches = find_matches(article['title'] + ' ' + article['summary'], entity_list)
        if matches:
            hits.append({**article, 'matches': list(set(matches))})
    return hits

def format_body(hits, label):
    date_str = datetime.now().strftime('%d %b %Y')
    if not hits:
        return f"Daily {label} Digest — {date_str}\n\nNo relevant news found today.\n"
    lines = [
        f"Daily {label} Digest — {date_str}",
        f"{len(hits)} article(s) matched across {len(RSS_FEEDS)} sources.",
        "=" * 60, ""
    ]
    for h in hits:
        lines += [
            f"  {h['title']}",
            f"  Source  : {h['source']}",
            f"  Date    : {h['pub']}",
            f"  Matched : {', '.join(h['matches'])}",
            f"  Link    : {h['link']}",
            ""
        ]
    return "\n".join(lines)

def send_email(subject, body):
    r = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
        json={"from": SENDER_EMAIL, "to": [RECIPIENT_EMAIL], "subject": subject, "text": body}
    )
    print(f"  {'Sent' if r.status_code in (200,201) else 'ERROR'} → {subject} ({r.status_code})")

def main():
    print(f"News Digest — {datetime.now().strftime('%d %b %Y %H:%M UTC')}")
    companies = clean_list(load_json("all_companies_master.json"))
    investors = clean_list(load_json("all_investors_master.json"))
    print(f"Loaded {len(companies)} companies, {len(investors)} investors")

    articles = fetch_articles()
    print(f"Fetched {len(articles)} articles")

    company_hits = build_hits(articles, companies)
    send_email(f"[Companies] News Digest {datetime.now().strftime('%d %b %Y')} — {len(company_hits)} match(es)",
               format_body(company_hits, "Companies"))

    investor_hits = build_hits(articles, investors)
    send_email(f"[Investors] News Digest {datetime.now().strftime('%d %b %Y')} — {len(investor_hits)} match(es)",
               format_body(investor_hits, "Investors"))

if __name__ == "__main__":
    main()
