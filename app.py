import time
import uuid
from datetime import date, datetime, timedelta, UTC
from flask_apscheduler import APScheduler
from flask_socketio import SocketIO, join_room
from psycopg2._psycopg import IntegrityError
from pytz import timezone
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, abort, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from werkzeug.utils import secure_filename
import os
from os import path
from flask_bcrypt import Bcrypt
from slugify import slugify
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://admin:WJeYgQNQlYx2Wnh7I2o6lstiVYEkCHtp@dpg-d0m9kgjuibrs7388lc3g-a.oregon-postgres.render.com/myblogdb_i028'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'trantienphuc'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    mobile = db.Column(db.String(100))
    avatar_url = db.Column(db.String(255))
    bio = db.Column(db.Text)
    joined_date = db.Column(db.Date, default=date.today)

    posts = db.relationship('Post', backref='user', lazy=True)
    comments = db.relationship('Comment', backref='user', lazy=True)
    messages = db.relationship('Message', back_populates='user', lazy='dynamic')
    notifications = db.relationship('Notification', back_populates='user', lazy='dynamic')
class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50))
    slug = db.Column(db.String(100), unique=True, nullable=False)

    posts = db.relationship('PostCategory', backref='category', lazy=True)

class Post(db.Model):
    __tablename__ = 'posts'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(255))
    slug = db.Column(db.String(255), unique=True, nullable=False)
    content = db.Column(db.Text)
    thumbnail_url = db.Column(db.String(255))
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    view_count = db.Column(db.Integer, default=0)
    status = db.Column(db.Enum('draft', 'published', 'archived', name='status_enum'), default='published')
    deleted_at = db.Column(db.DateTime, nullable=True)
    post_categories = db.relationship('PostCategory', backref='post', cascade="all, delete-orphan", lazy=True)
    comments = db.relationship('Comment', backref='post', cascade="all, delete-orphan", lazy='dynamic')
    tags = db.relationship('Tag', secondary='post_tags', back_populates='posts')
    notifications = db.relationship('Notification', back_populates='post')

class PostCategory(db.Model):
    __tablename__ = 'post_categories'

    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), primary_key=True)

class Comment(db.Model):
    __tablename__ = 'comments'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class Tag(db.Model):
    __tablename__ = 'tags'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    posts = db.relationship('Post', secondary='post_tags', back_populates='tags')

class PostTag(db.Model):
    __tablename__ = 'post_tags'

    post_id = db.Column(db.Integer, db.ForeignKey('posts.id' , ondelete='CASCADE'), primary_key=True)
    tag_id = db.Column(db.Integer, db.ForeignKey('tags.id' , ondelete='CASCADE'), primary_key=True)

class Message(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', back_populates='messages')

class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=True)

    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='notifications')
    post = db.relationship('Post', back_populates='notifications')

class KhamPha(db.Model):
    __tablename__ = 'khampha'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    filename = db.Column(db.String(255), nullable=False)  # Tên tệp video
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', backref='khamphas')

def create_default_categories():
    with app.app_context():
        if not Category.query.first():
            categories = [
                Category(name='Công nghệ', slug='cong-nghe'),
                Category(name='Đời sống', slug='doi-song'),
                Category(name='Thể thao', slug='the-thao'),
                Category(name='Du lịch', slug='du-lich'),
                Category(name='Ẩm thực', slug='am-thuc'),
                Category(name='Giải trí', slug='giai-tri'),
                Category(name='Lập trình', slug='lap-trinh'),
                Category(name='Văn hóa', slug='van-hoa'),
                Category(name='Âm nhạc', slug='am-nhac'),
            ]
            db.session.bulk_save_objects(categories)
            db.session.commit()
            print("✅ Danh mục mẫu đã được tạo.")

def deniUrl():
    if session.get('user') is not None:
        return redirect(url_for('hub'))

def protectedUrl():
    if session.get('user') is None:
        return redirect(url_for('login'))

@app.context_processor
def inject_categories():
    categories = Category.query.all()
    user_session = session.get('user')
    if not user_session:
        return dict(categories=categories, notifications=[])
    user_id = user_session['id']
    notifications = Notification.query.filter_by(user_id=user_id).order_by(Notification.created_at.desc()).limit(5).all()
    unread_count = Notification.query.filter_by(user_id=user_id, is_read=False).count()
    return dict(categories=categories ,notifications = notifications , unread_count = unread_count)

@app.route('/' , methods=['GET'])
def index():
    return render_template("hub.html")
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        check = deniUrl()
        if check:
            return check
        return render_template("login.html")

    # POST
    email = request.form.get('email')
    password = request.form.get('password')

    if not email or not password:
        return render_template("login.html", message="Vui lòng nhập email và mật khẩu")

    user = User.query.filter_by(email=email).first()
    if user and bcrypt.check_password_hash(user.password, password):
        session['user'] = {
            'id': user.id,
            'username': user.name,
            'image_url': user.avatar_url,
        }
        return redirect(url_for("hub"))

    return render_template("login.html", message="Sai email hoặc mật khẩu")
@app.route('/register', methods=['GET', 'POST'])
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        check = deniUrl()
        if check:
            return check
        return render_template("register.html")

    name = request.form.get('name')
    email = request.form.get('email')
    mobile = request.form.get('mobile')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    image = "images/avt.jpg"

    if not name or not email or not mobile or not password or not confirm_password:
        return render_template("register.html", message="Vui lòng điền đầy đủ thông tin")

    if password != confirm_password:
        return render_template("register.html", message="Mật khẩu không khớp")

    if User.query.filter_by(email=email).first():
        return render_template("register.html", message="Email đã được sử dụng")

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    user = User(name=name, email=email, password=hashed_password, mobile=mobile, avatar_url=image)

    try:
        db.session.add(user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return render_template("register.html", message="Email đã tồn tại")

    return redirect(url_for('login'))
@app.route('/tim-kiem')
def tim_kiem():
    keyword = request.args.get('keyword', '').strip()
    ketqua = []
    if keyword:
        ketqua = Post.query.filter(
            Post.status == 'published',
            or_(
                Post.title.ilike(f'%{keyword}%'),
                Post.content.ilike(f'%{keyword}%')
            )
        ).all()

    return render_template('timkiem.html', keyword=keyword, ketqua=ketqua)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for("login"))

@app.route('/trangchu')
def hub():
    check = protectedUrl()
    if check:
        return check
    from sqlalchemy import and_

    posts = Post.query.filter(
        and_(
            Post.status == 'published',
            Post.deleted_at == None
        )
    ).order_by(Post.created_at.desc()).all()
    postsView = Post.query.filter(
        and_(
            Post.status == 'published',
            Post.deleted_at == None
        )
    ).order_by(Post.view_count.desc()).limit(3).all()
    return render_template("index.html" , posts=posts , postsView=postsView)

@app.route('/danhmuc/<string:slug>')
def category(slug):
    category = Category.query.filter_by(slug=slug).first_or_404()
    posts = [pc.post for pc in category.posts if pc.post.deleted_at is None]

    return render_template("category.html" , posts=posts , category=category , slug=slug)

@app.route('/baiviet/<string:slug>')
def post(slug):
    baiviet = Post.query.filter(Post.slug == slug, Post.deleted_at == None).first_or_404()
    tags = baiviet.tags
    comments = baiviet.comments.order_by(Comment.created_at.desc()).all()
    current_category_ids = [pc.category_id for pc in baiviet.post_categories]
    related_posts = Post.query.join(PostCategory).filter(
        PostCategory.category_id.in_(current_category_ids),
        Post.id != baiviet.id,
        Post.status == 'published'
    ).distinct().limit(5).all()

    vietnam_tz = timezone('Asia/Ho_Chi_Minh')
    created_at_vn = baiviet.created_at.astimezone(vietnam_tz)

    viewed_posts = session.get('viewed_posts', [])
    if baiviet.id not in viewed_posts:
        baiviet.view_count += 1
        db.session.commit()
        viewed_posts.append(baiviet.id)
        session['viewed_posts'] = viewed_posts

    return render_template("detail.html",
                           baiviet=baiviet,
                           created_at_vn=created_at_vn,
                           related_posts=related_posts,
                           comments=comments , tags=tags,request=request)

@app.route('/taobaiviet', methods=['GET', 'POST'])
def createPost():
    if request.method == 'GET':
        check = protectedUrl()
        if check:
            return check
        categories = Category.query.all()
        return render_template("create.html", categories=categories)

    if request.method == 'POST':
        user_id = session.get('user')['id']
        title = request.form.get('title')
        slug = slugify(title)
        content = request.form.get('content')
        category_ids = request.form.getlist('category_ids')
        status = request.form.get('status')
        description = request.form.get('description')
        tags = request.form.get('tags')
        tag_list = [tag.strip().lower() for tag in tags.split(',')] if tags else []
        imageUrl = None
        if 'image' in request.files:
            image = request.files['image']
            if image.filename != '':
                filename = secure_filename(image.filename)
                filepath = os.path.join('static/uploads', filename)
                image.save(filepath)
                imageUrl = 'uploads/' + filename
        post = Post(
            user_id=user_id,
            title=title,
            slug=slug,
            content=content,
            thumbnail_url=imageUrl,
            description = description,
            status=status
        )

        db.session.add(post)
        db.session.commit()

        for cat_id in category_ids:
            db.session.add(PostCategory(post_id=post.id, category_id=int(cat_id)))

        for tag_name in tag_list:
            existing_tag = Tag.query.filter_by(name=tag_name).first()
            if not existing_tag:
                existing_tag = Tag(name=tag_name)
                db.session.add(existing_tag)
                db.session.flush()

            db.session.add(PostTag(post_id=post.id, tag_id=existing_tag.id))

        db.session.commit()
        return redirect('/blogger/' + str(user_id))
@app.route("/baiviet/edit/<string:slug>", methods=['GET', 'POST'])
def editPost(slug):
    post = Post.query.filter_by(slug=slug).first_or_404()
    if session.get('user') is None or session['user']['id'] != post.user_id:
        abort(403)
    if request.method == 'GET':
        selected_category_ids = [pc.category_id for pc in post.post_categories]
        tag_string = ", ".join([tag.name for tag in post.tags])
        categories = Category.query.all()
        return render_template("baivietedit.html", post=post,
                               selected_category_ids=selected_category_ids,
                               tag_string=tag_string,
                               categories=categories)

    # POST
    title = request.form.get('title')
    post.title = title
    post.slug = slugify(title)
    post.content = request.form.get('content')
    post.status = request.form.get('status')
    post.description = request.form.get('description')

    # Cập nhật categories
    category_ids = request.form.getlist('category_ids')
    post.post_categories.clear()
    for cid in category_ids:
        post.post_categories.append(PostCategory(category_id=int(cid)))

    # Cập nhật tags
    tags = request.form.get('tags', '')
    tag_list = [t.strip().lower() for t in tags.split(',') if t.strip()]
    post.tags.clear()
    for tag_name in tag_list:
        tag = Tag.query.filter_by(name=tag_name).first()
        if not tag:
            tag = Tag(name=tag_name)
            db.session.add(tag)
        post.tags.append(tag)

    # Cập nhật ảnh nếu có
    image = request.files.get('image')
    print(image)
    if image and image.filename != '':
        filename = f"{int(time.time())}_{secure_filename(image.filename)}"
        filepath = os.path.join('static/uploads', filename)
        image.save(filepath)
        post.thumbnail_url = 'uploads/' + filename

    print("New image_url:", post.thumbnail_url)
    db.session.commit()
    return redirect(url_for('post', slug=post.slug))

@app.route('/blogger/<string:id>')
def blogger(id):
    check = protectedUrl()
    if check:
        return check

    user = User.query.filter_by(id=id).first_or_404()
    post_count = len(user.posts)
    active_posts = [post for post in user.posts if post.deleted_at is None]
    total_views = sum(post.view_count for post in user.posts)
    return render_template("profile.html", user=user,
                           post_count=post_count, total_views=total_views , active_posts=active_posts)

@app.route('/blogger/edit/<string:id>', methods=['POST'])
def edit_blogger(id):
    user = User.query.filter_by(id=id).first()
    if not user:
        return "User not found", 404
    user.name = request.form['name']
    user.bio = request.form['bio']
    user.email = request.form['email']

    if 'avatar' in request.files:
        avatar = request.files['avatar']
        if avatar.filename != '':
            filename = secure_filename(avatar.filename)
            filepath = os.path.join('static/uploads', filename)
            avatar.save(filepath)
            user.avatar_url = 'uploads/' + filename

    db.session.commit()
    return redirect(url_for('blogger', id=id))

@socketio.on('join')
def handle_join(user_id):
    join_room(str(user_id))
    print(f"User {user_id} joined room.")

@app.route('/addComment', methods=['POST'])
def addComment():
    data = request.get_json()
    comment_text = data.get('comment')
    post_id = data.get('post_id')

    user_id = session.get('user')['id']
    user = User.query.filter_by(id=user_id).first_or_404()
    post = Post.query.filter_by(id=post_id).first_or_404()
    post_owner = post.user

    new_comment = Comment(
        content=comment_text,
        post_id=post_id,
        user_id=user_id,
    )

    if user.id != post_owner.id:
        notification_content = f"{user.name} vừa bình luận vào bài viết của bạn: {comment_text}"
        notification = Notification(user_id=post_owner.id, content=notification_content , post_id=post_id)
        db.session.add(notification)
        db.session.commit()


    db.session.add(new_comment)
    db.session.add(notification)
    db.session.commit()

    # Emit đến user đang sở hữu bài viết
    socketio.emit('new_notification', {
        'content': notification_content,
        'from': user.name,
        'timestamp': new_comment.created_at.strftime('%d/%m/%Y %H:%M'),
        'post_url': f'/baiviet/{post.slug}'
    }, to=str(post_owner.id))

    return jsonify({
        'comment': new_comment.content,
        'user_name': user.name,
        'avatar': user.avatar_url,
        'created_at': new_comment.created_at.strftime('%d/%m/%Y %H:%M')
    }), 200

@app.route('/notifications/mark-as-read', methods=['POST'])
def mark_notification_as_read():
    data = request.get_json()
    noti_id = data.get('id')
    if noti_id:
        noti = Notification.query.get(noti_id)
        if noti:
            noti.is_read = True
            db.session.commit()
            return jsonify({'status': 'success'})
    return jsonify({'status': 'failed'}), 400
@app.route('/deletepost', methods=['POST'])
def deletePost():
    data = request.get_json()
    post_id = data.get('post_id')
    post = Post.query.get(post_id)
    if not post_id:
        return jsonify({'error': 'post_id is required'}), 400
    if not post:
        return jsonify({'error': 'Post not found'}), 404
    if session.get('user') is None or session['user']['id'] != post.user_id:
        abort(403)
    post.deleted_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': f'Post {post_id} deleted (soft delete)'}), 200
def hard_delete_old_posts():
    threshold_date = datetime.utcnow() - timedelta(days=15)
    old_posts = Post.query.filter(
        Post.deleted_at != None,
        Post.deleted_at < threshold_date
    ).all()

    for post in old_posts:
        db.session.delete(post)
    db.session.commit()
@app.route("/kholuutru")
def kholuutru():
    posts = Post.query.filter(Post.deleted_at.isnot(None)).all()
    now = datetime.utcnow()

    for post in posts:
        if post.deleted_at is not None:
            expiration_time = post.deleted_at + timedelta(days=15)
            remaining = expiration_time - now
            post.remaining_seconds = max(int(remaining.total_seconds()), 0)
        else:
            post.remaining_seconds = 0
    return render_template("store.html", posts=posts)

@app.route('/restore_post', methods=['POST'])
def restore_post():
    data = request.get_json()
    post_id = data.get('post_id')
    post = Post.query.get_or_404(post_id)

    if post.deleted_at is None:
        return jsonify({'message': 'Bài viết chưa bị xóa.'}), 400

    post.deleted_at = None
    db.session.commit()
    return jsonify({'message': 'Khôi phục bài viết thành công.'})
@app.route('/delete_permanently', methods=['POST'])
def delete_permanently():
    data = request.get_json()
    post_id = data.get('post_id')
    post = Post.query.get_or_404(post_id)

    db.session.delete(post)
    db.session.commit()
    return jsonify({'message': 'Đã xóa bài viết khỏi hệ thống.'})

@socketio.on('sendMessage')
@app.route('/sendMessage', methods=['POST'])
def send_message():
    data = request.get_json()
    content = data.get('data')
    user = session.get('user')
    username = user.get('username') if user else 'Unknown'
    image = user.get('image_url') if user else 'Unknown'
    message = Message(content=content, user_id=user['id'])
    db.session.add(message)
    db.session.commit()

    msg_data = {
        'user_name': username,
        "image" :image,
        'content': content,
        'timestamp': message.timestamp.strftime('%Y-%m-%d %H:%M:%S')
    }
    socketio.emit('new_message', msg_data)
    return jsonify(msg_data)
@app.route('/messages', methods=['GET'])
def get_messages():
    messages = Message.query.order_by(Message.timestamp.asc()).all()
    result = []
    for msg in messages:
        print(msg.user.id , msg.user.name)
        result.append({
            'user_name' : msg.user.name,
            'id' : msg.user.id,
            'content': msg.content,
            "image" : msg.user.avatar_url,
            'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        })
    return jsonify(result)

@app.route("/taokhampha", methods=['GET', 'POST'])
def taokhampha():
    if request.method == "GET":
        check = protectedUrl()
        if check:
            return check
        return render_template("khamphacreate.html")
    # POST
    title = request.form.get('title')
    content = request.form.get('content')
    video = request.files.get('video')

    if not title or not video:
        flash("Vui lòng điền tiêu đề và tải lên video.", "error")
        return render_template("khamphacreate.html")

    videoName = secure_filename(video.filename)
    filepath = os.path.join('static/uploads', videoName)
    videoUrl = 'uploads/' + videoName
    video.save(filepath)

    new_khampha = KhamPha(
        title=title,
        description=content,
        filename=videoUrl,
        user_id= session['user']['id'],
    )

    db.session.add(new_khampha)
    db.session.commit()

    flash("Tạo khám phá thành công!", "success")
    return redirect(url_for('taokhampha'))

@app.route("/kham-pha", methods=['GET'])
def khampha_list():
    # Lấy tất cả khám phá trong db
    khampha_all = KhamPha.query.order_by(KhamPha.created_at.desc()).all()
    return render_template("khampha_list.html", khamphas=khampha_all)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('PageNotFound.html'), 404
@app.errorhandler(403)
def forbidden_error(error):
    return render_template("forbidden.html"), 403

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("Database Created")
        
    scheduler.add_job(id='Cleanup posts', func=hard_delete_old_posts, trigger='interval', days=1)
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, debug=True, host='0.0.0.0', port=port)
