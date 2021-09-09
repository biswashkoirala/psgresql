from fastapi import FastAPI, applications
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import urllib, os, sqlalchemy, databases
from fastapi.params import Query

from sqlalchemy import engine
from sqlalchemy.sql.expression import text

host_server = os.environ.get('host_server', 'localhost')
db_server_port = urllib.parse.quote_plus(str(os.environ.get('db_server_port', '5432')))
database_name = os.environ.get('database_name', 'fastapi')
db_username = urllib.parse.quote_plus(str(os.environ.get('db_username','postgres')))
db_password = urllib.parse.quote_plus(str(os.environ.get('db_password','himal')))
ssl_mode = urllib.parse.quote_plus(str(os.environ.get('ssl_mode','prefer')))
DATABASE_URL = 'postgresql://{}:{}@{}:{}/{}?sslmode={}'.format(db_username, db_password, host_server, db_server_port, database_name, ssl_mode)

metadata = sqlalchemy.MetaData()

notes = sqlalchemy.Table(
    "notes",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("text", sqlalchemy.String),
    sqlalchemy.Column("completed", sqlalchemy.Boolean),
)

engine = sqlalchemy.create_engine(
    #DATABASE_URL
    DATABASE_URL, pool_size=3, max_overflow=0
)

metadata.create_all(engine)

from pydantic import BaseModel

class NoteIn(BaseModel):
    text: str
    completed: bool

class Note(BaseModel):
    id: int
    text: str
    completed: bool

app = FastAPI(title="Rest API using FastAPI PostgreSQL Async Endpoints")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

#import databases

database = databases.Database(DATABASE_URL)

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

@app.post("/notes/", response_model= Note)
async def create_note(note: NoteIn):
    query = notes.insert().values(text= note.text, completed = note.completed)
    last_record_id = await database.execute(query)
    return {**note.dict(), "id": last_record_id}
    
@app.get("/notes/", response_model=List[Note])
async def read_notes(skip: int = 0, take: int = 20):
    query = notes.select().offset(skip).limit(take)
    return await database.fetch_all(query)


@app.put("/notes/{note_id}", response_model=Note)
async def update_note(note_id:int, payload: NoteIn):
    query = notes.update().where(notes.c.id == note_id).values(text = payload.text, completed = payload.completed)
    await database.execute(query)
    return {**payload.dict(), "id": note_id}


@app.get("/notes/{note_id}", response_model=Note)
async def read_notes(note_id: int):
    query = notes.select().where(notes.c.id == note_id)
    return await database.fetch_one(query)


@app.delete("/notes/{note_id}")
async def delete_notes(note_id: int):
    query = notes.delete().where(notes.c.id == note_id)
    await database.execute(query)
    return {"message":"Note with id: {} deleted successfully".format(note_id)}