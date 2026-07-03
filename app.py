import os
from datetime import datetime
from collections import Counter
from flask import Flask
from flask import render_template
from flask import request,jsonify
from flask import url_for,flash,session
from flask import redirect
from flask_sqlalchemy import SQLAlchemy
import fitz
import google.generativeai as genai
import json

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model=genai.GenerativeModel("gemini-2.5-flash")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy()
db.init_app(app)
app.app_context().push()

class User_Details(db.Model):
    __tablename__='User_Details'
    Name=db.Column(db.String)
    Email=db.Column(db.String,primary_key=True)
    Password=db.Column(db.String)

with app.app_context():
    db.create_all()
@app.route("/",methods=["GET","POST"])
def home():
    return render_template("home.html")
@app.route("/signup",methods=["GET","POST"])
def signup():
    if request.method=="POST":
        name=request.form["name"]
        email=request.form["email"]
        passw=request.form["passw"]
        cpassw=request.form["cpassw"]
        if(passw!=cpassw):
            flash("Password does not Match!","passmm")
            return redirect(url_for("signup"))
        if(User_Details.query.filter_by(Email=email.lower())).first():
            flash("Email Already attached to a Account. Login or use a different Email Address","userExist")
            return redirect(url_for("signup"))
        newUser=User_Details(Name=name,Email=email.lower(),Password=passw)
        session["name"]=name
        db.session.add(newUser)
        db.session.commit()
        flash("Account Created Successfull.Please Login")
        return redirect(url_for("login"))
    return render_template("SignUp.html")
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["address"].lower()
        password = request.form["password"]
        user = User_Details.query.filter_by(Email=username).first()
        if not user:
            flash("Email does not exist.", "error")
            return redirect(url_for("login"))
        if user.Password != password:
            flash("Incorrect password.", "error")
            return redirect(url_for("login"))
        session["name"]=user.Name
        return redirect(url_for("homePage"))
    return render_template("Login.html")
@app.route("/homePage", methods=["GET", "POST"])
def homePage():
    if "name" not in session:
        return redirect(url_for("login"))
    return render_template(
        "homePage.html",
        name=session["name"]
    )
@app.route("/analyze",methods=["GET","POST"])
def analyze():
    name=session.get("name")
    uploaded_file=request.files["resume"]
    if uploaded_file.filename=="":
        return "No File Selected"
    os.makedirs("uploads", exist_ok=True)
    uploaded_file.save(os.path.join("uploads", uploaded_file.filename))
    filepath=os.path.join("uploads",uploaded_file.filename)
    doc=fitz.open(filepath)
    role=request.form["role"]
    text=""
    for page in doc:
        text+=page.get_text()
    doc.close()
    print(text)
    prompt = f"""
    You are an expert ATS Resume Checker.
    Analyze the following resume for the role of "{role}".
    Resume:
    {text}
    Return ONLY valid JSON.
    The JSON format should be:
    {{
        "ats_score": 0,
        "strengths": [],
        "weaknesses": [],
        "missing_skills": [],
        "keywords_to_improve": [],
        "suggestions": []
    }}
    Do not write explanations.
    Do not use markdown.
    Do not use ```json.
    Return only JSON.
    """
    response=model.generate_content(prompt)
    result=json.loads(response.text)
    today = datetime.now().strftime("%d %B %Y")
    return render_template("results.html",name=name,result=result,filename=uploaded_file.filename,date=today)
if __name__=='__main__':
    app.run(host='0.0.0.0',port=7000,debug=True)