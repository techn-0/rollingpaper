from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_bcrypt import Bcrypt
from pymongo import MongoClient
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 세션 데이터 암호화에 사용되는 비밀 키 설정
bcrypt = Bcrypt(app)  # 비밀번호 암호화를 위한 Bcrypt 설정

# MongoDB 클라이언트 설정
client = MongoClient('localhost', 27017)
db = client['your_database_name']  # 사용할 데이터베이스 이름 설정
users_collection = db['users']  # 사용자 컬렉션 설정
messages_collection = db['messages']  # 메시지 컬렉션 설정

@app.route('/')
def index():
    if 'username' in session:  # 사용자가 로그인되어 있으면
        return redirect(url_for('users'))  # 유저 목록 페이지로 리다이렉트
    return render_template('login.html')  # 로그인 페이지 렌더링

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']  # 입력된 사용자 이름 가져오기
    password = request.form['password']  # 입력된 비밀번호 가져오기
    user = users_collection.find_one({'username': username})  # 사용자 이름으로 DB에서 사용자 찾기
    if user and bcrypt.check_password_hash(user['password'], password):  # 사용자가 존재하고 비밀번호가 일치하면
        session['username'] = username  # 세션에 사용자 이름 저장
        return redirect(url_for('users'))  # 유저 목록 페이지로 리다이렉트
    flash('Invalid username or password')  # 오류 메시지 출력
    return redirect(url_for('index'))  # 로그인 페이지로 리다이렉트

@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']  # 입력된 사용자 이름 가져오기
    password = request.form['password']  # 입력된 비밀번호 가져오기
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')  # 비밀번호 암호화
    users_collection.insert_one({'username': username, 'password': hashed_password})  # 사용자 정보 DB에 저장
    flash('Registration successful')  # 성공 메시지 출력
    return redirect(url_for('index'))  # 로그인 페이지로 리다이렉트

@app.route('/users')
def users():
    if 'username' not in session:  # 사용자가 로그인되어 있지 않으면
        return redirect(url_for('index'))  # 로그인 페이지로 리다이렉트
    users = users_collection.find()  # DB에서 모든 사용자 가져오기
    return render_template('users.html', users=users)  # 유저 목록 페이지 렌더링

@app.route('/logout')
def logout():
    session.pop('username', None)  # 세션에서 사용자 이름 제거
    return redirect(url_for('index'))  # 로그인 페이지로 리다이렉트

@app.route('/paper/<user_id>')
def paper(user_id):
    if 'username' not in session:  # 사용자가 로그인되어 있지 않으면
        return redirect(url_for('index'))  # 로그인 페이지로 리다이렉트
    messages = messages_collection.find({'recipient_id': user_id})  # 특정 사용자에게 보낸 메시지 가져오기
    return render_template('paper.html', messages=messages, user_id=user_id)  # 롤링 페이퍼 페이지 렌더링

@app.route('/message', methods=['POST'])
def message():
    if 'username' not in session:  # 사용자가 로그인되어 있지 않으면
        return redirect(url_for('index'))  # 로그인 페이지로 리다이렉트
    recipient_id = request.form['recipient_id']  # 쪽지 받을 사용자 ID 가져오기
    content = request.form['content']  # 쪽지 내용 가져오기
    messages_collection.insert_one({
        'content': content,
        'author': session['username'],  # 현재 사용자 이름을 작성자로 설정
        'recipient_id': recipient_id
    })  # 메시지 DB에 저장
    return redirect(url_for('paper', user_id=recipient_id))  # 다시 롤링 페이퍼 페이지로 리다이렉트

@app.route('/delete_message/<message_id>', methods=['POST'])
def delete_message(message_id):
    if 'username' not in session:  # 사용자가 로그인되어 있지 않으면
        return redirect(url_for('index'))  # 로그인 페이지로 리다이렉트
    message = messages_collection.find_one({'_id': ObjectId(message_id)})  # 메시지 ID로 메시지 찾기
    if message['author'] == session['username']:  # 메시지 작성자가 현재 사용자와 일치하면
        messages_collection.delete_one({'_id': ObjectId(message_id)})  # 메시지 삭제
    return redirect(url_for('paper', user_id=message['recipient_id']))  # 다시 롤링 페이퍼 페이지로 리다이렉트

if __name__ == '__main__':
    app.run(debug=True)  # 디버그 모드로 Flask 애플리케이션 실행
