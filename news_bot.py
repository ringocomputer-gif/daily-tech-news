import os, requests, feedparser
from datetime import datetime, timedelta
from google import genai

RSS_FEEDS = [
    ("전자신문", "https://rss.etnews.com/Section901.xml"),
    ("디일렉", "https://www.thelec.kr/rss/allArticle.xml"),
    ("ZDNet Korea", "https://zdnet.co.kr/rss/"),
    ("한국경제IT", "https://www.hankyung.com/feed/it"),
    ("전자신문SW", "https://rss.etnews.com/Section902.xml"),
    ("The Verge", "https://www.theverge.com/rss/index.xml"),
    ("GSMArena", "https://www.gsmarena.com/rss-news-reviews.php3"),
    ("AnandTech", "https://www.anandtech.com/rss/"),
    ("Tom's Hardware", "https://www.tomshardware.com/feeds/all"),
    ("9to5Mac", "https://9to5mac.com/feed/"),
]

def fetch_news():
    yesterday = datetime.now() - timedelta(days=1)
    articles = []
    for source, url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]:
                published = datetime(*entry.published_parsed[:6]) if hasattr(entry, 'published_parsed') and entry.published_parsed else datetime.now()
                if published > yesterday:
                    articles.append({
                        "source": source,
                        "title": entry.title,
                        "link": entry.link,
                        "summary": getattr(entry, 'summary', '')[:200]
                    })
        except Exception as e:
            print(f"{source} 수집 오류: {e}")
    return articles

def summarize_with_gemini(articles):
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    articles_text = "\n".join([
        f"[{a['source']}] {a['title']}\n{a['summary']}\n링크: {a['link']}"
        for a in articles
    ])
    prompt = f"""다음은 어제 하루 동안의 전자IT 뉴스입니다. 핵심 뉴스를 분야별로 한국어로 정리해주세요.

{articles_text}

형식:
📱 스마트폰 신제품 & 동향
- 뉴스 요약 (출처) - 링크

💻 컴퓨터 & 부품 신제품 & 동향
- 뉴스 요약 (출처) - 링크

💾 반도체 & 디스플레이
- 뉴스 요약 (출처) - 링크

🤖 AI & 소프트웨어
- 뉴스 요약 (출처) - 링크

각 분야 3개 이내로, 해외 뉴스는 한국어로 번역해서 한 줄 요약으로 작성해주세요."""
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text

def split_message(text, limit=900):
    lines = text.split("\n")
    parts = []
    current = ""
    for line in lines:
        if len(current) + len(line) + 1 > limit:
            parts.append(current.strip())
            current = line + "\n"
        else:
            current += line + "\n"
    if current.strip():
        parts.append(current.strip())
    return parts

def get_kakao_token():
    resp = requests.post("https://kauth.kakao.com/oauth/token", data={
        "grant_type": "refresh_token",
        "client_id": os.environ["KAKAO_REST_API_KEY"],
        "refresh_token": os.environ["KAKAO_REFRESH_TOKEN"],
    })
    return resp.json()["access_token"]

def send_kakao(message):
    token = get_kakao_token()
    today = datetime.now().strftime("%m/%d")
    import json
    parts = split_message(message)
    for i, part in enumerate(parts):
        prefix = f"📰 [{today}] 전자IT 뉴스 브리핑" if i == 0 else f"📰 [{today}] 전자IT 뉴스 브리핑 (계속)"
        template = {
            "object_type": "text",
            "text": f"{prefix}\n\n{part}",
            "link": {}
        }
        resp = requests.post(
            "https://kapi.kakao.com/v2/api/talk/memo/default/send",
            headers={"Authorization": f"Bearer {token}"},
            data={"template_object": json.dumps(template)}
        )
        print(f"카카오 전송 결과 ({i+1}/{len(parts)}): {resp.status_code}")

if __name__ == "__main__":
    print("뉴스 수집 중...")
    articles = fetch_news()
    print(f"{len(articles)}개 기사 수집 완료")
    if not articles:
        print("수집된 기사가 없습니다.")
    else:
        print("Gemini로 요약 중...")
        summary = summarize_with_gemini(articles)
        print("카카오톡 전송 중...")
        send_kakao(summary)
        print("완료!")
