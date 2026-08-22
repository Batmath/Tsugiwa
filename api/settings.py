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

# The DB Should exist when starting the API
class ParametersAPI(BaseSettings):
    DB_PATH : FilePath
    DUMP_PATH : FilePath
    API_PORT : int = 8080 # settings for api
    HOST_IP_ADDRESS : str = "0.0.0.0"

    @field_validator('DB_PATH', mode='before')
    @classmethod
    def validate_path(cls, value: FilePath, info : ValidationInfo) -> FilePath:
        """The initial FilePath behaviour is to reject even FilePath when the file they are 
            pointing at doesn't exist. validate_path ensure the file and path are created if 
            they don't exist.
        """
        if info.field_name not in list(extensions.keys()):
            raise ParameterError(f"The parameter added doesn't have corresponding extensions")
        if not isinstance(value, (str, Path)):
            raise TypeError(f"FILE_PATH must be a string or Path, got {type(value).__name__}")

        path = Path(value).expanduser().resolve()

        for ext in path.suffixes :
            if ext not in extensions[info.field_name]:
                raise TypeError(f"FILE_PATH must have correct extension, got {ext}, waiting for extension in: {extensions[info.field_name]}")

        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()

        return path
        
    @model_validator(mode='after')
    def ensure_db_init_from_dump(self):
        print(self.DB_PATH.stat().st_size)
        if self.DB_PATH.stat().st_size == 0:
            dbs.init_db(self.DB_PATH)
            dbs.build_db_from_dump(self.DUMP_PATH, self.DB_PATH)
        return self

if __name__ == "__main__":  
    p = ParametersAPI()
    print(p.model_dump())