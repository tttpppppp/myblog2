import time
import uuid
from datetime import date, datetime, timedelta, UTC
from functools import wraps
from zoneinfo import ZoneInfo

from flask_apscheduler import APScheduler
from flask_socketio import SocketIO, join_room
from psycopg2 import IntegrityError
from pytz import timezone
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, abort, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_, desc
from werkzeug.utils import secure_filename
import os
from flask_mail import Message as MailMessage , Mail
from flask_bcrypt import Bcrypt
from slugify import slugify
app = Flask(__name__)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = 'despacitovv@gmail.com'
app.config['MAIL_PASSWORD'] = 'gidk umyh klal pdwv'

app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False


app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://admin:WJeYgQNQlYx2Wnh7I2o6lstiVYEkCHtp@dpg-d0m9kgjuibrs7388lc3g-a.oregon-postgres.render.com/myblogdb_i028'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'trantienphuc'


mail = Mail(app)
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
    status = db.Column(db.String(50), default='inactive')
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))

    posts = db.relationship('Post', backref='user', lazy=True)
    comments = db.relationship('Comment', backref='user', lazy=True)
    messages = db.relationship('Message', back_populates='user',cascade='all, delete-orphan',passive_deletes=True
    )
    notifications = db.relationship('Notification', back_populates='user', lazy='dynamic')
    verifications = db.relationship("Verification", back_populates="user")
    khamphas = db.relationship('KhamPha', backref='user', cascade="all, delete", passive_deletes=True)
    role = db.relationship('Role', back_populates='users')
    histories = db.relationship('History', back_populates='user')

class Role(db.Model):
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), unique=True, nullable=False)  # ví dụ: 'admin', 'editor', 'user'
    description = db.Column(db.String(255))

    users = db.relationship('User', back_populates='role')

class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50))
    slug = db.Column(db.String(100), unique=True, nullable=False)
    status = db.Column(db.Boolean, default=True)  # Thêm cột status

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
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
    )

    view_count = db.Column(db.Integer, default=0)
    status = db.Column(db.Enum('draft', 'published', 'archived', name='status_enum'), default='published')
    deleted_at = db.Column(db.DateTime, nullable=True)
    post_categories = db.relationship('PostCategory', backref='post', cascade="all, delete-orphan", lazy=True)
    comments = db.relationship('Comment', backref='post', cascade="all, delete-orphan", lazy='dynamic')
    post_tags = db.relationship(
        'PostTag',
        back_populates='post',
        cascade="all, delete-orphan",
        lazy=True
    )
    notifications = db.relationship('Notification', back_populates='post')
    histories = db.relationship('History', back_populates='post')

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Tag(db.Model):
    __tablename__ = 'tags'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    post_tags = db.relationship(
        'PostTag',
        back_populates='tag',
        cascade="all, delete-orphan",
        lazy=True
    )

class PostTag(db.Model):
    __tablename__ = 'post_tags'

    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), primary_key=True)
    tag_id = db.Column(db.Integer, db.ForeignKey('tags.id'), primary_key=True)

    post = db.relationship('Post', back_populates='post_tags')
    tag = db.relationship('Tag', back_populates='post_tags')

class Message(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

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
    user_id = db.Column(db.String(36), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

class Verification(db.Model):
    __tablename__ = 'veri'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(100), nullable=False, unique=True)
    expiry = db.Column(db.DateTime, nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)

    user = db.relationship('User', back_populates='verifications')

class Visit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    count = db.Column(db.Integer, default=0)
    
class History(db.Model):
    __tablename__ = 'history'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id', ondelete='CASCADE'), nullable=True)
    viewed_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='histories')
    post = db.relationship('Post', back_populates='histories')

@app.before_request
def count_visit():
    if request.endpoint != 'static':  # Bỏ qua static file
        visit = Visit.query.first()
        if not visit:
            visit = Visit(count=1)
            db.session.add(visit)
        else:
            visit.count += 1
        db.session.commit()


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get('user')
        if not user or user.get('role') != 'ADMIN':
            return render_template("forbidden.html")
        return f(*args, **kwargs)
    return decorated_function


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

def sendMail(content, title, recipient):
    msg = MailMessage(
        subject=title,
        sender='despacitovv@gmail.com',
        recipients=[recipient]
    )
    msg.body = content

    try:
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Gửi mail thất bại: {e}")
        return False

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == "GET":
        code = request.args.get('code')
        return render_template("reset_password.html", code=code)

    # POST
    code = request.form.get('code')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')

    if password != confirm_password:
        flash("Mật khẩu không khớp")
        return redirect(url_for('reset_password', code=code))

    print("Code nhận được POST:", code)
    veri = Verification.query.filter_by(code=code).first()
    if veri is None:
        flash("Mã xác thực không hợp lệ")
        return redirect(url_for('reset_password', code=code))

    if veri.expiry < datetime.utcnow():
        flash("Mã xác thực đã hết hạn")
        return redirect(url_for('reset_password', code=code))

    user = User.query.get(veri.user_id)
    if user is None:
        flash("Người dùng không tồn tại")
        return redirect(url_for('reset_password', code=code))

    user.password = bcrypt.generate_password_hash(password).decode('utf-8')
    db.session.commit()
    db.session.delete(veri)
    db.session.commit()

    flash("Đặt lại mật khẩu thành công, bạn có thể đăng nhập lại.")
    return redirect(url_for('login'))

@app.route("/dashboard")
@admin_required
def dashboard():
    usersCount = User.query.count()
    postsCount = Post.query.count()
    visits = Visit.query.first().count
    return render_template("admin/dashboard.html", usersCount=usersCount, postsCount=postsCount , visits=visits )
@app.route("/users")
@admin_required
def manage_users():
    users = User.query.all()
    return render_template("admin/user.html" , users=users)

@app.route("/roles")
@admin_required
def manage_roles():
    roles = Role.query.all()
    return render_template("admin/role.html" , roles=roles)

@app.route("/categories")
@admin_required
def manage_categories():
    categories = Category.query.all()
    return render_template("admin/danhmuc.html" , categories=categories)
@app.route("/admin/user/delete/<string:user_id>")
@admin_required
def delete_user(user_id):
    user = User.query.get(user_id)
    if not user:
        flash("Người dùng không tồn tại", "danger")
    elif user.status == "banned":
        flash("Người dùng đã bị cấm trước đó", "warning")
    else:
        user.status = "banned"
        db.session.commit()
        flash("Đã cấm người dùng thành công", "success")

    return redirect(url_for('manage_users'))

@app.route("/admin/post/delete/<int:post_id>")
@admin_required
def delete_post(post_id):
    post = Post.query.get(post_id)
    if not post:
        flash("Bài viết không tồn tại", "danger")
        return redirect(url_for('posts'))

    db.session.delete(post)
    db.session.commit()
    flash("Đã xóa bài viết thành công", "success")
    return redirect(url_for('posts'))

@app.route('/admin/role/edit/<int:role_id>', methods=['GET', 'POST'])
def edit_role(role_id):
    role = Role.query.get_or_404(role_id)

    if request.method == 'POST':
        role.name = request.form['name']
        role.description = request.form['description']
        db.session.commit()
        flash('Cập nhật vai trò thành công!', 'success')
        return redirect(url_for('manage_roles'))

    return render_template('admin/editrole.html', role=role)

@app.route('/admin/role/delete/<int:role_id>', methods=['GET'])
def delete_role(role_id):
    role = Role.query.get_or_404(role_id)
    if role.users:
        flash('Không thể xoá vì có người dùng đang sử dụng vai trò này.', 'error')
        return redirect(url_for('manage_roles'))

    db.session.delete(role)
    db.session.commit()
    flash('Đã xoá vai trò thành công!', 'success')
    return redirect(url_for('manage_roles'))


@app.route('/admin/role/create', methods=['GET', 'POST'])
@admin_required
def create_role():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        existing_role = Role.query.filter_by(name=name).first()
        if existing_role:
            flash('Tên vai trò đã tồn tại.', 'error')
            return render_template('admin/form_role.html')


        new_role = Role(name=name, description=description)
        db.session.add(new_role)
        db.session.commit()
        flash('Thêm vai trò thành công!', 'success')
        return redirect(url_for('manage_roles'))

    return render_template('admin/form_role.html')

@app.route('/admin/category/create', methods=['GET', 'POST'])
@admin_required
def create_category():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        status = request.form.get('status')
        status = True if status == '1' else False

        if not name:
            flash('Tên danh mục không được để trống.', 'danger')
            return render_template('admin/form_category.html')

        slug = slugify(name)
        existing = Category.query.filter_by(slug=slug).first()
        if existing:
            flash('Slug đã tồn tại. Vui lòng chọn tên khác.', 'danger')
            return render_template('admin/form_category.html')

        new_category = Category(name=name, slug=slug, status=status)
        db.session.add(new_category)
        db.session.commit()

        flash('Danh mục đã được tạo thành công!', 'success')
        return redirect(url_for('manage_categories'))

    return render_template('admin/form_category.html')

@app.route('/admin/category/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_category(id):
    category = Category.query.get_or_404(id)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        status = request.form.get('status')

        if not name:
            flash('Tên danh mục không được để trống.', 'danger')
            return render_template('admin/editcategory.html', category=category)

        category.name = name
        category.slug = slugify(name)
        category.status = True if status == '1' else False

        db.session.commit()
        flash('Danh mục đã được cập nhật.', 'success')
        return redirect(url_for('manage_categories'))

    return render_template('admin/editcategory.html', category=category)


@app.route('/admin/category/delete/<int:id>', methods=['GET'])
@admin_required
def delete_category(id):
    category = Category.query.get_or_404(id)

    if not category.posts:
        db.session.delete(category)
        flash('Danh mục đã được xóa.', 'success')
    else:
        category.status = False
        flash('Danh mục có bài viết, đã chuyển sang trạng thái không hoạt động.', 'warning')

    db.session.commit()
    return redirect(url_for('manage_categories'))

@app.route("/posts")
def posts():
    posts = Post.query.order_by(desc(Post.created_at)).all()
    return render_template("admin/post.html", posts=posts)
@app.route('/' , methods=['GET'])
def index():
    return render_template("hub.html")
@app.route("/forgot-password", methods=['GET', 'POST'])
def forgot_password():
    if request.method == "GET":
        return render_template("quenmatkhau.html")
    email = request.form.get('email')
    if not email:
        return render_template("quenmatkhau.html", message="Vui lòng nhập email")

    user = User.query.filter_by(email=email).first()
    if not user:
        return render_template("quenmatkhau.html", message="Nếu email này tồn tại, chúng tôi sẽ gửi link đặt lại mật khẩu")

    code = str(uuid.uuid4())
    expiry_time = datetime.utcnow() + timedelta(minutes=15)

    veri = Verification(code=code, expiry=expiry_time , user_id=user.id)
    db.session.add(veri)
    db.session.commit()


    reset_link = url_for("reset_password", code=code, _external=True)

    subject = "MyBlog - Cập nhật lại mật khẩu"
    body = f"""
    Xin chào {user.name},

    Bạn hoặc ai đó đã yêu cầu đặt lại mật khẩu cho tài khoản MyBlog của bạn.
    Vui lòng nhấp vào liên kết bên dưới để đặt lại mật khẩu. Liên kết này chỉ có hiệu lực trong 15 phút.

    {reset_link}

    Nếu bạn không yêu cầu đặt lại mật khẩu, bạn có thể bỏ qua email này.

    Trân trọng,
    Ban quản trị MyBlog
    """

    is_success = sendMail(body , subject, user.email)
    if is_success:
        return render_template("quenmatkhau.html", message="Chúng tôi đã gửi liên kết xác thực đến email của bạn")
    else:
        return render_template("quenmatkhau.html", message="Gửi xác thực thất bại, vui lòng thử lại sau")

@app.route('/confirm', methods=['GET'])
def confirmRegister():
    code = request.args.get('code')
    veri = Verification.query.filter_by(code=code).first()

    if veri is None:
        message = "Mã xác thực không hợp lệ"
        return render_template("confirm_fail.html", message=message)

    if veri.expiry < datetime.utcnow():
        message = "Mã xác thực đã hết hạn"
        return render_template("confirm_fail.html", message=message)

    user = User.query.get(veri.user_id)
    if user is None:
        message = "Người dùng không tồn tại"
        return render_template("confirm_fail.html", message=message)

    user.status = "active"
    db.session.commit()
    flash("Xác thực thành công")
    return render_template("confirm_success.html")

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
    if not user:
        return render_template("login.html", message="Tài khoản không tồn tại!")
    if user.status == "inactive":
        return render_template("login.html", message="Vui lòng xác thực tài khoản")
    if user.status == "banned":
        return render_template("login.html", message="Tài khoản của bạn đã khóa vì vi phạm nguyên tắc cộng đồng!")
    if user and bcrypt.check_password_hash(user.password, password):
        session['user'] = {
            'id': user.id,
            'username': user.name,
            'image_url': user.avatar_url,
            'role' : user.role.name
        }
        return redirect(url_for("hub"))

    return render_template("login.html", message="Sai email hoặc mật khẩu")
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

    existing_user = User.query.filter_by(email=email).first()

    if existing_user:
        if existing_user.status == "inactive":
            code = str(uuid.uuid4())
            expiry_time = datetime.utcnow() + timedelta(minutes=15)

            veri = Verification(code=code, expiry=expiry_time, user_id=existing_user.id)
            db.session.add(veri)
            db.session.commit()

            reset_link = url_for("confirmRegister", code=code, _external=True)

            subject = "MyBlog - Xác thực lại tài khoản"
            body = f"""
            Xin chào {existing_user.name},

            Bạn đã đăng ký tài khoản nhưng chưa xác thực. Vui lòng nhấp vào liên kết bên dưới để xác thực tài khoản:

            {reset_link}

            Trân trọng,
            Ban quản trị MyBlog
            """
            is_success = sendMail(body, subject, existing_user.email)
            if is_success:
                return render_template("register.html", message="Chúng tôi đã gửi lại liên kết xác thực đến email của bạn")
            else:
                return render_template("register.html", message="Gửi xác thực thất bại, vui lòng thử lại sau")
        else:
            return render_template("register.html", message="Email đã được sử dụng")

    # Tạo mới user
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    user = User(
        name=name,
        email=email,
        password=hashed_password,
        mobile=mobile,
        avatar_url=image,
        role_id=2,
    )

    try:
        db.session.add(user)
        db.session.commit()

        code = str(uuid.uuid4())
        expiry_time = datetime.utcnow() + timedelta(minutes=15)

        veri = Verification(code=code, expiry=expiry_time, user_id=user.id)
        db.session.add(veri)
        db.session.commit()

        reset_link = url_for("confirmRegister", code=code, _external=True)

        subject = "MyBlog - Xác thực tài khoản"
        body = f"""
        Xin chào {user.name},

        Vui lòng nhấp vào liên kết bên dưới để xác thực tài khoản:

        {reset_link}

        Trân trọng,
        Ban quản trị MyBlog
        """

        is_success = sendMail(body, subject, user.email)
        if is_success:
            return render_template("register.html", message="Chúng tôi đã gửi liên kết xác thực đến email của bạn")
        else:
            return render_template("register.html", message="Gửi xác thực thất bại, vui lòng thử lại sau")

    except IntegrityError:
        db.session.rollback()
        return render_template("register.html", message="Đã có lỗi xảy ra, vui lòng thử lại sau.")
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

    posts = Post.query.join(PostCategory).join(Category).filter(
        Post.status == 'published',
        Post.deleted_at.is_(None),
        Category.status.is_(True)
    ).order_by(Post.created_at.desc()).all()


    postsView = Post.query.filter(
        Post.status == 'published',
        Post.deleted_at.is_(None)
    ).order_by(Post.view_count.desc()).limit(3).all()

    return render_template("index.html", posts=posts, postsView=postsView)


@app.route('/danhmuc/<string:slug>')
def category(slug):
    category = Category.query.filter_by(slug=slug).first_or_404()
    posts = [pc.post for pc in category.posts if pc.post.deleted_at is None]

    return render_template("category.html" , posts=posts , category=category , slug=slug)

@app.route('/baiviet/<string:slug>')
def post(slug):
    baiviet = Post.query.filter(Post.slug == slug, Post.deleted_at == None).first_or_404()
    tags = [pt.tag for pt in baiviet.post_tags]

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

    user_id = session.get("user")["id"]
    if user_id:
        existing_history = History.query.filter_by(
            user_id=user_id,
            post_id=baiviet.id
        ).first()

        if not existing_history:
            history = History(user_id=user_id, post_id=baiviet.id)
            db.session.add(history)
            db.session.commit()

    return render_template("detail.html",
                           baiviet=baiviet,
                           created_at_vn=created_at_vn,
                           related_posts=related_posts,
                           comments=comments,
                           tags=tags,
                           request=request)

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
        tag_string = ", ".join([post_tag.tag.name for post_tag in post.post_tags])


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
    post.post_tags.clear()
    for tag_name in tag_list:
        tag = Tag.query.filter_by(name=tag_name).first()
        if not tag:
            tag = Tag(name=tag_name)
            db.session.add(tag)
        post_tag = PostTag(post_id=post.id, tag_id=tag.id)
        post.post_tags.append(post_tag)

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
    db.session.add(new_comment)
    db.session.commit()

    if user.id != post_owner.id:
        notification_content = f"{user.name} vừa bình luận vào bài viết của bạn: {comment_text}"
        notification = Notification(user_id=post_owner.id, content=notification_content, post_id=post_id)
        db.session.add(notification)
        db.session.commit()
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
    user = session.get("user")
    if not user:
        return "Bạn chưa đăng nhập", 401
    user_id =  session.get('user')['id']
    posts = Post.query.filter(
        Post.user_id == user_id,
        Post.deleted_at.isnot(None)
    ).all()
    now = datetime.utcnow()
    for post in posts:
        expiration_time = post.deleted_at + timedelta(days=15)
        remaining = expiration_time - now
        post.remaining_seconds = max(int(remaining.total_seconds()), 0)
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
    khampha_all = KhamPha.query.order_by(KhamPha.created_at.desc()).all()
    return render_template("khampha_list.html", khamphas=khampha_all)

@app.route("/history", methods=['GET'])
def history():
    check = protectedUrl()
    if check:
        return check
    user_id = session.get('user').get('id')
    history_posts = db.session.query(Post).join(History, Post.id == History.post_id) \
        .filter(History.user_id == user_id).all()
    print(history_posts)
    return render_template("history.html" , historylist=history_posts)


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
