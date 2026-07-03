from pydantic import FilePath
from pydantic_settings import BaseSettings

# The DB Should exist when starting the API
class ParametersAPI(BaseSettings):
    DB_PATH : FilePath
    API_PORT : int = 8080 # settings for api

if __name__ == "__main__":  
    p = ParametersAPI()
    print(p.model_dump())