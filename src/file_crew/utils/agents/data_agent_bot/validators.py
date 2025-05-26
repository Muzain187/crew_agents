import logging,json,hashlib
from file_crew.utils.agents.data_agent_bot.sending_request import request_worker

from datetime import datetime,timezone
from copy import deepcopy
def prompt_missing_field(obj, field, prompt_text=None):
    """Prompt user for a missing field value and update the object."""
    if field not in obj or not str(obj.get(field, "")).strip():
        prompt = prompt_text or f"Please provide a value for '{field}': "
        obj[field] = input(prompt).strip()
    return obj

def prompt_fields_from_list(data_list, fields):
    """Prompt missing fields for each dict in the list."""
    for item in data_list:
        for field in fields:
            prompt_missing_field(item, field)

def ensure_all_fields_present(params, required_fields, entity):
    """Ensure all required fields are present, prompting the user for any missing fields."""
    logging.info(f"ensure_all_fields_present ----> : {params}")
    for param in params:
        if entity == "recon_summary":
            prompt_fields_from_list(param.get("summaryData", []), ["field_name", "summaryName"])
            prompt_fields_from_list(param.get("reconFieldSettings", []), ["side_name", "recon_name"])
        elif entity == "matching_rule_condition":
            for idx, match in enumerate(param.get("matchings", [])):
                match_value = match.get("matchValue", {})
                source_column = match.get("sourceColumn", {})
                if idx == 0:
                    prompt_fields_from_list([match_value], ["source_name", "field_name"])
                    prompt_fields_from_list([source_column], ["source_name", "field_name"])
                elif idx == 1:
                    prompt_fields_from_list([match_value], ["field_name"])
                    prompt_fields_from_list([source_column], ["source_name", "field_name"])
        elif entity == "twoside_condition":
            for match in param.get("matchings", []):
                match_value = match.get("matchValue", {})
                source_column = match.get("sourceColumn", {})
                prompt_fields_from_list([match_value, source_column], ["source_name","display_name"])
        for field in required_fields:
            if entity == "recon_source_fields_mapping" and field == "summarySide":
                prompt_missing_field(param, "summarySide")
            elif field == "summary_side" and isinstance(param.get(field), list):
                continue
            else:
                prompt_missing_field(param, field)
                if field == "reconType":
                    param[field] = param[field].title()
        # Handle nested summary_side label prompts
        if "summary_side" in param and isinstance(param["summary_side"], list):
            for side in param["summary_side"]:
                while not side.get("label", "").strip():
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

def summary_updation(recon_field_map_ref_id, paramerters,entity):
    for param_dict in paramerters:
        if entity == "get_summary_ref_id":
            field_map = {item["display_name"]: item for item in recon_field_map_ref_id.get("reconFieldMappings", [])}
            for item in param_dict.get("summaryData",[]):
                field = item["display_name"]
                if field in field_map:
                    map_entry = field_map[field]
                    item["refId"] = map_entry.get("refId", "")
                    item["fieldMapRefId"] = map_entry.get("fieldMapRefId", "")
                    item["reconRefId"] = map_entry.get("reconRefId", "")
                    item["created_date"] = get_utc_timestamp()
            for item in param_dict.get("groupByColumns", []):
                field = item.get("display_name")
                if field in field_map:
                    map_entry = field_map[field]
                    item["refId"] = map_entry.get("refId", "")
                    item["fieldMapRefId"] = map_entry.get("fieldMapRefId", "")
                    item["reconRefId"] = map_entry.get("reconRefId", "")
                    item["recon_ref_id"] = map_entry.get("reconRefId", "")
                    item["ref_id"] = map_entry.get("fieldMapRefId", "")
                    item["dd_ref_id"] = map_entry.get("refId", "")
                    item["created_date"] = get_utc_timestamp()
                    item["modified_date"] = get_utc_timestamp()
            if recon_field_map_ref_id.get("reconFieldMappings"):
                recon_ref_id = recon_field_map_ref_id["reconFieldMappings"][0].get("reconRefId", "")
                param_dict["reconRefId"] = recon_ref_id
                for item in param_dict.get("reconFieldSettings",[]):
                    item["recon_ref_id"]= recon_ref_id
                    item["created_date"] = get_utc_timestamp()
        elif entity == "side_ref_id":
            for recon_entry in recon_field_map_ref_id:
                ref_id = recon_entry.get("ref_id")
                side_name = recon_entry.get("side_name")
                if ref_id and side_name:
                    for item in param_dict.get("reconFieldSettings", []):
                        if item.get("side_name") == side_name:
                            item["ref_id"] = ref_id
    return paramerters

def update_reconRefId(reconRefId_list, parameters,entity):
    for param in parameters:
        if entity == "event_name_creation":
            if isinstance(param, dict):
              recon_name = param.get("reconName", "")
              for entry in reconRefId_list:
                  if entry.get("reconName") == recon_name:
                      param["reconRefId"] = entry.get("recon_ref_id", [None])[0]
                      break
              else:
                  param["reconRefId"] = None
              param.pop("reconName", None)
        elif entity == "event_setup":
            if isinstance(param, dict):
                recon_name = param.get("reconName", "")
                for entry in reconRefId_list:
                    if entry.get("reconName") == recon_name:
                        param["reconRefId"] = entry.get("recon_ref_id", [None])[0]
    return parameters

def matching_condition_update(matching_conditions, parameters, entity, data_dic, matching_rule_type, match_status,rule_ref_id):
  for parameter in parameters:
    if entity == "match_status":
      match_entry = parameter.get("matchings", [{}])[0] # Get the first (and likely only) match entry
      if "matchType" in match_entry and match_entry["matchType"].get("label"):
        match_label = match_entry["matchType"]["label"]
        for match_type in matching_conditions.get("data", []):
          if match_type.get("label") == match_label:
            match_entry["matchType"] = match_type
            break
      field_map = {item["display_name"]: item for item in data_dic.get("data", {}).get("reconFieldMappings", [])}
      logging.info(f"=================>field_map: {field_map}")

      match_value_dict = match_entry.get("matchValue", {})
      logging.info(f"=================>match_value_dict:{match_value_dict}")
      field = match_value_dict.get("display_name")
      if field and field in field_map:
        logging.info(f"===================>field : {field}")
        map_entry = field_map[field]
        match_value_dict["ref_id"] = map_entry.get("refId", "")
        match_value_dict["value"] = map_entry.get("refId", "")
        match_value_dict["created_date"] = get_utc_timestamp()
        match_value_dict["source_ref_id"]=map_entry.get("reconRefId","")
        match_value_dict["field_name"]=map_entry.get("field_name","")
        match_value_dict["field_type"]=map_entry.get("fieldType","")
        match_value_dict["modified_date"]=get_utc_timestamp()

      source_column_dict = match_entry.get("sourceColumn", {})
      field_data = source_column_dict.get("display_name")
      if field_data and field_data in field_map:
        map_value = field_map[field_data]
        source_column_dict["ref_id"] = map_value.get("refId", "")
        source_column_dict["value"] = map_value.get("refId", "")
        source_column_dict["field_ref_id"] = map_value.get("refId", "")
        source_column_dict["created_date"] = get_utc_timestamp()
        source_column_dict["field_name"]=map_value.get("field_name","")
        source_column_dict["field_type"]=map_value.get("fieldType","")
        source_column_dict["modified_date"]=get_utc_timestamp()
        source_column_dict["source_ref_id"]=map_value.get("reconRefId","")

      for rule_type in matching_rule_type.get("data", []):
        if parameter.get("matchingRuleType") == rule_type.get("label"):
          parameter["matchingRuleType"] = rule_type.get("value")
          break
      for status in match_status.get("data", []):
        if parameter.get("matchStatus") == status.get("label"):
          parameter["matchStatus"] = status.get("value")
          break
      for rule in rule_ref_id.get("data", []):
        if parameter.get("matchingRuleName") == rule.get("rule_name"):
          parameter["ruleId"] = rule.get("ref_id")
          break
  return parameter