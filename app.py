import math
import requests
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)


# --- Вспомогательная функция для безопасной валидации чисел ---
def get_number(data, key):
    val = data.get(key)
    if val is None:
        return None, f"Поле '{key}' обязательно."
    if not isinstance(val, (int, float)):
        return None, f"Поле '{key}' должно быть числом."
    return val, None


# ========== РОУТЫ ДЛЯ HTML-СТРАНИЦ ==========
@app.get("/")
def index():
    return render_template("index.html", active_page="home")

@app.get("/calculator")
def calculator_page():
    return render_template("calculator.html", active_page="calculator")

@app.get("/discount")
def discount_page():
    return render_template("discount.html", active_page="discount")

@app.get("/currency")
def currency_page():
    return render_template("currency.html", active_page="currency")


# ========== API-ЭНДПОИНТЫ ==========
@app.post("/calculate")
def calculate():
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"detail": "Тело запроса должно быть в формате JSON."}), 400

    num1, err1 = get_number(data, "num1")
    if err1: return jsonify({"detail": err1}), 400
    
    op = str(data.get("operation", "")).lower()

    # Тригонометрия и факториал (унарные операции)
    if op in ["sin", "cos", "tan", "cotan", "factorial"]:
        if op == "sin": result = math.sin(math.radians(num1))
        elif op == "cos": result = math.cos(math.radians(num1))
        elif op == "tan": 
            if math.cos(math.radians(num1)) == 0:
                return jsonify({"detail": "Тангенс 90/270° не определён."}), 400
            result = math.tan(math.radians(num1))
        elif op == "cotan":
            if math.sin(math.radians(num1)) == 0:
                return jsonify({"detail": "Котангенс 0/180° не определён."}), 400
            result = 1 / math.tan(math.radians(num1))
        elif op == "factorial":
            if num1 < 0 or not num1.is_integer():
                return jsonify({"detail": "Факториал — только для целых неотрицательных чисел."}), 400
            result = math.factorial(int(num1))
        return jsonify({"status": "success", "operation": op, "result": result}), 200

    # Бинарные операции
    num2, err2 = get_number(data, "num2")
    if err2: return jsonify({"detail": err2}), 400

    if op == "add": result = num1 + num2
    elif op == "subtract": result = num1 - num2
    elif op == "multiply": result = num1 * num2
    elif op == "divide":
        if num2 == 0: return jsonify({"detail": "Деление на ноль."}), 400
        result = num1 / num2
    elif op == "power": result = num1 ** num2
    else:
        return jsonify({"detail": f"Операция '{op}' не поддерживается."}), 400

    return jsonify({"status": "success", "operation": op, "result": result}), 200


@app.post("/discount")
def calculate_discount():
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"detail": "Ожидался JSON"}), 400
    
    price, err1 = get_number(data, "price")
    if err1: return jsonify({"detail": err1}), 400
    
    percent, err2 = get_number(data, "discount_percent")
    if err2: return jsonify({"detail": err2}), 400

    if price < 0 or percent < 0 or percent > 100:
        return jsonify({"detail": "Цена не может быть отрицательной, а скидка от 0 до 100%."}), 400

    final_price = price - (price * (percent / 100))
    
    return jsonify({
        "original_price": price,
        "discount_percent": percent,
        "final_price": round(final_price, 2)
    }), 200


@app.post("/currency")
def convert_currency():
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"detail": "Ожидался JSON"}), 400

    amount, err1 = get_number(data, "amount")
    if err1: return jsonify({"detail": err1}), 400
    if amount <= 0:
        return jsonify({"detail": "Сумма должна быть больше 0"}), 400

    base = str(data.get("from", "RUB")).upper()
    target = str(data.get("to", "RUB")).upper()

    # Если обе валюты одинаковые
    if base == target:
        return jsonify({
            "amount": amount,
            "from": base,
            "to": target,
            "rate": 1.0,
            "converted_amount": amount
        }), 200

    url = "https://www.cbr-xml-daily.ru/daily_json.js"

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        cbr_data = response.json()
        valutes = cbr_data.get("Valute", {})

        # Функция для получения курса валюты к рублю (сколько рублей за 1 единицу валюты)
        def get_rate_to_rub(currency_code):
            if currency_code == "RUB":
                return 1.0
            if currency_code not in valutes:
                raise ValueError(f"Валюта {currency_code} не найдена в API ЦБ.")
            v = valutes[currency_code]
            # Value — стоимость Nominal единиц валюты в рублях
            return v["Value"] / v["Nominal"]

        # Получаем курсы к рублю для обеих валют
        rate_base_to_rub = get_rate_to_rub(base)   # сколько рублей за 1 base
        rate_target_to_rub = get_rate_to_rub(target) # сколько рублей за 1 target

        # Конвертируем: amount base -> рубли -> target
        # amount * (рублей за 1 base) = рублей
        # рублей / (рублей за 1 target) = target
        converted_amount = amount * rate_base_to_rub / rate_target_to_rub

        # Курс 1 base = X target
        rate = rate_base_to_rub / rate_target_to_rub

        return jsonify({
            "amount": amount,
            "from": base,
            "to": target,
            "rate": round(rate, 6),
            "converted_amount": round(converted_amount, 2)
        }), 200

    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
    except requests.exceptions.Timeout:
        return jsonify({"detail": "Превышено время ожидания ответа от сервиса курсов."}), 504
    except requests.exceptions.RequestException:
        return jsonify({"detail": "Ошибка получения данных от внешнего API."}), 502

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080) #nosec B104