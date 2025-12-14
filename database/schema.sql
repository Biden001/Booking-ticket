-- HUY CINEMA - Database Schema theo Class Diagram
-- SQLite Version

-- ===== BẢNG USERS (Khách hàng + Admin) =====
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,           -- username
    email TEXT,                               -- email
    password TEXT NOT NULL,                   -- password (hashed)
    full_name TEXT,                           -- ten
    phone TEXT,                               -- sdt
    is_admin INTEGER DEFAULT 0,               -- phân biệt Admin/KhachHang
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ===== BẢNG PHIM (Movies) =====
CREATE TABLE IF NOT EXISTS movies_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,    -- maphim
    title TEXT NOT NULL,                      -- tenphim
    genre TEXT,                               -- theloai
    duration INTEGER,                         -- thoiluong
    poster_url TEXT,                          -- poster
    trailer_url TEXT,                         -- trailer
    description TEXT,                         -- tomtat
    director TEXT,                            -- daodien
    cast_members TEXT                         -- dienvien
);

-- ===== BẢNG PHÒNG CHIẾU (Theater) =====
CREATE TABLE IF NOT EXISTS theaters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                       -- maphong (Rạp 1, Rạp 2, etc.)
    seat_rows INTEGER DEFAULT 5,              -- soghengoi
    seats_per_row INTEGER DEFAULT 10,         -- soluongghe / row
    total_seats INTEGER DEFAULT 50            -- soluongghe total
);

-- ===== BẢNG SUẤT CHIẾU (Showtimes) =====
CREATE TABLE IF NOT EXISTS showtimes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,    -- masuatchieu
    movie_id INTEGER,                         -- maphim
    theater TEXT,                             -- maphong
    show_date TEXT,                           -- ngaychieu
    show_time TEXT,                           -- giochieu
    price REAL DEFAULT 75000,                 -- giave
    FOREIGN KEY (movie_id) REFERENCES movies_info(id) ON DELETE CASCADE
);

-- ===== BẢNG GHẾ (Seats) =====
CREATE TABLE IF NOT EXISTS seats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,    -- maghe
    showtime_id INTEGER,                      -- liên kết suất chiếu
    seat_number TEXT,                         -- soghe (A1, A2, B1, etc.)
    status TEXT DEFAULT 'available',          -- trangthai (available, reserved, booked)
    FOREIGN KEY (showtime_id) REFERENCES showtimes(id) ON DELETE CASCADE
);

-- ===== BẢNG ĐẶT VÉ / VÉ (Bookings/Tickets) =====
CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,    -- mave / madat
    user_id INTEGER,                          -- maKH
    showtime_id INTEGER,                      -- masuatchieu
    seat_id INTEGER,                          -- maghe (reference)
    seat_number TEXT,                         -- maghe (display)
    price REAL,                               -- giave
    status TEXT DEFAULT 'confirmed',          -- trangthai (confirmed, cancelled, paid)
    booking_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- demnguoc / thời gian đặt
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (showtime_id) REFERENCES showtimes(id) ON DELETE CASCADE,
    FOREIGN KEY (seat_id) REFERENCES seats(id) ON DELETE SET NULL
);