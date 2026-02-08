from pathlib import Path
from sqlite3 import dbapi2 as sqlite3
from quart import Quart
from quart import render_template, g, redirect, request, url_for, session
from quart_discord import DiscordOAuth2Session, requires_authorization, Unauthorized

import os


app = Quart(__name__)

app.secret_key = bytes.fromhex(os.getenv("SECRET_KEY"))

app.config["DISCORD_CLIENT_ID"] = os.getenv("DISCORD_CLIENT_ID")
app.config["DISCORD_CLIENT_SECRET"] = os.getenv("DISCORD_CLIENT_SECRET")
app.config["DISCORD_REDIRECT_URI"] = "http://127.0.0.1:5000/callback"

discord = DiscordOAuth2Session(app)

def run() -> None:
    app.run(debug=True)


app.config.update({
  "DATABASE": Path(app.root_path) / "blog.db",
})


def _connect_db():
    engine = sqlite3.connect(app.config["DATABASE"])
    engine.row_factory = sqlite3.Row
    return engine


def init_db():
    db = _connect_db()
    with open(Path(app.root_path) / "schema.sql", mode="r") as file_:
        db.cursor().executescript(file_.read())
    db.commit()


def _get_db():
    if not hasattr(g, "sqlite_db"):
        g.sqlite_db = _connect_db()
    return g.sqlite_db


@app.get("/")
async def posts():
    db = _get_db()
    cur = db.execute(
        """SELECT title, text
             FROM post
         ORDER BY id DESC""",
    )
    posts_q = cur.fetchall()
    return await render_template("posts.html", posts=posts_q)


@app.route("/create/", methods=["GET", "POST"])
async def create():
    if request.method == "POST":
        db = _get_db()
        form = await request.form
        db.execute(
            "INSERT INTO post (title, text) VALUES (?, ?)",
            [form["title"], form["text"]],
        )
        db.commit()
        return redirect(url_for("posts"))
    else:
        return await render_template("create.html")


@app.route("/callback/")
async def callback():
    await discord.callback()
    return redirect(url_for(".me"))

@app.errorhandler(Unauthorized)
async def redirect_unauthorized(e):
    return redirect(url_for("login"))


@app.route("/login/")
async def login():
    return await discord.create_session()


@app.route("/me/")
@requires_authorization
async def me():
    user = await discord.fetch_user()
    return f"""
        <html>
            <head>
                <title>{user.name}</title>
            </head>
            <body>
                <img src='{user.avatar_url}' />
                <p>{user.id}</p>
            </body>
        </html>"""