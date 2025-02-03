import torch
import torch.nn as nn
import torch.optim as optim
import yfinance as yf
import numpy as np
import test_alpaca as ta
device = "cuda" if torch.cuda.is_available() else "cpu"
print("DEVICE:", device, "\n")

# Stock market
# I want to know in a sense if I should buy, sell, or hold
# I want to know the probability of the stock going up or down aka A PREDICTER
# I need to train a NN on market data to the understand key levels where to buy or sell
# I need to take into account certain features to predict

# Features: MA50, MA200, RSI, NEWS

# BUY SIGNALS:
# 1. MA50 < MA200 and starting to form golden cross; MA50 -> MA10, MA200 -> MA50 if day trading
# 2. RSI < 30 and signs of a oversold period
# 3. NEWS is positive

# SELL SIGNALS:
# 1. MA50 > MA200 and starting to form death cross
# 2. RSI > 70 and signs of an overbought period
# 3. NEWS is negative

t = ta.trade_bot("NVDA")
pre_data, labels = t.pre_processing(t.stock_data(7))
start = t.start
symbols: list[str] = []
data: dict[list]= {}
for i in pre_data:
    symbols.append(i)
    tensor = list(pre_data[i].values())
    data[i]= {
        "features": torch.tensor(tensor),
        "label": torch.tensor(labels[i])
        }
    
# list of dict with each dict having name, ma10, ma50, and rsi
# I want a list of dict with the name to be the key to the features ma10, ma50, and rsi
class trade_model(nn.Module):
    def __init__(self):
        super(trade_model, self).__init__()
        self.fc1 = nn.Linear(3, 5) # input layer (3) ->
        self.fc2 = nn.Linear(5, 1) # output layer (1)
    def forward(self, input):
        x = torch.relu(self.fc1(input))
        output = torch.sigmoid(self.fc2(x))
        return output

print("Start Training...")
# Initialize model, loss, and optimizer
model = trade_model()
criterion = nn.BCELoss()  # Binary Cross-Entropy for classification
optimizer = optim.Adam(model.parameters(), lr=0.01)

"""# training/testing data
training_data: dict = {}
testing_data: dict = {}
for i in range(len(data)):
    if i % 2 == 0:
        training_data[symbols[i]] = data[symbols[i]] 
    if i % 2 == 1:
        testing_data[symbols[i]] = data[symbols[i]] 
print("TRAINING\n",training_data, "\nTESTING\n", testing_data)"""

# Training loop
epochs = 500
for epoch in range(epochs):
    optimizer.zero_grad()  # Reset gradients

    # Use modulo to cycle through symbols if needed
    i = symbols[epoch % len(symbols)]  # Prevent index out of range
    features = data[i]["features"].to(device)  # Move features to the appropriate device
    label = data[i]["label"].float().to(device)  # Convert label to float tensor and move to device

    # Forward pass
    outputs = model(features)  # Predict based on input

    # Compute loss
    loss = criterion(outputs.view(-1), label.view(-1))  # Ensure both are 1D tensors

    # Backward pass
    loss.backward()
    optimizer.step()

    # Print loss every 10 epochs
    if epoch % 10 == 0:
        print(f"Epoch {epoch}, Loss: {loss.item()}")
