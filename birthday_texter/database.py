from sqlmodel import Session, SQLModel, create_engine

from .config import DATABASE_PATH, prepare_data_dir

prepare_data_dir()
engine = create_engine(
    f"sqlite:///{DATABASE_PATH}", connect_args={"check_same_thread": False}
)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
