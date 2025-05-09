from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
import uvicorn,logging,psycopg2
from dotenv import find_dotenv, load_dotenv
from typing import Any
load_dotenv(find_dotenv(".env"))

class PostgresSQLConnectionConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="POSTGRES_")
    HOST: str = "local"
    USER: str = "vincilium"
    PASSWORD: str = "vincilium"
    DATABASE: str = "blockreconsit"
    PORT: str = "5452"

pg_config = PostgresSQLConnectionConfig()
postgres_config = {
    "user": "blockuser",
    "password": "vinciluser",
    "host": "18.206.131.186",
    "port": 5452,
    "database": "blockreconsit"
}

pg_client = psycopg2.connect(**postgres_config)
print("-------------->pgclient:",pg_client)

class RefIdConfigurationRequest(BaseModel):
    sourceName: Optional[str] = Field(None)
    source_dd_name: Optional[str] = Field(None)
    sourceNames: Optional[str] = Field(None)

app = FastAPI()

def query_execution(table_name, column_name, value, corresponding_name,origin_table):
    cursor = pg_client.cursor()
    ref_id_query = None
    if table_name in ["st_source_config"]:
        ref_id_query = f"SELECT ref_id FROM {table_name} WHERE {column_name} = '{value}'"
    if table_name == "st_data_dictionary" and corresponding_name is not None:
        ref_id_query = (
            f"SELECT ref_id FROM {table_name} WHERE source_ref_id = (SELECT ref_id FROM {origin_table} WHERE {column_name} = '{corresponding_name}') "
            f"and field_name = '{value}';")
    logging.info(f"-----------------> ref_id_query:{ref_id_query}")
    cursor.execute(ref_id_query)
    ref_id_fetched = cursor.fetchall()  # <-- fetches all rows
    if table_name == "st_data_dictionary" and corresponding_name is None:
        return ref_id_fetched
    ref_id = ref_id_fetched[0] if ref_id_fetched else None

    logging.info(f"-----------> {column_name} ref id was collected : {ref_id}")
    return ref_id

def extract_ref_ids(source_name, source_dd_name):
    def collect_ids(table_name, column_name, names_list, corresponding_name, origin_table):
        if isinstance(names_list, str):
            print("--->", names_list)
            ref_ids = query_execution(table_name, column_name, names_list, corresponding_name,origin_table)
            return ref_ids
    response = {}

    if source_name is not None:
        response["source_ref_id"] = collect_ids("st_source_config", "source_name", source_name, None, None)
        response["sourceName"] = source_name
    elif source_name is not None and source_dd_name is not None :
        response["source_dd_ref_id"] = collect_ids("st_data_dictionary", "source_name", source_dd_name, source_name,
                                                   "st_source_config")
        response["source_dd_name"] = source_dd_name
    return response

@app.post("/engine/ref-ids")
def collect_ref_ids(request: RefIdConfigurationRequest):
    logging.info(f"source_name: {request.sourceName}, source_dd_name: {request.source_dd_name}")
    source_dd_name = request.source_dd_name
    source_name = request.sourceName
    ref_id = extract_ref_ids(source_name, source_dd_name, )
    return JSONResponse(content=ref_id)

if __name__ == "__main__":
    uvicorn.run(app='main:app', host="127.0.0.1", port=8001, reload=True)

