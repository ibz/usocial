from bs4 import BeautifulSoup
import nltk
from nltk.corpus import stopwords
from nltk.stem.porter import PorterStemmer
from nltk.tokenize import RegexpTokenizer
from nltk.stem.wordnet import WordNetLemmatizer
import re
from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer

from musocial import models


def extract_topn_from_vector(feature_names, sorted_items, topn=10):
    """get the feature names and tf-idf score of top n items"""
    sorted_items = sorted_items[:topn]
    score_vals = []
    feature_vals = []
    for idx, score in sorted_items:
        score_vals.append(round(score, 3))
        feature_vals.append(feature_names[idx])
    results = {}
    for idx in range(len(feature_vals)):
        results[feature_vals[idx]]=score_vals[idx]
    return results

def sort_coo(coo_matrix):
    tuples = zip(coo_matrix.col, coo_matrix.data)
    return sorted(tuples, key=lambda x: (x[1], x[0]), reverse=True)

def main():
    stop_words = set(stopwords.words("english"))
    feed_items = {}
    for feed in models.Feed.query.all():
        for item in feed.items:
            if item.content_from_feed:
                # TODO: check lang
                feed_items.setdefault(feed.id, []).append(item)
    corpus = {}
    for feed_id, items in feed_items.items():
        feed_texts = []
        for item in items:
            soup = BeautifulSoup(item.content_from_feed, 'html.parser')
            text = re.sub('[^a-zA-Z]', ' ', soup.text)
            text = text.lower()
            text = re.sub("&lt;/?.*?&gt;", " &lt;&gt; ", text)
            text = re.sub("(\\d|\\W)+", " ", text)
            text = text.split()
            ps = PorterStemmer() # TODO: ?
            lem = WordNetLemmatizer()
            text = [lem.lemmatize(word) for word in text if word not in stop_words]
            text = " ".join(text)
            feed_texts.append(text)
        corpus[feed_id] = " ".join(feed_texts)
    cv = CountVectorizer(max_df=0.8, stop_words=stop_words, max_features=10000, ngram_range=(1, 3))
    X = cv.fit_transform(list(corpus.values()))
    tfidf_transformer = TfidfTransformer(smooth_idf=True, use_idf=True)
    tfidf_transformer.fit(X)
    feature_names = cv.get_feature_names()

    for feed_id, doc in corpus.items():
        tf_idf_vector = tfidf_transformer.transform(cv.transform([doc]))
        sorted_items = sort_coo(tf_idf_vector.tocoo())
        keywords = extract_topn_from_vector(feature_names, sorted_items, 5)
        feed = models.Feed.query.filter_by(id=feed_id).first()
        print(f"Title: {feed.title}\nURL: {feed.url}\nKeywords: {keywords}")

if __name__ == '__main__':
    main()
