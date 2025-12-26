import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

# ================== CONFIG ==================
st.set_page_config(page_title="Task Manager", layout="wide")
DB = "task_manager.db"

# ================== DB ==================
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

    # admin + 4 member
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

# ================== AUTH ==================
def login():
    st.sidebar.header("Dang nhap")
    user = st.sidebar.text_input("Username")
    pwd = st.sidebar.text_input("Password", type="password")

    if st.sidebar.button("Login"):
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
            st.sidebar.error("Sai tai khoan")

def logout():
    st.sidebar.button("Logout", on_click=lambda: st.session_state.clear())

# ================== TASK ==================
def add_task():
    st.subheader("Them cong viec")
    with st.form("add_task"):
        title = st.text_input("Tieu de")
        desc = st.text_area("Mo ta")
        assigned = st.selectbox("Giao cho", users)
        priority = st.selectbox("Uu tien", ["Thap", "Trung binh", "Cao"])
        deadline = st.date_input("Deadline", date.today())
        submit = st.form_submit_button("Them")

        if submit:
            conn = get_conn()
            conn.execute("""
                INSERT INTO tasks 
                (title, description, assigned_to, priority, status, deadline, created_at)
                VALUES (?, ?, ?, ?, 'Chua lam', ?, ?)
            """, (title, desc, assigned, priority, deadline, datetime.now()))
            conn.commit()
            st.success("Da them cong viec")
            st.rerun()

def update_task(task_id, status):
    conn = get_conn()
    conn.execute("UPDATE tasks SET status=? WHERE id=?", (status, task_id))
    conn.commit()

# ================== MAIN ==================
st.title("📝 Cong cu theo doi cong viec")

if "user" not in st.session_state:
    login()
    st.stop()

logout()
st.sidebar.success(f"Xin chao: {st.session_state.user}")

conn = get_conn()
users = pd.read_sql("SELECT username FROM users", conn)["username"].tolist()

# ================== FILTER ==================
st.sidebar.header("Bo loc")
filter_user = st.sidebar.selectbox("Nguoi thuc hien", ["Tat ca"] + users)
filter_status = st.sidebar.selectbox(
    "Trang thai",
    ["Tat ca", "Chua lam", "Dang lam", "Hoan thanh", "Tre han"]
)

query = "SELECT * FROM tasks"
params = []

if filter_user != "Tat ca":
    query += " WHERE assigned_to=?"
    params.append(filter_user)

df = pd.read_sql(query, conn, params=params)

if filter_status != "Tat ca":
    df = df[df["status"] == filter_status]

today = date.today().isoformat()
df.loc[(df["status"] != "Hoan thanh") & (df["deadline"] < today), "status"] = "Tre han"

# ================== ADMIN ==================
if st.session_state.role == "admin":
    add_task()

# ================== TASK LIST ==================
st.subheader("Danh sach cong viec")

if df.empty:
    st.info("Chua co cong viec")
else:
    for _, r in df.iterrows():
        with st.expander(f"[{r['status']}] {r['title']} - {r['assigned_to']}"):
            st.write(r["description"])
            st.write("Deadline:", r["deadline"])
            if r["assigned_to"] == st.session_state.user or st.session_state.role == "admin":
                new_status = st.selectbox(
                    "Cap nhat trang thai",
                    ["Chua lam", "Dang lam", "Hoan thanh"],
                    index=["Chua lam", "Dang lam", "Hoan thanh"].index(
                        r["status"] if r["status"] != "Tre han" else "Dang lam"
                    ),
                    key=f"status_{r['id']}"
                )
                if st.button("Luu", key=f"save_{r['id']}"):
                    update_task(r["id"], new_status)
                    st.rerun()
