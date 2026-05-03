from flask import Flask, render_template, request, redirect, session
from db import get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import uuid
import os

# IMPORT ANALYTICS
from analytics.engine import *

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "super_secret_key_123")

# ----------------------
# HELPER
# ----------------------
def safe_date(date_val):
    if isinstance(date_val, str):
        return date_val
    return date_val.strftime("%Y-%m-%d")

def monthly_trend(transactions):
    trend = {}

    for t in transactions:
        if t["type"] == "expense":
            date_val = t["date"]

            if isinstance(date_val, str):
                month = date_val[:7]   # YYYY-MM
            else:
                month = date_val.strftime("%Y-%m")

            trend[month] = trend.get(month, 0) + t["amount"]

    return trend

# ----------------------
# HOME
# ----------------------
@app.route("/")
def home():
    print("HOME ROUTE START")
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM transactions WHERE user_id=%s", (session["user_id"],))
    transactions = cursor.fetchall()

    cursor.execute(
            "SELECT * FROM budgets WHERE user_id=%s",
            (session["user_id"],)
        )

    budgets_data = cursor.fetchall()

        # 🔥 FIX: normalize categories
    budgets = {
            b["category"].strip().title(): b["amount"]
            for b in budgets_data
        }
    conn.close()
    
    income = total_income(transactions)
    expense = total_expense(transactions)
    balance = current_balance(transactions)
    
    hour = datetime.now().hour

    if hour < 12:
        greeting = "GOOD MORNING"
    elif hour < 18:
        greeting = "GOOD AFTERNOON"
    else:
        greeting = "GOOD EVENING"   
    today_total = today_spending(transactions)
    weekly = weekly_spending(transactions)
    monthly = monthly_spending(transactions)
    yearly = yearly_spending(transactions)

    insights = generate_insights(transactions)
    budget_insights = budget_intelligence(transactions, budgets)
    trend_data = monthly_trend(transactions)
    budget_data = budget_usage(transactions, budgets)
    
    username = session.get("username")
    
    print("HOME ROUTE END")
    return render_template(
        "index.html",
        transactions=[t for t in transactions if t["date"].strftime("%Y-%m-%d") == datetime.now().strftime("%Y-%m-%d")],
        income=income,
        expense=expense,
        balance=balance,
        today_total=today_total,
        weekly=weekly,
        monthly=monthly,
        yearly=yearly,
        chart_data=category_chart_data(transactions),
        budgets=budgets,
        totals=category_spending(transactions),
        warnings=budget_warnings(transactions, budgets),
        insights=insights,
        trend_data=trend_data,
        budget_insights=budget_insights,
        username=username,
        greeting=greeting,
        budget_data=budget_data

    )
    
# ----------------------
# ADD EXPENSE
# ----------------------
@app.route("/add", methods=["GET", "POST"])
def add():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT name FROM categories")
    categories = [r["name"] for r in cursor.fetchall()]

    if request.method == "POST":
        try:
            id = str(uuid.uuid4())
            name = request.form["name"]

            category = request.form.get("category")
            if category == "__new__":
                category = request.form.get("new_category")

            if not category:
                category = "Other"

            if category == "Food":
                amount = (
                    float(request.form.get("breakfast", 0) or 0) +
                    float(request.form.get("lunch", 0) or 0) +
                    float(request.form.get("dinner", 0) or 0)
                )
            else:
                amount = float(request.form.get("amount", 0) or 0)

            date = datetime.now().strftime("%Y-%m-%d")

            cursor.execute("""
                INSERT INTO transactions (id, type, name, amount, category, date, user_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (id, "expense", name, amount, category, date, session["user_id"]))

            conn.commit()

        except Exception as e:
            print("ERROR:", e)

        finally:
            conn.close()

        return redirect("/")

    conn.close()
    return render_template("add.html", categories=categories)

# ----------------------
# ADD INCOME
# ----------------------
@app.route("/add_income", methods=["GET", "POST"])
def add_income():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            id = str(uuid.uuid4())
            name = request.form["name"]
            amount = float(request.form.get("amount", 0) or 0)
            date = datetime.now().strftime("%Y-%m-%d")

            cursor.execute("""
                INSERT INTO transactions (id, type, name, amount, category, date, user_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (id, "income", name, amount, "Income", date, session["user_id"]))

            conn.commit()

        except Exception as e:
            print("ERROR:", e)

        finally:
            conn.close()

        return redirect("/")

    return render_template("add_income.html")

# ----------------------
# DELETE
# ----------------------
@app.route("/delete/<id>")
def delete(id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM transactions WHERE id=%s AND user_id=%s",
        (id, session["user_id"])
    )

    conn.commit()
    conn.close()

    return redirect("/")

# ----------------------
# HISTORY
# ----------------------
@app.route("/history")
def history():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM transactions WHERE user_id=%s", (session["user_id"],))
    transactions = cursor.fetchall()

    conn.close()

    return render_template("history.html", transactions=transactions)

# ----------------------
# SET BUDGET
# ----------------------
@app.route("/set-budget", methods=["GET", "POST"])
def set_budget():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # GET categories
    cursor.execute("SELECT name FROM categories")
    categories = [r["name"] for r in cursor.fetchall()]

    if request.method == "POST":
        cursor = conn.cursor()

        category = request.form.get("category")

        if category == "__new__":
            category = request.form.get("new_category")

        if not category or category.strip() == "":
            category = "Other"

        # 🔥 FIX: normalize category
        category = category.strip().title()

        amount = float(request.form.get("amount", 0))

        # 🔥 FIX: FORCE UPDATE PER USER
        cursor.execute("""
            DELETE FROM budgets
            WHERE user_id=%s AND category=%s
        """, (session["user_id"], category))

        cursor.execute("""
            INSERT INTO budgets (user_id, category, amount)
            VALUES (%s, %s, %s)
        """, (session["user_id"], category, amount))

        conn.commit()
        conn.close()

        return redirect("/")

    conn.close()
    return render_template("set_budget.html", categories=categories)
# ----------------------
# AUTH
# ----------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        username = request.form["username"]
        password = generate_password_hash(request.form["password"])

        # CHECK IF USER EXISTS
        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        existing_user = cursor.fetchone()

        if existing_user:
            conn.close()
            return "⚠️ Username already exists, try another"

        user_id = str(uuid.uuid4())

        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (id, username, password)
            VALUES (%s, %s, %s)
        """, (user_id, username, password))

        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        username = request.form["username"]
        password = request.form["password"]

        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()

        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect("/")
        else:
            return "Invalid credentials"

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

#    calculator route
@app.route('/calculator')
def calculator():
    return render_template('calculator.html')

#   help route
@app.route('/help')
def help_page():
    return render_template('help.html')

# ----------------------
# ERRORS

# ----------------------
@app.errorhandler(500)
def internal_error(e):
    return render_template("error.html"), 500

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

# ----------------------
# RUN
# ----------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)