from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from huggingface_hub import InferenceClient


app=Flask(__name__, template_folder='../frontend/templates', static_folder='../frontend/static')
app.config['SQLALCHEMY_DATABASE_URI']='sqlite:///data.db' 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False  
app.secret_key = 'your_secret_key'
db=SQLAlchemy(app)

class User(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    email=db.Column(db.String(120),unique=True, nullable=False)
    password=db.Column(db.String(120),nullable=False)
    chats=db.relationship('ChatHistory',back_populates='user',lazy=True)

class ChatHistory(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    user_input=db.Column(db.String(500),nullable=False)
    ai_response=db.Column(db.String(500),nullable=False)
    user_id=db.Column(db.Integer,db.ForeignKey('user.id'), nullable=False)
    user=db.relationship('User',back_populates='chats')

@app.route('/')
def home():
    if 'email' in session:
        return redirect(url_for('chat'))
    return redirect(url_for('signin'))

@app.route('/signin',methods=['GET','POST'])
def signin():
    if request.method=='POST':
        email=request.form['email']
        password=request.form['password']
        user=User.query.filter_by(email=email).first()
        if not user:
            return render_template('signin.html',error="Email not found. Please sign up first.",signup_url=url_for('signup'))
        if not check_password_hash(user.password,password):
            return render_template('signin.html',error="Invalid password. Please try again.")
        session['email'] = email
        return redirect(url_for('chat'))
    return render_template('signin.html')

@app.route('/signup',methods=['GET','POST'])
def signup():
    if request.method=='POST':
        email=request.form['email']
        password=request.form['password']
        existing_user=User.query.filter_by(email=email).first()
        if existing_user:
            return render_template('signup.html',error="Email already exists.")
        hashed_password=generate_password_hash(password)
        new_user=User(email=email,password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('signin'))
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('email', None)
    return redirect(url_for('signin'))

client = InferenceClient(api_key="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")

@app.route('/chat',methods=['GET', 'POST'])
def chat():
    if 'email' not in session:
        return redirect(url_for('signin'))
    user = User.query.filter_by(email=session['email']).first()
    if request.method == 'POST':
        user_input = request.form['user_input']
        print(f"User Input: {user_input}") 
        try:
            messages = [{"role": "user", "content": user_input}]
            completion = client.chat.completions.create(
                model="microsoft/DialoGPT-medium",
                messages=messages,
                max_tokens=500
            )
            ai_response = completion.choices[0].message["content"]
        except Exception as e:
            ai_response = "Sorry, there was an error generating a response."
        print(f"AI Response: {ai_response}")  
        chat = ChatHistory(user_input=user_input, ai_response=ai_response, user_id=user.id)
        db.session.add(chat)
        db.session.commit()
        return redirect(url_for('chat'))
    chat_history = ChatHistory.query.filter_by(user_id=user.id).all()
    return render_template('chat.html', chat_history=chat_history)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'email' not in session:
        return redirect(url_for('signin'))
    user = User.query.filter_by(email=session['email']).first()
    if request.method == 'POST':
        new_email = request.form['email']
        if new_email != user.email:
            existing_user = User.query.filter_by(email=new_email).first()
            if existing_user:
                flash("Email already exists.", "error")
            else:
                user.email = new_email
                db.session.commit()
                flash("Profile updated successfully.", "success")
                return redirect(url_for('profile'))
    return render_template('profile.html', user=user)

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if 'email' not in session:
        return redirect(url_for('signin'))
    user = User.query.filter_by(email=session['email']).first()
    if request.method == 'POST':
        old_password = request.form['old_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        if not check_password_hash(user.password, old_password):
            flash("Current password is incorrect.", "error")
        elif new_password != confirm_password:
            flash("Passwords do not match.", "error")
        else:
            hashed_new_password = generate_password_hash(new_password)
            user.password = hashed_new_password
            db.session.commit()
            flash("Password changed successfully.", "success")
            return redirect(url_for('signin')) 
    return render_template('change_password.html')

@app.route('/new_conversation', methods=['POST'])
def new_conversation():
    if 'email' not in session:
        return redirect(url_for('signin'))
    user=User.query.filter_by(email=session['email']).first()
    ChatHistory.query.filter_by(user_id=user.id).delete()  
    db.session.commit()
    return redirect(url_for('chat'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)