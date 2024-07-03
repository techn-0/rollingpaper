from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_bcrypt import Bcrypt
from pymongo import MongoClient
from bson.objectid import ObjectId
import os
from flask import url_for
import uuid
from flask import send_from_directory

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 세션 데이터 암호화에 사용되는 비밀 키 설정
bcrypt = Bcrypt(app)  # 비밀번호 암호화를 위한 Bcrypt 설정

# MongoDB 클라이언트 설정
client = MongoClient('localhost', 27017)
db = client['rollingpaper']  # 사용할 데이터베이스 이름 설정
users_collection = db['users']  # 사용자 컬렉션 설정
messages_collection = db['messages']  # 메시지 컬렉션 설정

# 파일 업로드 설정
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'mp3', 'wav', 'mp4'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
        session['nickname'] = user['nickname']  # 닉네임을 세션에 저장
        return redirect(url_for('users'))  # 유저 목록 페이지로 리다이렉트
    error = '잘못된 유저네임 또는 비밀번호 입니다.'
    return render_template('login.html', error=error)

@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    password = request.form['password']
    name = request.form['name']
    nickname = request.form['nickname']

    existing_user = users_collection.find_one({'username': username})
    if existing_user:
        error = '이미 존재하는 아이디입니다.'
        return render_template('login.html', error=error)

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    profile_pic = request.files['profile_pic']  # 업로드된 프로필 사진 파일 가져오기
    profile_pic_filename = None

    if profile_pic and allowed_file(profile_pic.filename):
        filename = f"{uuid.uuid4().hex}.{profile_pic.filename.rsplit('.', 1)[1].lower()}"
        profile_pic_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        profile_pic.save(profile_pic_path)
        profile_pic_filename = f"uploads/{filename}"

    users_collection.insert_one({
        'username': username,
        'password': hashed_password,
        'name': name,
        'nickname': nickname,
        'profile_picture': profile_pic_filename  # 프로필 사진 경로 저장
    })

    success = '회원가입이 완료되었습니다.'
    return render_template('login.html', success=success)

@app.route('/users')
def users():
    if 'username' not in session:  # 사용자가 로그인되어 있지 않으면
        return redirect(url_for('index'))  # 로그인 페이지로 리다이렉트
    

    users = users_collection.find().sort('name', 1)  # 1은 오름차 -1은 내림차 DB에서 모든 사용자 가져오기
    return render_template('users.html', users=users)  # 유저 목록 페이지 렌더링

@app.route('/logout')
def logout():
    session.pop('username', None)  # 세션에서 사용자 이름 제거
    return redirect(url_for('index'))  # 로그인 페이지로 리다이렉트

@app.route('/paper/<user_id>')
def paper(user_id):
    if 'username' not in session:  # 사용자가 로그인되어 있지 않으면
        return redirect(url_for('index'))  # 로그인 페이지로 리다이렉트

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

    return render_template('paper.html', messages=messages_with_file_url, recipient=recipient)


@app.route('/message', methods=['POST'])
def message():
    if 'username' not in session:
        return redirect(url_for('index'))

    recipient_id = request.form['recipient_id']
    content = request.form['content']
    author = session['nickname']  # 사용자 닉네임을 작성자로 설정

    file = request.files['file']
    file_url = None
    if file and allowed_file(file.filename):
        filename = f"{uuid.uuid4().hex}.{file.filename.rsplit('.', 1)[1].lower()}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        # Use '/' instead of os.path.join for URL paths
        file_url = f"uploads/{filename}"

    messages_collection.insert_one({
        'content': content,
        'recipient_id': recipient_id,
        'author': author,
        'file_url': file_url
    })
    return redirect(url_for('paper', user_id=recipient_id))


@app.route('/delete_message/<message_id>', methods=['POST'])
def delete_message(message_id):
    if 'username' not in session:  # 사용자가 로그인되어 있지 않으면
        return redirect(url_for('index'))  # 로그인 페이지로 리다이렉트
    
    message = messages_collection.find_one({'_id': ObjectId(message_id)})
    if not message:
        flash('메모를 찾을 수 없습니다.')
        return redirect(url_for('paper', user_id=message['recipient_id']))

    # 파일 경로가 존재하면 파일을 삭제합니다.
    file_url = message.get('file_url')
    if file_url:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(file_url))
        if os.path.exists(file_path):
            os.remove(file_path)
    
    # 메모를 삭제합니다.
    messages_collection.delete_one({'_id': ObjectId(message_id)})
    
    return redirect(url_for('paper', user_id=message['recipient_id']))

@app.route('/my_messages')
def my_messages():
    if 'username' not in session:
        return redirect(url_for('index'))

    # 현재 사용자의 닉네임을 가져옵니다.
    nickname = session['nickname']

    # 현재 사용자가 작성한 모든 쪽지를 가져옵니다.
    messages = messages_collection.find({'author': nickname})

    return render_template('my_messages.html', messages=messages)



#프로필 수정
@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'username' not in session:  # 사용자가 로그인되어 있지 않으면
        return redirect(url_for('index'))  # 로그인 페이지로 리다이렉트

    username = session['username']
    user = users_collection.find_one({'username': username})  # 세션에서 현재 사용자 가져오기

    if request.method == 'POST':
        name = request.form['name']
        nickname = request.form['nickname']
        profile_pic = request.files['profile_pic']
        profile_pic_filename = user['profile_picture']

        if profile_pic and allowed_file(profile_pic.filename):
            if profile_pic_filename:
                old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(profile_pic_filename))
                if os.path.exists(old_file_path):
                    os.remove(old_file_path)

            filename = f"{uuid.uuid4().hex}.{profile_pic.filename.rsplit('.', 1)[1].lower()}"
            profile_pic_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            profile_pic.save(profile_pic_path)
            profile_pic_filename = f"uploads/{filename}"

        update_fields = {
            'name': name,
            'nickname': nickname,
            'profile_picture': profile_pic_filename
        }

        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if current_password and new_password and confirm_password:
            if not bcrypt.check_password_hash(user['password'], current_password):
                flash('현재 비밀번호가 잘못되었습니다.')
                return render_template('edit_profile.html', user=user)
            if new_password != confirm_password:
                flash('새 비밀번호가 일치하지 않습니다.')
                return render_template('edit_profile.html', user=user)
            hashed_new_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
            update_fields['password'] = hashed_new_password

        users_collection.update_one(
            {'username': username},
            {'$set': update_fields}
        )

        session['nickname'] = nickname  # 세션에 닉네임 갱신
        flash('프로필이 성공적으로 변경되었습니다.')
        return redirect(url_for('edit_profile'))

    return render_template('edit_profile.html', user=user)



#회원탈퇴
@app.route('/delete_profile', methods=['POST'])
def delete_profile():
    if 'username' not in session:
        return redirect(url_for('index'))
    
    username = session['username']
    user = users_collection.find_one({'username': username})
    if user:
        # 사용자와 관련된 모든 데이터를 삭제
        users_collection.delete_one({'username': username})
        messages_collection.delete_many({'author': user['nickname']})
        messages_collection.delete_many({'recipient_id': str(user['_id'])})

        #프로필사진 파일 삭제
        profile_picture = user.get('profile_picture')
        if profile_picture:
            profile_pic_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(profile_picture))
            if os.path.exists(profile_pic_path):
                os.remove(profile_pic_path)
        
        # 세션 종료
        session.clear()
        
        flash('회원탈퇴가 완료되었습니다.')
        return redirect(url_for('index'))
    else:
        flash('회원 탈퇴 실패: 이미 처리된 사용자입니다.')
        return redirect(url_for('edit_profile'))



if __name__ == '__main__':
    app.run(debug=True)

    