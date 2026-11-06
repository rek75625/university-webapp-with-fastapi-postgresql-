import os
from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlmodel import Field, Session, SQLModel, create_engine, select

# ---------- 1. A table, described as a model ----------
class StudentBase(SQLModel):
    name: str = Field(index=True, min_length=2)
    course: str
    score: int = Field(default=0, ge=0, le=100)

class Student(StudentBase, table=True):         # table=True -> a real database table
    id: int | None = Field(default=None, primary_key=True)

class StudentCreate(StudentBase):               # what clients send
    pass

# ---------- 2. Connect to a SQLite database file ----------
if os.path.exists("school.db"):
    os.remove("school.db")                      # start fresh for this demo
engine = create_engine("sqlite:///school.db", connect_args={"check_same_thread": False})
SQLModel.metadata.create_all(engine)            # create the tables

def get_session():                              # one session per request (Module 6)
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]
app = FastAPI()

@app.post("/students", response_model=Student, status_code=201)
def create_student(data: StudentCreate, session: SessionDep):
    student = Student.model_validate(data)
    session.add(student)
    session.commit()                            # save to the database
    session.refresh(student)                    # load the new id
    return student

@app.get("/students", response_model=list[Student])
def list_students(session: SessionDep, course: str | None = None, min_score: int = 0):
    query = select(Student).where(Student.score >= min_score)
    if course:
        query = query.where(Student.course == course)
    return session.exec(query.order_by(Student.score.desc())).all()

@app.delete("/students/{student_id}", status_code=204)
def delete_student(student_id: int, session: SessionDep):
    student = session.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    session.delete(student)
    session.commit()

client = TestClient(app)
for s in [{"name": "Priya", "course": "FastAPI", "score": 88},
          {"name": "Sam", "course": "spaCy", "score": 72},
          {"name": "Aisha", "course": "FastAPI", "score": 95}]:
    print(client.post("/students", json=s).json())
print("FastAPI students, highest first:", client.get("/students?course=FastAPI").json())
print("Delete 2:", client.delete("/students/2").status_code,
      "| delete 2 again:", client.delete("/students/2").status_code)

# ---------- 3. The data really is in the database file ----------
with Session(engine) as session:
    print("Rows in school.db:", [(s.id, s.name) for s in session.exec(select(Student)).all()])