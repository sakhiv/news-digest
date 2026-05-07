#!/usr/bin/env python3
import json, re, time, os
from datetime import datetime, timezone, timedelta
import feedparser
import requests

SCRIPT_DIR       = os.path.dirname(os.path.abspath(__file__))
SHEET_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwk_tmev8Kuz7n09l-hgOYnoc4Idndmk-6n_RMt-aUMVQKRx1I3qLEN5nNNmlUQPCPzHw/exec"

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
                    'pub':     pub.strftime('%d %b %Y') if pub else datetime.now().strftime('%d %b %Y')
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

def post_to_sheet(hits, label, run_date):
    if not hits:
        print(f"  No matches for {label}, nothing to post.")
        return
    rows = []
    for h in hits:
        rows.append({
            'run_date': run_date,
            'date':     h['pub'],
            'type':     label,
            'title':    h['title'],
            'matched':  ', '.join(h['matches']),
            'source':   h['source'],
            'link':     h['link']
        })
    r = requests.post(
        SHEET_SCRIPT_URL,
        headers={'Content-Type': 'text/plain'},
        data=json.dumps({'rows': rows}),
        allow_redirects=True
    )
    print(f"  Sheet post [{label}]: {r.status_code} — {len(rows)} rows added")

def main():
    run_date = datetime.now().strftime('%d %b %Y')
    print(f"News Digest — {datetime.now().strftime('%d %b %Y %H:%M UTC')}")
    companies = clean_list(load_json("all_companies_master.json"))
    investors = clean_list(load_json("all_investors_master.json"))
    print(f"Loaded {len(companies)} companies, {len(investors)} investors")

    articles = fetch_articles()
    print(f"Fetched {len(articles)} articles")

    company_hits = build_hits(articles, companies)
    print(f"Company matches: {len(company_hits)}")
    post_to_sheet(company_hits, "Company", run_date)

    investor_hits = build_hits(articles, investors)
    print(f"Investor matches: {len(investor_hits)}")
    post_to_sheet(investor_hits, "Investor", run_date)

    print("Done.")

if __name__ == "__main__":
    main()
