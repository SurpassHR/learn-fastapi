import sqlite3
from typing import Optional
from fastapi import FastAPI, Response, status
from pydantic import BaseModel

app = FastAPI()

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
    conn = sqlite3.connect("todos.db")
    return conn

def close_db_conn(conn: sqlite3.Connection):
    conn.commit()
    conn.close()

@app.post("/users/{user_id}")
def add_user(user_id: str):
    if user_id in todos:
        return Response(status_code=status.HTTP_409_CONFLICT)
    todos[user_id] = []
    return Response(status_code=status.HTTP_201_CREATED)

@app.get("/users")
def get_users():
    return {"users": list(todos.keys())}

class TodoItem(BaseModel):
    title: Optional[str] = None
    item: Optional[str] = None
    prioity: Optional[str] = None

@app.get("/users/{user_id}/todos")
def read_todos(user_id):
    if user_id not in todos:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    return {"todos": todos[user_id]}

@app.post("/users/{user_id}/todos")
def add_todo(user_id: str, todo: TodoItem):
    if user_id not in todos:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    todos[user_id].append(todo.model_dump())
    return Response(status_code=status.HTTP_202_ACCEPTED)

@app.delete("/users/{user_id}/todos/{id}")
def delete_todo(user_id: str, id: int):
    if user_id not in todos:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    if id < 0 or id >= len(todos[user_id]):
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    todos[user_id].pop(id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@app.patch("/users/{user_id}/todos/{id}")
def update_todo(user_id: str, id: int, todo: TodoItem):
    if user_id not in todos:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    if id < 0 or id >= len(todos[user_id]):
        return Response(status_code=status.HTTP_404_NOT_FOUND)

    current = todos[user_id][id]
    if todo.title is not None:
        current["title"] = todo.title
    if todo.item is not None:
        current["item"] = todo.item
    if todo.prioity is not None:
        current["prioity"] = todo.prioity

    return Response(status_code=status.HTTP_202_ACCEPTED)

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
        done INTEGER,
        priority TEXT,
        created_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    close_db_conn(conn)
