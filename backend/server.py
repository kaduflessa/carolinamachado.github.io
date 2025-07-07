from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, timedelta
import jwt
import bcrypt
import os
from pymongo import MongoClient
import uuid
from bson import ObjectId

# Environment variables
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017/')
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-here')

# MongoDB connection
client = MongoClient(MONGO_URL)
db = client.curso_saude_db

# Collections
users_collection = db.users
courses_collection = db.courses
enrollments_collection = db.enrollments
payments_collection = db.payments

app = FastAPI(title="Plataforma de Cursos Carolina Machado")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Pydantic models
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    user_type: str  # 'admin', 'instructor', 'student'

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class CourseCreate(BaseModel):
    title: str
    description: str
    price: float
    category: str
    level: str  # 'iniciante', 'intermediario', 'avançado'
    duration_hours: int
    thumbnail_url: Optional[str] = None

class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    category: Optional[str] = None
    level: Optional[str] = None
    duration_hours: Optional[int] = None
    thumbnail_url: Optional[str] = None

# Helper functions
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_jwt_token(user_id: str, email: str, user_type: str) -> str:
    payload = {
        'user_id': user_id,
        'email': email,
        'user_type': user_type,
        'exp': datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def verify_jwt_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )

# Dependency for authentication
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = verify_jwt_token(token)
    user = users_collection.find_one({"user_id": payload['user_id']})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado"
        )
    return user

def get_admin_user(current_user: dict = Depends(get_current_user)):
    if current_user['user_type'] != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas administradores."
        )
    return current_user

def get_instructor_user(current_user: dict = Depends(get_current_user)):
    if current_user['user_type'] not in ['admin', 'instructor']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas instrutores e administradores."
        )
    return current_user

# Routes
@app.get("/api/")
async def root():
    return {"message": "Plataforma de Cursos Carolina Machado - API v1.0"}

@app.post("/api/auth/register")
async def register(user: UserCreate):
    # Check if user already exists
    existing_user = users_collection.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já cadastrado"
        )
    
    # Create new user
    user_id = str(uuid.uuid4())
    hashed_password = hash_password(user.password)
    
    new_user = {
        "user_id": user_id,
        "name": user.name,
        "email": user.email,
        "password": hashed_password,
        "user_type": user.user_type,
        "created_at": datetime.utcnow(),
        "is_active": True
    }
    
    users_collection.insert_one(new_user)
    
    # Create JWT token
    token = create_jwt_token(user_id, user.email, user.user_type)
    
    return {
        "message": "Usuário registrado com sucesso",
        "token": token,
        "user": {
            "user_id": user_id,
            "name": user.name,
            "email": user.email,
            "user_type": user.user_type
        }
    }

@app.post("/api/auth/login")
async def login(user: UserLogin):
    # Find user by email
    db_user = users_collection.find_one({"email": user.email})
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha inválidos"
        )
    
    # Verify password
    if not verify_password(user.password, db_user['password']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha inválidos"
        )
    
    # Check if user is active
    if not db_user.get('is_active', True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Conta desativada"
        )
    
    # Create JWT token
    token = create_jwt_token(db_user['user_id'], db_user['email'], db_user['user_type'])
    
    return {
        "message": "Login realizado com sucesso",
        "token": token,
        "user": {
            "user_id": db_user['user_id'],
            "name": db_user['name'],
            "email": db_user['email'],
            "user_type": db_user['user_type']
        }
    }

@app.get("/api/auth/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    return {
        "user_id": current_user['user_id'],
        "name": current_user['name'],
        "email": current_user['email'],
        "user_type": current_user['user_type']
    }

@app.get("/api/courses")
async def get_courses():
    courses = []
    for course in courses_collection.find():
        course['_id'] = str(course['_id'])
        courses.append(course)
    return courses

@app.post("/api/courses")
async def create_course(course: CourseCreate, current_user: dict = Depends(get_instructor_user)):
    course_id = str(uuid.uuid4())
    new_course = {
        "course_id": course_id,
        "title": course.title,
        "description": course.description,
        "price": course.price,
        "category": course.category,
        "level": course.level,
        "duration_hours": course.duration_hours,
        "thumbnail_url": course.thumbnail_url,
        "instructor_id": current_user['user_id'],
        "instructor_name": current_user['name'],
        "created_at": datetime.utcnow(),
        "is_active": True,
        "enrollments": 0
    }
    
    courses_collection.insert_one(new_course)
    new_course['_id'] = str(new_course['_id'])
    
    return {
        "message": "Curso criado com sucesso",
        "course": new_course
    }

@app.get("/api/courses/{course_id}")
async def get_course(course_id: str):
    course = courses_collection.find_one({"course_id": course_id})
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curso não encontrado"
        )
    
    course['_id'] = str(course['_id'])
    return course

@app.put("/api/courses/{course_id}")
async def update_course(course_id: str, course_update: CourseUpdate, current_user: dict = Depends(get_instructor_user)):
    course = courses_collection.find_one({"course_id": course_id})
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curso não encontrado"
        )
    
    # Check if user is the instructor or admin
    if current_user['user_type'] != 'admin' and course['instructor_id'] != current_user['user_id']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Você pode editar apenas seus próprios cursos."
        )
    
    # Update course
    update_data = {}
    for field, value in course_update.dict(exclude_unset=True).items():
        update_data[field] = value
    
    if update_data:
        update_data['updated_at'] = datetime.utcnow()
        courses_collection.update_one(
            {"course_id": course_id},
            {"$set": update_data}
        )
    
    updated_course = courses_collection.find_one({"course_id": course_id})
    updated_course['_id'] = str(updated_course['_id'])
    
    return {
        "message": "Curso atualizado com sucesso",
        "course": updated_course
    }

@app.get("/api/instructor/courses")
async def get_instructor_courses(current_user: dict = Depends(get_instructor_user)):
    courses = []
    for course in courses_collection.find({"instructor_id": current_user['user_id']}):
        course['_id'] = str(course['_id'])
        courses.append(course)
    return courses

@app.get("/api/admin/users")
async def get_all_users(current_user: dict = Depends(get_admin_user)):
    users = []
    for user in users_collection.find({}, {"password": 0}):
        user['_id'] = str(user['_id'])
        users.append(user)
    return users

@app.get("/api/admin/stats")
async def get_admin_stats(current_user: dict = Depends(get_admin_user)):
    total_users = users_collection.count_documents({})
    total_courses = courses_collection.count_documents({})
    total_instructors = users_collection.count_documents({"user_type": "instructor"})
    total_students = users_collection.count_documents({"user_type": "student"})
    
    return {
        "total_users": total_users,
        "total_courses": total_courses,
        "total_instructors": total_instructors,
        "total_students": total_students
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)