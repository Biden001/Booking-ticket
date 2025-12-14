"""
HUY CINEMA - Models theo Class Diagram
Các class đại diện cho các thực thể trong hệ thống đặt vé xem phim
"""

import sqlite3
import hashlib
import os
from datetime import datetime
from typing import List, Optional, Dict, Any

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), 'database.db')

def get_db():
    """Kết nối database"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ===== CLASS ADMIN =====
class Admin:
    """
    Class Admin - Quản trị viên
    Attributes:
        - username: string
        - password: string
    Methods:
        + XemThongKeTongQuan(): Xem thống kê tổng quan hệ thống
    """
    
    def __init__(self, username: str, password: str, id: int = None):
        self.id = id
        self.username = username
        self.password = password
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Mã hóa mật khẩu"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    @classmethod
    def dang_nhap(cls, username: str, password: str) -> Optional['Admin']:
        """Đăng nhập admin"""
        conn = get_db()
        user = conn.execute(
            'SELECT * FROM users WHERE username = ? AND password = ? AND is_admin = 1',
            (username, cls.hash_password(password))
        ).fetchone()
        conn.close()
        
        if user:
            return cls(user['username'], user['password'], user['id'])
        return None
    
    def xem_thong_ke_tong_quan(self) -> Dict[str, Any]:
        """Xem thống kê tổng quan hệ thống"""
        conn = get_db()
        
        stats = {
            'tong_phim': conn.execute('SELECT COUNT(*) FROM movies_info').fetchone()[0],
            'tong_suat_chieu': conn.execute('SELECT COUNT(*) FROM showtimes').fetchone()[0],
            'tong_ve_dat': conn.execute('SELECT COUNT(*) FROM bookings WHERE status = "confirmed"').fetchone()[0],
            'tong_doanh_thu': conn.execute('SELECT COALESCE(SUM(price), 0) FROM bookings WHERE status = "confirmed"').fetchone()[0],
            'tong_khach_hang': conn.execute('SELECT COUNT(*) FROM users WHERE is_admin = 0').fetchone()[0],
        }
        
        conn.close()
        return stats
    
    def lay_top_phim_doanh_thu(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Lấy top phim có doanh thu cao nhất"""
        conn = get_db()
        
        rows = conn.execute('''
            SELECT 
                m.id,
                m.title,
                m.poster_url,
                COUNT(b.id) as so_ve_ban,
                COALESCE(SUM(b.price), 0) as doanh_thu
            FROM movies_info m
            LEFT JOIN showtimes s ON m.id = s.movie_id
            LEFT JOIN bookings b ON s.id = b.showtime_id AND b.status = 'confirmed'
            GROUP BY m.id
            ORDER BY doanh_thu DESC
            LIMIT ?
        ''', (limit,)).fetchall()
        
        conn.close()
        
        return [
            {
                'id': row['id'],
                'title': row['title'],
                'poster_url': row['poster_url'],
                'so_ve_ban': row['so_ve_ban'],
                'doanh_thu': row['doanh_thu']
            }
            for row in rows
        ]


# ===== CLASS PHIM =====
class Phim:
    """
    Class Phim - Thông tin phim
    Attributes:
        - maphim: string (id)
        - tenphim: string (title)
        - poster: string (poster_url)
        - thoiluong: int (duration)
        - tomtat: string (description)
        - trailer: string (trailer_url)
        - daodien: string (director)
        - dienvien: string (cast)
    Methods:
        + KiemTraTrangThai(): Kiểm tra trạng thái phim
        + ThemPhim(): Thêm phim mới
        + CapNhatPhim(): Cập nhật thông tin phim
        + XoaPhim(): Xóa phim
    """
    
    def __init__(self, tenphim: str, poster: str = None, thoiluong: int = 0,
                 tomtat: str = None, trailer: str = None, daodien: str = None,
                 dienvien: str = None, theloai: str = None, maphim: int = None):
        self.maphim = maphim
        self.tenphim = tenphim
        self.poster = poster
        self.thoiluong = thoiluong
        self.tomtat = tomtat
        self.trailer = trailer
        self.daodien = daodien
        self.dienvien = dienvien
        self.theloai = theloai
    
    @classmethod
    def lay_tat_ca(cls) -> List['Phim']:
        """Lấy tất cả phim"""
        conn = get_db()
        rows = conn.execute('SELECT * FROM movies_info ORDER BY id DESC').fetchall()
        conn.close()
        
        return [cls(
            maphim=row['id'],
            tenphim=row['title'],
            theloai=row['genre'],
            thoiluong=row['duration'],
            poster=row['poster_url'],
            trailer=row['trailer_url'],
            tomtat=row['description'],
            daodien=row['director'] if 'director' in row.keys() else None,
            dienvien=row['cast_members'] if 'cast_members' in row.keys() else None
        ) for row in rows]
    
    @classmethod
    def tim_theo_id(cls, maphim: int) -> Optional['Phim']:
        """Tìm phim theo ID"""
        conn = get_db()
        row = conn.execute('SELECT * FROM movies_info WHERE id = ?', (maphim,)).fetchone()
        conn.close()
        
        if row:
            return cls(
                maphim=row['id'],
                tenphim=row['title'],
                theloai=row['genre'],
                thoiluong=row['duration'],
                poster=row['poster_url'],
                trailer=row['trailer_url'],
                tomtat=row['description'],
                daodien=row['director'] if 'director' in row.keys() else None,
                dienvien=row['cast_members'] if 'cast_members' in row.keys() else None
            )
        return None
    
    @classmethod
    def tim_kiem(cls, tu_khoa: str) -> List['Phim']:
        """Tìm kiếm phim theo từ khóa"""
        conn = get_db()
        rows = conn.execute(
            'SELECT * FROM movies_info WHERE title LIKE ? OR genre LIKE ? OR director LIKE ? OR cast_members LIKE ?',
            (f'%{tu_khoa}%', f'%{tu_khoa}%', f'%{tu_khoa}%', f'%{tu_khoa}%')
        ).fetchall()
        conn.close()
        
        return [cls(
            maphim=row['id'],
            tenphim=row['title'],
            theloai=row['genre'],
            thoiluong=row['duration'],
            poster=row['poster_url'],
            trailer=row['trailer_url'],
            tomtat=row['description'],
            daodien=row['director'] if 'director' in row.keys() else None,
            dienvien=row['cast_members'] if 'cast_members' in row.keys() else None
        ) for row in rows]
    
    def kiem_tra_trang_thai(self) -> str:
        """Kiểm tra trạng thái phim (đang chiếu, sắp chiếu, ngừng chiếu)"""
        conn = get_db()
        suat_chieu = conn.execute(
            'SELECT COUNT(*) FROM showtimes WHERE movie_id = ? AND show_date >= date("now")',
            (self.maphim,)
        ).fetchone()[0]
        conn.close()
        
        if suat_chieu > 0:
            return "Đang chiếu"
        return "Ngừng chiếu"
    
    def them_phim(self) -> int:
        """Thêm phim mới vào database"""
        conn = get_db()
        cursor = conn.execute(
            '''INSERT INTO movies_info (title, genre, duration, poster_url, trailer_url, description, director, cast_members)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (self.tenphim, self.theloai, self.thoiluong, self.poster, self.trailer, self.tomtat, self.daodien, self.dienvien)
        )
        self.maphim = cursor.lastrowid
        conn.commit()
        conn.close()
        return self.maphim
    
    def cap_nhat_phim(self) -> bool:
        """Cập nhật thông tin phim"""
        conn = get_db()
        conn.execute(
            '''UPDATE movies_info SET title = ?, genre = ?, duration = ?, 
               poster_url = ?, trailer_url = ?, description = ?, director = ?, cast_members = ? WHERE id = ?''',
            (self.tenphim, self.theloai, self.thoiluong, self.poster, self.trailer, self.tomtat, self.daodien, self.dienvien, self.maphim)
        )
        conn.commit()
        conn.close()
        return True
    
    def xoa_phim(self) -> bool:
        """Xóa phim"""
        conn = get_db()
        conn.execute('DELETE FROM movies_info WHERE id = ?', (self.maphim,))
        conn.commit()
        conn.close()
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Chuyển đổi thành dictionary"""
        return {
            'id': self.maphim,
            'title': self.tenphim,
            'genre': self.theloai,
            'duration': self.thoiluong,
            'poster_url': self.poster,
            'trailer_url': self.trailer,
            'description': self.tomtat,
            'director': self.daodien,
            'cast_members': self.dienvien
        }


# ===== CLASS PHONG CHIEU =====
class PhongChieu:
    """
    Class PhòngChiếu - Phòng chiếu phim
    Attributes:
        - maphong: string
        - soghengoi: int (số ghế ngồi)
        - soluongghe: int (số lượng ghế)
    """
    
    def __init__(self, maphong: str, soghengoi: int = 50, soluongghe: int = 50):
        self.maphong = maphong
        self.soghengoi = soghengoi
        self.soluongghe = soluongghe
    
    @classmethod
    def lay_tat_ca(cls) -> List['PhongChieu']:
        """Lấy danh sách tất cả phòng chiếu"""
        # Mặc định có 3 phòng chiếu
        return [
            cls('Rạp 1', 50, 50),
            cls('Rạp 2', 50, 50),
            cls('Rạp 3', 50, 50),
        ]


# ===== CLASS SUAT CHIEU =====
class SuatChieu:
    """
    Class SuấtChiếu - Suất chiếu phim
    Attributes:
        - masuatchieu: string (id)
        - maphong: string (theater)
        - maphim: string (movie_id)
        - ngaychieu: date (show_date)
        - giochieu: time (show_time)
    Methods:
        + ThemSuatChieu(): Thêm suất chiếu
        + XoaSuatChieu(): Xóa suất chiếu
        + CapNhatSuatChieu(): Cập nhật suất chiếu
    """
    
    def __init__(self, maphim: int, maphong: str, ngaychieu: str, giochieu: str,
                 giave: float = 75000, masuatchieu: int = None):
        self.masuatchieu = masuatchieu
        self.maphim = maphim
        self.maphong = maphong
        self.ngaychieu = ngaychieu
        self.giochieu = giochieu
        self.giave = giave
    
    @classmethod
    def lay_theo_phim(cls, maphim: int) -> List['SuatChieu']:
        """Lấy tất cả suất chiếu của một phim"""
        conn = get_db()
        rows = conn.execute(
            'SELECT * FROM showtimes WHERE movie_id = ? ORDER BY show_date, show_time',
            (maphim,)
        ).fetchall()
        conn.close()
        
        return [cls(
            masuatchieu=row['id'],
            maphim=row['movie_id'],
            maphong=row['theater'],
            ngaychieu=row['show_date'],
            giochieu=row['show_time'],
            giave=row['price']
        ) for row in rows]
    
    @classmethod
    def tim_theo_id(cls, masuatchieu: int) -> Optional['SuatChieu']:
        """Tìm suất chiếu theo ID"""
        conn = get_db()
        row = conn.execute('SELECT * FROM showtimes WHERE id = ?', (masuatchieu,)).fetchone()
        conn.close()
        
        if row:
            return cls(
                masuatchieu=row['id'],
                maphim=row['movie_id'],
                maphong=row['theater'],
                ngaychieu=row['show_date'],
                giochieu=row['show_time'],
                giave=row['price']
            )
        return None
    
    @classmethod
    def lay_tat_ca(cls) -> List['SuatChieu']:
        """Lấy tất cả suất chiếu"""
        conn = get_db()
        rows = conn.execute('''
            SELECT s.*, m.title FROM showtimes s
            JOIN movies_info m ON s.movie_id = m.id
            ORDER BY s.show_date DESC
        ''').fetchall()
        conn.close()
        
        return [cls(
            masuatchieu=row['id'],
            maphim=row['movie_id'],
            maphong=row['theater'],
            ngaychieu=row['show_date'],
            giochieu=row['show_time'],
            giave=row['price']
        ) for row in rows]
    
    def them_suat_chieu(self) -> int:
        """Thêm suất chiếu mới"""
        conn = get_db()
        cursor = conn.execute(
            'INSERT INTO showtimes (movie_id, theater, show_date, show_time, price) VALUES (?, ?, ?, ?, ?)',
            (self.maphim, self.maphong, self.ngaychieu, self.giochieu, self.giave)
        )
        self.masuatchieu = cursor.lastrowid
        
        # Tạo ghế cho suất chiếu
        rows = ['A', 'B', 'C', 'D', 'E']
        for row in rows:
            for num in range(1, 11):
                conn.execute(
                    'INSERT INTO seats (showtime_id, seat_number, status) VALUES (?, ?, "available")',
                    (self.masuatchieu, f'{row}{num}')
                )
        
        conn.commit()
        conn.close()
        return self.masuatchieu
    
    def xoa_suat_chieu(self) -> bool:
        """Xóa suất chiếu"""
        conn = get_db()
        conn.execute('DELETE FROM seats WHERE showtime_id = ?', (self.masuatchieu,))
        conn.execute('DELETE FROM showtimes WHERE id = ?', (self.masuatchieu,))
        conn.commit()
        conn.close()
        return True
    
    def cap_nhat_suat_chieu(self) -> bool:
        """Cập nhật suất chiếu"""
        conn = get_db()
        conn.execute(
            '''UPDATE showtimes SET movie_id = ?, theater = ?, show_date = ?, 
               show_time = ?, price = ? WHERE id = ?''',
            (self.maphim, self.maphong, self.ngaychieu, self.giochieu, self.giave, self.masuatchieu)
        )
        conn.commit()
        conn.close()
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Chuyển đổi thành dictionary"""
        return {
            'id': self.masuatchieu,
            'movie_id': self.maphim,
            'theater': self.maphong,
            'show_date': self.ngaychieu,
            'show_time': self.giochieu,
            'price': self.giave
        }


# ===== CLASS GHE =====
class Ghe:
    """
    Class Ghế - Ghế ngồi trong phòng chiếu
    Attributes:
        - maghe: string (id)
        - soghe: int (seat_number)
        - trangthai: boolean (status)
        - maphong: string
    Methods:
        + KiemTraTrangThai(): Kiểm tra ghế có trống không
        + DatGhe(): Đặt ghế
        + GiuGheTamThoi(): Giữ ghế tạm thời
        + ThemGhe(): Thêm ghế
        + XoaGhe(): Xóa ghế
        + SuaGhe(): Sửa ghế
    """
    
    def __init__(self, soghe: str, masuatchieu: int, trangthai: str = 'available', maghe: int = None):
        self.maghe = maghe
        self.soghe = soghe
        self.trangthai = trangthai
        self.masuatchieu = masuatchieu
    
    @classmethod
    def lay_theo_suat_chieu(cls, masuatchieu: int) -> List['Ghe']:
        """Lấy tất cả ghế của một suất chiếu"""
        conn = get_db()
        rows = conn.execute(
            'SELECT * FROM seats WHERE showtime_id = ? ORDER BY seat_number',
            (masuatchieu,)
        ).fetchall()
        conn.close()
        
        return [cls(
            maghe=row['id'],
            soghe=row['seat_number'],
            trangthai=row['status'],
            masuatchieu=row['showtime_id']
        ) for row in rows]
    
    @classmethod
    def tim_theo_id(cls, maghe: int) -> Optional['Ghe']:
        """Tìm ghế theo ID"""
        conn = get_db()
        row = conn.execute('SELECT * FROM seats WHERE id = ?', (maghe,)).fetchone()
        conn.close()
        
        if row:
            return cls(
                maghe=row['id'],
                soghe=row['seat_number'],
                trangthai=row['status'],
                masuatchieu=row['showtime_id']
            )
        return None
    
    def kiem_tra_trang_thai(self) -> bool:
        """Kiểm tra ghế có trống không"""
        return self.trangthai == 'available'
    
    def dat_ghe(self) -> bool:
        """Đặt ghế (chuyển trạng thái thành booked)"""
        conn = get_db()
        conn.execute('UPDATE seats SET status = "booked" WHERE id = ?', (self.maghe,))
        conn.commit()
        conn.close()
        self.trangthai = 'booked'
        return True
    
    def giu_ghe_tam_thoi(self) -> bool:
        """Giữ ghế tạm thời"""
        conn = get_db()
        conn.execute('UPDATE seats SET status = "reserved" WHERE id = ?', (self.maghe,))
        conn.commit()
        conn.close()
        self.trangthai = 'reserved'
        return True
    
    def huy_ghe(self) -> bool:
        """Hủy đặt ghế (chuyển về available)"""
        conn = get_db()
        conn.execute('UPDATE seats SET status = "available" WHERE id = ?', (self.maghe,))
        conn.commit()
        conn.close()
        self.trangthai = 'available'
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Chuyển đổi thành dictionary"""
        return {
            'id': self.maghe,
            'seat_number': self.soghe,
            'status': self.trangthai,
            'showtime_id': self.masuatchieu
        }


# ===== CLASS KHACH HANG =====
class KhachHang:
    """
    Class KháchHàng - Khách hàng
    Attributes:
        - maKH: string (id)
        - ten: string (full_name)
        - email: string
        - sdt: int (phone)
        - username: string
        - password: string
    Methods:
        + DatVe(): Đặt vé
        + ThanhToan(): Thanh toán
        + XemLichChieu(): Xem lịch chiếu
        + CapNhatThongTin(): Cập nhật thông tin cá nhân
    """
    
    def __init__(self, username: str, password: str = None, ten: str = None,
                 email: str = None, sdt: str = None, maKH: int = None, is_admin: int = 0):
        self.maKH = maKH
        self.ten = ten
        self.email = email
        self.sdt = sdt
        self.username = username
        self.password = password
        self.is_admin = is_admin
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Mã hóa mật khẩu"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    @classmethod
    def dang_nhap(cls, username: str, password: str) -> Optional['KhachHang']:
        """Đăng nhập khách hàng"""
        conn = get_db()
        user = conn.execute(
            'SELECT * FROM users WHERE username = ? AND password = ?',
            (username, cls.hash_password(password))
        ).fetchone()
        conn.close()
        
        if user:
            return cls(
                maKH=user['id'],
                username=user['username'],
                password=user['password'],
                ten=user['full_name'],
                email=user['email'],
                sdt=user['phone'],
                is_admin=user['is_admin']
            )
        return None
    
    @classmethod
    def dang_ky(cls, username: str, password: str, email: str = None,
                ten: str = None, sdt: str = None) -> Optional['KhachHang']:
        """Đăng ký tài khoản mới"""
        conn = get_db()
        
        # Kiểm tra username đã tồn tại
        existing = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
        if existing:
            conn.close()
            return None
        
        cursor = conn.execute(
            'INSERT INTO users (username, email, password, full_name, phone) VALUES (?, ?, ?, ?, ?)',
            (username, email, cls.hash_password(password), ten, sdt)
        )
        maKH = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return cls(
            maKH=maKH,
            username=username,
            password=cls.hash_password(password),
            ten=ten,
            email=email,
            sdt=sdt
        )
    
    @classmethod
    def tim_theo_id(cls, maKH: int) -> Optional['KhachHang']:
        """Tìm khách hàng theo ID"""
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE id = ?', (maKH,)).fetchone()
        conn.close()
        
        if user:
            return cls(
                maKH=user['id'],
                username=user['username'],
                password=user['password'],
                ten=user['full_name'],
                email=user['email'],
                sdt=user['phone'],
                is_admin=user['is_admin']
            )
        return None
    
    @classmethod
    def lay_tat_ca(cls) -> List['KhachHang']:
        """Lấy danh sách tất cả khách hàng"""
        conn = get_db()
        rows = conn.execute('SELECT * FROM users ORDER BY id').fetchall()
        conn.close()
        
        return [cls(
            maKH=row['id'],
            username=row['username'],
            ten=row['full_name'],
            email=row['email'],
            sdt=row['phone'],
            is_admin=row['is_admin']
        ) for row in rows]
    
    def dat_ve(self, masuatchieu: int, danh_sach_ghe: List[int]) -> List['Ve']:
        """Đặt vé cho khách hàng - có xử lý race condition"""
        danh_sach_ve = []
        suat_chieu = SuatChieu.tim_theo_id(masuatchieu)
        
        if not suat_chieu:
            return []
        
        # Sử dụng một connection duy nhất với transaction để tránh race condition
        conn = get_db()
        conn.isolation_level = 'IMMEDIATE'  # Lock database ngay khi bắt đầu transaction
        
        try:
            for maghe in danh_sach_ghe:
                # Kiểm tra và đặt ghế trong cùng một transaction
                # Cho phép đặt ghế available HOẶC ghế đang được chính user này giữ (held)
                ghe_row = conn.execute('''
                    SELECT * FROM seats 
                    WHERE id = ? AND (status = "available" OR (status = "held" AND held_by = ?))
                ''', (maghe, self.maKH)).fetchone()
                
                if ghe_row:
                    # Cập nhật trạng thái ghế ngay lập tức
                    result = conn.execute('''
                        UPDATE seats 
                        SET status = "booked", held_by = NULL, held_until = NULL 
                        WHERE id = ? AND (status = "available" OR (status = "held" AND held_by = ?))
                    ''', (maghe, self.maKH))
                    
                    # Kiểm tra xem có thực sự cập nhật được không
                    if result.rowcount > 0:
                        # Tạo booking record
                        cursor = conn.execute('''
                            INSERT INTO bookings (user_id, showtime_id, seat_id, seat_number, price, status)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (self.maKH, masuatchieu, ghe_row['id'], ghe_row['seat_number'], suat_chieu.giave, 'confirmed'))
                        
                        ve = Ve(
                            mave=cursor.lastrowid,
                            maghe=ghe_row['seat_number'],
                            masuatchieu=masuatchieu,
                            maKH=self.maKH,
                            giave=suat_chieu.giave
                        )
                        danh_sach_ve.append(ve)
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
        
        return danh_sach_ve
    
    def xem_lich_chieu(self, maphim: int = None) -> List[SuatChieu]:
        """Xem lịch chiếu"""
        if maphim:
            return SuatChieu.lay_theo_phim(maphim)
        return SuatChieu.lay_tat_ca()
    
    def cap_nhat_thong_tin(self, email: str = None, ten: str = None, sdt: str = None) -> bool:
        """Cập nhật thông tin cá nhân"""
        conn = get_db()
        
        if email:
            self.email = email
        if ten:
            self.ten = ten
        if sdt:
            self.sdt = sdt
        
        conn.execute(
            'UPDATE users SET email = ?, full_name = ?, phone = ? WHERE id = ?',
            (self.email, self.ten, self.sdt, self.maKH)
        )
        conn.commit()
        conn.close()
        return True
    
    def doi_mat_khau(self, mat_khau_cu: str, mat_khau_moi: str) -> bool:
        """Đổi mật khẩu"""
        if self.password != self.hash_password(mat_khau_cu):
            return False
        
        conn = get_db()
        conn.execute(
            'UPDATE users SET password = ? WHERE id = ?',
            (self.hash_password(mat_khau_moi), self.maKH)
        )
        conn.commit()
        conn.close()
        self.password = self.hash_password(mat_khau_moi)
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Chuyển đổi thành dictionary"""
        return {
            'id': self.maKH,
            'username': self.username,
            'full_name': self.ten,
            'email': self.email,
            'phone': self.sdt,
            'is_admin': self.is_admin
        }


# ===== CLASS VE =====
class Ve:
    """
    Class Vé - Vé xem phim
    Attributes:
        - mave: string (id)
        - maghe: string (seat_number)
        - masuatchieu: string (showtime_id)
        - maKH: string (user_id)
    Methods:
        + XuatVeDienTu(): Xuất vé điện tử
        + HuyDonDatVe(): Hủy đơn đặt vé
        + XacNhanThanhToan(): Xác nhận thanh toán
        + TaoMa(): Tạo mã vé
    """
    
    def __init__(self, maghe: str, masuatchieu: int, maKH: int,
                 giave: float = 75000, trangthai: str = 'confirmed', mave: int = None):
        self.mave = mave
        self.maghe = maghe
        self.masuatchieu = masuatchieu
        self.maKH = maKH
        self.giave = giave
        self.trangthai = trangthai
        self.thoi_gian_dat = datetime.now()
    
    @classmethod
    def lay_theo_khach_hang(cls, maKH: int) -> List['Ve']:
        """Lấy tất cả vé của khách hàng"""
        conn = get_db()
        rows = conn.execute('''
            SELECT b.*, m.title, m.poster_url, s.theater, s.show_date, s.show_time
            FROM bookings b
            JOIN showtimes s ON b.showtime_id = s.id
            JOIN movies_info m ON s.movie_id = m.id
            WHERE b.user_id = ?
            ORDER BY b.booking_time DESC
        ''', (maKH,)).fetchall()
        conn.close()
        
        return [cls(
            mave=row['id'],
            maghe=row['seat_number'],
            masuatchieu=row['showtime_id'],
            maKH=row['user_id'],
            giave=row['price'],
            trangthai=row['status']
        ) for row in rows]
    
    @classmethod
    def tim_theo_id(cls, mave: int) -> Optional['Ve']:
        """Tìm vé theo ID"""
        conn = get_db()
        row = conn.execute('SELECT * FROM bookings WHERE id = ?', (mave,)).fetchone()
        conn.close()
        
        if row:
            return cls(
                mave=row['id'],
                maghe=row['seat_number'],
                masuatchieu=row['showtime_id'],
                maKH=row['user_id'],
                giave=row['price'],
                trangthai=row['status']
            )
        return None
    
    @classmethod
    def lay_tat_ca(cls) -> List[Dict[str, Any]]:
        """Lấy tất cả vé (cho admin)"""
        conn = get_db()
        rows = conn.execute('''
            SELECT b.*, u.username, m.title, se.seat_number as seat_num, st.show_date
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            JOIN showtimes st ON b.showtime_id = st.id
            JOIN movies_info m ON st.movie_id = m.id
            JOIN seats se ON b.seat_id = se.id
            ORDER BY b.booking_time DESC
        ''').fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def tao_ve(self) -> int:
        """Tạo vé mới"""
        conn = get_db()
        
        # Lấy seat_id từ seat_number
        ghe = conn.execute(
            'SELECT id FROM seats WHERE showtime_id = ? AND seat_number = ?',
            (self.masuatchieu, self.maghe)
        ).fetchone()
        
        cursor = conn.execute('''
            INSERT INTO bookings (user_id, showtime_id, seat_id, seat_number, price, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (self.maKH, self.masuatchieu, ghe['id'] if ghe else None, self.maghe, self.giave, self.trangthai))
        
        self.mave = cursor.lastrowid
        conn.commit()
        conn.close()
        return self.mave
    
    def xuat_ve_dien_tu(self) -> Dict[str, Any]:
        """Xuất thông tin vé điện tử"""
        conn = get_db()
        row = conn.execute('''
            SELECT b.*, m.title, s.theater, s.show_date, s.show_time, u.full_name
            FROM bookings b
            JOIN showtimes s ON b.showtime_id = s.id
            JOIN movies_info m ON s.movie_id = m.id
            JOIN users u ON b.user_id = u.id
            WHERE b.id = ?
        ''', (self.mave,)).fetchone()
        conn.close()
        
        if row:
            return {
                'ma_ve': self.tao_ma(),
                'ten_phim': row['title'],
                'rap': row['theater'],
                'ngay_chieu': row['show_date'],
                'gio_chieu': row['show_time'],
                'ghe': row['seat_number'],
                'gia_ve': row['price'],
                'khach_hang': row['full_name'],
                'trang_thai': row['status']
            }
        return {}
    
    def huy_don_dat_ve(self) -> bool:
        """Hủy đơn đặt vé"""
        conn = get_db()
        booking = conn.execute('SELECT seat_id FROM bookings WHERE id = ?', (self.mave,)).fetchone()
        
        if booking:
            conn.execute('UPDATE bookings SET status = "cancelled" WHERE id = ?', (self.mave,))
            conn.execute('UPDATE seats SET status = "available" WHERE id = ?', (booking['seat_id'],))
            conn.commit()
            self.trangthai = 'cancelled'
        
        conn.close()
        return True
    
    def xac_nhan_thanh_toan(self) -> bool:
        """Xác nhận thanh toán"""
        conn = get_db()
        conn.execute('UPDATE bookings SET status = "paid" WHERE id = ?', (self.mave,))
        conn.commit()
        conn.close()
        self.trangthai = 'paid'
        return True
    
    def tao_ma(self) -> str:
        """Tạo mã vé"""
        return f"VE{self.mave:06d}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Chuyển đổi thành dictionary"""
        return {
            'id': self.mave,
            'seat_number': self.maghe,
            'showtime_id': self.masuatchieu,
            'user_id': self.maKH,
            'price': self.giave,
            'status': self.trangthai
        }


# ===== CLASS DAT CHO =====
class DatCho:
    """
    Class ĐặtChỗ - Thông tin đặt chỗ
    Attributes:
        - madat: string
        - maghe: string
        - masuatchieu: string
        - maKH: string
        - demnguoc: datetime (thời gian giữ chỗ)
    Methods:
        + HuyDat(): Hủy đặt chỗ
    """
    
    def __init__(self, maghe: int, masuatchieu: int, maKH: int, madat: int = None):
        self.madat = madat
        self.maghe = maghe
        self.masuatchieu = masuatchieu
        self.maKH = maKH
        self.demnguoc = datetime.now()
    
    def giu_cho(self) -> bool:
        """Giữ chỗ tạm thời"""
        ghe = Ghe.tim_theo_id(self.maghe)
        if ghe and ghe.kiem_tra_trang_thai():
            ghe.giu_ghe_tam_thoi()
            return True
        return False
    
    def huy_dat(self) -> bool:
        """Hủy đặt chỗ"""
        ghe = Ghe.tim_theo_id(self.maghe)
        if ghe:
            ghe.huy_ghe()
            return True
        return False
    
    def xac_nhan_dat(self) -> Optional[Ve]:
        """Xác nhận đặt chỗ và tạo vé"""
        ghe = Ghe.tim_theo_id(self.maghe)
        suat_chieu = SuatChieu.tim_theo_id(self.masuatchieu)
        
        if ghe and suat_chieu:
            ve = Ve(
                maghe=ghe.soghe,
                masuatchieu=self.masuatchieu,
                maKH=self.maKH,
                giave=suat_chieu.giave
            )
            ve.tao_ve()
            ghe.dat_ghe()
            return ve
        return None
