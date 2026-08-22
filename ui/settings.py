from pydantic import BaseModel, FilePath, ValidationError, field_validator, ValidationInfo, ValidationError, model_validator
from pydantic_settings import BaseSettings
from pathlib import Path
import shared.db_scheme as dbs
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

class ParameterError(Exception):
    pass

extensions = {"DB_PATH" : [".db"]}

# The DB Should exist when starting the UI
class ParametersUI(BaseSettings):
    UI_PORT : int = 7950
    HOST_IP_ADDRESS : str = "0.0.0.0"
    API_PORT : int = 8080
    API_URL : str = ""

    @model_validator(mode='after')
    def update_port(self):
        self.API_URL = f"http://api:{self.API_PORT}"
        return self

if __name__ == "__main__":
    p = ParametersUI()
    print(p.model_dump())