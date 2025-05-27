# 📰 Flask Blog Platform

Một nền tảng blog cá nhân được xây dựng bằng **Flask**, sử dụng **PostgreSQL** làm hệ quản trị cơ sở dữ liệu, hỗ trợ **SocketIO** để mở rộng khả năng real-time, bảo mật bằng **bcrypt**, và tích hợp **APScheduler** để thực thi các tác vụ định kỳ.

🌐 **Truy cập ngay tại:**  
👉 [https://myblog2-400d.onrender.com](https://myblog2-400d.onrender.com)

<p align="center">
  <img src="https://github.com/user-attachments/assets/6400300c-84cb-4b12-8060-793648f46d1f" width="45%" />
  <img src="https://github.com/user-attachments/assets/8f099987-da62-4e66-87d8-cae7b4449fe3"
" width="45%" />
</p>


<p align="center">
  <img src="https://github.com/user-attachments/assets/17fb094b-13c1-4266-84c7-1151128b2247"
" width="45%" />
  <img src="https://github.com/user-attachments/assets/21327b47-7b6f-4162-84d9-4c4afecb188e" width="45%" />
</p>
<p align="center">
  <img src="https://github.com/user-attachments/assets/b4f66cf5-000b-4516-bc03-854f86edcd53"
" width="45%" />
  <img src="" width="45%" />
</p>
## 🌟 Tính năng chính

- ✅ Đăng ký / Đăng nhập với mật khẩu mã hóa bằng bcrypt
- 📝 Tạo bài viết với:
  - Tiêu đề, mô tả, nội dung, ảnh thumbnail
  - Chọn nhiều danh mục và gắn thẻ (tags)
- 🔍 Xem chi tiết bài viết, tăng lượt xem
- 💬 Bình luận cho bài viết
- 📁 Quản lý danh mục (category)
- 🏷️ Hệ thống thẻ (tags) đa dạng
- 🔔 Thông báo người dùng (notifications)
- 🧠 Tự động tạo danh mục mặc định nếu chưa có
- 🔒 Kiểm tra session để bảo vệ URL yêu cầu đăng nhập
- 🕒 Quản lý trạng thái bài viết: Nháp, Đã xuất bản, Đã lưu trữ
- 🧑‍🤝‍🧑 Giao tiếp người dùng (tin nhắn) - qua `SocketIO`
- 📅 Lập lịch định kỳ với `APScheduler`

## 🧪 Công nghệ sử dụng

| Công nghệ | Vai trò |
|----------|---------|
| **Flask** | Web Framework chính |
| **Flask-SQLAlchemy** | ORM để thao tác với PostgreSQL |
| **PostgreSQL** | Hệ quản trị cơ sở dữ liệu |
| **Flask-SocketIO** | Xử lý real-time (chat, thông báo) |
| **Flask-Bcrypt** | Mã hóa mật khẩu người dùng |
| **APScheduler** | Thực thi các tác vụ định kỳ |
| **Jinja2** | Template Engine |
| **Tailwindcss** | Template |
| **Slugify** | Tạo đường dẫn thân thiện từ tiêu đề |
| **Werkzeug** | Quản lý upload file |

