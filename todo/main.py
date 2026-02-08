import sqlite3
from typing import Optional
from fastapi import FastAPI, Response, status
from pydantic import BaseModel

app = FastAPI()
db_name = "todos.db"

todos = {
    "user1": [
        {"title": "买牛奶", "done": False, "priority": "high"},
        {"title": "写报告", "done": True, "priority": "low"}
    ],
    "user2": [
        {"title": "运动", "done": False, "priority": "medium"}
    ]
}

def conn_db()->sqlite3.Connection:
    conn = sqlite3.connect(db_name)
    return conn

def close_db_conn(conn: sqlite3.Connection):
    conn.commit()
    conn.close()

@app.post("/users/{user_id}")
def add_user(user_id: str):
    conn = conn_db()
    cur = conn.cursor()

    # 检查是否存在
    cur.execute("SELECT 1 FROM users WHERE id=?", (user_id,))
    if cur.fetchone():
        conn.close()
        return Response(status_code=status.HTTP_409_CONFLICT)

    cur.execute(
        "INSERT INTO users (id, created_at) VALUES (?, datetime('now'))",
        (user_id,)
    )
    conn.commit()
    conn.close()

    return Response(status_code=status.HTTP_201_CREATED)


@app.get("/users")
def get_users():
    conn = conn_db()
    cur = conn.cursor()

    cur.execute("SELECT id FROM users")
    rows = cur.fetchall()
    conn.close()

    return {"users": [r[0] for r in rows]}


class TodoItem(BaseModel):
    title: Optional[str] = None
    item: Optional[str] = None
    prioity: Optional[str] = None

@app.get("/users/{user_id}/todos")
def read_todos(user_id: str):
    conn = conn_db()
    cur = conn.cursor()

    # 用户不存在
    cur.execute("SELECT 1 FROM users WHERE id=?", (user_id,))
    if cur.fetchone() is None:
        conn.close()
        return Response(status_code=status.HTTP_404_NOT_FOUND)

    cur.execute("""
        SELECT id, title, item, prioity
        FROM todos WHERE user_id=?
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()

    todos = [
        {"id": r[0], "title": r[1], "item": r[2], "prioity": r[3]}
        for r in rows
    ]

    return {"todos": todos}


@app.post("/users/{user_id}/todos")
def add_todo(user_id: str, todo: TodoItem):
    conn = conn_db()
    cur = conn.cursor()

    cur.execute("SELECT 1 FROM users WHERE id=?", (user_id,))
    if cur.fetchone() is None:
        conn.close()
        return Response(status_code=status.HTTP_404_NOT_FOUND)

    cur.execute("""
        INSERT INTO todos (user_id, title, item, prioity, created_at)
        VALUES (?, ?, ?, ?, datetime('now'))
    """, (user_id, todo.title, todo.item, todo.prioity))

    conn.commit()
    conn.close()

    return Response(status_code=status.HTTP_202_ACCEPTED)

@app.delete("/users/{user_id}/todos/{id}")
def delete_todo(user_id: str, id: int):
    conn = conn_db()
    cur = conn.cursor()

    # 用户不存在
    cur.execute("SELECT 1 FROM users WHERE id=?", (user_id,))
    if cur.fetchone() is None:
        conn.close()
        return Response(status_code=status.HTTP_404_NOT_FOUND)

    # todo 是否存在
    cur.execute("SELECT 1 FROM todos WHERE id=? AND user_id=?", (id, user_id))
    if cur.fetchone() is None:
        conn.close()
        return Response(status_code=status.HTTP_404_NOT_FOUND)

    cur.execute("DELETE FROM todos WHERE id=? AND user_id=?", (id, user_id))
    conn.commit()
    conn.close()

    return Response(status_code=status.HTTP_204_NO_CONTENT)

@app.patch("/users/{user_id}/todos/{id}")
def update_todo(user_id: str, id: int, todo: TodoItem):
    conn = conn_db()
    cur = conn.cursor()

    # 用户不存在
    cur.execute("SELECT 1 FROM users WHERE id=?", (user_id,))
    if cur.fetchone() is None:
        conn.close()
        return Response(status_code=status.HTTP_404_NOT_FOUND)

    # 获取当前 todo
    cur.execute("""
        SELECT title, item, prioity
        FROM todos WHERE id=? AND user_id=?
    """, (id, user_id))
    row = cur.fetchone()

    if row is None:
        conn.close()
        return Response(status_code=status.HTTP_404_NOT_FOUND)

    title = todo.title if todo.title is not None else row[0]
    item = todo.item if todo.item is not None else row[1]
    prioity = todo.prioity if todo.prioity is not None else row[2]

    cur.execute("""
        UPDATE todos
        SET title=?, item=?, prioity=?
        WHERE id=? AND user_id=?
    """, (title, item, prioity, id, user_id))

    conn.commit()
    conn.close()

    return Response(status_code=status.HTTP_202_ACCEPTED)

import sqlite3

def init_db():
    conn = conn_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS todos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        title TEXT,
        item TEXT,
        prioity TEXT,
        created_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )