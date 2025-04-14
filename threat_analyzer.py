from datetime import datetime
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from dateparser import parse  # For flexible date parsing
from .database import Database
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


class ThreatAnalyzer:

    def __init__(self):
        self.db = Database()
        self.hacker_news_url = "https://news.ycombinator.com/"

    def scrape_hacker_news(self):
        """Scrape latest news from Hacker News"""
        scraped_data = []
        headers = {
            'User-Agent':
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        try:
            # Implement retry logic for HTTP requests
            session = requests.Session()
            retry_strategy = Retry(total=3,
                                   backoff_factor=1,
                                   status_forcelist=[500, 502, 503, 504])
            session.mount('https://', HTTPAdapter(max_retries=retry_strategy))

            response = session.get(self.hacker_news_url,
                                   headers=headers,
                                   timeout=10)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                articles = soup.find_all(
                    'tr', class_='athing')[:5]  # Get the latest 5 stories

                for article in articles:
                    title = article.find('a', class_='storylink').get_text(
                        strip=True) if article.find(
                            'a', class_='storylink') else 'No Title'
                    link = article.find(
                        'a', class_='storylink')['href'] if article.find(
                            'a', class_='storylink') else 'No Link'

                    # Convert relative URLs to absolute URLs
                    link = urljoin(self.hacker_news_url, link)

                    # Parse the date using BeautifulSoup or another method
                    date = article.find('span', class_='age')
                    if date:
                        date = date.get_text()
                    else:
                        date = "No Date"

                    scraped_data.append({
                        'title': title,
                        'link': link,
                        'date': date
                    })

        except Exception as e:
            print(f"Error scraping Hacker News data: {str(e)}")
            return {'error': str(e)}

        return scraped_data

    def compare_and_get_latest(self, api_response, hacker_news_data):
        """Compare API response with Hacker News scraped data and return the latest one"""
        latest_data = {}

        # Extract timestamps from both sources
        api_timestamp = api_response.get('timestamp', None)
        hacker_news_timestamps = [
            parse(item['date']) if item.get('date') else datetime.min
            for item in hacker_news_data
        ]

        # Determine the latest source
        if api_timestamp and hacker_news_timestamps:
            api_time = datetime.strptime(api_timestamp, "%Y-%m-%dT%H:%M:%S.%f")
            hacker_news_latest_time = max(hacker_news_timestamps)

            if hacker_news_latest_time > api_time:
                latest_data = {
                    'source': 'Hacker News',
                    'data': hacker_news_data
                }
            else:
                latest_data = {'source': 'API', 'data': api_response}
        elif api_timestamp:
            latest_data = {'source': 'API', 'data': api_response}
        elif hacker_news_timestamps:
            latest_data = {'source': 'Hacker News', 'data': hacker_news_data}
        else:
            latest_data = {
                'source': 'Unknown',
                'data': 'No relevant threat data found'
            }

        return latest_data

    def store_response(self, query, response, tags):
        """Store analysis response and scraped data"""
        try:
            raw_response = {
                'timestamp': datetime.utcnow().isoformat(),
                'raw_api_response': response,
                'query': query
            }

            hacker_news_data = self.scrape_hacker_news()
            latest_data = self.compare_and_get_latest(response,
                                                      hacker_news_data)

            combined_response = {
                'latest_data': latest_data,
                'scraped_hacker_news': hacker_news_data,
                'raw_data': raw_response
            }

            return self.db.store_analysis(query, combined_response, tags)
        except Exception as e:
            print(f"Error storing analysis: {str(e)}")
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'query': query,
                'response': response,
                'tags': tags,
                'error': str(e)
            }

    def generate_threat_report(self, analysis_data):
        """Generate a formatted threat analysis report"""
        report = []
        report.append("📊 THREAT ANALYSIS REPORT")
        report.append("=" * 50)

        latest_data = analysis_data.get('latest_data', {})

        if latest_data['source'] == 'Hacker News':
            report.append("\n🌐 Source: Hacker News")
            hacker_news_data = latest_data['data']

            for item in hacker_news_data:
                report.append(f"\n🔹 {item['title']}")
                report.append(f"   🔗 Link: {item['link']}")
                report.append(f"   🕒 Date: {item['date']}")
                report.append("-" * 50)

        elif latest_data['source'] == 'API':
            report.append("\n📡 Source: API Response")
            report.append(str(latest_data['data']))

        else:
            report.append("\nNo threat analysis data available.")

        return "\n".join(report)


# In your main script or testing script
if __name__ == "__main__":
    analyzer = ThreatAnalyzer()

    # Test the web scraping
    hacker_news_data = analyzer.scrape_hacker_news()

    if 'error' in hacker_news_data:
        print(f"Error in scraping: {hacker_news_data['error']}")
    else:
        print("Scraped Hacker News Data:")
        for article in hacker_news_data:
            print(f"Title: {article['title']}")
            print(f"Link: {article['link']}")
            print(f"Date: {article['date']}")
            print("-" * 50)
