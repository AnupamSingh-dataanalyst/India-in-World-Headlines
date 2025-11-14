import feedparser
import requests
import json
from datetime import datetime
import re

class IndiaNewsBot:
    def __init__(self, discord_webhook_url):
        self.webhook_url = discord_webhook_url
        self.news_sources = {
            'The Guardian': 'https://www.theguardian.com/world/rss',
            'New York Times': 'https://rss.nytimes.com/services/xml/rss/nyt/World.xml',
            'Dawn (Pakistan)': 'https://www.dawn.com/feeds/home'
        }
        
    def fetch_articles(self):
        """Fetch articles from all news sources"""
        all_articles = []
        
        for source_name, rss_url in self.news_sources.items():
            try:
                print(f"Fetching from {source_name}...")
                feed = feedparser.parse(rss_url)
                
                for entry in feed.entries:
                    title = entry.get('title', '')
                    
                    # Check if "India" is mentioned in title (case insensitive)
                    if re.search(r'\bIndia\b', title, re.IGNORECASE):
                        article = {
                            'source': source_name,
                            'title': title,
                            'link': entry.get('link', ''),
                            'published': entry.get('published', 'Date not available'),
                            'summary': entry.get('summary', '')[:300]  # First 300 chars for analysis
                        }
                        all_articles.append(article)
                        print(f"  ✓ Found: {title[:60]}...")
                
            except Exception as e:
                print(f"Error fetching from {source_name}: {e}")
        
        return all_articles
    
    def analyze_with_ai(self, article):
        """
        Analyze article sentiment and category using Claude API
        """
        try:
            prompt = f"""Analyze this news article title and summary about India:

Title: {article['title']}
Summary: {article['summary']}

Provide analysis in this EXACT JSON format (no other text):
{{
    "sentiment": "positive" or "negative" or "neutral",
    "category": "Politics" or "Economy" or "Sports" or "Technology" or "Defense" or "Diplomacy" or "Other",
    "reasoning": "brief 1 sentence explanation"
}}"""

            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"Content-Type": "application/json"},
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 1000,
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data['content'][0]['text'].strip()
                
                # Remove markdown code blocks if present
                content = re.sub(r'```json\s*|\s*```', '', content).strip()
                
                analysis = json.loads(content)
                return analysis
            else:
                print(f"API error: {response.status_code}")
                return self.fallback_analysis(article)
                
        except Exception as e:
            print(f"AI analysis error: {e}")
            return self.fallback_analysis(article)
    
    def fallback_analysis(self, article):
        """Simple keyword-based analysis if AI fails"""
        title_lower = article['title'].lower()
        summary_lower = article['summary'].lower()
        text = title_lower + " " + summary_lower
        
        # Sentiment keywords
        positive_words = ['success', 'growth', 'win', 'boost', 'improve', 'achievement', 'celebrates']
        negative_words = ['crisis', 'conflict', 'concern', 'attack', 'threat', 'decline', 'warns']
        
        pos_count = sum(1 for word in positive_words if word in text)
        neg_count = sum(1 for word in negative_words if word in text)
        
        if pos_count > neg_count:
            sentiment = "positive"
        elif neg_count > pos_count:
            sentiment = "negative"
        else:
            sentiment = "neutral"
        
        # Category keywords
        if any(word in text for word in ['election', 'government', 'minister', 'parliament', 'party']):
            category = "Politics"
        elif any(word in text for word in ['economy', 'trade', 'gdp', 'market', 'business']):
            category = "Economy"
        elif any(word in text for word in ['cricket', 'sport', 'match', 'olympic']):
            category = "Sports"
        elif any(word in text for word in ['tech', 'digital', 'ai', 'startup']):
            category = "Technology"
        elif any(word in text for word in ['military', 'defense', 'army', 'border']):
            category = "Defense"
        else:
            category = "Other"
        
        return {
            "sentiment": sentiment,
            "category": category,
            "reasoning": "Keyword-based analysis"
        }
    
    def get_emoji(self, sentiment, category):
        """Get appropriate emojis"""
        sentiment_emoji = {
            'positive': '🟢',
            'negative': '🔴',
            'neutral': '🟡'
        }
        
        category_emoji = {
            'Politics': '🏛️',
            'Economy': '💰',
            'Sports': '⚽',
            'Technology': '💻',
            'Defense': '🛡️',
            'Diplomacy': '🤝',
            'Other': '📰'
        }
        
        return sentiment_emoji.get(sentiment, '⚪'), category_emoji.get(category, '📰')
    
    def format_discord_message(self, articles_with_analysis):
        """Format articles into Discord embed format"""
        if not articles_with_analysis:
            return {
                "username": "What is World is writng about India?",
                "avatar_url": "https://flagcdn.com/w160/in.png",
                "embeds": [{
                    "title": "📰 News Update",
                    "description": "No articles mentioning India found in the last check.",
                    "color": 3447003,
                    "timestamp": datetime.utcnow().isoformat()
                }]
            }
        
        embeds = []
        
        # Header embed
        embeds.append({
            "title": "🌍 What is world saying about India",
            "description": f"Found **{len(articles_with_analysis)}** articles mentioning India",
            "color": 16744192,  # Orange color
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Article embeds
        for item in articles_with_analysis:
            article = item['article']
            analysis = item['analysis']
            
            sentiment_emoji, category_emoji = self.get_emoji(
                analysis['sentiment'], 
                analysis['category']
            )
            
            # Color based on sentiment
            color_map = {
                'positive': 5763719,    # Green
                'negative': 15548997,   # Red
                'neutral': 16776960     # Yellow
            }
            
            embed = {
                "title": f"{category_emoji} {article['title'][:200]}",
                "url": article['link'],
                "color": color_map.get(analysis['sentiment'], 3447003),
                "fields": [
                    {
                        "name": "📰 Source",
                        "value": article['source'],
                        "inline": True
                    },
                    {
                        "name": f"{sentiment_emoji} Sentiment",
                        "value": analysis['sentiment'].capitalize(),
                        "inline": True
                    },
                    {
                        "name": "🏷️ Category",
                        "value": analysis['category'],
                        "inline": True
                    },
                    {
                        "name": "📅 Published",
                        "value": article['published'][:50],
                        "inline": False
                    }
                ],
                "footer": {
                    "text": analysis.get('reasoning', '')[:100]
                }
            }
            embeds.append(embed)
        
        payload = {
            "username": "What is world saying about India",
            "avatar_url": "https://flagcdn.com/w160/in.png",
            "embeds": embeds
        }
        
        return payload
    
    def send_to_discord(self, payload):
        """Send formatted message to Discord webhook"""
        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 204:
                print("✓ Successfully sent to Discord!")
                return True
            else:
                print(f"Discord webhook error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"Error sending to Discord: {e}")
            return False
    
    def run(self):
        """Main execution"""
        print("="*60)
        print("What is world saying about India - News Bot")
        print("="*60)
        
        # Fetch articles
        print("\n1. Fetching articles from news sources...")
        articles = self.fetch_articles()
        print(f"\n✓ Found {len(articles)} articles mentioning India\n")
        
        if not articles:
            print("No articles found. Sending notification...")
            payload = self.format_discord_message([])
            self.send_to_discord(payload)
            return
        
        # Analyze with AI
        print("2. Analyzing articles with AI...")
        articles_with_analysis = []
        
        for article in articles:
            print(f"\n  Analyzing: {article['title'][:60]}...")
            analysis = self.analyze_with_ai(article)
            print(f"    Sentiment: {analysis['sentiment']} | Category: {analysis['category']}")
            
            articles_with_analysis.append({
                'article': article,
                'analysis': analysis
            })
        
        # Send to Discord
        print("\n3. Sending to Discord...")
        payload = self.format_discord_message(articles_with_analysis)
        self.send_to_discord(payload)
        
        print("\n" + "="*60)
        print("Bot execution completed!")
        print("="*60)


# ============================================
# USAGE
# ============================================

if __name__ == "__main__":
    import os
    # Get webhook from environment variable (GitHub Secret)
    DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK')
    
    if not DISCORD_WEBHOOK_URL:
        print("ERROR: DISCORD_WEBHOOK environment variable not set!")
        exit(1)
