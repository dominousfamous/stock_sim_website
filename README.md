# Stock Simulation
#### video URL: https://youtu.be/_aXJsiIyhrA
#### Description
The purpose of this project was to introduce inexperienced people to the world of stocks and trading - especially me.
Just like me, I believe that there are a good number of people who are afraid and hesitant to start investing in stocks.
This project is a simulation of trading stocks. Although it does not account for all the factors that come into play when trading stocks,
it uses real stocks and their real-time values.

I split the backend side of this project into two parts - application.py and views.py.

Application.py contains all the necessary aspects of starting the application - configuring the Flask app,
ensuring the user's API key is set(requirement for IEX), configuring the session to use the filesystem over cookies,
and finally running the app.

views.py contains the majority of the backend code for the web application. It contains all the routes, important methods,
login_required decorator, etc.

The frontend aspect of this project, on the other hand, was split up into two main folders: static-which contains the css file for this app - and
templates-which contains all the html files.

**layout.html** : base html page that every other html page extends; contains all the links at the navbar, IEX attribution link, and the important note at the top of the page

**register.html** : html page that allows users to register

**login.html** : html page that lets users login

**home.html** : html page that lets users view stocks of a variety of categories, as well as finding out the current price of stocks

**account.html** : html page for the page that shows the user's stocks, their values, and how much cash they have

**history.html** : html page that shows all of the user's transactions(buy,sell)

**buy.html** : html page that lets users buy stocks of their choice

**sell.html** : html page that lets users sell stocks that they own

**changeMoney.html** : allows users to deposit and withdraw money

**changePassword.html** : allows users to change their password

The main difficulty I had with this project is the homepage. I wanted users to be able to view all the stocks that belong to a particular category(for instance:airlines).
At first I tried to make calls to the IEX API for every stock that existed, but that took a ridiculous amount of time, and I did not have enough tokens/credit for my
free IEX account. I resorted to storing all the stocks' symbol,name and category into a SQL table, once and for all, so that whenever I would need to filter through
all the stocks depending on what category the user chose, all I needed to do was execute one or more fairly simple SQL queries. 

**Conclusion
This was truly one of the most entertaining projects I have ever done throughout all of the projects I did in different subjects. Unfortunately, this website isn't available 
to the whole world. It is only available to me, specifically the desktop these files are located on. To make it accessible to the whole world, I would need to deploy my web
application through Heroku or purchasing a domain name, but the purpose of this project wasn't mainly to make it available to everyone - rather it was for me to merely code a 
website, which I always wanted to do.
