from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import random
from flask_mail import Mail, Message

app = Flask(__name__)
app.secret_key = "secretkey"

# ---------------- MAIL CONFIG ----------------
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'lokeshkumarloki580@gmail.com'
app.config['MAIL_PASSWORD'] = 'rmml gvsm ixlz oyyc'

mail = Mail(app)

# ---------------- DATABASE ----------------
def get_connection():
    con = sqlite3.connect("notes.db")
    con.row_factory = sqlite3.Row
    return con

# ---------------- LOGIN ----------------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']

        con = get_connection()
        cur = con.cursor()
        cur.execute("SELECT * FROM users WHERE email=?", (email,))
        user = cur.fetchone()
        con.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            flash("Login successful!", "success")
            return redirect('/dashboard')
        else:
            flash("Invalid credentials", "danger")

    return render_template("login.html")

# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        con = get_connection()
        cur = con.cursor()
        cur.execute("INSERT INTO users (username,email,password) VALUES (?,?,?)",
                    (username, email, password))
        con.commit()
        con.close()

        flash("Registered Successfully!", "success")
        return redirect('/')

    return render_template("register.html")

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully!", "info")
    return redirect('/')

# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    if "user_id" not in session:
        return redirect('/')

    search = request.args.get('search')

    con = get_connection()
    cur = con.cursor()

    if search:
        cur.execute(
            "SELECT * FROM notes WHERE user_id=? AND (title LIKE ? OR content LIKE ?)",
            (session['user_id'], f"%{search}%", f"%{search}%")
        )
    else:
        cur.execute(
            "SELECT * FROM notes WHERE user_id=?",
            (session['user_id'],)
        )

    notes = cur.fetchall()
    con.close()

    return render_template("dashboard.html", notes=notes)

# ---------------- ADD NOTE ----------------
@app.route('/addnote', methods=['GET', 'POST'])
def add_note():
    if "user_id" not in session:
        return redirect('/')

    if request.method == "POST":
        title = request.form['title']
        content = request.form['content']

        con = get_connection()
        cur = con.cursor()
        cur.execute("INSERT INTO notes (title,content,user_id) VALUES (?,?,?)",
                    (title, content, session['user_id']))
        con.commit()
        con.close()

        flash("Note added successfully!", "success")
        return redirect('/dashboard')

    return render_template("add_note.html")

# ---------------- VIEW ALL ----------------
@app.route('/viewall')
def viewall():
    if "user_id" not in session:
        return redirect('/')

    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT * FROM notes WHERE user_id=?", (session['user_id'],))
    notes = cur.fetchall()
    con.close()

    return render_template("view_all.html", notes=notes)

# ---------------- VIEW NOTE ----------------
@app.route('/viewnotes/<int:id>')
def view_note(id):
    if "user_id" not in session:
        return redirect('/')

    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT * FROM notes WHERE id=? AND user_id=?",
                (id, session['user_id']))
    note = cur.fetchone()
    con.close()

    return render_template("view_note.html", note=note)

# ---------------- UPDATE NOTE ----------------
@app.route('/updatenote/<int:id>', methods=['GET', 'POST'])
def update_note(id):
    if "user_id" not in session:
        return redirect('/')

    con = get_connection()
    cur = con.cursor()

    if request.method == "POST":
        title = request.form['title']
        content = request.form['content']

        cur.execute("UPDATE notes SET title=?,content=? WHERE id=? AND user_id=?",
                    (title, content, id, session['user_id']))
        con.commit()
        con.close()

        flash("Note updated successfully!", "success")
        return redirect('/viewall')

    cur.execute("SELECT * FROM notes WHERE id=? AND user_id=?",
                (id, session['user_id']))
    note = cur.fetchone()
    con.close()

    return render_template("update_note.html", note=note)

# ---------------- DELETE NOTE ----------------
@app.route('/deletenote/<int:id>')
def delete_note(id):
    if "user_id" not in session:
        return redirect('/')

    con = get_connection()
    cur = con.cursor()
    cur.execute("DELETE FROM notes WHERE id=? AND user_id=?",
                (id, session['user_id']))
    con.commit()
    con.close()

    flash("Note deleted successfully!", "danger")
    return redirect('/dashboard')





# ---------------- FORGOT PASSWORD ----------------
otp_store = {}

@app.route('/forgot', methods=['GET', 'POST'])
def forgot():
    if request.method == "POST":
        email = request.form['email']

        # check user exists
        con = get_connection()
        cur = con.cursor()
        cur.execute("SELECT * FROM users WHERE email=?", (email,))
        user = cur.fetchone()
        con.close()

        if not user:
            flash("Email not found!", "danger")
            return redirect('/forgot')

        otp = random.randint(100000, 999999)
        otp_store[email] = otp

        msg = Message(
            subject="Your OTP Code",
            sender=app.config['MAIL_USERNAME'],
            recipients=[email]
        )
        msg.body = f"Your OTP is: {otp}"

        try:
            mail.send(msg)
            flash("OTP sent to your email!", "success")
        except:
            flash("Failed to send OTP!", "danger")

        return redirect('/verify')

    return render_template("forgot.html")


# ---------------- VERIFY OTP ----------------
@app.route('/verify', methods=['GET', 'POST'])
def verify():
    if request.method == "POST":
        otp = int(request.form['otp'])

        for email, real_otp in otp_store.items():
            if otp == real_otp:
                session['reset_email'] = email
                flash("OTP verified!", "success")
                return redirect('/reset')

        flash("Invalid OTP", "danger")

    return render_template("verify.html")


# ---------------- RESET PASSWORD ----------------
@app.route('/reset', methods=['GET', 'POST'])
def reset():
    if "reset_email" not in session:
        return redirect('/')

    if request.method == "POST":
        password = generate_password_hash(request.form['password'])

        con = get_connection()
        cur = con.cursor()
        cur.execute("UPDATE users SET password=? WHERE email=?",
                    (password, session['reset_email']))
        con.commit()
        con.close()

        session.pop('reset_email', None)
        flash("Password reset successful!", "success")
        return redirect('/')

    return render_template("reset.html")




# ---------------- CONTACT ----------------
@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == "POST":
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')

        if not name or not email or not message:
            flash("All fields are required!", "danger")
            return redirect('/contact')

        msg = Message(
            subject="New Contact Message",
            sender=app.config['MAIL_USERNAME'],
            recipients=[app.config['MAIL_USERNAME']]
        )

        msg.body = f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}"

        try:
            mail.send(msg)
            flash("Message sent successfully!", "success")
        except:
            flash("Email sending failed!", "danger")

        return redirect('/contact')

    return render_template("contact.html")


# ---------------- ABOUT ----------------
@app.route('/about')
def about():
    return render_template("about.html")
# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)