from fastapi import APIRouter , HTTPException, Depends, Body, status
from sqlalchemy import select, join, update, text
from sqlalchemy.orm import Session

from models.table_data import Task, Person
from schemas.Datatypes import UserCreate, UserResponse,UserLogin, TaskCreate, TaskResponse, UserTaskResponse
from Scripts.model import generate_sql
from Access.tokens import create_access_token, get_users, admin_required
from database import get_database

from base import SessionLocal
from jose import JWTError, jwt #json token generation
from datetime import datetime, timedelta
from fastapi.security import HTTPBearer
from typing import Annotated, List

router = APIRouter()

# It offers the user to login to the website and generate token
@router.post("/login", tags = ["Sign up"])
def login(newuser : UserLogin, db: Session = Depends(get_database)):
    user = db.query(Person).filter(Person.email == newuser.email).first()
    if not user or not newuser.password==user.password:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )
    access_token = create_access_token(data={"sub": user.email, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}

#User Section
# Create a new user
@router.post("/users/", response_model=UserResponse, tags = ["User managementation"])
def create_user(Datatypes: UserCreate, db: Session = Depends(get_database), admin = Depends(admin_required)):
    new_user = Person(username=Datatypes.username, email=Datatypes.email, password=Datatypes.password, role=Datatypes.role)
    new_user.created_by = admin.user_id
    db.add(new_user)
    try:
        db.commit()
        db.refresh(new_user)
        return new_user
    except Exception as e:
        db.rollback()
        print(e)
        raise HTTPException(status_code=400, detail="Email already exists")

# Read all users ###
@router.get("/users/", response_model=list[UserResponse], tags = ["User managementation"])
def get_users(db: Session = Depends(get_database), data = Depends(get_users)):
    return db.query(Person).all()

# Update a user
@router.put("/users/{user_id}", response_model=UserResponse, tags = ["User managementation"])
def update_user(user_id: int, user: UserCreate, db: Session = Depends(get_database), admin = Depends(admin_required), data = Depends(get_users)):
    existing_user = db.query(Person).filter(Person.id == user_id).first()
    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")

    existing_user.username = user.username
    existing_user.email = user.email
    existing_user.password = user.password
    db.commit()
    db.refresh(existing_user)
    return existing_user

# Delete a user
@router.delete("/users/{user_id}", response_model=dict, tags = ["User managementation"])
def delete_user(user_id: int, db: Session = Depends(get_database), admin = Depends(admin_required), data = Depends(get_users)):
    user = db.query(Person).filter(Person.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}

#TASK SECTION
#Task
@router.get("/alltasks/", response_model=list[TaskResponse], tags = ["Task managementation"])
def get_tasks(db: Session = Depends(get_database)):
    return db.query(Task).all()

#create new task
@router.post("/tasks/", response_model=TaskResponse, tags = ["Task managementation"])
def create_task(Datatypes: TaskCreate, db: Session = Depends(get_database)):
    new_task = Task(ToDo = Datatypes.ToDo, Status = Datatypes.Status, isExist = Datatypes.isExist, user_id = Datatypes.user_id)
    db.add(new_task)
    try:
        db.commit()
        db.refresh(new_task)
        return new_task
    except Exception as e:
        db.rollback()
        print(e)
        raise HTTPException(status_code=400, detail = "Email already exists")

# Update
@router.put("/update_task/{task_id}",response_model=TaskResponse, tags = ["Task managementation"])
def update_task(task_id:int,user: TaskCreate, db: Session = Depends(get_database)):
    new_task = db.query(Task).filter(task_id == Task.id).first()
    if not new_task:
        raise HTTPException(status_code=404, detail="Task not found")
    if new_task.status == "Completed":
        new_task.status = "Pending"
    elif new_task.status == "Pending":
        new_task.status = "Completed"
    db.commit()
    db.refresh(new_task)
    return new_task

# Delete 
@router.delete("/delete_users/{task_id}", response_model=dict, tags = ["Task managementation"])
def delete_user(task_id: int, db: Session = Depends(get_database)):
    new_task = db.query(Task).filter(task_id == Task.id).first()
    if not new_task:
        raise HTTPException(status_code=404, detail="Task not found")
    if new_task.isExist:
        new_task.isExist = False
        db.commit()
        return {"message" : "Task deleted successfully"}
    return {"message" : "Task is already deleted"}


#usertaskresponse
@router.get("/user_tasks/{user_id}", response_model=UserTaskResponse, tags = ["UserTask managementation"])
def get_tasks_of_user(user_id : int, db : Session = Depends(get_database)):
    stmt = select(Person, Task).join(Task, Task.user_id == Person.user_id).where(Person.user_id == user_id)
    res =  db.execute(stmt).all()
    if not res:
        raise HTTPException(status=404, detail="Not Found")
    user,_ = res[0]
    tasks = [task for _, task in res]
    return{
        "user_id" :user.user_id,
        "username": user.username,
        "email": user.email,
        "tasks":tasks
    }

#change the pending status into completed status
@router.put("/usesr_tasks_update/{user_id}", tags = ["UserTask managementation"])
def update_tasks_of_user(user_id : int, db : Session = Depends(get_database)):
   tasks = db.query(Task).filter(Task.user_id==user_id).all()
   if not tasks:
       raise HTTPException(status_code=404, detail="userID not found")
   for task in tasks:
       if(task.Status=="completed"):
           return {"message": "Already completed"}
       else:
           task.Status = "completed"
           db.commit()
   return {"message": "Successfully status updated"}

# 
@router.delete("/task_user/{user_id}", tags = ["UserTask managementation"])
def delete_tasks_by_userid(user_id: int, db: Session = Depends(get_database)):
    tasks = db.query(Task).filter(Task.user_id == user_id).all()
    if not tasks:
        raise HTTPException(status_code=404, detail="tasks not found for given user_id")
    for task in tasks:
        task.isExist = False
        db.commit()
    return {"message": f"{len(tasks)} are successfully deleted"}

#
@router.post("/get-Query/", tags = ["mysql queries"])
def get_query(user_prompt: str = Body(...), db: Session = Depends(get_database)):
    try:
        message = generate_sql(user_prompt)
        result = db.execute(text(message))
        rows = result.fetchall()
        column_names = result.keys()
        output = [dict(zip(column_names, row)) for row in rows]
        return {"message": message, "data": output}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Query execution failed: {str(e)}")




