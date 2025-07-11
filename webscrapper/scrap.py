from requests_html import HTMLSession
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
import json
import time
from dateutil import parser
import dns.resolver
import requests


def resolve_domain(domain):
    """Resolve domain to IP using Google's DNS"""
    resolver = dns.resolver.Resolver()
    resolver.nameservers = ['8.8.8.8']
    try:
        answers = resolver.resolve(domain, 'A')
        return answers[0].address
    except Exception as e:
        print(f"Failed to resolve {domain}: {e}")
        return None


def get_bleeping_news():
    """Scrape latest news from BleepingComputer using requests-html"""
    domain = "www.bleepingcomputer.com"
    ip = resolve_domain(domain)
    if not ip:
        return []
    url = f"https://{domain}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Host": domain
    }
    news = []

    try:
        session = HTMLSession()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        session.mount('https://', HTTPAdapter(max_retries=retries))
        response = session.get(url, headers=headers, timeout=30, proxies={"http": None, "https": None})
        articles = response.html.find("#bc-home-news-main-wrap li")

        for art in articles:
            try:
                title = art.find("h4 a", first=True)
                if not title:
                    continue

                url_path = title.attrs["href"]
                full_url = urljoin(url, url_path)

                date_tag = art.find("li.bc_news_date", first=True)
                time_tag = art.find("li.bc_news_time", first=True)
                date_str = ""
                if date_tag and time_tag:
                    date_str = f"{date_tag.text} {time_tag.text}"
                elif date_tag:
                    date_str = date_tag.text

                article = {
                    "source": "BC",
                    "title": title.text.strip(),
                    "url": full_url,
                    "date": date_str.strip() if date_str else ""
                }

                try:
                    if article["date"]:
                        date_obj = parser.parse(article["date"])
                        article["date"] = date_obj.isoformat() + "Z"
                    else:
                        article["date"] = ""
                except Exception:
                    article["date"] = ""

                try:
                    article_response = session.get(full_url, headers=headers, timeout=30,
                                                   proxies={"http": None, "https": None})
                    article_soup = BeautifulSoup(article_response.text, 'html.parser')
                    summary_tag = article_soup.find("meta", attrs={"name": "description"})
                    article["summary"] = summary_tag["content"].strip() if summary_tag else ""
                    tags = []
                    tags_section = article_soup.find("div", class_="tags")
                    if tags_section:
                        tag_links = tags_section.find_all("a")
                        tags = [tag.text.strip() for tag in tag_links]
                    article["tags"] = tags
                    article["severity"] = None
                    article["cvssScore"] = None
                except Exception as e:
                    print(f"Error processing article {full_url}: {e}")
                    article["summary"] = ""
                    article["tags"] = []
                    article["severity"] = None
                    article["cvssScore"] = None

                news.append(article)
                time.sleep(1)
            except Exception:
                continue

        return news

    except Exception as e:
        print(f"⚠️ Error fetching BleepingComputer: {e}")
        return []


def get_zdi_blog_posts():
    """Scrape latest blog posts from Zero Day Initiative"""
    domain = "www.zerodayinitiative.com"
    ip = resolve_domain(domain)
    if not ip:
        return []
    base_url = f"https://{domain}"
    blog_url = f"{base_url}/blog"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Host": domain
    }
    posts = []

    try:
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        session.mount('https://', HTTPAdapter(max_retries=retries))
        response = session.get(blog_url, headers=headers, timeout=30, proxies={"http": None, "https": None})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        for post in soup.find_all("div", class_="contentBlock"):
            try:
                title_tag = post.find("h2", class_="title").find("a")
                title = title_tag.get_text(strip=True)
                link = title_tag["href"]
                full_link = urljoin(base_url, link)

                date_tag = post.find("li", class_="date")
                date_str = date_tag.get_text(strip=True) if date_tag else ""

                article = {
                    "source": "ZDI",
                    "title": title,
                    "url": full_link,
                    "date": date_str
                }

                try:
                    if article["date"]:
                        date_obj = parser.parse(article["date"])
                        article["date"] = date_obj.isoformat() + "Z"
                    else:
                        article["date"] = ""
                except Exception:
                    article["date"] = ""

                try:
                    article_response = session.get(full_link, headers=headers, timeout=30,
                                                   proxies={"http": None, "https": None})
                    article_soup = BeautifulSoup(article_response.text, 'html.parser')
                    summary_tag = article_soup.find("meta", attrs={"name": "description"})
                    article["summary"] = summary_tag["content"].strip() if summary_tag else ""
                    tags = []
                    tags_section = article_soup.find("div", class_="tags")
                    if tags_section:
                        tag_links = tags_section.find_all("a")
                        tags = [tag.text.strip() for tag in tag_links]
                    article["tags"] = tags
                    article["severity"] = None
                    article["cvssScore"] = None
                except Exception as e:
                    print(f"Error processing article {full_link}: {e}")
                    article["summary"] = ""
                    article["tags"] = []
                    article["severity"] = None
                    article["cvssScore"] = None

                posts.append(article)
                time.sleep(1)
            except Exception:
                continue

        return posts

    except Exception as e:
        print(f"⚠️ Error fetching Zero Day Initiative: {e}")
        return []


def get_hacker_news():
    """Scrape headlines from The Hacker News"""
    domain = "thehackernews.com"
    ip = resolve_domain(domain)
    if not ip:
        return []
    url = f"https://{domain}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Host": domain
    }
    news = []

    try:
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        session.mount('https://', HTTPAdapter(max_retries=retries))
        response = session.get(url, headers=headers, timeout=30, proxies={"http": None, "https": None})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        for headline in soup.find_all("h2", class_="home-title"):
            try:
                title = headline.get_text(strip=True)
                link = headline.find_parent("a")["href"]

                date_tag = headline.find_next("span", class_="h-datetime")
                date_str = date_tag.get_text(strip=True) if date_tag else ""

                article = {
                    "source": "THN",
                    "title": title,
                    "url": link,
                    "date": date_str
                }

                try:
                    if article["date"]:
                        date_obj = parser.parse(article["date"])
                        article["date"] = date_obj.isoformat() + "Z"
                    else:
                        article["date"] = ""
                except Exception:
                    article["date"] = ""

                try:
                    article_response = session.get(link, headers=headers, timeout=30,
                                                   proxies={"http": None, "https": None})
                    article_soup = BeautifulSoup(article_response.text, 'html.parser')
                    summary_tag = article_soup.find("meta", attrs={"name": "description"})
                    article["summary"] = summary_tag["content"].strip() if summary_tag else ""
                    tags = []
                    tags_section = article_soup.find("div", class_="tags")
                    if tags_section:
                        tag_links = tags_section.find_all("a")
                        tags = [tag.text.strip() for tag in tag_links]
                    article["tags"] = tags
                    article["severity"] = None
                    article["cvssScore"] = None
                except Exception as e:
                    print(f"Error processing article {link}: {e}")
                    article["summary"] = ""
                    article["tags"] = []
                    article["severity"] = None
                    article["cvssScore"] = None

                news.append(article)
                time.sleep(1)
            except Exception:
                continue

        return news

    except Exception as e:
        print(f"⚠️ Error fetching The Hacker News: {e}")
        return []


def scrape_all_sources():
    """Aggregate news from all sources"""
    print("\n🔄 Fetching news from all sources...")
    sources = [
        ("Bleeping Computer", get_bleeping_news),
        ("Zero Day Initiative", get_zdi_blog_posts),
        ("The Hacker News", get_hacker_news)
    ]

    all_articles = []
    for name, scraper in sources:
        try:
            articles = scraper()
            print(f"✅ Found {len(articles)} articles from {name}")
            all_articles.extend(articles)
        except Exception as e:
            print(f"⚠️ Failed to fetch from {name}: {str(e)}")

    for i, article in enumerate(all_articles, 1):
        article["id"] = str(i)

    return [dict(article, link=article.pop("url")) for article in all_articles]


def display_news(articles):
    """Display articles in a clean terminal format"""
    if not articles:
        print("\nNo articles found from any sources.")
        return

    print("\n" + "=" * 50)
    print("🔷 CYBERSECURITY NEWS AGGREGATOR 🔷")
    print(f"📅 Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50 + "\n")

    sources = {}
    for article in articles:
        source = article["source"]
        if source not in sources:
            sources[source] = []
        sources[source].append(article)

    for source, articles in sources.items():
        print(f"\n📌 {source.upper()}")
        print("-" * (len(source) + 2))

        for i, article in enumerate(articles, 1):
            print(f"\n{i}. {article['title']}")
            print(f"   🔗 {article['link']}")
            if article["date"]:
                print(f"   📅 {article['date']}")

    print("\n" + "=" * 50)
    print(f"Total articles: {len(articles)}")
    print("=" * 50)


def save_to_json(articles, filename="cybersecurity_news.json"):
    """Save articles to JSON file"""
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(articles, f, indent=2, ensure_ascii=False)
        print(f"\n✅ Saved {len(articles)} articles to {filename}")
    except Exception as e:
        print(f"⚠️ Error saving to JSON: {e}")


if __name__ == "__main__":
    all_articles = scrape_all_sources()
    display_news(all_articles)
    save_option = input("\nSave to JSON file? (y/n): ").strip().lower()
    if save_option == "y":
        filename = input("Filename (default: cybersecurity_news.json): ").strip()
        save_to_json(all_articles, filename or "cybersecurity_news.json")
