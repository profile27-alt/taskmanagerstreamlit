import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

# ================== CẤU HÌNH ==================
st.set_page_config(page_title="Công cụ theo dõi công việc", layout="wide")
DB = "task_manager.db"

# ================== DATABASE ==================
def get_conn():
    return sqlite3.connect(DB, check_same_thread=False)

def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT,
        role TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        description TEXT,
        assigned_to TEXT,
        priority TEXT,
        status TEXT,
        deadline TEXT,
        created_at TEXT
    )
    """)

    users = [
        ("admin", "123", "admin"),
        ("user1", "123", "member"),
        ("user2", "123", "member"),
        ("user3", "123", "member"),
        ("user4", "123", "member"),
    ]

    for u in users:
        c.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?)", u)

    conn.commit()
    conn.close()

init_db()

# ================== ĐĂNG NHẬP ==================
def login():
    st.sidebar.header("Đăng nhập")
    user = st.sidebar.text_input("Tên đăng nhập")
    pwd = st.sidebar.text_input("Mật khẩu", type="password")

    if st.sidebar.button("Đăng nhập"):
        conn = get_conn()
        df = pd.read_sql(
            "SELECT * FROM users WHERE username=? AND password=?",
            conn,
            params=(user, pwd)
        )
        if not df.empty:
            st.session_state.user = user
            st.session_state.role = df.iloc[0]["role"]
            st.rerun()
        else:
            st.sidebar.error("Sai tên đăng nhập hoặc mật khẩu")

def logout():
    st.sidebar.button("Đăng xuất", on_click=lambda: st.session_state.clear())

# ================== CÔNG VIỆC ==================
def add_task(users):
    st.subheader("Thêm công việc")
    with st.form("add_task"):
        title = st.text_input("Tiêu đề")
        desc = st.text_area("Mô tả công việc")
        assigned = st.selectbox("Giao cho", users)
        priority = st.selectbox("Mức độ ưu tiên", ["Thấp", "Trung bình", "Cao"])
        deadline = st.date_input("Hạn hoàn thành", date.today())
        submit = st.form_submit_button("Thêm công việc")

        if submit:
            conn = get_conn()
            conn.execute("""
                INSERT INTO tasks 
                (title, description, assigned_to, priority, status, deadline, created_at)
                VALUES (?, ?, ?, ?, 'Chưa làm', ?, ?)
            """, (title, desc, assigned, priority, deadline, datetime.now()))
            conn.commit()
            st.success("Đã thêm công việc")
            st.rerun()

def update_task(task_id, status):
    conn = get_conn()
    conn.execute("UPDATE tasks SET status=? WHERE id=?", (status, task_id))
    conn.commit()

# ================== GIAO DIỆN CHÍNH ==================
st.title("📝 Công cụ theo dõi công việc")

if "user" not in st.session_state:
    login()
    st.stop()

logout()
st.sidebar.success(f"Xin chào: {st.session_state.user}")

conn = get_conn()
users = pd.read_sql("SELECT username FROM users", conn)["username"].tolist()

# ================== BỘ LỌC ==================
st.sidebar.header("Bộ lọc")
filter_user = st.sidebar.selectbox("Người thực hiện", ["Tất cả"] + users)
filter_status = st.sidebar.selectbox(
    "Trạng thái",
    ["Tất cả", "Chưa làm", "Đang làm", "Hoàn thành", "Trễ hạn"]
)

query = "SELECT * FROM tasks"
params = []

if filter_user != "Tất cả":
    query += " WHERE assigned_to=?"
    params.append(filter_user)

df = pd.read_sql(query, conn, params=params)

if filter_status != "Tất cả":
    df = df[df["status"] == filter_status]

today = date.today().isoformat()
df.loc[(df["status"] != "Hoàn thành") & (df["deadline"] < today), "status"] = "Trễ hạn"

# ================== ADMIN ==================
if st.session_state.role == "admin":
    add_task(users)

# ================== DANH SÁCH ==================
st.subheader("Danh sách công việc")

if df.empty:
    st.info("Chưa có công việc nào")
else:
    for _, r in df.iterrows():
        with st.expander(f"[{r['status']}] {r['title']} – {r['assigned_to']}"):
            st.write("📌 **Mô tả:**", r["description"])
            st.write("⏰ **Hạn hoàn thành:**", r["deadline"])
            st.write("🔥 **Ưu tiên:**", r["priority"])

            if r["assigned_to"] == st.session_state.user or st.session_state.role == "admin":
                new_status = st.selectbox(
                    "Cập nhật trạng thái",
                    ["Chưa làm", "Đang làm", "Hoàn thành"],
                    index=["Chưa làm", "Đang làm", "Hoàn thành"].index(
                        r["status"] if r["status"] != "Trễ hạn" else "Đang làm"
                    ),
                    key=f"status_{r['id']}"
                )
                if st.button("Lưu", key=f"save_{r['id']}"):
                    update_task(r["id"], new_status)
                    st.rerun()
