import hashlib
import io
import math
import random
import smtplib
import sqlite3
from email.mime.text import MIMEText

import requests
from flask import Flask, render_template, send_file, request, jsonify, session, redirect, flash, url_for
import os

from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
GAMES_DIR = r"D:\BaiduNetdiskDownload\7723Games"
GAMES_PER_PAGE = 18

# 邮箱配置
SMTP_SERVER = "smtp.163.com"
SMTP_USERNAME = "XXXXXX@163.com"
SMTP_PASSWORD = "XXXXXXXXX"

app.secret_key = 'wapsisfuckinggame'  # 设置一个秘密密钥用于会话

import hashlib

def get_game_id(game_name):
    return hashlib.md5(game_name.encode('utf-8')).hexdigest()

# 数据库初始化函数
def init_db():
    conn = sqlite3.connect('wap_games.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL,
                  email TEXT UNIQUE NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS verification_codes
                 (email TEXT PRIMARY KEY,
                  code TEXT NOT NULL,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS comments
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  category TEXT,
                  game TEXT,
                  user_id INTEGER,
                  content TEXT,
                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (id))''')
    conn.commit()
    conn.close()

# 确保在应用启动时调用这个函数
init_db()

def send_verification_email(email, code):
    sender = SMTP_USERNAME
    receiver = email
    message = MIMEText(f'Your verification code is: {code}')
    message['Subject'] = '[NoReply] Email Verification'
    message['From'] = sender
    message['To'] = receiver
    print(" ---------------------- send_verification_email ----------------------")
    with smtplib.SMTP(SMTP_SERVER) as server:
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(sender, [receiver], message.as_string())
        server.quit()


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('wap_games.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['logged_in'] = True  # 添加这行
            session['username'] = username  # 可选：如果你想在其他地方使用用户名
            flash('登录成功！', 'success')
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='用户名或密码错误')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        conn = sqlite3.connect('wap_games.db')
        c = conn.cursor()

        # 检查用户名是否已存在
        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        if c.fetchone():
            conn.close()
            return render_template('register.html', error='用户名已存在')

        # 检查邮箱是否已存在
        c.execute("SELECT * FROM users WHERE email = ?", (email,))
        if c.fetchone():
            conn.close()
            return render_template('register.html', error='邮箱已被使用')

        # 创建新用户
        hashed_password = generate_password_hash(password)
        c.execute("INSERT INTO users (username, password, email) VALUES (?, ?, ?)",
                  (username, hashed_password, email))
        conn.commit()
        conn.close()

        flash('注册成功，请登录', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.clear()
    flash('您已成功登出', 'success')
    return redirect(url_for('index'))


@app.route('/send_verification_code', methods=['POST'])
def send_verification_code():
    data = request.get_json()
    if not data or 'email' not in data:
        return jsonify({"success": False, "error": "No email provided"}), 400

    email = data['email']
    verification_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])

    conn = sqlite3.connect('wap_games.db')
    c = conn.cursor()
    c.execute("REPLACE INTO verification_codes (email, code) VALUES (?, ?)", (email, verification_code))
    conn.commit()
    conn.close()

    try:
        send_verification_email(email, verification_code)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

def get_thumbnail_path(game_path):
    for file in os.listdir(game_path):
        if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
            return os.path.join(game_path, file)
    return None


@app.route('/')
def index():
    categories = [d for d in os.listdir(GAMES_DIR) if os.path.isdir(os.path.join(GAMES_DIR, d))]
    games = []
    search_query = request.args.get('search', '').lower()
    category_filter = request.args.get('category', '')
    page = int(request.args.get('page', 1))

    for category in categories:
        if category_filter and category != category_filter:
            continue
        category_path = os.path.join(GAMES_DIR, category)
        for game in os.listdir(category_path):
            if search_query in game.lower():
                game_path = os.path.join(category_path, game)
                thumbnail = get_thumbnail_path(game_path)
                games.append({
                    'name': game,
                    'category': category,
                    'thumbnail': os.path.relpath(thumbnail, GAMES_DIR) if thumbnail else None
                })

    total_games = len(games)
    total_pages = math.ceil(total_games / GAMES_PER_PAGE)
    start_index = (page - 1) * GAMES_PER_PAGE
    end_index = start_index + GAMES_PER_PAGE
    games_to_display = games[start_index:end_index]

    return render_template('index.html', categories=categories, games=games_to_display,
                           page=page, total_pages=total_pages, search_query=search_query,
                           category_filter=category_filter)

@app.route('/serve_default_image')
def serve_default_image():
    # 这里使用新的 API 获取默认图片
    response = requests.get('http://192.168.31.44:8080/i/2024/08/27/wb06v8-0.jpg')
    if response.status_code == 200:
        return send_file(
            io.BytesIO(response.content),
            mimetype='image/jpeg'  # 或其他适当的 MIME 类型
        )
    else:
        # 如果 API 请求失败，可以返回一个静态的默认图片
        return send_file('static/ad/img.png', mimetype='image/jpeg')
@app.route('/game/<category>/<game>')
def game(category, game):
    # 获取游戏评论
    # 获取游戏的 ID（MD5 哈希）
    game_id = get_game_id(game)

    # 获取游戏评论
    conn = sqlite3.connect('wap_games.db')
    c = conn.cursor()
    c.execute("""SELECT users.username, comments.content, comments.created_at 
                 FROM comments 
                 JOIN users ON comments.user_id = users.id 
                 WHERE comments.game_id = ? 
                 ORDER BY comments.created_at DESC""", (game_id,))
    comments = [dict(username=row[0], content=row[1], created_at=row[2]) for row in c.fetchall()]
    conn.close()

    game_path = os.path.join(GAMES_DIR, category, game)
    files = os.listdir(game_path)
    images = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
    other_files = [f for f in files if not f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.txt', '.html', '.cfg'))]
    return render_template('game.html', comments=comments, category=category, game=game, images=images, other_files=other_files)


@app.route('/game/<category>/<game>/comment', methods=['POST'])
def add_comment(category, game):
    if not session.get('logged_in'):
        flash('请先登录后再发表评论。', 'error')
        return redirect(url_for('game', category=category, game=game))

    content = request.form.get('content')
    if not content:
        flash('评论内容不能为空。', 'error')
        return redirect(url_for('game', category=category, game=game))
    game_id = get_game_id(game)
    conn = sqlite3.connect('wap_games.db')
    c = conn.cursor()
    c.execute("INSERT INTO comments (game_id, user_id, content) VALUES (?, ?, ?)",
              (game_id, session['user_id'], content))
    conn.commit()
    conn.close()

    flash('评论发表成功！', 'success')
    return redirect(url_for('game', category=category, game=game))




@app.route('/download/<category>/<game>/<file>')
def download(category, game, file):
    file_path = os.path.join(GAMES_DIR, category, game, file)
    if file.lower().endswith(('.txt', '.html')):
        return "This file type is not available for download.", 403
    return send_file(file_path, as_attachment=True)


@app.route('/thumbnail/<path:thumbnail>')
def serve_thumbnail(thumbnail):
    return send_file(os.path.join(GAMES_DIR, thumbnail))


@app.route('/game_image/<category>/<game>/<image>')
def serve_game_image(category, game, image):
    image_path = os.path.join(GAMES_DIR, category, game, image)
    return send_file(image_path)


if __name__ == '__main__':
    app.run(debug=True,port=8888,host='0.0.0.0',threaded=True)