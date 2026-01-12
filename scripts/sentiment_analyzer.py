#!/usr/bin/env python3
"""
Sentiment Analyzer
Analyzes reviews to identify top complaint reasons using NLP
"""

import os
import json
import re
from collections import Counter
from datetime import datetime
import pandas as pd
import numpy as np

from config_loader import load_config, get_data_dir, get_output_dir, ensure_directories

# Optional NLP imports
try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False

try:
    import nltk
    from nltk.tokenize import word_tokenize
    from nltk.corpus import stopwords
    from nltk.stem import WordNetLemmatizer
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

try:
    from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
    from sklearn.decomposition import LatentDirichletAllocation
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

# Complaint categories
COMPLAINT_CATEGORIES = {
    "price_value": ["expensive", "overpriced", "pricey", "cost", "money", "worth", "value", "rip off"],
    "customer_service": ["rude", "unhelpful", "ignored", "staff", "employee", "service", "attitude", "dismissive"],
    "product_quality": ["quality", "cheap", "broke", "defect", "damage", "poor", "disappointing"],
    "scent_issues": ["smell", "scent", "fragrance", "odor", "throw", "weak scent", "overpowering"],
    "burn_quality": ["burn", "wick", "tunnel", "uneven", "smoke", "soot", "flame"],
    "longevity": ["last", "hour", "burn time", "short", "quick", "duration"],
    "shipping": ["shipping", "package", "box", "arrived", "broken", "damaged", "delivery"],
    "store_experience": ["store", "location", "crowded", "wait", "line", "parking"],
    "return_refund": ["return", "refund", "exchange", "policy", "money back"],
    "authenticity": ["fake", "authentic", "counterfeit", "real", "genuine"]
}


class SentimentAnalyzer:
    def __init__(self, config=None):
        self.config = config or load_config()
        self.reviews_df = None
        self.negative_reviews = None
        self.analysis = {}
        self.data_dir = get_data_dir() / "reviews"
        self.output_dir = get_output_dir() / "analysis"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if NLTK_AVAILABLE:
            try:
                nltk.download('punkt', quiet=True)
                nltk.download('stopwords', quiet=True)
                nltk.download('wordnet', quiet=True)
                self.stop_words = set(stopwords.words('english'))
                self.lemmatizer = WordNetLemmatizer()
            except:
                self.stop_words = set()
                self.lemmatizer = None

    def load_reviews(self):
        """Load reviews from data directory"""
        print("📂 Loading reviews...")

        # Try JSON first
        json_file = self.data_dir / "all_reviews.json"
        csv_file = self.data_dir / "all_reviews.csv"

        if json_file.exists():
            with open(json_file, 'r') as f:
                data = json.load(f)
            self.reviews_df = pd.DataFrame(data)
            print(f"✅ Loaded {len(self.reviews_df)} reviews from JSON")
        elif csv_file.exists():
            self.reviews_df = pd.read_csv(csv_file)
            print(f"✅ Loaded {len(self.reviews_df)} reviews from CSV")
        else:
            print("❌ No review files found!")
            return False

        return True

    def calculate_sentiment(self, text):
        """Calculate sentiment score"""
        if not text or not isinstance(text, str):
            return 0

        if TEXTBLOB_AVAILABLE:
            return TextBlob(text).sentiment.polarity
        else:
            # Simple keyword-based
            negative = ["bad", "terrible", "awful", "horrible", "poor", "worst", "disappointed", "hate", "waste"]
            positive = ["great", "amazing", "love", "excellent", "best", "wonderful", "fantastic", "perfect"]

            text_lower = text.lower()
            neg = sum(1 for w in negative if w in text_lower)
            pos = sum(1 for w in positive if w in text_lower)

            if neg + pos == 0:
                return 0
            return (pos - neg) / (pos + neg)

    def filter_negative(self):
        """Filter to negative reviews only"""
        print("\n🔍 Filtering negative reviews...")

        threshold = self.config.get('analysis', {}).get('sentiment_threshold', -0.1)
        min_rating = self.config.get('analysis', {}).get('min_rating_negative', 3)

        self.reviews_df['sentiment'] = self.reviews_df['text'].apply(self.calculate_sentiment)

        if 'rating' in self.reviews_df.columns:
            mask = (self.reviews_df['rating'] <= min_rating) | (self.reviews_df['sentiment'] < threshold)
        else:
            mask = self.reviews_df['sentiment'] < threshold

        self.negative_reviews = self.reviews_df[mask].copy()
        print(f"✅ Found {len(self.negative_reviews)} negative reviews")

        return self.negative_reviews

    def categorize_complaint(self, text):
        """Categorize complaint by keywords"""
        if not text:
            return ["other"]

        text_lower = text.lower()
        categories = []

        for category, keywords in COMPLAINT_CATEGORIES.items():
            for kw in keywords:
                if kw in text_lower:
                    categories.append(category)
                    break

        return categories if categories else ["other"]

    def preprocess_text(self, text):
        """Clean and preprocess text"""
        if not text:
            return ""

        text = text.lower()
        text = re.sub(r'[^a-zA-Z\s]', '', text)

        if NLTK_AVAILABLE and self.lemmatizer:
            try:
                tokens = word_tokenize(text)
                tokens = [self.lemmatizer.lemmatize(t) for t in tokens
                         if t not in self.stop_words and len(t) > 2]
                return ' '.join(tokens)
            except:
                pass

        return text

    def extract_key_phrases(self, texts, n=20):
        """Extract key phrases using TF-IDF"""
        if not SKLEARN_AVAILABLE or not texts:
            return []

        try:
            vectorizer = TfidfVectorizer(
                max_features=100,
                ngram_range=(1, 3),
                stop_words='english',
                min_df=2
            )
            matrix = vectorizer.fit_transform(texts)
            features = vectorizer.get_feature_names_out()
            scores = np.array(matrix.mean(axis=0)).flatten()
            top_idx = scores.argsort()[-n:][::-1]
            return [(features[i], scores[i]) for i in top_idx]
        except:
            return []

    def topic_modeling(self, texts, n_topics=None):
        """Extract topics using LDA"""
        if not SKLEARN_AVAILABLE or not texts or len(texts) < 5:
            return []

        if n_topics is None:
            n_topics = self.config.get('analysis', {}).get('n_topics', 10)

        try:
            vectorizer = CountVectorizer(max_features=200, stop_words='english', min_df=2)
            matrix = vectorizer.fit_transform(texts)
            features = vectorizer.get_feature_names_out()

            lda = LatentDirichletAllocation(
                n_components=min(n_topics, len(texts) // 2),
                random_state=42,
                max_iter=20
            )
            lda.fit(matrix)

            topics = []
            for idx, topic in enumerate(lda.components_):
                top_idx = topic.argsort()[-8:][::-1]
                topics.append({
                    "topic_id": idx + 1,
                    "keywords": [features[i] for i in top_idx]
                })
            return topics
        except:
            return []

    def analyze(self):
        """Run full analysis"""
        print("\n📊 Analyzing complaints...")

        if self.negative_reviews is None or len(self.negative_reviews) == 0:
            print("❌ No negative reviews to analyze")
            return {}

        # Categorize
        print("   Categorizing...")
        self.negative_reviews['categories'] = self.negative_reviews['text'].apply(self.categorize_complaint)

        category_counts = Counter()
        for cats in self.negative_reviews['categories']:
            for c in cats:
                category_counts[c] += 1

        # Preprocess
        print("   Preprocessing...")
        self.negative_reviews['processed'] = self.negative_reviews['text'].apply(self.preprocess_text)
        texts = self.negative_reviews['processed'].dropna().tolist()

        # Key phrases
        print("   Extracting phrases...")
        n_phrases = self.config.get('analysis', {}).get('n_key_phrases', 20)
        phrases = self.extract_key_phrases(texts, n_phrases)

        # Topics
        print("   Topic modeling...")
        topics = self.topic_modeling(texts)

        # By brand
        brand_analysis = {}
        if 'brand' in self.negative_reviews.columns:
            for brand in self.negative_reviews['brand'].unique():
                brand_reviews = self.negative_reviews[self.negative_reviews['brand'] == brand]
                brand_cats = Counter()
                for cats in brand_reviews['categories']:
                    for c in cats:
                        brand_cats[c] += 1
                brand_analysis[brand] = dict(brand_cats.most_common(10))

        # Sample complaints
        samples = {}
        for category in list(category_counts.keys())[:10]:
            cat_reviews = self.negative_reviews[
                self.negative_reviews['categories'].apply(lambda x: category in x)
            ]['text'].head(3).tolist()
            samples[category] = cat_reviews

        self.analysis = {
            "total_negative": len(self.negative_reviews),
            "category_counts": dict(category_counts.most_common()),
            "top_10": dict(category_counts.most_common(10)),
            "key_phrases": phrases[:20],
            "topics": topics,
            "by_brand": brand_analysis,
            "samples": samples
        }

        return self.analysis

    def generate_report(self):
        """Generate analysis report"""
        print("\n📝 Generating report...")

        report = []
        report.append("=" * 70)
        report.append("COMPETITOR REVIEW SENTIMENT ANALYSIS")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 70)
        report.append("")

        report.append(f"Total reviews analyzed: {len(self.reviews_df) if self.reviews_df is not None else 0}")
        report.append(f"Negative reviews: {self.analysis.get('total_negative', 0)}")
        report.append("")

        report.append("TOP 10 COMPLAINT CATEGORIES")
        report.append("-" * 40)

        for rank, (cat, count) in enumerate(self.analysis.get('top_10', {}).items(), 1):
            pct = (count / max(self.analysis.get('total_negative', 1), 1)) * 100
            report.append(f"{rank}. {cat.upper().replace('_', ' ')}: {count} ({pct:.1f}%)")

            samples = self.analysis.get('samples', {}).get(cat, [])
            if samples:
                for s in samples[:2]:
                    truncated = s[:150] + "..." if len(s) > 150 else s
                    report.append(f"   - \"{truncated}\"")
            report.append("")

        report.append("\nKEY PHRASES")
        report.append("-" * 40)
        for phrase, score in self.analysis.get('key_phrases', [])[:15]:
            report.append(f"  • {phrase}")

        report.append("\nBY BRAND")
        report.append("-" * 40)
        for brand, cats in self.analysis.get('by_brand', {}).items():
            report.append(f"\n{brand}:")
            for cat, count in list(cats.items())[:5]:
                report.append(f"  • {cat}: {count}")

        report.append("\n" + "=" * 70)

        report_text = "\n".join(report)

        # Save
        report_file = self.output_dir / "sentiment_report.txt"
        with open(report_file, 'w') as f:
            f.write(report_text)
        print(f"📄 Report saved: {report_file}")

        json_file = self.output_dir / "analysis.json"
        with open(json_file, 'w') as f:
            json.dump(self.analysis, f, indent=2, default=str)
        print(f"📄 JSON saved: {json_file}")

        if self.negative_reviews is not None:
            csv_file = self.output_dir / "negative_reviews.csv"
            self.negative_reviews.to_csv(csv_file, index=False)
            print(f"📄 CSV saved: {csv_file}")

        print("\n" + report_text)
        return report_text

    def run(self):
        """Run complete analysis pipeline"""
        print("=" * 60)
        print("🔬 Sentiment Analysis Pipeline")
        print("=" * 60)

        ensure_directories()

        if not self.load_reviews():
            return None

        self.filter_negative()
        self.analyze()
        return self.generate_report()


def main():
    analyzer = SentimentAnalyzer()
    analyzer.run()


if __name__ == "__main__":
    main()
