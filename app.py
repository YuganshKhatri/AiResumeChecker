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
    You are an expert ATS (Applicant Tracking System) Resume Analyzer.
    Your task is to evaluate the following resume ONLY for the job role: "{role}".
    Resume:
    {text}

    IMPORTANT INSTRUCTIONS:
    1. Use the scoring rubric below exactly.
    2. Do not guess randomly or change the scoring criteria.
    3. Be objective and consistent.
    4. Assume this same rubric is used for every resume.
    5. Return ONLY valid JSON.
    6. Do not include markdown or explanations outside the JSON.

    SCORING RUBRIC (Total = 100)

    1. Skills Match (40 points)
    - Compare the candidate's technical and soft skills with those expected for the given role.
    - Award points based on relevance and completeness.

    2. Experience Relevance (20 points)
    - Evaluate how relevant the work experience is for the target role.
    - Consider internships, projects, and practical experience if professional experience is limited.

    3. Projects (15 points)
    - Evaluate the quality, complexity, technologies used, and relevance of projects.

    4. Resume Structure & Formatting (10 points)
    - Check section organization, readability, ATS-friendly formatting, and consistency.

    5. Education & Certifications (5 points)
    - Evaluate educational background and relevant certifications.

    6. Keywords Coverage (10 points)
    - Compare the resume against common keywords expected for the target role.
    - Deduct points for important missing keywords.

    FINAL ATS SCORE
    Final ATS Score = Sum of all six categories.
    Do NOT invent an arbitrary score.
    The final score MUST equal the sum of the category scores.

    Return ONLY the following JSON:

    {{
    "ats_score": 0,
    "score_breakdown": {
        "skills_match": 0,
        "experience": 0,
        "projects": 0,
        "formatting": 0,
        "education": 0,
        "keywords": 0
    },
        "strengths": [],
        "weaknesses": [],
        "missing_skills": [],
        "keywords_to_improve": [],
        "suggestions": [],
        "summary": ""
    }}
    """
    response=model.generate_content(prompt)
    result=json.loads(response.text)
    today = datetime.now().strftime("%d %B %Y")
    return render_template("results.html",name=name,result=result,filename=uploaded_file.filename,date=today,role=role)
if __name__=='__main__':
    app.run(host='0.0.0.0',port=7000,debug=True)