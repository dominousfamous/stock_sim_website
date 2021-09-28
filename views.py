import os
import sqlite3
import requests
import urllib.parse
from functools import wraps
from datetime import datetime
from flask import Blueprint, render_template, flash, redirect, session, request
from werkzeug.security import check_password_hash, generate_password_hash

#Configure blueprint
views = Blueprint("views", __name__)

#Configure SQL table
#TODO

#Login_required decorator
def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return wrap

#lookup stock info
def lookup(symbol):
    # Contact API
    try:
        api_key = os.environ.get("API_KEY")
        url = f"https://cloud.iexapis.com/stable/stock/{urllib.parse.quote_plus(symbol)}/quote?token={api_key}"
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException:
        return None

    # Parse response
    try:
        quote = response.json()
        return {
            "name": quote["companyName"],
            "price": float(quote["latestPrice"]),
            "symbol": quote["symbol"]
        }
    except (KeyError, TypeError, ValueError):
        return None

#change float value into dollar-cent form
def usd(value):
    return f"${value:,.2f}"

#########################  START OF ROUTES #############################

#Register users
@views.route("/register", methods = ["GET", "POST"])
def register():
    con = sqlite3.connect("database.db")
    db = con.cursor()
    
    #if method is post
    if request.method == "POST":

        username = request.form.get('username').strip()
        password = request.form.get('password').strip()
        confirmation = request.form.get('confirmation').strip()
        startMoney = request.form.get('startMoney').strip()

        #if user didn't enter any of the fields in
        if not username:
            flash("Please enter a username", category = "error")
            return redirect("/register")
        elif not password:
            flash("Please enter a password", category = "error")
            return redirect("/register")
        elif not confirmation:
            flash("Please confirm your password", category = "error")
            return redirect("/register")
        elif not startMoney:
            flash("Please enter the amount you want to start with", category = "error")
            return redirect("/register")

        #if password and confirmation don't match
        if password != confirmation:
            flash("Passwords don't match", category = "error")
            return redirect("/register")

        #check if user entered valid currency digits
        try:
            startMoney = float(startMoney)

            #if negative number
            if startMoney<0:
                flash("Please enter a positive value", category = "error")
                return redirect("/register")
        except:
            flash("Please enter only decimal or whole-numbers values(no $ sign please!)", category = "error")
            return redirect("/register")

        #Collect information from users table
        db.execute("SELECT * FROM users WHERE username=?;", (username,))

        rows = db.fetchall()

        #if there is entry for this username
        if len(rows)!=0:
            flash("Username already exists", category = "error")
            return redirect("/register")
        else:
            #Hash the user's password
            password_hash = generate_password_hash(password)

            #Insert into users the username, hashed password, and starting cash
            db.execute("INSERT INTO users (username, hash, cash) VALUES(?,?,?)", (username, password_hash, startMoney))
        con.commit()
        con.close()
        #return user to login page
        flash("Successfully registered!", category="success")
        return redirect('/login')

    #if method is get
    else:
        return render_template("register.html")


@views.route("/login", methods = ["GET","POST"])
def login():

    con = sqlite3.connect("database.db")
    db = con.cursor()

    #Forget prior user_id
    session.clear()
    #session.permanent = True

    #if method is post
    if request.method == "POST":

        #if user didn't enter any of the fields in
        username = request.form.get("username").strip()
        password = request.form.get("password").strip()

        if not username:
            flash("Please enter your username", category="error")
            return redirect("/login")
        elif not password:
            flash("Please enter your password", category="error")
            return redirect("/login")

        #Collect information from users table about this username
        db.execute("SELECT * FROM users WHERE username=?;", (username,))
        rows = db.fetchall()

        #if there isn't only one user with this username
        if len(rows)!=1:
            flash("You entered the wrong username", category="error")
            return redirect("/login")

        #if password doesn't match hashed password
        if not check_password_hash(rows[0][2], password):
            flash("You entered the wrong password", category="error")
            return redirect("/login")

        #remember user id in session
        session["user_id"] = rows[0][0]
        
        #remember user username in session
        session['user'] = rows[0][1]
        con.commit()
        con.close()

        #redirect to homepage
        flash("Logged in!", category="success")
        return redirect("/")

    #if method is get
    else:
        return render_template("login.html")

@views.route("/", methods = ["GET", "POST"])
@login_required
def index():
    con = sqlite3.connect("database.db")
    db = con.cursor()
    
    #all the categories
    db.execute("SELECT DISTINCT category FROM symbols ORDER BY category")
    tags = db.fetchall()
    length = len(tags)

    #if method is post
    if request.method=="POST":
        
        #getting list of stocks based on category
        if request.form.get("category"):
            category = request.form.get("category")
            db.execute("SELECT * FROM symbols WHERE category=?;", (category,))
            results = db.fetchall()
            results_length = len(results)

            return render_template("home.html", selection = True, tags = tags, results = results, results_length = results_length, length = length, category = category)

        #Quoting price of stock
        elif request.form.get("symbol"):
            symbol = request.form.get("symbol").strip().upper()

            values = lookup(symbol)

            if values is None:
                flash("Please enter a valid stock symbol", category = "error")
                return redirect("/")

            company = values['name']
            price = usd(values['price'])

            return render_template("home.html", quoted = True, symbol = symbol, company = company, price = price, tags = tags, length = length)

        #if user didn't submit either form
        else:
            return redirect("/")

    #if method is get
    else:
        db.execute("SELECT DISTINCT category FROM symbols ORDER BY category")
        tags = db.fetchall()
        length = len(tags)
        return render_template("home.html", quoted = False, selection = False, tags = tags, length = length)


@views.route("/account")
@login_required
def account():
    user_id = session['user_id']
    con = sqlite3.connect("database.db")
    db = con.cursor()

    db.execute("SELECT symbol,name,shares FROM userStock WHERE id=?;", (user_id,))
    values = db.fetchall()

    #check if any of the stocks have 0 shares
    for index in range(len(values)):
        if values[index][2] == 0:
            #if so, remove that line
            symbol = values[index][0]
            db.execute("DELETE FROM userStock WHERE symbol=? AND id = ?;", (symbol, user_id))
            con.commit()

    db.execute("SELECT symbol,name,shares FROM userStock WHERE id=?;", (user_id,))
    values = db.fetchall()

    #GET current stock price for every symbol
    table = {}

    for i in range(len(values)):
        symbol = values[i][0]
        price = lookup(symbol)['price']
        table[symbol] = round(price,2)

    #Current cash of user
    db.execute("SELECT cash FROM users WHERE id = ?", (user_id,))
    cash = db.fetchall()[0][0]

    #Total cash
    total_cash = 0
    for i in range(len(values)):
        shares = values[i][2]
        symbol = values[i][0]
        price = table[symbol]
        total_cash = total_cash + (shares*price)
    
    return render_template("account.html", total_cash = total_cash, cash = cash, values = values, table = table, length = len(values))


@views.route("/changeMoney", methods = ["GET","POST"])
@login_required
def changeMoney():

    con = sqlite3.connect("database.db")
    db = con.cursor()
    
    #if method is post
    if request.method == "POST":
        
        #if DEPOSIT
        if request.form.get("deposit"):
            try:
                deposit = float(request.form.get("deposit").strip())

                #if number is negative
                if deposit<0:
                    flash("Please enter a value greater than 0", category = "error")
                    return redirect("/changeMoney")
            except:
                flash("Please enter only decimals/whole-numbers (no $ etc)", category = "error")
                return redirect("/changeMoney")

            #Add money into users table where id = user_id
            user_id = session['user_id']
            db.execute("SELECT cash FROM users WHERE id = ?;", (user_id,))
            current_cash = db.fetchall()[0][0]
            db.execute("UPDATE users SET cash = ? WHERE id = ?;", (current_cash + deposit, user_id))
            con.commit()

        #if WITHDRAW
        elif request.form.get("withdraw"):
            try:
                withdraw = float(request.form.get("withdraw").strip())
                
                #if number is negative
                if withdraw<0:
                    flash("Please enter a value greater than 0", category = "error")
                    return redirect("/changeMoney")
            except:
                flash("Please enter only decimals/whole-numbers (no $ etc)", category = "error")
                return redirect("/changeMoney")

            #Remove money from users table where id = user_id
            user_id = session['user_id']
            db.execute("SELECT cash FROM users WHERE id = ?;", (user_id,))
            current_cash = db.fetchall()[0][0]

            #if user is trying to withdraw more than he/she currently has
            if current_cash < withdraw:
                flash("You are trying to withdraw more than you currently own", category = "error")
                return redirect("/changeMoney")

            db.execute("UPDATE users SET cash = ? WHERE id = ?;", (current_cash - withdraw, user_id))
            con.commit()

        #if neither
        else:
            flash("Please enter in a value", category="error")
            return redirect("/changeMoney")

        flash("Successfully updated!", category = "success")
        return redirect("/account")
            
    #if method is get
    else:
        return render_template("changeMoney.html")

@views.route("/history")
@login_required
def history():
    con = sqlite3.connect("database.db")
    db = con.cursor()
    user_id = session['user_id']
    db.execute("SELECT symbol,name,shares,price,time FROM transactions WHERE user_id=?;", (user_id,))
    values = db.fetchall()
    length = len(values)

    return render_template("history.html", values = values, length = length)

@views.route("/buy", methods = ["GET", "POST"])
@login_required
def buy():
    con = sqlite3.connect("database.db")
    db = con.cursor()

    #if method is post
    if request.method == "POST":

        #if user didn't enter in any fields
        if not request.form.get("symbol"):
            flash("Please enter in a stock symbol", category = "error")
            return redirect("/buy")
        if not request.form.get("shares"):
            flash("Please enter how many shares you want to buy", category = "error")
            return redirect("/buy")

        symbol = request.form.get("symbol").strip().upper()

        #if symbol is invalid
        if lookup(symbol) is None:
            flash("Please enter in a valid symbol", category = "error")
            return redirect("/buy")

        #if shares is not an integer
        if not request.form.get("shares").strip().isnumeric():
            flash("Please enter in a whole number of shares", category = "error")
            return redirect("/buy")

        buy_shares = int(request.form.get("shares").strip())

        #if user entered in a value <=0 for shares
        if buy_shares<=0:
            flash("Please enter in a value greater than 0", category = "error")
            return redirect("/buy")

        results = lookup(symbol)

        #current price of stock
        stock_price = round(results['price'],2)

        #name of company
        name = results['name']

        #id of current user
        user_id = session["user_id"]

        #current cash user owns
        db.execute("SELECT cash FROM users WHERE id = ?;", (user_id,))
        current_cash = db.fetchall()[0][0]

        #total price of everything
        total_price = stock_price * buy_shares

        #if user has enough money
        if current_cash>=total_price:

            #update user's cash
            db.execute("UPDATE users SET cash = ? WHERE id = ?;", (current_cash - total_price, user_id))
            con.commit()

            #calculate time
            now = datetime.now()
            date_time = now.strftime("%m/%d/%Y %H:%M:%S")

            #if there is an entry already for this symbol in the userStock table for this user
            db.execute("SELECT symbol,shares FROM userStock WHERE id = ?;", (user_id,))
            table = db.fetchall()

            flag = True
            
            for i in range(len(table)):
                if table[i][0] == symbol:
                    table_shares = table[i][1]
                    db.execute("UPDATE userStock SET shares = ? WHERE id = ? AND symbol = ?;", (table_shares + buy_shares, user_id, symbol))
                    con.commit()
                    flag = False
                    break

            if flag:
                db.execute("INSERT INTO userStock (id,symbol,name,shares) VALUES(?,?,?,?)", (user_id, symbol, name, buy_shares))
                con.commit()
            db.execute("INSERT INTO transactions (user_id,symbol,name,shares,price,time) VALUES(?,?,?,?,?,?)", (user_id, symbol, name, buy_shares, stock_price, date_time))
            con.commit()
        
        #if not enough money
        else:
            flash("You do not have enough money", category="error")
            return redirect("/buy")

        flash("Bought!", category="success")
        return redirect("/account")

    #if method is get
    else:
        return render_template("buy.html")


@views.route("/sell", methods = ["GET", "POST"])
@login_required
def sell():
    con = sqlite3.connect("database.db")
    db = con.cursor()

    #get all symbols and shares
    user_id = session['user_id']
    db.execute("SELECT symbol,name,shares FROM userStock WHERE id = ?;", (user_id,))
    rows = db.fetchall()

    #if user has any stock with 0 shares
    for index in range(len(rows)):
        if rows[index][2] == 0:
            #remove the row from table
            symbol = rows[index][0]
            db.execute("DELETE FROM userStock WHERE symbol = ? AND id = ?;", (symbol, user_id))
            con.commit()

    db.execute("SELECT symbol, name, shares FROM userStock WHERE id = ?;", (user_id,))
    values = db.fetchall()
    table = {}

    for i in range(len(values)):
        symbol = values[i][0]
        shares = values[i][2]

        table[symbol] = shares

    #if method is post
    if request.method == "POST":

        #if user didn't enter in any fields
        if not request.form.get("symbol"):
            flash("Please select a stock", category = "error")
            return redirect("/sell")
        if not request.form.get("shares"):
            flash("Please enter how many shares you would like to sell", category = "error")
            return redirect("/sell")

        #if shares is not an integer
        if not request.form.get("shares").strip().isnumeric():
            flash("Please enter in a whole number of shares", category = "error")
            return redirect("/sell")

        symbol = request.form.get("symbol").strip()
        sell_shares = int(request.form.get("shares").strip())

        #if user entered in a value <=0 for shares
        if sell_shares<=0:
            flash("Please enter in a value greater than 0", category = "error")
            return redirect("/sell")

        #if user even owns the stock
        if symbol not in table:
            flash("You don't own this stock", category = "error")
            return redirect("/sell")
        else:
            #if user has no shares of the company
            if table[symbol] <= 0:
                flash("You don't own any shares of this company", category = "error")
                return redirect("/sell")
            else:
                #if user entered in more shares than they own
                current_shares = table[symbol]
                if sell_shares>current_shares:
                    flash("You don't own that many shares of this company", category = "error")
                    return redirect("/sell")
                else:
                    #current price and name of stock
                    values = lookup(symbol)
                    stock_price = values['price']
                    name = values['name']
                    total = sell_shares * stock_price

                    #take away shares from userStock
                    db.execute("UPDATE userStock SET shares = ? WHERE id = ? AND symbol = ?;", (current_shares - sell_shares, user_id, symbol))
                    con.commit()

                    #add cash to user
                    db.execute("SELECT cash FROM users WHERE id = ?;", (user_id,))
                    cash = db.fetchall()[0][0]
                    db.execute("UPDATE users SET cash = ? WHERE id = ?;", (cash + total, user_id))
                    con.commit()

                    #add data into transactions
                    now = datetime.now()
                    date_time = now.strftime("%d/%m/%Y %H:%M:%S")

                    db.execute("INSERT INTO transactions (user_id, symbol, name, shares, price, time) VALUES (?,?,?,?,?,?)", (user_id, symbol, name, -1 * sell_shares, stock_price, date_time))
                    con.commit()
        con.close()           
        flash("Sold!", category = "success")
        return redirect("/account")
    
    #if method is get
    else:
        return render_template("sell.html", values = values, length = len(values))


@views.route("/changePassword", methods = ["GET", "POST"])
@login_required
def changePassword():
    con = sqlite3.connect("database.db")
    db = con.cursor()

    #if method is post
    if request.method == "POST":
        
        current_pass = request.form.get("currentPassword").strip()
        new_pass = request.form.get("newPassword").strip()
        confirm_pass = request.form.get("confirmation").strip()

        #Check for any errors
        if not current_pass:
            flash("Please enter your current password", category = "error")
            return redirect("/changePassword")
        elif not new_pass:
            flash("Please enter your new password", category = "error")
            return redirect("/changePassword")
        elif not confirm_pass:
            flash("Please confirm your new password", category = "error")
            return redirect("/changePassword")
        elif new_pass != confirm_pass:
            flash("Passwords do not match", category = "error")
            return redirect("/changePassword")

        #current user id
        user_id = session["user_id"]
        
        #current pass hashed
        db.execute("SELECT hash FROM users WHERE id = ?;", (user_id,))
        rows = db.fetchall()[0][0]

        #new pass hashed
        confirm_pass_hashed = generate_password_hash(confirm_pass)

        #check if user entered correct current pass
        if check_password_hash(rows, current_pass):
            
            #if yes, change password to new password
            db.execute("UPDATE users SET hash = ? WHERE id = ?;", (confirm_pass_hashed, user_id))
            con.commit()
        else:
            
            #if not
            flash("You entered the wrong current password", category = "error")
            return redirect("/changePassword")
        
        con.close()
        flash("Password successfully changed!", category = "success")
        return redirect("/login")

    #if method is get
    else:
        return render_template("changePassword.html")

@views.route("/logout")
@login_required
def logout():
    #clear session
    session.clear()

    return redirect("/login")