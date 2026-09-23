from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.db import create_db_and_tables, seed_database
from app.routers import catalog, proposals, tasks, teams


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    seed_database()
    yield


app = FastAPI(title="TaskReady API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    messages = []
    for error in exc.errors():
        field = ".".join(str(part) for part in error["loc"])
        kind, context = error["type"], error.get("ctx", {})
        if kind == "string_too_short":
            message = f"минимум {context['min_length']} символов"
        elif kind == "string_too_long":
            message = f"максимум {context['max_length']} символов"
        elif kind == "value_error":
            message = str(context.get("error", "некорректное значение"))
        else:
            message = {
                "missing": "обязательное поле",
                "url_scheme": "нужна ссылка http(s)",
                "url_parsing": "нужна корректная ссылка http(s)",
                "literal_error": "недопустимое значение",
            }.get(kind, "некорректное значение")
        messages.append(f"{field}: {message}")
    return JSONResponse(status_code=422, content={"detail": "; ".join(messages)})


app.include_router(tasks.router, prefix="/api", tags=["Задачи"])
app.include_router(catalog.router, prefix="/api", tags=["Каталог"])
app.include_router(proposals.router, prefix="/api", tags=["Отклики"])
app.include_router(teams.router, prefix="/api", tags=["Команды"])
