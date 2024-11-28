import openai as ai
import testStock as ts

ai.api_key;
messages = [];
def _send_to_chatGPT(message, model = "gpt-3.5-turbo"):
    messages.append(message);
    try:
        response = ai.chat.completions.create(
            messages = messages,
            model = model,
        )
        return response.choices[0].message.content;
    except ai.OpenAIError as error:
        print("Error: ", error)

"""ask gpt about related stocks based on if long or short, also optimize search based on int;
recommended optimize is a int between 2 - 4, any greater will cause expenintial increase in runtime"""
def ask_gpt(optimize: int = 3, style: str = "swing"):
    promptStyle = {
        "swing" : "From the given data identify stocks currently forming or heading towards a golden cross, focus on those with strong bullish signals and give relevant news, ",
        "short" : "You are a progresive swing trader, from the following data determine up to 10 bearish and trending down stocks also share relevant news on each stock, ",
        "default" : ""
    }
    #symbol: str = input("Type a Stock Symbol to the rating on that stock and relating stocks:\n");
    stock = ts.Stock("NVDA");
    stock.related_stocks(optimize, style);
    text = {'role': 'user', 'content': (promptStyle[style]) + str(stock.cache)};
    response = _send_to_chatGPT(text);
    messages.append(response);
    print("\n", response, "\n");
    return response;

ask_gpt(250);