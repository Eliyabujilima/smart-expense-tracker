from datetime import datetime, timedelta

# ----------------------
# HELPER
# ----------------------

def normalize_category(cat):
    if not cat:
        return "other"
    return cat.strip().lower()

def parse_date(d):
    if isinstance(d, str):
        return datetime.strptime(d, "%Y-%m-%d")
    return datetime.combine(d, datetime.min.time())


# ----------------------
# CLEAN TRANSACTION HELPER (IMPORTANT 🔥)
# ----------------------
def clean_transactions(transactions):
    return [
        t for t in transactions
        if t.get("category") not in ["__new__", None, ""]
    ]


# ----------------------
# CORE CALCULATIONS
# ----------------------
def total_income(transactions):
    return sum(t["amount"] for t in transactions if t["type"] == "income")


def total_expense(transactions):
    return sum(t["amount"] for t in transactions if t["type"] == "expense")


def current_balance(transactions):
    return total_income(transactions) - total_expense(transactions)


# ----------------------
# TIME ANALYTICS
# ----------------------
def today_spending(transactions):
    today = datetime.now().strftime("%Y-%m-%d")

    return sum(
        t["amount"] for t in transactions
        if t["type"] == "expense" and str(t["date"]) == today
    )


def weekly_spending(transactions):
    today = datetime.now()
    week_ago = today - timedelta(days=7)

    return sum(
        t["amount"] for t in transactions
        if t["type"] == "expense"
        and parse_date(t["date"]) >= week_ago
    )


def monthly_spending(transactions):
    now = datetime.now()

    return sum(
        t["amount"] for t in transactions
        if t["type"] == "expense"
        and parse_date(t["date"]).month == now.month
        and parse_date(t["date"]).year == now.year
    )
    
def yearly_spending(transactions):
    year = datetime.now().year

    return sum(
        t["amount"] for t in transactions
        if t["type"] == "expense"
        and parse_date(t["date"]).year == year
    )

# ----------------------
# CATEGORY ANALYTICS
# ----------------------
def category_spending(transactions):
    totals = {}

    for t in transactions:
        if t["type"] == "expense":
            cat = t["category"]

            # 🔥 FIX: normalize category
            cat = cat.strip().title()

            totals[cat] = totals.get(cat, 0) + t["amount"]

    return totals

def category_chart_data(transactions):
    return category_spending(transactions)


# ----------------------
# RANGE ANALYTICS
# ----------------------
def spending_by_range(transactions, start_date, end_date):
    transactions = clean_transactions(transactions)

    start = parse_date(start_date)
    end = parse_date(end_date)

    results = [
        t for t in transactions
        if t["type"] == "expense" and start <= parse_date(t["date"]) <= end
    ]

    total = sum(t["amount"] for t in results)

    return total, results


# ----------------------
# BUDGET WARNINGS
# ----------------------
def budget_warnings(transactions, budgets):
    warnings = []
    totals = category_spending(transactions)

    for cat, limit in budgets.items():
        spent = totals.get(cat, 0)

        if limit == 0:
            continue

        if spent > limit:
            diff = spent - limit
            warnings.append(f"🔴 {cat}: Exceeded by {diff:.0f} TSh")
        elif spent >= 0.8 * limit:
            remaining = limit - spent
            warnings.append(f"🟡 {cat}: Near limit ({remaining:.0f} TSh left)")

    return warnings


def budget_usage(transactions, budgets):
    usage = {}
    totals = category_spending(transactions)

    for cat, limit in budgets.items():
        spent = totals.get(cat, 0)

        percent = (spent / limit * 100) if limit > 0 else 0

        usage[cat] = {
            "spent": spent,
            "limit": limit,
            "percent": round(percent, 1)
        }

    return usage

# ----------------------
# SMART INSIGHTS (FIXED 🔥)
# ----------------------
def generate_insights(transactions):
    insights = []

    income = total_income(transactions)
    expense = total_expense(transactions)

    # ----------------------
    # SAFETY CHECK
    # ----------------------
    if expense == 0:
        insights.append("📊 No expenses recorded yet")
        return insights

    if income == 0 and expense > 0:
        insights.append("⚠️ You are spending without income")

    if income > 0 and expense > income:
        insights.append("🔴 You are overspending your income")

    # ----------------------
    # CATEGORY INSIGHT (FIXED ACCURACY)
    # ----------------------
    categories = category_spending(transactions)

    total_expense_value = sum(categories.values())

    if total_expense_value > 0:
        top_category = max(categories, key=categories.get)
        top_value = categories[top_category]

        percentage = (top_value / total_expense_value) * 100

        if percentage >= 50:
            insights.append(
                f"📊 High concentration: {percentage:.0f}% of spending is on {top_category}"
            )
        else:
            insights.append(
                f"📊 Spending is balanced across categories (Top: {top_category} {percentage:.0f}%)"
            )

    # ----------------------
    # DAILY SPENDING INSIGHT (FIXED)
    # ----------------------
    today = today_spending(transactions)

    if today > 0:
        monthly = monthly_spending(transactions)
        avg_daily = monthly / 30 if monthly > 0 else today

        if today > avg_daily * 1.5:
            insights.append("📈 Today’s spending is unusually high")
        elif today < avg_daily:
            insights.append("📉 Today’s spending is under control")

    # ----------------------
    # SAVINGS INSIGHT (FIXED)
    # ----------------------
    if income > 0:
        savings = income - expense
        saving_rate = (savings / income) * 100

        if saving_rate >= 30:
            insights.append("💚 Strong savings behavior")
        elif 10 <= saving_rate < 30:
            insights.append("🟡 Moderate savings — room for improvement")
        else:
            insights.append("⚠️ Low savings rate")

    return insights

def budget_intelligence(transactions, budgets):
    insights = []
    totals = category_spending(transactions)

    for cat, limit in budgets.items():
        if limit == 0:
            continue

        spent = totals.get(cat, 0)
        percent = (spent / limit) * 100 if limit > 0 else 0

        if percent > 100:
            insights.append(f"🔴 {cat}: Over budget ({percent:.0f}%)")
        elif percent > 80:
            insights.append(f"🟡 {cat}: High spending ({percent:.0f}%)")
        elif percent > 0:
            insights.append(f"🟢 {cat}: Good control ({percent:.0f}%)")

    return insights