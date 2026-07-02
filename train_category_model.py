"""
Builds category_model.pkl as a self-contained scikit-learn Pipeline
(TfidfVectorizer -> MultinomialNB) so it can classify raw merchant/description
text directly -- no separate vectorizer file to keep in sync.

The original category_model.pkl in this repo was a bare MultinomialNB with no
accompanying vectorizer, so it couldn't actually transform text input. This
script replaces it with a working pipeline trained on a seed dataset covering
the four existing categories (Travel, Food, Office, Other). Run this again any
time you want to retrain on more data.
"""
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

SEED_DATA = [
    # Travel
    ("uber ride to airport", "Travel"),
    ("ola cab fare", "Travel"),
    ("indigo flight ticket booking", "Travel"),
    ("irctc train ticket", "Travel"),
    ("petrol pump fuel", "Travel"),
    ("metro card recharge", "Travel"),
    ("hotel booking makemytrip", "Travel"),
    ("taxi fare downtown", "Travel"),
    ("parking fee", "Travel"),
    ("toll plaza payment", "Travel"),
    # Food
    ("swiggy food order", "Food"),
    ("zomato dinner delivery", "Food"),
    ("starbucks coffee", "Food"),
    ("dominos pizza", "Food"),
    ("restaurant bill lunch", "Food"),
    ("grocery store bigbasket", "Food"),
    ("supermarket vegetables fruits", "Food"),
    ("mcdonalds burger meal", "Food"),
    ("cafe snacks", "Food"),
    ("bakery bread cake", "Food"),
    # Office
    ("staples office supplies", "Office"),
    ("printer ink cartridge", "Office"),
    ("stationery pens notebooks", "Office"),
    ("software subscription license", "Office"),
    ("coworking space rent", "Office"),
    ("courier shipping charges", "Office"),
    ("laptop accessories amazon", "Office"),
    ("internet broadband bill", "Office"),
    ("conference registration fee", "Office"),
    ("business cards printing", "Office"),
    # Other
    ("electricity bill payment", "Other"),
    ("mobile recharge", "Other"),
    ("movie tickets pvr", "Other"),
    ("gym membership fee", "Other"),
    ("pharmacy medicine purchase", "Other"),
    ("clothing store purchase", "Other"),
    ("gift shop present", "Other"),
    ("salon haircut", "Other"),
    ("subscription netflix", "Other"),
    ("miscellaneous purchase", "Other"),
]

def train_and_save(path="category_model.pkl"):
    texts, labels = zip(*SEED_DATA)
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
        ("clf", MultinomialNB()),
    ])
    pipeline.fit(texts, labels)
    with open(path, "wb") as f:
        pickle.dump(pipeline, f)
    print(f"Trained on {len(texts)} examples, classes: {sorted(set(labels))}")
    print(f"Saved pipeline to {path}")

if __name__ == "__main__":
    train_and_save()
