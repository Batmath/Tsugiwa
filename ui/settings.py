from pydantic import FilePath
from pydantic_settings import BaseSettings

# The DB Should exist when starting the UI
class ParametersUI(BaseSettings):
    DB_PATH : FilePath
    UI_PORT : int = 7950 # settings for ui

if __name__ == "__main__":  
    p = ParametersUI()
    print(p.model_dump())