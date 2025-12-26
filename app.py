import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

st.set_page_config(page_title="Công cụ theo dõi công việc", layout="wide")
DB = "task_manager.db"

# ================= DATABASE =================
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

    default_users = [
        ("admin", "123", "admin"),
        ("user1", "123", "member"),
        ("user2", "123", "member"),
        ("user3", "123", "member"),
        ("user4", "123", "member"),
    ]

    for u in default_users:
        c.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?)", u)

    conn.commit()
    conn.close()

init_db()

# ================= AUTH =================
def login():
    st.sidebar.header("Đăng nhập")
    u = st.sidebar.text_input("Tên đăng nhập")
    p = st.sidebar.text_input("Mật khẩu", type="password")

    if st.sidebar.button("Đăng nhập"):
        conn = get_conn()
        df = pd.read_sql(
            "SELECT * FROM users WHERE username=? AND password=?",
            conn,
            params=(u, p)
        )
        if not df.empty:
            st.session_state.user = u
            st.session_state.role = df.iloc[0]["role"]
            st.rerun()
        else:
            st.sidebar.error("Sai tài khoản hoặc mật khẩu")

def logout():
    st.sidebar.button("Đăng xuất", on_click=lambda: st.session_state.clear())

# ================= USER MANAGEMENT =================
def user_management():
    st.subheader("👤 Quản lý người dùng")
    conn = get_conn()
    users_df = pd.read_sql("SELECT username, role FROM users", conn)

    st.dataframe(users_df, use_container_width=True)

    st.markdown("### ➕ Thêm người dùng")
    with st.form("add_user"):
        u = st.text_input("Tên đăng nhập")
        p = st.text_input("Mật khẩu")
        r = st.selectbox("Vai trò", ["member", "admin"])
        if st.form_submit_button("Thêm"):
            conn.execute(
                "INSERT INTO users VALUES (?, ?, ?)", (u, p, r)
            )
            conn.commit()
            st.success("Đã thêm user")
            st.rerun()

    st.markdown("### 🔐 Đổi mật khẩu")
    with st.form("change_pass"):
        u = st.selectbox("Chọn user", users_df["username"])
        p = st.text_input("Mật khẩu mới")
        if st.form_submit_button("Đổi mật khẩu"):
            conn.execute(
                "UPDATE users SET password=? WHERE username=?", (p, u)
            )
            conn.commit()
            st.success("Đã đổi mật khẩu")

    st.markdown("### ❌ Xóa user")
    u = st.selectbox("Chọn user để xóa", users_df["username"])
    if st.button("Xóa user"):
        conn.execute("DELETE FROM users WHERE username=?", (u,))
        conn.commit()
        st.warning("Đã xóa user")
        st.rerun()

# ================= TASK =================
def create_task(users):
    st.subheader("➕ Tạo công việc")
    with st.form("create_task"):
        title = st.text_input("Tiêu đề")
        desc = st.text_area("Mô tả")
        assign = st.selectbox("Giao cho", users)
        pr = st.selectbox("Ưu tiên", ["Thấp", "Trung bình", "Cao"])
        dl = st.date_input("Hạn hoàn thành", date.today())
        if st.form_submit_button("Tạo"):
            conn = get_conn()
            conn.execute("""
                INSERT INTO tasks 
                (title, description, assigned_to, priority, status, deadline, created_at)
                VALUES (?, ?, ?, ?, 'Chưa làm', ?, ?)
            """, (title, desc, assign, pr, dl, datetime.now()))
            conn.commit()
            st.success("Đã tạo công việc")

def manage_tasks():
    st.subheader("📋 Quản lý công việc")
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM tasks", conn)

    if st.session_state.role != "admin":
        df = df[df["assigned_to"] == st.session_state.user]

    today = date.today().isoformat()
    df.loc[(df["status"] != "Hoàn thành") & (df["deadline"] < today), "status"] = "Trễ hạn"

    for _, r in df.iterrows():
        with st.expander(f"[{r['status']}] {r['title']} – {r['assigned_to']}"):
            st.write(r["description"])
            st.write("Hạn:", r["deadline"])
            if st.session_state.role == "admin" or r["assigned_to"] == st.session_state.user:
                s = st.selectbox(
                    "Cập nhật trạng thái",
                    ["Chưa làm", "Đang làm", "Hoàn thành"],
                    index=["Chưa làm", "Đang làm", "Hoàn thành"].index(
                        r["status"] if r["status"] != "Trễ hạn" else "Đang làm"
                    ),
                    key=f"s_{r['id']}"
                )
                if st.button("Lưu", key=f"b_{r['id']}"):
                    conn.execute(
                        "UPDATE tasks SET status=? WHERE id=?", (s, r["id"])
                    )
                    conn.commit()
                    st.rerun()

# ================= DASHBOARD =================
def dashboard():
    st.subheader("📊 Dashboard")
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM tasks", conn)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Tổng việc", len(df))
    col2.metric("Đang làm", len(df[df["status"] == "Đang làm"]))
    col3.metric("Hoàn thành", len(df[df["status"] == "Hoàn thành"]))
    col4.metric("Trễ hạn", len(df[df["status"] == "Trễ hạn"]))

    st.markdown("### Công việc theo người")
    st.bar_chart(df["assigned_to"].value_counts())

# ================= MAIN =================
st.title("📝 Công cụ theo dõi công việc")

if "user" not in st.session_state:
    login()
    st.stop()

logout()
st.sidebar.success(f"Xin chào: {st.session_state.user}")

conn = get_conn()
users = pd.read_sql("SELECT username FROM users", conn)["username"].tolist()

tabs = st.tabs(["➕ Tạo công việc", "📋 Quản lý công việc", "📊 Dashboard", "👤 Người dùng"])

if st.session_state.role == "admin":
    with tabs[0]:
        create_task(users)
else:
    with tabs[0]:
        st.info("Chỉ admin được tạo công việc")

with tabs[1]:
    manage_tasks()

with tabs[2]:
    dashboard()

if st.session_state.role == "admin":
    with tabs[3]:
        user_management()
else:
    with tabs[3]:
        st.warning("Bạn không có quyền truy cập")
