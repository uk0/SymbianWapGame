import os
from flask import Flask, render_template_string, request, send_file, url_for, abort
from werkzeug.utils import secure_filename
from PIL import Image
import io
import base64
import hashlib
import string

app = Flask(__name__)

# 配置
ROOT_DIR = 'D:\\BaiduNetdiskDownload\\7723Games'  # 请替换为你的实际目录路径
ITEMS_PER_PAGE = 50
THUMBNAIL_SIZE = (320, 320)
THUMBNAIL_CACHE = {}


def get_file_info(path):
    name = os.path.basename(path)
    if os.path.isdir(path):
        thumbnail = next((f for f in os.listdir(path) if f.lower().endswith(('.png', '.jpg'))), None)
        return {'name': name, 'is_dir': True, 'thumbnail': thumbnail}
    else:
        ext = os.path.splitext(name)[1].lower()
        is_download = ext in ['.jar', '.sis', '.sisx','.zip']
        is_image = ext in ['.png', '.jpg', '.jpeg']
        size = os.path.getsize(path)
        return {'name': name, 'is_dir': False, 'is_download': is_download, 'is_image': is_image, 'size': size}


def create_thumbnail(image_path):
    key = hashlib.md5(image_path.encode()).hexdigest()
    if key in THUMBNAIL_CACHE:
        return THUMBNAIL_CACHE[key]

    try:
        with Image.open(image_path) as img:
            img.thumbnail(THUMBNAIL_SIZE)
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            thumbnail = base64.b64encode(buffered.getvalue()).decode()
            THUMBNAIL_CACHE[key] = thumbnail
            return thumbnail
    except Exception as e:
        print(f"Error creating thumbnail for {image_path}: {e}")
        return None


def get_all_subdirectories():
    all_dirs = []
    for letter in string.ascii_uppercase:
        letter_path = os.path.join(ROOT_DIR, letter)
        if os.path.isdir(letter_path):
            subdirs = [os.path.join(letter, d) for d in os.listdir(letter_path) if
                       os.path.isdir(os.path.join(letter_path, d))]
            all_dirs.extend(subdirs)
    return all_dirs


@app.route('/')
def home():
    alphabet_dirs = [dir for dir in os.listdir(ROOT_DIR) if dir in string.ascii_uppercase]

    # 获取所有子目录
    all_subdirs = get_all_subdirectories()

    search = request.args.get('search', '').lower()
    if search:
        all_subdirs = [d for d in all_subdirs if search in d.lower()]

    # 分页
    page = int(request.args.get('page', 1))
    total_pages = (len(all_subdirs) - 1) // ITEMS_PER_PAGE + 1
    start = (page - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    subdirs = all_subdirs[start:end]

    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>WAP Game Browser</title>
        <style>
            body { font-family: Arial, sans-serif; font-size: 14px; line-height: 1.4; padding: 10px; max-width: 600px; margin: 0 auto; }
            h1 { font-size: 18px; color: #333; }
            .alphabet { display: flex; flex-wrap: wrap; justify-content: center; margin-bottom: 10px; }
            .letter { margin: 2px; padding: 2px 5px; border: 1px solid #ddd; border-radius: 3px; text-decoration: none; color: #333; }
            .search { margin-bottom: 10px; }
            .search input[type="text"] { width: 70%; }
            .search input[type="submit"] { width: 25%; }
            ul { list-style-type: none; padding: 0; }
            li { margin-bottom: 5px; }
            .pagination { margin-top: 10px; text-align: center; }
            .pagination a { padding: 2px 5px; text-decoration: none; color: #333; }
        </style>
    </head>
    <body>
        <h1>WAP Game Browser</h1>
        <div class="alphabet">
        {% for dir in alphabet_dirs %}
            <a class="letter" href="{{ url_for('index', subpath=dir) }}">{{ dir }}</a>
        {% endfor %}
        </div>
        <div class="search">
            <form action="{{ url_for('home') }}" method="get">
                <input type="text" name="search" placeholder="Search games...">
                <input type="submit" value="Search">
            </form>
        </div>
        <h2>Games List</h2>
        <ul>
        {% for subdir in subdirs %}
            <li><a href="{{ url_for('index', subpath=subdir) }}">{{ subdir }}</a></li>
        {% endfor %}
        </ul>

        <div class="pagination">
            {% if page > 1 %}
                <a href="{{ url_for('home', page=page-1, search=request.args.get('search', '')) }}">Previous</a>
            {% endif %}

            <span>Page {{ page }} of {{ total_pages }}</span>

            {% if page < total_pages %}
                <a href="{{ url_for('home', page=page+1, search=request.args.get('search', '')) }}">Next</a>
            {% endif %}
        </div>
    </body>
    </html>
    ''', alphabet_dirs=alphabet_dirs, subdirs=subdirs, page=page, total_pages=total_pages)


@app.route('/<path:subpath>')
def index(subpath=''):
    try:
        full_path = os.path.join(ROOT_DIR, subpath)
        if not os.path.exists(full_path):
            abort(404)

        if os.path.isfile(full_path):
            return send_file(full_path)

        files = [get_file_info(os.path.join(full_path, f)) for f in os.listdir(full_path)]

        search = request.args.get('search', '').lower()
        if search:
            files = [f for f in files if search in f['name'].lower()]

        # 分页
        page = int(request.args.get('page', 1))
        total_pages = (len(files) - 1) // ITEMS_PER_PAGE + 1
        start = (page - 1) * ITEMS_PER_PAGE
        end = start + ITEMS_PER_PAGE
        files = files[start:end]

        # 为图片文件创建缩略图
        for file in files:
            if file.get('is_image'):
                img_path = os.path.join(full_path, file['name'])
                file['thumbnail'] = create_thumbnail(img_path)

        return render_template_string('''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>WAP Game Browser - {{ current_dir }}</title>
            <style>
                body { font-family: Arial, sans-serif; font-size: 14px; line-height: 1.4; padding: 10px; max-width: 600px; margin: 0 auto; }
                h1 { font-size: 18px; color: #333; }
                ul { list-style-type: none; padding: 0; }
                li { margin-bottom: 5px; }
                img { max-width: 120px; max-height: 120px; }
                .search { margin-bottom: 10px; }
                .search input[type="text"] { width: 70%; }
                .search input[type="submit"] { width: 25%; }
                .pagination { margin-top: 10px; text-align: center; }
                .pagination a { padding: 2px 5px; text-decoration: none; color: #333; }
                .file-size { color: #666; font-size: 0.8em; }
                .back-link { margin-bottom: 10px; }
            </style>
        </head>
        <body>
            <div class="back-link">
                <a href="{{ url_for('home') }}">Back to Home</a>
            </div>
            <h1>{{ current_dir }}</h1>
            <div class="search">
                <form action="{{ url_for('index', subpath=subpath) }}" method="get">
                    <input type="text" name="search" placeholder="Search files...">
                    <input type="submit" value="Search">
                </form>
            </div>
            <ul>
            {% for file in files %}
                <li>
                    {% if file.is_dir %}
                        <a href="{{ url_for('index', subpath=subpath+'/'+file.name) }}">
                        {% if file.thumbnail %}
                            [IMG] 
                        {% endif %}
                        {{ file.name }}/
                        </a>
                    {% elif file.is_download %}
                        <a href="{{ url_for('index', subpath=subpath+'/'+file.name) }}">Download {{ file.name }}</a>
                        <span class="file-size">({{ '{:.2f}'.format(file.size / 1024 / 1024) }} MB)</span>
                    {% elif file.is_image %}
                        <img src="data:image/png;base64,{{ file.thumbnail }}" alt="{{ file.name }}">
                        <br>{{ file.name }}
                        <span class="file-size">({{ '{:.2f}'.format(file.size / 1024 / 1024) }} MB)</span>
                    {% else %}
                        {{ file.name }}
                        <span class="file-size">({{ '{:.2f}'.format(file.size / 1024 / 1024) }} MB)</span>
                    {% endif %}
                </li>
            {% endfor %}
            </ul>

            <div class="pagination">
                {% if page > 1 %}
                    <a href="{{ url_for('index', subpath=subpath, page=page-1, search=request.args.get('search', '')) }}">Previous</a>
                {% endif %}

                <span>Page {{ page }} of {{ total_pages }}</span>

                {% if page < total_pages %}
                    <a href="{{ url_for('index', subpath=subpath, page=page+1, search=request.args.get('search', '')) }}">Next</a>
                {% endif %}
            </div>
        </body>
        </html>
        ''', files=files, subpath=subpath, current_dir=os.path.basename(full_path) or 'Root',
                                      page=page, total_pages=total_pages)
    except Exception as e:
        return f"An error occurred: {str(e)}", 500

if __name__ == '__main__':
    app.run(port=8888, debug=True,host='0.0.0.0',threaded=True)