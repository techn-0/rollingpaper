from flask import Flask, request, jsonify, render_template, redirect, url_for
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
import jwt
import os
from dotenv import load_dotenv
from bson import ObjectId  # Import ObjectId

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

client = MongoClient(os.getenv('MONGODB_URI'))
db = client['user_database']
users_collection = db['users']

def create_jwt_token(user_id):
    payload = {
        'user_id': str(user_id),  # ObjectId를 문자열로 변환
        'exp': datetime.now(timezone.utc) + timedelta(hours=1)  # UTC 시간 생성
    }
    token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')
    return token

# 파일 업로드 설정
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'mp3', 'wav', 'mp4'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    return render_template('login2.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'] # 입력된 사용자 이름 가져오기
        password = request.form['password']  # 입력된 비밀번호 가져오기
        user = users_collection.find_one({'username': username}) # 사용자 이름으로 DB에서 사용자 찾기
        if user and user['password'] == password: #사용자가 일치하고 비밀번호가 일치하면
            token = create_jwt_token(user['_id']) #토큰 발급
            response = jsonify({'token': token}) #json응답 생성
            response.set_cookie('token', token, httponly=True) #쿠키설정
            return response
        return jsonify({'message': '잘못된 유저네임 또는 비밀번호 입니다.'}), 401
    return render_template('login2.html')

@app.route('/signup', methods=['POST'])
def signup():
    username = request.form['username']
    password = request.form['password']
    confirm_password = request.form['confirm_password']
    name = request.form['name']
    nickname = request.form['nickname']

    if password != confirm_password:
        return jsonify({'message': '비밀번호가 일치하지 않습니다.'}), 400

    if users_collection.find_one({'username': username}):
        return jsonify({'message': '이미 존재하는 아이디입니다.'}), 400

    profile_pic = request.files.get('profile_pic')  # 업로드된 프로필 사진 파일 가져오기
    profile_pic_filename = None

    if profile_pic and allowed_file(profile_pic.filename):
        filename = f"{uuid.uuid4().hex}.{profile_pic.filename.rsplit('.', 1)[1].lower()}"
        profile_pic_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        profile_pic.save(profile_pic_path)
        profile_pic_filename = f"uploads/{filename}"

    users_collection.insert_one({
        'username': username,
        'password': password,
        'name': name,
        'nickname': nickname,
        'profile_picture': profile_pic_filename  # 프로필 사진 경로 저장
    })

    return redirect(url_for('login'))

@app.route('/users')
def success():
    token = request.cookies.get('token')
    if token:
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            user_id = ObjectId(payload['user_id'])  # 'user_id'를 ObjectId로 변환
            user = users_collection.find_one({'_id': user_id})  # MongoDB에서 사용자 검색
            if user:
                return render_template('users.html')
            else:
                return 'User not found', 404
        except jwt.ExpiredSignatureError:
            return 'Token has expired', 401
        except jwt.InvalidTokenError:
            return 'Invalid Token', 401
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    # 'token' 쿠키를 빈 값으로 설정하고 max_age를 0으로 설정하여 삭제합니다.
    response = redirect(url_for('login'))
    response.set_cookie('token', '', httponly=True, max_age=0)
    return response

if __name__ == '__main__':
    app.run(debug=True)
