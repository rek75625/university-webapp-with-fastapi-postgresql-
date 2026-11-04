# from datetime import date
# from fastapi import FastAPI
# from fastapi.testclient import TestClient
# from pydantic import BaseModel, EmailStr, Field
# from starlette.testclient import TestClient as TestClient

# app = FastAPI()

# class Address(BaseModel):
#     city: str
#     country: str = "UK"                                     # default value

# class Enrolment(BaseModel):
#     name: str = Field(min_length=2, max_length=50)
#     email: EmailStr                                        # must look like an email
#     age: int = Field(ge=16, le=100)
#     course: str
#     start_date: date | None = None                         # optional
#     address: Address                                       # a nested model

# @app.post("/enrolments")
# def create_enrolment(enrolment: Enrolment):                # a model argument = the request body
#     data = enrolment.model_dump()
#     return {"message": f"Welcome to {enrolment.course}, {enrolment.name}!", "received": data}

# client = TestClient(app)
# good = {"name": "Priya", "email": "priya@example.com", "age": "21", "course": "FastAPI",
#         "start_date": "2026-11-02", "address": {"city": "Leeds"}}
# r = client.post("/enrolments", json=good)
# print(r.status_code, r.json())

# bad = {"name": "P", "email": "not-an-email", "age": 12, "address": {}}
# r = client.post("/enrolments", json=bad)
# print("\n", r.status_code, sep="")
# for err in r.json()["detail"]:
#     print(f"  {' -> '.join(map(str, err['loc'])):22} {err['msg']}")
# from fastapi import FastAPI, HTTPException, Request, status
# from fastapi.responses import JSONResponse
# from fastapi.testclient import TestClient
# from pydantic import BaseModel, EmailStr

# app = FastAPI()

# class UserIn(BaseModel):                     # what the client SENDS
#     username: str
#     email: EmailStr
#     password: str

# class UserOut(BaseModel):                    # what the API RETURNS: no password!
#     id: int
#     username: str
#     email: EmailStr

# users = {}

# class UsernameTaken(Exception):              # our own error type
#     def __init__(self, username: str):
#         self.username = username

# @app.exception_handler(UsernameTaken)
# def username_taken_handler(request: Request, exc: UsernameTaken):
#     return JSONResponse(status_code=409,
#                         content={"error": "username_taken",
#                                  "message": f"'{exc.username}' is already registered"})

# @app.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
# def create_user(user: UserIn):
#     if any(u["username"] == user.username for u in users.values()):
#         raise UsernameTaken(user.username)
#     new_id = len(users) + 1
#     users[new_id] = {"id": new_id, **user.model_dump()}   # stored WITH the password
#     return users[new_id]                                    # response_model filters it out

# @app.get("/users/{user_id}", response_model=UserOut)
# def get_user(user_id: int):
#     if user_id not in users:
#         raise HTTPException(status_code=404, detail=f"User {user_id} not found",
#                             headers={"X-Error": "missing-user"})
#     return users[user_id]

# client = TestClient(app)
# body = {"username": "sam", "email": "sam@example.com", "password": "s3cret!"}
# r = client.post("/users", json=body);  
# print(r.status_code, r.json())
# r = client.post("/users", json=body);  
# print(r.status_code, r.json())
# r = client.get("/users/1");            
# print(r.status_code, r.json())
# r = client.get("/users/7");            
# print(r.status_code, r.json(), "| header:", r.headers["x-error"])
# print("Stored internally:", users[1])

from fastapi import FastAPI, HTTPException, Response, status
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

app = FastAPI(title="Tasks API")

class TaskCreate(BaseModel):                 # for POST and PUT: everything required
    title: str = Field(min_length=1, max_length=100)
    priority: int = Field(default=2, ge=1, le=3)
    done: bool = False

class TaskUpdate(BaseModel):                 # for PATCH: everything optional
    title: str | None = Field(default=None, min_length=1, max_length=100)
    priority: int | None = Field(default=None, ge=1, le=3)
    done: bool | None = None

class Task(TaskCreate):                      # what we return: adds the id
    id: int

tasks: dict[int, Task] = {}
next_id = 1

def find(task_id: int) -> Task:
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks[task_id]

@app.post("/tasks", response_model=Task, status_code=status.HTTP_201_CREATED,tags=['Posting a Task'])   # Create
def create_task(data: TaskCreate):
    global next_id
    task = Task(id=next_id, **data.model_dump())
    tasks[next_id] = task
    next_id += 1
    return task

@app.get("/tasks", response_model=list[Task], tags=['Reading Tasks'])                                    # Read all
def list_tasks(done: bool | None = None):
    return [t for t in tasks.values() if done is None or t.done == done]

@app.get("/tasks/{task_id}", response_model=Task, tags=['Reading Tasks'])                                # Read one
def get_task(task_id: int):
    return find(task_id)

@app.put("/tasks/{task_id}", response_model=Task, tags=['Updating Tasks'])                                # Replace
def replace_task(task_id: int, data: TaskCreate):
    find(task_id)
    tasks[task_id] = Task(id=task_id, **data.model_dump())
    return tasks[task_id]

@app.patch("/tasks/{task_id}", response_model=Task, tags=['Updating Tasks'])                              # Update some fields
def update_task(task_id: int, data: TaskUpdate):
    task = find(task_id)
    changes = data.model_dump(exclude_unset=True)       # only the fields the client sent
    tasks[task_id] = task.model_copy(update=changes)
    return tasks[task_id]

@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, tags=['Deleting Tasks'])          # Delete
def delete_task(task_id: int):
    find(task_id)
    del tasks[task_id]
    return Response(status_code=status.HTTP_204_NO_CONTENT)

client = TestClient(app)
steps = [("post", "/tasks", {"title": "Finish Module 5", "priority": 1}),
         ("post", "/tasks", {"title": "Revise Pydantic"}),
         ("patch", "/tasks/1", {"done": True}),
         ("get", "/tasks?done=false", None),
         ("put", "/tasks/2", {"title": "Revise Pydantic models", "priority": 3}),
         ("delete", "/tasks/1", None),
         ("get", "/tasks/1", None),
         ("get", "/tasks", None)]
for method, url, body in steps:
    r = client.request(method.upper(), url, json=body)
    print(f"{method.upper():6} {url:18} {r.status_code}  {r.json() if r.content else '(no body)'}")