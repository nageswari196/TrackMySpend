"""
Auto-categorization of expenses from free text (merchant name / OCR text /
description), using the trained TF-IDF + Naive Bayes pipeline.
"""
import pickle
import streamlit as st

MODEL_PATH = "category_model.pkl"

@st.cache_resource
def _load_model():
    try:
        with open(MODEL_PATH, "rb") as f:
            return pickle.load(f)
    except FileNotFoundError:
        return None

def predict_category(text: str) -> str | None:
    """Returns a predicted category, or None if no model / empty text."""
    model = _load_model()
    if model is None or not text or not text.strip():
        return None
    try:
        return model.predict([text])[0]
    except Exception:
        return None
