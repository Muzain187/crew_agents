from common.pg_client import pg_client
import logging

postgres_config = {
    "user": "blockuser",
    "password": "vinciluser",
    "host": "18.206.131.186",
    "port": 5452,
    "database": "blockreconsit"
}

def query_execution(table_name, column_name, value, corresponding_name,origin_table,
                    recon_ref_id,source_ref_id,recon_dd_name,recon_dd_ref_id):
    cursor = pg_client.cursor()
    ref_id_query = None
    if table_name in ["st_recon_config", "st_source_config"]:
        ref_id_query = f"SELECT ref_id FROM {table_name} WHERE {column_name} = '{value}'"
    if table_name == "st_data_dictionary" and corresponding_name is not None:
        ref_id_query = (
            f"SELECT ref_id FROM {table_name} WHERE source_ref_id = (SELECT ref_id FROM {origin_table} WHERE {column_name} = '{corresponding_name}') "
            f"and field_name = '{value}';")
    if table_name == "st_recon_settings":
        ref_id_query = (
            f"SELECT ref_id FROM {table_name} WHERE recon_ref_id = (SELECT ref_id FROM st_recon_config WHERE {column_name} = '{corresponding_name}') "
            f"and side_name = '{value}';")
    if table_name == "st_data_dictionary" and corresponding_name is None:
        ref_id_query = (
            f"SELECT field_name,ref_id FROM {table_name} WHERE source_ref_id = (SELECT ref_id FROM {origin_table} WHERE {column_name} = '{value}');")
    if table_name == "st_recon_source_field_map":
        ref_id_query=(f"SELECT ref_id FROM {table_name} WHERE recon_ref_id = '{recon_ref_id}' and source_ref_id = '{source_ref_id}'"
                      f"and recon_dd_name = '{recon_dd_name}'and recon_dd_ref_id = '{recon_dd_ref_id}';")
    logging.info(f"-----------------> ref_id_query:{ref_id_query}")
    cursor.execute(ref_id_query)
    ref_id_fetched = cursor.fetchall()  # <-- fetches all rows
    if table_name == "st_data_dictionary" and corresponding_name is None:
        return ref_id_fetched
    ref_id = ref_id_fetched[0] if ref_id_fetched else None

    logging.info(f"-----------> {column_name} ref id was collected : {ref_id}")
    return ref_id


def extract_ref_ids(source_name, recon_name, recon_dd_name, source_dd_name, side_name, source_names,
                    recon_names,recon_ref_id,source_ref_id,recon_dd_ref_id):
    def collect_ids(table_name, column_name, names_list, corresponding_name, origin_table):
        if isinstance(names_list, str):
            print("--->", names_list)
            ref_ids = query_execution(table_name, column_name, names_list, corresponding_name,origin_table,None,None,
                                      None,None)
            return ref_ids
    def mappingIdCollect(table_name,recon_ref_id,source_ref_id,recon_dd_name,recon_dd_ref_id):
        ref_ids = query_execution(table_name, None, None, None,None,
                                  recon_ref_id,source_ref_id,recon_dd_name,recon_dd_ref_id)
        return ref_ids

    response = {}
    if recon_ref_id is not None and source_ref_id is not None and recon_dd_name is not None and recon_dd_ref_id is not None:
        response["mapping_ref_id"] = mappingIdCollect("st_recon_source_field_map", recon_ref_id,source_ref_id,recon_dd_name,recon_dd_ref_id)
        # response["recon_dd_name"] = recon_dd_name
    elif recon_name is not None and recon_dd_name is None and source_dd_name is None and side_name is None and source_name is None:
        response["recon_ref_id"] = collect_ids("st_recon_config", "recon_name", recon_name, None, None)
        response["reconName"] = recon_name
    elif source_name is not None and recon_name is None and recon_dd_name is None and source_dd_name is None and side_name is None:
        response["source_ref_id"] = collect_ids("st_source_config", "source_name", source_name, None, None)
        response["sourceName"] = source_name
    elif recon_name is not None and recon_dd_name is not None and source_dd_name is None and side_name is None and source_name is None:
        response["recon_dd_ref_id"] = collect_ids("st_data_dictionary", "recon_name", recon_dd_name, recon_name,
                                                  "st_recon_config")
        response["recon_dd_name"] = recon_dd_name
    elif source_name is not None and source_dd_name is not None and recon_dd_name is None and side_name is None and recon_name is None:
        response["source_dd_ref_id"] = collect_ids("st_data_dictionary", "source_name", source_dd_name, source_name,
                                                   "st_source_config")
        response["source_dd_name"] = source_dd_name
    elif recon_name is not None and side_name is not None and recon_dd_name is None and source_dd_name is None and source_name is None:
        response["side_ref_id"] = collect_ids("st_recon_settings", "recon_name", side_name, recon_name, None)
        response["summary_side"] = side_name
    elif source_names is not None and side_name is None and recon_dd_name is None and  source_dd_name is None and source_name is None and recon_name is None:
        response["source_ref_id"] = collect_ids("st_source_config", "source_name", source_names, None, None)
        response["sourceName"] = source_names
        result = collect_ids("st_data_dictionary", "source_name",  source_names,None,"st_source_config")
        if result:
            response["source_dd_name"], response["source_dd_ref_id"] = zip(*result)
            response["source_dd_name"] = list(response["source_dd_name"])
            response["source_dd_ref_id"] = list(response["source_dd_ref_id"])
    elif recon_names is not None and side_name is None and recon_dd_name is None and source_dd_name is None and source_name is None and recon_name is None and source_names is None:
        response["recon_ref_id"] = collect_ids("st_recon_config", "recon_name", recon_names, None, None)
        response["reconName"] = recon_names
        result = collect_ids("st_data_dictionary", "recon_name",  recon_names,None,"st_recon_config")
        if result:
            response["recon_dd_name"], response["recon_dd_ref_id"] = zip(*result)
            response["recon_dd_name"] = list(response["recon_dd_name"])
            response["recon_dd_ref_id"] = list(response["recon_dd_ref_id"])

    return response
