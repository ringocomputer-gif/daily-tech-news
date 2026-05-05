import os, requests, feedparser
from datetime import datetime, timedelta
from anthropic import Anthropic

RSS_FEEDS = [
    ("전자신문", "https://www.etnews.com/rss/allArticle.xml"),
    ("디일렉", "https://www.thelec.kr/rss/allArticle.xml"),
    ("ZDNet Korea", "https://zdnet.co.kr/rss/"),
    ("IT조선", "https://it.chosun.com/rss/"),
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

def summarize_with_claude(articles):
    client = Anthropic()
    articles_text = "\n".join([
        f"[{a['source']}] {a['title']}\n{a['summary']}\n링크: {a['link']}"
        for a in articles
    ])
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{
            "role": "user",
            "content": f"""다음은 어제 하루 동안의 전자IT 뉴스입니다. 핵심 뉴스를 분야별로 정리해주세요.

{articles_text}

형식:
📱 스마트폰/가전
- 뉴스 요약 (출처) - 링크

💾 반도체/디스플레이
- 뉴스 요약 (출처) - 링크

🤖 AI/소프트웨어
- 뉴스 요약 (출처) - 링크

각 분야 3개 이내로, 한 줄 요약으로 작성해주세요."""
        }]
    )
    return response.content[0].text

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
    template = {
        "object_type": "text",
        "text": f"📰 [{today}] 전자IT 뉴스 브리핑\n\n{message}",
        "link": {
            "web_url": "https://www.etnews.com",
            "mobile_web_url": "https://www.etnews.com"
        }
    }
    resp = requests.post(
        "https://kapi.kakao.com/v2/api/talk/memo/default/send",
        headers={"Authorization": f"Bearer {token}"},
        data={"template_object": json.dumps(template)}
    )
    print("카카오 전송 결과:", resp.status_code, resp.text)

if __name__ == "__main__":
    print("뉴스 수집 중...")
    articles = fetch_news()
    print(f"{len(articles)}개 기사 수집 완료")
    if not articles:
        print("수집된 기사가 없습니다.")
    else:
        print("Claude로 요약 중...")
        summary = summarize_with_claude(articles)
        print("카카오톡 전송 중...")
        send_kakao(summary)
        print("완료!")
