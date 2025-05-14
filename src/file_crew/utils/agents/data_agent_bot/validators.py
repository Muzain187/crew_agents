import logging,json,hashlib
from file_crew.utils.agents.data_agent_bot.sending_request import request_worker

from datetime import datetime,timezone
from copy import deepcopy

def ensure_all_fields_present(params, required_fields, entity):
    """Ensure all required fields are present, prompting the user for any missing fields."""
    logging.info(f"ensure_all_fields_present----> :{params}")
    if entity in ["recon", "source", "source_configuration","recon_source_fields_mapping","recon_source_selected",
                  "recon_field_configure", "source_field_settings", "recon_side_configure","matching_rule_name"]:
        for parameter in params:
            for field in required_fields:
                if entity == "recon_source_fields_mapping" and field == "summarySide":
                    if not parameter.get("summarySide", "").strip():
                        parameter["summarySide"] = input("Please provide a value for 'summarySide': ").strip()
                if field == "summary_side" and isinstance(parameter.get(field), list):
                    continue
                if field not in parameter or not str(parameter.get(field, "")).strip():
                    parameter[field] = input(f"Please provide a value for '{field}': ").strip()
                    if field == "reconType":
                        parameter[field] = parameter[field].title()
            if "summary_side" in parameter:
                for side in parameter["summary_side"]:
                    while "label" not in side or not side["label"].strip():
                        side["label"] = input("Please provide a value for 'side name': ").strip()
                        side["value"] = side["label"]
    return params

def modifying_recon_source_ids(parameters, ref_id_holding):
    """Update parameters with source and recon reference IDs based on the ref_id_holding mapping."""
    ref_id = [
        {key: value[0] if isinstance(value, list) else value for key, value in entry.items()}
        for entry in ref_id_holding
    ]
    logging.info(f"ref_id ----->: {ref_id}")
    source_ref_mapping = {entry["sourceName"]: entry["source_ref_id"] for entry in ref_id if
                          "source_ref_id" in entry}
    recon_ref_mapping = {entry["reconName"]: entry["recon_ref_id"] for entry in ref_id if "recon_ref_id" in entry}
    # Build the new source_configuration parameters list
    updated_source_config = []
    for param in parameters:
        source_name = param["sourceName"]
        if source_name in source_ref_mapping:
            updated_source_config.append(
                {"sourceRefId": source_ref_mapping[source_name]})  # If the sourceName exists, update sourceRefId
        if source_name in recon_ref_mapping:
            updated_source_config.append({"sourceRefId": recon_ref_mapping[source_name]})
    # Add new entries from ref_id if they are not already in updated_source_config
    existing_sources = {param["sourceName"] for param in parameters}
    logging.info(f"existing_source: {existing_sources}")
    existing_recons = {param["sourceName"] for param in parameters if
                       "sourceName" in param and "origin" in param and param["origin"] == "recon"}
    logging.info(f"existing_recons: {existing_recons}")
    for entry in ref_id:
        if "source_ref_id" in entry and entry["sourceName"] not in existing_sources:
            updated_source_config.append({"sourceName": entry["sourceName"], "sourceRefId": entry["source_ref_id"]})
        if "recon_ref_id" in entry and entry["reconName"] not in existing_recons:
            updated_source_config.append({"sourceName": entry["reconName"], "sourceRefId": entry["recon_ref_id"]})
    for i, config in enumerate(updated_source_config):
        if i < len(parameters):
            parameters[i]["sourceRefId"] = config["sourceRefId"]
    return json.dumps(parameters, indent=2)

def get_utc_timestamp():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
def normalize_final_ref_id_holding(data):
    """Normalize a list of dictionaries by expanding list values into multiple records with aligned scalar values."""
    normalized = []
    for item in data:
        max_len = max((len(v) for v in item.values() if isinstance(v, list)), default=1)
        for i in range(max_len):
            new_item = {}
            for k, v in item.items():
                if isinstance(v, list):
                    new_item[k] = v[i] if i < len(v) else v[-1]
                else:
                    new_item[k] = v
            normalized.append(new_item)
    return normalized

def create_lookup(data):
    """Returns lookup dictionaries for recon and source from a list of dicts."""
    return {
        "recon": {d["reconName"]: d["recon_ref_id"] for d in data if "reconName" in d},
        "source": {d["sourceName"]: d["source_ref_id"] for d in data if "sourceName" in d},
        # "recon_dd": [(d["recon_dd_ref_id"], d["recon_dd_name"]) for d in data if "recon_dd_ref_id" in d],
        # "source_dd": [(d["source_dd_ref_id"], d["source_dd_name"]) for d in data if "source_dd_ref_id" in d]
    }
