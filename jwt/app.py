from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
import jwt
import os
import uuid
from dotenv import load_dotenv
from bson import ObjectId  # Import ObjectId

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

client = MongoClient(os.getenv('MONGODB_URI'))
db = client['user_database'] # 사용할 데이터베이스 이름 설정
users_collection = db['users']  # 사용자 컬렉션 설정
messages_collection = db['messages']  # 메시지 컬렉션 설정

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
def users():
    token = request.cookies.get('token')
    if token:
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            user_id = ObjectId(payload['user_id'])  # 'user_id'를 ObjectId로 변환
            user = users_collection.find_one({'_id': user_id})  # MongoDB에서 사용자 검색
            if user:
                users = users_collection.find().sort('name', 1)  # 1은 오름차 -1은 내림차 DB에서 모든 사용자 가져오기
                return render_template('users.html', users=users) # 유저 목록 페이지 렌더링
            else:
                return 'User not found', 404
        except jwt.ExpiredSignatureError:
            return 'Token has expired', 401
        except jwt.InvalidTokenError:
            return 'Invalid Token', 401
    return redirect(url_for('login'))

@app.route('/paper/<user_id>')
def paper(user_id):
    token = request.cookies.get('token')
    if token:
        try:

            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            my_id = ObjectId(payload['user_id'])  # 'user_id'를 ObjectId로 변환
            my = users_collection.find_one({'_id': my_id})  # MongoDB에서 사용자 검색

            recipient = users_collection.find_one({'_id': ObjectId(user_id)})
            if not recipient:
                return "User not found", 404
            
            messages = messages_collection.find({'recipient_id': user_id})

            messages_with_file_url = []
            for message in messages:
                file_url = message.get('file_url')
                if file_url:
                    file_extension = file_url.rsplit('.', 1)[1].lower()
                    message['file_url'] = url_for('static', filename=file_url)
                messages_with_file_url.append(message)

            return render_template('paper.html', messages=messages_with_file_url, recipient=recipient, my=my) # 유저 목록 페이지 렌더링
        except jwt.ExpiredSignatureError:
            return 'Token has expired', 401 # 토큰 만료 처리
        except jwt.InvalidTokenError:
            return 'Invalid Token', 401 #유효성 만료
    return redirect(url_for('login'))

@app.route('/message', methods=['POST'])
def message():
    token = request.cookies.get('token')
    if token:
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            user_id = ObjectId(payload['user_id'])
            user = users_collection.find_one({'_id': user_id})

            recipient_id = request.form["recipient_id"]
            content = request.form["content"]
            author = user['nickname']
            theme = request.form["theme"]

            file = request.files['file']
            file_url = None
            if file and allowed_file(file.filename):
                filename = f"{uuid.uuid4().hex}.{file.filename.rsplit('.', 1)[1].lower()}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                file_url = f"uploads/{filename}"

            messages_collection.insert_one({
                "content": content,
                "recipient_id": recipient_id,
                'author': author,
                'file_url': file_url,
                "theme": theme
            })

            return redirect(url_for('paper', user_id=recipient_id))
        except jwt.ExpiredSignatureError:
            return 'Token has expired', 401 # 토큰 만료 처리
        except jwt.InvalidTokenError:
            return 'Invalid Token', 401 #유효성 만료
    return redirect(url_for('login'))

@app.route("/xy_update", methods=["POST"])
def update_data():
    token = request.cookies.get('token')
    if token:
        try:
            data = request.json  # JSON 형태로 요청 데이터를 받음
            id = data.get("id")  # JSON에서 ID 값 추출
            new_x = data.get("newX")  # JSON에서 X 좌표 값 추출
            new_y = data.get("newY")  # JSON에서 Y 좌표 값 추출
            recipient_id = data.get("recipient")
            
            # MongoDB에서 documents의 'messages' 컬렉션을 선택
            collection = messages_collection
            
            # 'id'가 주어진 item_id와 일치하는 문서를 찾고, 'newx'와 'newy' 필드를 업데이트
            collection.update_one(
                {"_id": ObjectId(id)}, {"$set": {"newx": new_x, "newy": new_y}}
            )
            
            return redirect(url_for('paper', user_id=recipient_id))
        except jwt.ExpiredSignatureError:
            return 'Token has expired', 401 # 토큰 만료 처리
        except jwt.InvalidTokenError:
            return 'Invalid Token', 401 #유효성 만료
    return redirect(url_for('login'))

@app.route('/my_messages')
def my_messages():
    token = request.cookies.get('token')
    if token:
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            user_id = ObjectId(payload['user_id'])
            user = users_collection.find_one({'_id': user_id})
            # 현재 사용자의 닉네임을 가져옵니다.
            nickname = user['nickname']

            # 현재 사용자가 작성한 모든 쪽지를 가져옵니다.
            messages = list(messages_collection.find({'author': nickname}))

            

            # 가져온 쪽지의 recipient_id 리스트를 만듭니다.
            recipient_ids = [message['recipient_id'] for message in messages]
            print(recipient_ids)

            recipient_ids = [ObjectId(id_str) for id_str in recipient_ids]

            # 해당 쪽지를 받은 유저의 이름을 가져옵니다. (recipient_id를 가진 유저 name을 조회)
            ToUsers = users_collection.find({'_id': {'$in': recipient_ids}}, {'_id': 1, 'name': 1})
            ToUsers_dict = {str(user['_id']): user.get('name', 'No Name') for user in ToUsers}

            # 메시지와 수신자의 이름을 결합합니다.
            final_result = []
            for message in messages:
                recipient_id = str(message['recipient_id'])
                ToName = ToUsers_dict.get(recipient_id, "Name not found")
                final_result.append({
                    '_id' : message['_id'],
                    'content': message['content'],
                    'file_url': message.get('file_url'),
                    'author': message['author'],
                    'theme' : message['theme'],
                    'ToName': ToName
                })
            
            return render_template('my_messages.html', messages=final_result)
        except jwt.ExpiredSignatureError:
            return 'Token has expired', 401 # 토큰 만료 처리
        except jwt.InvalidTokenError:
            return 'Invalid Token', 401 #유효성 만료
    return redirect(url_for('login'))

@app.route('/delete_message/<message_id>/<recipient_id>', methods=['POST'])
def delete_message(message_id, recipient_id):
    token = request.cookies.get('token')
    if token:
        try:       
            message = messages_collection.find_one({'_id': ObjectId(message_id)})
            if not message:
                jsonify({'message': '메모를 찾을 수 없습니다.'}), 401
            recipient = recipient_id

                # 파일 경로가 존재하면 파일을 삭제합니다.
            file_url = message.get('file_url')
            if file_url:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(file_url))
                if os.path.exists(file_path):
                    os.remove(file_path)
                
            # 메모를 삭제합니다.
            messages_collection.delete_one({'_id': ObjectId(message_id)})
            return redirect(url_for('paper', user_id=recipient))
        except jwt.ExpiredSignatureError:
            return 'Token has expired', 401 # 토큰 만료 처리
        except jwt.InvalidTokenError:
            return 'Invalid Token', 401 #유효성 만료
    return redirect(url_for('login'))

@app.route('/delete_my_message/<message_id>', methods=['POST'])
def delete_my_message(message_id):
    token = request.cookies.get('token')
    if token:
        try:       
            message = messages_collection.find_one({'_id': ObjectId(message_id)})
            if not message:
                jsonify({'message': '메모를 찾을 수 없습니다.'}), 401

                # 파일 경로가 존재하면 파일을 삭제합니다.
            file_url = message.get('file_url')
            if file_url:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(file_url))
                if os.path.exists(file_path):
                    os.remove(file_path)
                
            # 메모를 삭제합니다.
            messages_collection.delete_one({'_id': ObjectId(message_id)})
            return redirect(url_for('my_messages'))
        except jwt.ExpiredSignatureError:
            return 'Token has expired', 401 # 토큰 만료 처리
        except jwt.InvalidTokenError:
            return 'Invalid Token', 401 #유효성 만료
    return redirect(url_for('login'))
    




@app.route('/logout')
def logout():
    # 'token' 쿠키를 빈 값으로 설정하고 max_age를 0으로 설정하여 삭제합니다.
    response = redirect(url_for('login'))
    response.set_cookie('token', '', httponly=True, max_age=0)
    return response

if __name__ == '__main__':
    app.run(debug=True)
