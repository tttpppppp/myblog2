import uuid
from datetime import date, datetime, timedelta, UTC
from flask_apscheduler import APScheduler
from flask_socketio import SocketIO
from pytz import timezone
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
from os import path
from flask_bcrypt import Bcrypt
from slugify import slugify
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://admin:WJeYgQNQlYx2Wnh7I2o6lstiVYEkCHtp@dpg-d0m9kgjuibrs7388lc3g-a/myblogdb_i028'
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


def deniUrl():
    if session.get('user') is not None:
        return redirect(url_for('hub'))

def protectedUrl():
    if session.get('user') is None:
        return redirect(url_for('login'))

@app.context_processor
def inject_categories():
    categories = Category.query.all()
    return dict(categories=categories)
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

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and  bcrypt.check_password_hash(user.password,password):
            session['user'] = {
                'id': user.id,
                'username': user.name,
                'image_url': user.avatar_url,
            }
            return redirect(url_for("hub"))
        else:
            return render_template("login.html", message="Sai email hoặc mật khẩu")
    return render_template("login.html", message="Unexpected error")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        check = deniUrl()
        if check:
            return check
        return render_template("register.html")
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        mobile = request.form.get('mobile')
        password = request.form.get('password')
        image = "images/avt.jpg"
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(name=name, email=email, password=hashed_password, mobile=mobile , avatar_url=image)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))

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
                           comments=comments , tags=tags)

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
    if image and image.filename != '':
        filename = secure_filename(image.filename)
        filepath = os.path.join('static/uploads', filename)
        image.save(filepath)
        post.image_url = 'uploads/' + filename

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

@app.route('/addComment', methods=['POST'])
def addComment():
    data = request.get_json()
    comment_text = data.get('comment')
    post_id = data.get('post_id')

    user_id = session.get('user')['id']
    user = User.query.filter_by(id=user_id).first_or_404()

    new_comment = Comment(
        content=comment_text,
        post_id=post_id,
        user_id=user_id,
    )

    db.session.add(new_comment)
    db.session.commit()

    return jsonify({
        'comment': new_comment.content,
        'user_name': user.name,
        'avatar': user.avatar_url,
        'created_at': new_comment.created_at.strftime('%d/%m/%Y %H:%M')
    }), 200

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
