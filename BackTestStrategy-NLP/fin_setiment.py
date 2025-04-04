from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

# ✅ Set up NLP Model
device = "cuda:0" if torch.cuda.is_available() else "cpu"
tokenizer = AutoTokenizer.from_pretrained("yiyanghkust/finbert-tone")
model = AutoModelForSequenceClassification.from_pretrained("yiyanghkust/finbert-tone").to(device)

# ✅ Optimized Sentiment Estimation (Batch Processing)
def estimate_sentiment(news, model = model, tokenizer = tokenizer, device = device):
    labels = ["positive", "negative", "neutral"]
    if not news:
        return {}

    tokens = tokenizer(news, return_tensors="pt", padding=True, truncation=True, max_length=512).to(device)
    logits = model(**tokens).logits
    probabilities = torch.nn.functional.softmax(logits, dim=-1)

    sentiment_counts = {label: 0.0 for label in labels}
    total_prob = 0.0

    for prob in probabilities:
        sentiment = labels[torch.argmax(prob)]
        sentiment_counts[sentiment] += prob.max().item()
        total_prob += prob.max().item()

    # Get the sentiment with the greatest probability
    max_sentiment = max(sentiment_counts, key=sentiment_counts.get)
    max_probability = sentiment_counts[max_sentiment] / total_prob if total_prob > 0 else 0

    return max_probability, max_sentiment

# ✅ Sequential Execution (Ensures Order)
"""account = api.get_account()
print("ACCOUNT:", account.status)
print("CUDA:", device)

symbol = "PLTR"
print("SYMBOL:", symbol, "\n")

start_date = datetime(2024, 1, 1)
period = 5

for _ in range(365 // period):
    start_date += timedelta(days=period)
    
    print(f"Processing DATE: {start_date}")

    # Fetch news sequentially (ensures chronological order)
    news = fetch_news(symbol, period, start_date)

    # Process sentiment in order
    sentiment_score, probability_score = estimate_sentiment(news)

    # Output results in order
    print(f"DATE: {start_date}")
    print(f"Weighted Sentiment/Probablity Scores: {sentiment_score}, {probability_score} \n")"""