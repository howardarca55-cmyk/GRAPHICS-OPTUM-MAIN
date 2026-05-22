from flask import Flask, request, redirect, url_for, session, render_template, jsonify
from flask_bcrypt import Bcrypt, generate_password_hash
from db import get_connection
import mysql.connector
import config
import os
import smtplib
import random
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

BASE = os.path.dirname(__file__)
TMPL = os.path.join(BASE, "..", "templates")
STAT = os.path.join(BASE, "..", "statistics")

app = Flask(__name__,
    template_folder=TMPL,
    static_folder=STAT,
    static_url_path=""
)
app.secret_key = config.SECRET_KEY
bcrypt = Bcrypt(app)


# ── Helpers 
def logged_in():
    return "user_id" in session


# ── Home 
@app.route("/")
def index():
    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM categories ORDER BY name")
    categories = cursor.fetchall()

    cursor.execute("""
        SELECT p.*, c.name AS category_name
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.category_id
        ORDER BY p.product_id DESC
    """)
    products = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("index.html",
        products=products,
        categories=categories,
        user=session.get("email"),
        logged_in=logged_in()
    )


# ── Register
@app.route("/register", methods=["GET", "POST"])
def register():
    error   = None
    success = None

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email    = request.form.get("email",    "").strip()
        password = request.form.get("password", "").strip()

        if not username or not email or not password:
            error = "All fields are required."

        elif len(password) < 6:
            error = "Password must be at least 6 characters."

        else:
            hashed = bcrypt.generate_password_hash(password).decode("utf-8")
            try:
                conn   = get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                    (username, email, hashed)
                )
                conn.commit()
                cursor.close()
                conn.close()
                return render_template("login.html",
                    error=None,
                    success="Account created! You can now login.",
                    logged_in=False
                )

            except mysql.connector.errors.IntegrityError:
                error = "Email or username is already registered."

            except mysql.connector.Error as e:
                error = f"Database error: {str(e)}"

    return render_template("register.html", error=error, logged_in=logged_in())


# ── Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if logged_in():
        return redirect(url_for("index"))

    error = None
    if request.method == "POST":
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not email or not password:
            error = "All fields are required."
        else:
            conn   = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            cursor.close()
            conn.close()

            if user and bcrypt.check_password_hash(user["password"], password):
                session["user_id"]  = user["user_id"]
                session["email"]    = user["email"]
                session["username"] = user["username"]
                return redirect(url_for("index"))
            else:
                error = "Invalid email or password."

    return render_template("login.html", error=error, logged_in=False)

# ---- new password reset route
def send_reset_code(to_email, code):
    msg = MIMEMultipart()
    msg["From"]    = config.MAIL_USERNAME
    msg["To"]      = to_email
    msg["Subject"] = "Your Password Reset Code"

    body = f"""
    <h2>Password Reset Code</h2>
    <p>Your verification code is:</p>
    <h1 style="letter-spacing: .5rem; color: crimson;">{code}</h1>
    <p>This code expires in <strong>5 minutes</strong>.</p>
    <p>If you did not request this, ignore this email.</p>
    """
    msg.attach(MIMEText(body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(config.MAIL_USERNAME, config.MAIL_PASSWORD)
        server.sendmail(config.MAIL_USERNAME, to_email, msg.as_string())


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    error     = None
    success   = None
    code_sent = False

    if request.method == "POST":
        email = request.form.get("email", "").strip()

        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if not user:
            error = "No account found with that email."
        else:
            code       = str(random.randint(100000, 999999))
            expires_at = datetime.now() + timedelta(minutes=5)

            cursor.execute(
                "INSERT INTO password_resets (email, code, expires_at, used) VALUES (%s, %s, %s, 0)",
                (email, code, expires_at)
            )
            conn.commit()

            try:
                send_reset_code(email, code)
                session["reset_email"] = email
                success   = "Code sent! Check your email."
                code_sent = True
            except Exception as e:
                error = f"Failed to send email: {str(e)}"

        cursor.close()
        conn.close()

    return render_template("forgot.html",
        error=error,
        success=success,
        code_sent=code_sent,
        logged_in=logged_in()
    )


@app.route("/verify-code", methods=["POST"])
def verify_code():
    code  = request.form.get("verification_code", "").strip()
    email = session.get("reset_email")
    error = None

    if not email:
        return redirect(url_for("forgot_password"))

    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT * FROM password_resets
        WHERE email = %s AND code = %s AND used = 0
        ORDER BY expires_at DESC LIMIT 1
    """, (email, code))
    record = cursor.fetchone()
    cursor.close()
    conn.close()

    if not record:
        error = "Invalid code. Please try again."
    elif datetime.now() > record["expires_at"]:
        error = "Code has expired. Please request a new one."
    else:
        return redirect(url_for("new_password"))

    return render_template("forgot.html",
        error=error,
        success=None,
        logged_in=logged_in()
    )


@app.route("/new-password")
def new_password():
    if not session.get("reset_email"):
        return redirect(url_for("forgot_password"))
    return render_template("newpass.html", error=None, success=None, logged_in=logged_in())


@app.route("/reset-password", methods=["POST"])
def reset_password():
    email      = session.get("reset_email")
    new_pw     = request.form.get("new_password",     "").strip()
    confirm_pw = request.form.get("confirm_password", "").strip()

    if not email:
        return redirect(url_for("forgot_password"))

    error = None
    if len(new_pw) < 6:
        error = "Password must be at least 6 characters."
    elif new_pw != confirm_pw:
        error = "Passwords do not match."
    else:
        hashed = bcrypt.generate_password_hash(new_pw).decode("utf-8")
        conn   = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE users SET password = %s WHERE email = %s",
            (hashed, email)
        )
        cursor.execute(
            "UPDATE password_resets SET used = 1 WHERE email = %s",
            (email,)
        )
        conn.commit()
        cursor.close()
        conn.close()

        session.pop("reset_email", None)
        return render_template("login.html",
            error=None,
            success="Password reset! You can now log in.",
            logged_in=False
        )

    return render_template("newpass.html", error=error, success=None, logged_in=logged_in())

# ── Logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ── Dashboard (protected)
@app.route("/dashboard")
def dashboard():
    if not logged_in():
        return redirect(url_for("login"))

    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT user_id, username, email FROM users WHERE user_id = %s", (session["user_id"],))
    user = cursor.fetchone()

    cursor.execute("""
        SELECT o.order_id, o.total_amount, o.order_date,
               pm.method_name AS payment_method,
               COUNT(oi.order_item_id) AS item_count
        FROM orders o
        LEFT JOIN payment_methods pm ON o.payment_id = pm.payment_id
        LEFT JOIN order_items oi ON o.order_id = oi.order_id
        WHERE o.user_id = %s
        GROUP BY o.order_id, o.total_amount, o.order_date, pm.method_name
        ORDER BY o.order_date DESC
    """, (session["user_id"],))
    orders = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("dashboard.html",
        user=user,
        orders=orders,
        logged_in=True,
        pw_error=None,
        pw_success=None,
        profile_success=None
    )


# ── Change Password
@app.route("/dashboard/change-password", methods=["POST"])
def change_password():
    if not logged_in():
        return redirect(url_for("login"))

    current_pw = request.form.get("current_password", "").strip()
    new_pw     = request.form.get("new_password",     "").strip()
    confirm_pw = request.form.get("confirm_password", "").strip()

    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (session["user_id"],))
    user = cursor.fetchone()

    pw_error   = None
    pw_success = None

    if not bcrypt.check_password_hash(user["password"], current_pw):
        pw_error = "Current password is incorrect."
    elif len(new_pw) < 6:
        pw_error = "New password must be at least 6 characters."
    elif new_pw != confirm_pw:
        pw_error = "Passwords do not match."
    else:
        hashed = bcrypt.generate_password_hash(new_pw).decode("utf-8")
        try:
            cursor.execute(
                "UPDATE users SET password = %s WHERE user_id = %s",
                (hashed, session["user_id"])
            )
            conn.commit()
            pw_success = "Password updated successfully."
        except Exception as e:
            conn.rollback()
            pw_error = f"Failed to update password: {str(e)}"

    cursor.close()
    conn.close()

    return render_template("dashboard.html",
    user=user,
    orders=[],
    logged_in=True,
    pw_error=pw_error,
    pw_success=pw_success,
    profile_success=None
)

# ── Shop Page
@app.route("/shop")
def shop():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT p.*, c.name AS category_name
        FROM products p
        LEFT JOIN categories c
        ON p.category_id = c.category_id
    """)

    products = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("shop.html",
        products=products,
        user=session.get("email"),
        logged_in=logged_in()
    )


# ── Cart
@app.route("/cart")
def cart():
    return render_template("cart.html",
        user=session.get("email"),
        logged_in=logged_in()
    )


# ── User profile
@app.route("/user")
def user():
    if not logged_in():
        return redirect(url_for("login"))
    return render_template("user.html",
        user=session.get("email"),
        logged_in=logged_in()
    )


# ── Products API
@app.route("/api/products")
def api_products():
    category_id = request.args.get("category_id")
    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)

    if category_id:
        cursor.execute("""
            SELECT p.*, c.name AS category_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.category_id
            WHERE p.category_id = %s
            ORDER BY p.product_id DESC
        """, (category_id,))
    else:
        cursor.execute("""
            SELECT p.*, c.name AS category_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.category_id
            ORDER BY p.product_id DESC
        """)

    products = cursor.fetchall()
    cursor.close()
    conn.close()

    for p in products:
        if p.get("price"):
            p["price"] = float(p["price"])

    return jsonify(products)


# ── Contact Form
@app.route("/contact", methods=["POST"])
def contact():
    name    = request.form.get("name", "").strip()
    email   = request.form.get("email", "").strip()
    message = request.form.get("message", "").strip()
    return redirect(url_for("index") + "#contact")


if __name__ == "__main__":
    app.run(debug=True)