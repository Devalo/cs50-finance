import os
import datetime

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash


from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd



# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    user_shares = db.execute("SELECT * FROM stocks WHERE user_id = :user_id AND is_sold = 0", user_id=session["user_id"])
    cash_amount = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id=session["user_id"])

    tot = []
    for cash in user_shares:
        i =lookup(cash["symbol"])
        j = i["price"]
        a = cash["amount"]
        k = j * a

        tot.append(k)

    return render_template("index.html", shares=user_shares, lookup=lookup, total=round(sum(tot), 2), cash_left=round(cash_amount[0]["cash"], 2))




    #Display a table with all of the current user stock,
    # the number of shares of each, the current price of
    # each stock, and the total value of each holding.

    # Display the users current cash balance


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        amount = int(request.form.get("amount"))

        if symbol == "":
            return apology("Symbol field cannot be blank")
        if amount == "" or amount <= 0:
            return apology("Amount field cannot be blank and must be over 0")

        get_share = lookup(symbol)
        share_name = get_share["name"]
        share_price = get_share["price"]
        cash_amount = check_user_cash_amount()

        total = amount * share_price
        if cash_amount < total:
            return apology("Insufficient founds.")
        else:
            db.execute("INSERT INTO stocks (name, symbol, amount, price, user_id) VALUES (:name, :symbol, :amount, :price, :user_id)", name=share_name, symbol=symbol, amount=amount, price=share_price, user_id=session["user_id"])
            new_amount = cash_amount - total
            db.execute("UPDATE users SET cash = :new_total WHERE id = :user_id", new_total=new_amount, user_id=session["user_id"])
            return redirect("/")

    else:
        return render_template("buy.html")
    # When requested via GET, should display form to buy a stock
    # When form is submitted via POST, purchase the stock so long
    # as the user can afford it.


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    return apology("TODO")

    # Display a table with history of all transactions,
    # listing row by row every buy and every sell


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        session["username"] = rows[0]["username"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        symbol = request.form.get("symbol")

        get_symbol = lookup(symbol)
        share_name = get_symbol["name"]
        share_price = get_symbol["price"]

        return render_template("quoted.html", share_symbol=symbol.upper(), share_name = share_name, share_price = share_price)
    else:
        return render_template("quote.html")

    # When requested via GET, should display form to request a stock rate
    # When form is submitted via POST, lookup the stock symbol by calling
    # the lookup function, and display the results


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        password_confirmation = request.form.get("password_confirmation")
        if password != password_confirmation:
            return apology("Passwords dont match", 401)

        if check_if_user_already_exists(username) == False:
            password_hash = generate_password_hash(password)
            db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)", username=username, hash=password_hash)
            return redirect("/")
        else: return apology("Username already exists")

    else:
        return render_template("register.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    stocks = db.execute("SELECT id, symbol, amount FROM stocks WHERE user_id = :user_id AND is_sold = 0", user_id=session["user_id"])

    if request.method == "POST":

        stock_to_sell = request.form.get("symbol")
        amount_to_sell = request.form.get("amount")
        stocks_available = db.execute("SELECT amount FROM stocks WHERE user_id = :user_id AND id = :stock_id", user_id=session["user_id"], stock_id=stock_to_sell)
        if stock_to_sell == None:
            return apology("No stock selected")
        elif amount_to_sell == None or int(amount_to_sell) <= 0:
            return apology("Amount must be present, and over 0")
        else:
            if stocks_available[0]["amount"] < int(amount_to_sell):
                return apology("Not enough stocks")
            else:
                selected_stock = db.execute("SELECT * FROM stocks WHERE user_id = :user_id AND id = :stock_id", user_id=session["user_id"], stock_id=stock_to_sell)
                user_cash = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id=session["user_id"])
                price = selected_stock[0]["price"] * int(amount_to_sell)
                date = datetime.datetime.now()
                date_format = date.strftime("%d-%m-%y %H:%M:%S")

                db.execute("UPDATE stocks SET amount = :new_val WHERE user_id = :user_id", new_val=stocks_available[0]["amount"]-int(amount_to_sell), user_id=session["user_id"])
                db.execute("UPDATE users SET cash = :new_val WHERE id = :user_id", new_val=user_cash[0]["cash"]+price, user_id=session["user_id"])

                db.execute("INSERT INTO history (symbol, amount, price, date, user_id) VALUES (:symbol, :amount, :price, :date, :user_id)", symbol=selected_stock[0]["symbol"], amount=int(amount_to_sell), price=price, date=date_format, user_id=session["user_id"])



                amount_left = db.execute("SELECT amount FROM stocks WHERE user_id = :user_id AND id = :stock_id", user_id=session["user_id"], stock_id=stock_to_sell)
                print(amount_left)
                if amount_left[0]["amount"] == 0:
                    db.execute("UPDATE stocks SET is_sold = :new_val WHERE user_id = :user_id AND id = :stock_id ", new_val = 1, user_id=session["user_id"], stock_id=stock_to_sell)

                return redirect("/")

    else:
        return render_template("sell.html", stocks=stocks)

    # When requested via GET, should display form to sell a stock.

    # When form is submitted via POST, sell the spcified number of shares of stock.
    # and update the users cach


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)

# Checks if a username is already in the database
def check_if_user_already_exists(username):
    rows = db.execute("SELECT * FROM users WHERE username = :username", username=username)
    if len(rows) != 0:
        return True
    else:
        return False

def check_user_cash_amount():
    row = db.execute("SELECT cash FROM users WHERE username = :username", username=session["username"])
    return row[0]["cash"]
