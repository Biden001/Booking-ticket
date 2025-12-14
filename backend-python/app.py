"""
HUY CINEMA - Full-stack Python Flask Server
Sử dụng OOP với các Class theo Class Diagram
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_cors import CORS
from functools import wraps
import sqlite3
import hashlib
import os
from datetime import datetime

# Import các class từ models
from models import (
    Admin, Phim, PhongChieu, SuatChieu, Ghe, 
    KhachHang, Ve, DatCho, get_db
)

app = Flask(__name__)
app.secret_key = 'huy-cinema-secret-key-2025'
CORS(app)

# Database path - using models.py
DB_PATH = os.path.join(os.path.dirname(__file__), 'database.db')

# ===== DECORATORS =====
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Vui lòng đăng nhập để tiếp tục.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Vui lòng đăng nhập để tiếp tục.', 'warning')
            return redirect(url_for('login'))
        if not session.get('is_admin'):
            flash('Bạn không có quyền truy cập trang này.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# ===== PUBLIC ROUTES =====
@app.route('/')
def index():
    # Sử dụng class Phim
    phim_list = Phim.lay_tat_ca()
    movies = [p.to_dict() for p in phim_list]
    return render_template('index.html', movies=movies)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    # Sử dụng class Phim
    phim_list = Phim.tim_kiem(query)
    movies = [p.to_dict() for p in phim_list]
    return render_template('index.html', movies=movies, query=query)

@app.route('/movie/<int:movie_id>')
def movie_detail(movie_id):
    # Sử dụng class Phim và SuatChieu
    phim = Phim.tim_theo_id(movie_id)
    if not phim:
        flash('Không tìm thấy phim.', 'error')
        return redirect(url_for('index'))
    
    suat_chieu_list = SuatChieu.lay_theo_phim(movie_id)
    movie = phim.to_dict()
    showtimes = [s.to_dict() for s in suat_chieu_list]
    return render_template('movie_detail.html', movie=movie, showtimes=showtimes)

# ===== AUTH ROUTES =====
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Sử dụng class KhachHang
        khach_hang = KhachHang.dang_nhap(username, password)
        
        if khach_hang:
            session['user_id'] = khach_hang.maKH
            session['username'] = khach_hang.username
            session['is_admin'] = bool(khach_hang.is_admin)
            flash(f'Chào mừng {khach_hang.username}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Sai tên đăng nhập hoặc mật khẩu.', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        full_name = request.form.get('full_name')
        phone = request.form.get('phone')
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')
        
        if password != confirm:
            flash('Mật khẩu xác nhận không khớp.', 'error')
            return render_template('register.html')
        
        # Sử dụng class KhachHang
        khach_hang = KhachHang.dang_ky(
            username=username,
            password=password,
            email=email,
            ten=full_name,
            sdt=phone
        )
        
        if not khach_hang:
            flash('Tên đăng nhập đã tồn tại.', 'error')
            return render_template('register.html')
        
        flash('Đăng ký thành công! Vui lòng đăng nhập.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Đã đăng xuất.', 'success')
    return redirect(url_for('index'))

# ===== HELPER FUNCTIONS =====
def giai_phong_ghe_het_han():
    """Tự động giải phóng các ghế đã hết thời gian giữ"""
    conn = get_db()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Giải phóng ghế đã hết hạn giữ
    conn.execute('''
        UPDATE seats 
        SET status = 'available', held_by = NULL, held_until = NULL
        WHERE status = 'held' AND held_until < ?
    ''', (now,))
    
    conn.commit()
    conn.close()

def huy_ve_qua_gio():
    """Tự động hủy các vé đã quá giờ chiếu"""
    conn = get_db()
    now = datetime.now()
    current_date = now.strftime('%Y-%m-%d')
    current_time = now.strftime('%H:%M')
    
    # Tìm và hủy các vé có suất chiếu đã qua
    expired_bookings = conn.execute('''
        UPDATE bookings 
        SET status = 'expired'
        WHERE status = 'confirmed' 
        AND showtime_id IN (
            SELECT id FROM showtimes 
            WHERE show_date < ? 
            OR (show_date = ? AND show_time < ?)
        )
    ''', (current_date, current_date, current_time)).rowcount
    
    # Cập nhật ghế về trạng thái available
    conn.execute('''
        UPDATE seats 
        SET status = 'available'
        WHERE id IN (
            SELECT seat_id FROM bookings 
            WHERE status = 'expired'
        )
    ''')
    
    conn.commit()
    conn.close()
    return expired_bookings

def kiem_tra_suat_chieu_hop_le(showtime_id):
    """Kiểm tra xem suất chiếu có còn hợp lệ để đặt vé không"""
    suat_chieu = SuatChieu.tim_theo_id(showtime_id)
    if not suat_chieu:
        return False, 'Không tìm thấy suất chiếu.'
    
    now = datetime.now()
    current_date = now.strftime('%Y-%m-%d')
    current_time = now.strftime('%H:%M')
    
    # So sánh ngày và giờ
    if suat_chieu.ngaychieu < current_date:
        return False, 'Suất chiếu này đã qua ngày chiếu.'
    elif suat_chieu.ngaychieu == current_date and suat_chieu.giochieu < current_time:
        return False, 'Suất chiếu này đã qua giờ chiếu.'
    
    return True, suat_chieu

# ===== BOOKING ROUTES =====
@app.route('/booking/<int:showtime_id>')
@login_required
def booking(showtime_id):
    # Giải phóng ghế hết hạn và hủy vé quá giờ
    giai_phong_ghe_het_han()
    huy_ve_qua_gio()
    
    # Kiểm tra suất chiếu còn hợp lệ không
    hop_le, result = kiem_tra_suat_chieu_hop_le(showtime_id)
    if not hop_le:
        flash(result, 'error')
        return redirect(url_for('index'))
    
    suat_chieu = result
    phim = Phim.tim_theo_id(suat_chieu.maphim)
    
    # Lấy danh sách ghế với thông tin held_by
    conn = get_db()
    seats_data = conn.execute('''
        SELECT id, seat_number, status, held_by, held_until, showtime_id
        FROM seats WHERE showtime_id = ? ORDER BY seat_number
    ''', (showtime_id,)).fetchall()
    conn.close()
    
    user_id = session.get('user_id')
    seats = []
    for s in seats_data:
        seat_dict = {
            'id': s['id'],
            'seat_number': s['seat_number'],
            'status': s['status'],
            'showtime_id': s['showtime_id'],
            'held_by': s['held_by'],
            'is_held_by_me': s['held_by'] == user_id if s['status'] == 'held' else False
        }
        seats.append(seat_dict)
    
    showtime = suat_chieu.to_dict()
    movie = phim.to_dict() if phim else {}
    
    return render_template('booking.html', showtime=showtime, movie=movie, seats=seats)

# ===== SEAT HOLDING API =====
@app.route('/api/hold-seat', methods=['POST'])
@login_required
def hold_seat():
    """API giữ ghế tạm thời khi user chọn"""
    from flask import jsonify
    
    data = request.get_json()
    seat_id = data.get('seat_id')
    showtime_id = data.get('showtime_id')
    user_id = session.get('user_id')
    
    if not seat_id or not showtime_id:
        return jsonify({'success': False, 'message': 'Thiếu thông tin ghế'}), 400
    
    # Giải phóng ghế hết hạn trước
    giai_phong_ghe_het_han()
    
    conn = get_db()
    conn.isolation_level = 'IMMEDIATE'
    
    try:
        # Kiểm tra ghế có available không (hoặc đang được chính user này giữ)
        seat = conn.execute('''
            SELECT * FROM seats 
            WHERE id = ? AND showtime_id = ? 
            AND (status = 'available' OR (status = 'held' AND held_by = ?))
        ''', (seat_id, showtime_id, user_id)).fetchone()
        
        if not seat:
            conn.close()
            return jsonify({'success': False, 'message': 'Ghế đã được người khác chọn'}), 409
        
        # Giữ ghế trong 5 phút
        from datetime import timedelta
        held_until = (datetime.now() + timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S')
        
        conn.execute('''
            UPDATE seats 
            SET status = 'held', held_by = ?, held_until = ?
            WHERE id = ? AND (status = 'available' OR (status = 'held' AND held_by = ?))
        ''', (user_id, held_until, seat_id, user_id))
        
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Đã giữ ghế', 'held_until': held_until})
        
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/release-seat', methods=['POST'])
@login_required
def release_seat():
    """API bỏ giữ ghế khi user bỏ chọn"""
    from flask import jsonify
    
    data = request.get_json()
    seat_id = data.get('seat_id')
    user_id = session.get('user_id')
    
    if not seat_id:
        return jsonify({'success': False, 'message': 'Thiếu thông tin ghế'}), 400
    
    conn = get_db()
    
    # Chỉ cho phép bỏ ghế do chính user đang giữ
    conn.execute('''
        UPDATE seats 
        SET status = 'available', held_by = NULL, held_until = NULL
        WHERE id = ? AND held_by = ?
    ''', (seat_id, user_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Đã bỏ giữ ghế'})

@app.route('/api/get-seats/<int:showtime_id>')
@login_required
def get_seats(showtime_id):
    """API lấy trạng thái ghế realtime"""
    from flask import jsonify
    
    # Giải phóng ghế hết hạn trước
    giai_phong_ghe_het_han()
    
    user_id = session.get('user_id')
    conn = get_db()
    seats_data = conn.execute('''
        SELECT id, seat_number, status, held_by
        FROM seats WHERE showtime_id = ? ORDER BY seat_number
    ''', (showtime_id,)).fetchall()
    conn.close()
    
    seats = []
    for s in seats_data:
        seats.append({
            'id': s['id'],
            'seat_number': s['seat_number'],
            'status': s['status'],
            'is_held_by_me': s['held_by'] == user_id if s['status'] == 'held' else False
        })
    
    return jsonify({'seats': seats})

@app.route('/book', methods=['POST'])
@login_required
def book_seat():
    showtime_id = request.form.get('showtime_id')
    seat_ids = request.form.getlist('seat_ids')
    
    if not seat_ids:
        flash('Vui lòng chọn ít nhất một ghế.', 'warning')
        return redirect(url_for('booking', showtime_id=showtime_id))
    
    # Kiểm tra lại suất chiếu trước khi đặt
    hop_le, result = kiem_tra_suat_chieu_hop_le(int(showtime_id))
    if not hop_le:
        flash(result, 'error')
        return redirect(url_for('index'))
    
    # Sử dụng class KhachHang
    khach_hang = KhachHang.tim_theo_id(session['user_id'])
    if khach_hang:
        so_ghe_yeu_cau = len(seat_ids)
        ve_list = khach_hang.dat_ve(int(showtime_id), [int(sid) for sid in seat_ids])
        
        if len(ve_list) == 0:
            flash('Không thể đặt vé. Các ghế đã được người khác đặt trước.', 'error')
            return redirect(url_for('booking', showtime_id=showtime_id))
        elif len(ve_list) < so_ghe_yeu_cau:
            flash(f'Chỉ đặt được {len(ve_list)}/{so_ghe_yeu_cau} ghế. Một số ghế đã được người khác đặt trước.', 'warning')
        else:
            flash(f'Đặt vé thành công! Đã đặt {len(ve_list)} ghế.', 'success')
    else:
        flash('Không tìm thấy thông tin khách hàng.', 'error')
    
    return redirect(url_for('my_bookings'))

@app.route('/my-bookings')
@login_required
def my_bookings():
    # Hủy vé quá giờ trước khi hiển thị
    huy_ve_qua_gio()
    
    # Sử dụng class Ve
    conn = get_db()
    bookings = conn.execute('''
        SELECT b.*, m.title, m.poster_url, s.theater, s.show_date, s.show_time
        FROM bookings b
        JOIN showtimes s ON b.showtime_id = s.id
        JOIN movies_info m ON s.movie_id = m.id
        WHERE b.user_id = ?
        ORDER BY b.booking_time DESC
    ''', (session['user_id'],)).fetchall()
    conn.close()
    
    return render_template('my_bookings.html', bookings=bookings)

@app.route('/cancel-booking/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    # Sử dụng class Ve
    ve = Ve.tim_theo_id(booking_id)
    
    if ve and ve.maKH == session['user_id']:
        ve.huy_don_dat_ve()
        flash('Đã hủy vé thành công.', 'success')
    else:
        flash('Không tìm thấy vé.', 'error')
    
    return redirect(url_for('my_bookings'))

# ===== ACCOUNT ROUTES =====
@app.route('/account')
@login_required
def account():
    # Sử dụng class KhachHang
    khach_hang = KhachHang.tim_theo_id(session['user_id'])
    user = khach_hang.to_dict() if khach_hang else {}
    return render_template('account.html', user=user)

@app.route('/update-profile', methods=['POST'])
@login_required
def update_profile():
    email = request.form.get('email')
    full_name = request.form.get('full_name')
    phone = request.form.get('phone')
    
    # Sử dụng class KhachHang
    khach_hang = KhachHang.tim_theo_id(session['user_id'])
    if khach_hang:
        khach_hang.cap_nhat_thong_tin(email=email, ten=full_name, sdt=phone)
        flash('Cập nhật thông tin thành công!', 'success')
    
    return redirect(url_for('account'))

@app.route('/change-password', methods=['POST'])
@login_required
def change_password():
    current = request.form.get('current_password')
    new = request.form.get('new_password')
    confirm = request.form.get('confirm_password')
    
    if new != confirm:
        flash('Mật khẩu xác nhận không khớp.', 'error')
        return redirect(url_for('account'))
    
    # Sử dụng class KhachHang
    khach_hang = KhachHang.tim_theo_id(session['user_id'])
    if not khach_hang:
        flash('Không tìm thấy tài khoản.', 'error')
        return redirect(url_for('account'))
    
    # Kiểm tra mật khẩu hiện tại
    conn = get_db()
    user = conn.execute(
        'SELECT * FROM users WHERE id = ? AND password = ?',
        (session['user_id'], KhachHang.hash_password(current))
    ).fetchone()
    
    if not user:
        flash('Mật khẩu hiện tại không đúng.', 'error')
        conn.close()
        return redirect(url_for('account'))
    
    conn.execute('UPDATE users SET password = ? WHERE id = ?', 
                (KhachHang.hash_password(new), session['user_id']))
    conn.commit()
    conn.close()
    
    flash('Đổi mật khẩu thành công!', 'success')
    return redirect(url_for('account'))

# ===== ADMIN ROUTES =====
@app.route('/admin')
@admin_required
def admin():
    # Hủy vé quá giờ trước khi hiển thị
    huy_ve_qua_gio()
    
    # Sử dụng các class model
    phim_list = Phim.lay_tat_ca()
    movies = [p.to_dict() for p in phim_list]
    
    conn = get_db()
    showtimes = conn.execute('''
        SELECT s.*, m.title FROM showtimes s
        JOIN movies_info m ON s.movie_id = m.id
        ORDER BY s.show_date DESC
    ''').fetchall()
    
    bookings = conn.execute('''
        SELECT b.*, u.username, m.title, se.seat_number, st.show_date
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        JOIN showtimes st ON b.showtime_id = st.id
        JOIN movies_info m ON st.movie_id = m.id
        JOIN seats se ON b.seat_id = se.id
        ORDER BY b.booking_time DESC
    ''').fetchall()
    
    khach_hang_list = KhachHang.lay_tat_ca()
    users = [kh.to_dict() for kh in khach_hang_list]
    conn.close()
    
    # Thống kê tổng quan (sử dụng class Admin)
    admin_user = Admin(session['username'], '')
    stats = admin_user.xem_thong_ke_tong_quan()
    top_phim = admin_user.lay_top_phim_doanh_thu(10)
    
    return render_template('admin.html', movies=movies, showtimes=showtimes, 
                          bookings=bookings, users=users, stats=stats, top_phim=top_phim)

@app.route('/admin/add-movie', methods=['POST'])
@admin_required
def admin_add_movie():
    title = request.form.get('title')
    genre = request.form.get('genre')
    duration = request.form.get('duration')
    poster_url = request.form.get('poster_url')
    trailer_url = request.form.get('trailer_url')
    description = request.form.get('description')
    director = request.form.get('director')
    cast_members = request.form.get('cast_members')
    
    # Sử dụng class Phim
    phim = Phim(
        tenphim=title,
        theloai=genre,
        thoiluong=int(duration) if duration else 0,
        poster=poster_url,
        trailer=trailer_url,
        tomtat=description,
        daodien=director,
        dienvien=cast_members
    )
    phim.them_phim()
    
    flash(f'Đã thêm phim "{title}"!', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/edit-movie/<int:movie_id>', methods=['POST'])
@admin_required
def admin_edit_movie(movie_id):
    title = request.form.get('title')
    genre = request.form.get('genre')
    duration = request.form.get('duration')
    poster_url = request.form.get('poster_url')
    trailer_url = request.form.get('trailer_url')
    description = request.form.get('description')
    director = request.form.get('director')
    cast_members = request.form.get('cast_members')
    
    # Sử dụng class Phim
    phim = Phim.tim_theo_id(movie_id)
    if phim:
        phim.tenphim = title
        phim.theloai = genre
        phim.thoiluong = int(duration) if duration else 0
        phim.poster = poster_url
        phim.trailer = trailer_url
        phim.tomtat = description
        phim.daodien = director
        phim.dienvien = cast_members
        phim.cap_nhat_phim()
        flash(f'Đã cập nhật phim "{title}"!', 'success')
    else:
        flash('Không tìm thấy phim!', 'error')
    
    return redirect(url_for('admin'))

@app.route('/admin/delete-movie/<int:movie_id>', methods=['POST'])
@admin_required
def admin_delete_movie(movie_id):
    # Sử dụng class Phim
    phim = Phim.tim_theo_id(movie_id)
    if phim:
        phim.xoa_phim()
    flash('Đã xóa phim!', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/add-showtime', methods=['POST'])
@admin_required
def admin_add_showtime():
    movie_id = request.form.get('movie_id')
    theater = request.form.get('theater')
    show_date = request.form.get('show_date')
    show_time = request.form.get('show_time')
    price = request.form.get('price')
    
    # Sử dụng class SuatChieu
    suat_chieu = SuatChieu(
        maphim=int(movie_id),
        maphong=theater,
        ngaychieu=show_date,
        giochieu=show_time,
        giave=float(price) if price else 75000
    )
    suat_chieu.them_suat_chieu()
    
    flash('Đã thêm suất chiếu với 50 ghế!', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/delete-showtime/<int:showtime_id>', methods=['POST'])
@admin_required
def admin_delete_showtime(showtime_id):
    # Sử dụng class SuatChieu
    suat_chieu = SuatChieu.tim_theo_id(showtime_id)
    if suat_chieu:
        suat_chieu.xoa_suat_chieu()
    flash('Đã xóa suất chiếu!', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/cancel-booking/<int:booking_id>', methods=['POST'])
@admin_required
def admin_cancel_booking(booking_id):
    # Sử dụng class Ve
    ve = Ve.tim_theo_id(booking_id)
    if ve:
        ve.huy_don_dat_ve()
        flash('Đã hủy đặt vé!', 'success')
    return redirect(url_for('admin'))

# ===== INIT DATABASE =====
def init_db():
    conn = get_db()
    
    # Create tables
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT,
            password TEXT NOT NULL,
            full_name TEXT,
            phone TEXT,
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS movies_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            genre TEXT,
            duration INTEGER,
            poster_url TEXT,
            trailer_url TEXT,
            description TEXT,
            director TEXT,
            cast_members TEXT
        );
        
        CREATE TABLE IF NOT EXISTS theaters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            seat_rows INTEGER DEFAULT 5,
            seats_per_row INTEGER DEFAULT 10,
            total_seats INTEGER DEFAULT 50
        );
        
        CREATE TABLE IF NOT EXISTS showtimes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            movie_id INTEGER,
            theater TEXT,
            show_date TEXT,
            show_time TEXT,
            price REAL DEFAULT 75000,
            FOREIGN KEY (movie_id) REFERENCES movies_info(id)
        );
        
        CREATE TABLE IF NOT EXISTS seats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            showtime_id INTEGER,
            seat_number TEXT,
            status TEXT DEFAULT 'available',
            held_by INTEGER DEFAULT NULL,
            held_until TEXT DEFAULT NULL,
            FOREIGN KEY (showtime_id) REFERENCES showtimes(id),
            FOREIGN KEY (held_by) REFERENCES users(id)
        );
        
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            showtime_id INTEGER,
            seat_id INTEGER,
            seat_number TEXT,
            price REAL,
            status TEXT DEFAULT 'confirmed',
            booking_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (showtime_id) REFERENCES showtimes(id),
            FOREIGN KEY (seat_id) REFERENCES seats(id)
        );
    ''')

    # Ensure columns exist for older databases
    try:
        conn.execute('ALTER TABLE movies_info ADD COLUMN trailer_url TEXT')
    except sqlite3.OperationalError:
        pass
    
    try:
        conn.execute('ALTER TABLE movies_info ADD COLUMN director TEXT')
    except sqlite3.OperationalError:
        pass
    
    try:
        conn.execute('ALTER TABLE movies_info ADD COLUMN cast_members TEXT')
    except sqlite3.OperationalError:
        pass
    
    # Thêm cột held_by và held_until cho bảng seats (migration)
    try:
        conn.execute('ALTER TABLE seats ADD COLUMN held_by INTEGER DEFAULT NULL')
    except sqlite3.OperationalError:
        pass
    
    try:
        conn.execute('ALTER TABLE seats ADD COLUMN held_until TEXT DEFAULT NULL')
    except sqlite3.OperationalError:
        pass
    
    # Check if data exists - kiểm tra CẢ users VÀ movies để tránh lặp
    users_count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    movies_count = conn.execute('SELECT COUNT(*) FROM movies_info').fetchone()[0]
    
    if users_count == 0 and movies_count == 0:
        # Add sample users - sử dụng KhachHang.hash_password
        conn.execute("INSERT INTO users (username, email, password, full_name, is_admin) VALUES (?, ?, ?, ?, ?)",
                    ('admin', 'admin@cinema.com', KhachHang.hash_password('admin123'), 'Administrator', 1))
        conn.execute("INSERT INTO users (username, email, password, full_name) VALUES (?, ?, ?, ?)",
                    ('user1', 'user1@email.com', KhachHang.hash_password('123456'), 'Nguyen Van A'))
        
        # Add sample movies với đầy đủ thông tin
        movies = [
            ('Avengers: Endgame', 'Hành động, Sci-Fi', 181, 'https://image.tmdb.org/t/p/w500/or06FN3Dka5tuj1mYAMzsGwzTdp.jpg', 'https://www.youtube.com/embed/TcMBFSGVi1c', 'Anthony Russo, Joe Russo', 'Robert Downey Jr., Chris Evans, Mark Ruffalo'),
            ('Spider-Man: No Way Home', 'Hành động, Phiêu lưu', 148, 'https://image.tmdb.org/t/p/w500/1g0dhYtq4irTY1GPXvft6k4YLjm.jpg', 'https://www.youtube.com/embed/JfVOs4VSpmA', 'Jon Watts', 'Tom Holland, Zendaya, Benedict Cumberbatch'),
            ('Oppenheimer', 'Tiểu sử, Lịch sử', 180, 'https://image.tmdb.org/t/p/w500/8Gxv8gSFCU0XGDykEGv7zR1n2ua.jpg', 'https://www.youtube.com/embed/uYPbbksJxIg', 'Christopher Nolan', 'Cillian Murphy, Emily Blunt, Matt Damon'),
            ('The Batman', 'Hành động, Tội phạm', 176, 'https://image.tmdb.org/t/p/w500/74xTEgt7R36Fpooo50r9T25onhq.jpg', 'https://www.youtube.com/embed/mqqft2x_Aa4', 'Matt Reeves', 'Robert Pattinson, Zoë Kravitz, Paul Dano'),
            ('Dune', 'Sci-Fi, Phiêu lưu', 155, 'https://image.tmdb.org/t/p/w500/d5NXSklXo0qyIYkgV94XAgMIckC.jpg', 'https://www.youtube.com/embed/n9xhJrPXop4', 'Denis Villeneuve', 'Timothée Chalamet, Rebecca Ferguson, Zendaya'),
            ('Avatar: The Way of Water', 'Sci-Fi, Phiêu lưu', 192, 'https://image.tmdb.org/t/p/w500/t6HIqrRAclMCA60NsSmeqe9RmNV.jpg', 'https://www.youtube.com/embed/d9MyW72ELq0', 'James Cameron', 'Sam Worthington, Zoe Saldana, Sigourney Weaver'),
            ('John Wick: Chapter 4', 'Hành động, Tội phạm', 169, 'https://image.tmdb.org/t/p/w500/vZloFAK7NmvMGKE7VkF5UHaz0I.jpg', 'https://www.youtube.com/embed/qEVUtrk8_B4', 'Chad Stahelski', 'Keanu Reeves, Donnie Yen, Bill Skarsgård'),
            ('Guardians of the Galaxy Vol. 3', 'Hành động, Hài', 150, 'https://image.tmdb.org/t/p/w500/r2J02Z2OpNTctfOSN1Ydgii51I3.jpg', 'https://www.youtube.com/embed/u3V5KDHRQvk', 'James Gunn', 'Chris Pratt, Zoe Saldana, Dave Bautista'),
            ('Barbie', 'Hài, Phiêu lưu', 114, 'https://image.tmdb.org/t/p/w500/iuFNMS8U5cb6xfzi51Dbkovj7vM.jpg', 'https://www.youtube.com/embed/pBk4NYhWNMM', 'Greta Gerwig', 'Margot Robbie, Ryan Gosling, America Ferrera'),
            ('Mission: Impossible - Dead Reckoning', 'Hành động, Phiêu lưu', 163, 'https://image.tmdb.org/t/p/w500/NNxYkU70HPurnNCSiCjYAmacwm.jpg', 'https://www.youtube.com/embed/avz06PDqDbM', 'Christopher McQuarrie', 'Tom Cruise, Hayley Atwell, Ving Rhames'),
            ('Fast X', 'Hành động, Tội phạm', 141, 'https://image.tmdb.org/t/p/w500/fiVW06jE7z9YnO4trhaMEdclSiC.jpg', 'https://www.youtube.com/embed/eoOaKN4qCKw', 'Louis Leterrier', 'Vin Diesel, Michelle Rodriguez, Jason Momoa'),
            ('Wonka', 'Gia đình, Hài', 116, 'https://image.tmdb.org/t/p/w500/qhb1qOilapbapxWQn9jtRCMwXJF.jpg', 'https://www.youtube.com/embed/otNh9bTjXWg', 'Paul King', 'Timothée Chalamet, Gustave Die, Murray Abraham'),
        ]
        
        for m in movies:
            if len(m) == 7:
                conn.execute('INSERT INTO movies_info (title, genre, duration, poster_url, trailer_url, director, cast_members) VALUES (?, ?, ?, ?, ?, ?, ?)', m)
            else:
                conn.execute('INSERT INTO movies_info (title, genre, duration, poster_url, trailer_url) VALUES (?, ?, ?, ?, ?)', m)
        
        # Add sample showtimes
        showtimes_data = [
            (1, 'Rạp 1', '2025-12-15', '10:00', 75000),
            (1, 'Rạp 2', '2025-12-15', '14:00', 85000),
            (2, 'Rạp 1', '2025-12-15', '16:00', 75000),
            (3, 'Rạp 3', '2025-12-16', '19:00', 95000),
            (4, 'Rạp 2', '2025-12-16', '20:00', 85000),
        ]
        
        for st in showtimes_data:
            cursor = conn.execute('INSERT INTO showtimes (movie_id, theater, show_date, show_time, price) VALUES (?, ?, ?, ?, ?)', st)
            showtime_id = cursor.lastrowid
            
            # Create seats
            for row in ['A', 'B', 'C', 'D', 'E']:
                for num in range(1, 11):
                    conn.execute('INSERT INTO seats (showtime_id, seat_number, status) VALUES (?, ?, "available")',
                               (showtime_id, f'{row}{num}'))
        
        conn.commit()
        print('✅ Database initialized with sample data!')
    
    conn.close()

# ===== RUN =====
if __name__ == '__main__':
    init_db()
    
    print('''
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   🎬 HUY CINEMA - Full-stack Python Flask                 ║
║                                                           ║
║   ✅ Server: http://localhost:3000                        ║
║   ✅ 100% Python - Không cần JavaScript frontend          ║
║                                                           ║
║   📂 Tài khoản mẫu:                                       ║
║   - Admin: admin / admin123                               ║
║   - User:  user1 / 123456                                 ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    ''')
    
    app.run(host='0.0.0.0', port=3000, debug=True)
