from loguru import logger
from copy import deepcopy
from file_crew.utils.agents.data_agent_bot.validators import (ensure_all_fields_present, modifying_recon_source_ids,\
                            normalize_final_ref_id_holding,create_lookup,summary_updation,matching_condition_update,update_reconRefId)
from file_crew.utils.agents.data_agent_bot.mapping_generation import (update_recon_source_selected,group_fields_by_ref,enrich_mapping_blocks,\
                                                                 payload_hash_value_creator,update_ref_id_from_mapping)
from file_crew.utils.agents.data_agent_bot.sending_request import names_refid_collecting
from file_crew.utils.agents.data_agent_bot.sending_request import request_worker
from collections import defaultdict
import logging,json
from file_crew.utils.common.config import access_token

def assigning_value(item, operation):
    """Processes parameters by sending requests and collecting names and responses."""
    multiple_name = []
    request_sending = None
    entity = item.get('entity')
    url = item.get('url', {})
    method = item.get('method', {})
    for parameter in item.get('parameters', []):
        logging.info(f"assigning_Value function Processing parameter: {parameter}")
        try:
            request_sending, name = request_worker(operation, entity, parameter, url, method,access_token.token)
            logging.info(f"Received response: {request_sending}")
            logging.info(f"Name extracted: {name}")
            multiple_name.extend(name)
        except Exception as e:
            logging.error(f"Error during sending request for parameter {parameter}: {e}")
            continue
    return request_sending, multiple_name

def map_notcontain_refid_collection(entity,param,final_ref_id):
    """Collects and returns reference ID mappings based on provided entity and parameters, excluding those already in final_ref_id."""
    final_ref_id_holding = []
    name_hold = {k: param[k] for k in ("reconName", "sourceNames","sourceName","summarySide") if k in param}
    for k, v in name_hold.items():
        single_hold = {k: v}
        logging.info(f"------>{k}: {single_hold}")
        name_holding = None
        if entity == "recon_field_configure" and k == "sourceName":
            name_holding = {"reconName": v}
        elif k == "sourceName":
            if v != "No Recon Selected":
                name_holding = {"sourceName": v}
            else:
                continue
        elif k == "sourceNames":
            name_holding = {"sourceNames": v}
        elif k == "reconName":
            name_holding = {"reconNames": v}
        elif k == "summarySide":
            recon_name_value = next((item["reconName"] for item in final_ref_id if "reconName" in item), None)
            name_holding = {"summarySide": v, "reconName": recon_name_value}
            logging.info(f"--------> summarySide name_holding:{name_holding}")
        logging.info(f"****************{k} name name holding:{name_holding}")
        name_holds = names_refid_collecting(name_holding)
        final_ref_id_holding.extend(name_holds)
    return final_ref_id_holding

def modifying_mapping_id_collection(final_ref_id_holding):
    """
    Adds a 'mapping_ref_id' to each recon item in the list based on matched source items.
    It pairs recon and source items, creates a mapping using `assigning_value()`,
    and updates the correct recon entry in the original list with this mapping.
    """
    enriched_output = []
    recon_items = [
        {
            'recon_ref_id': item['recon_ref_id'],
            'recon_dd_name': item['recon_dd_name'],
            'recon_dd_ref_id': item['recon_dd_ref_id']
        }
        for item in final_ref_id_holding if 'recon_ref_id' in item
    ]
    recon_items = [dict(t) for t in {tuple(d.items()) for d in recon_items}]
    source_ref_ids = list({item['source_ref_id'] for item in final_ref_id_holding if 'source_ref_id' in item})
    for recon in recon_items:
        for source_ref_id in source_ref_ids:
            results = {
                'recon_ref_id': recon['recon_ref_id'],
                'source_ref_id': source_ref_id,
                'recon_dd_name': recon['recon_dd_name'],
                'recon_dd_ref_id': recon['recon_dd_ref_id']
            }
            mapping_id = request_worker("read", "reference_id", results, None, None,None)
            logger.info(f"---------> Raw mapping_id from worker: {mapping_id}")
            if isinstance(mapping_id, tuple) and 'mapping_ref_id' in mapping_id[0]:
                mapping_ref = mapping_id[0]['mapping_ref_id']
                if isinstance(mapping_ref, list) and mapping_ref:
                    mapping_ref = mapping_ref[0]
                enriched_output.append({
                    **recon,
                    'source_ref_id': source_ref_id,
                    'mapping_ref_id': mapping_ref
                })
                for item in final_ref_id_holding:
                    if (
                            item.get('recon_dd_name') == recon['recon_dd_name'] and
                            item.get('recon_dd_ref_id') == recon['recon_dd_ref_id']
                    ):
                        item.update({'mapping_ref_id': mapping_ref})
                        break
    return final_ref_id_holding, enriched_output

def endpoint_worker(payloads):
    """Call a generic REST endpoint and process entities accordingly."""
    operation = payloads.get('operation')
    logging.info(f"Operation received: {operation}")
    final_ref_id_holding = []
    mapping_id_collecting = []
    request_sending = recon_name = source_names = None
    for item in payloads.get('entities', []):
        entity = item.get('entity')
        entity_parameters = item.get("parameters", [])
        logging.info(f"Processing entity: {entity}")
        try:
            if entity in ["recon", "source"]:
                request_sending, name_holding = assigning_value(item, operation)
                final_ref_id_holding.extend(name_holding)
                logging.info(f"Fetched recon or source reference ID for {request_sending}: {final_ref_id_holding}")
            if entity == "recon_side_configure":
                request_sending, name_holding = assigning_value(item, operation)
                logging.info(f"Fetched recon side configure reference id for :{request_sending}:{final_ref_id_holding}")
                final_ref_id_holding.extend(name_holding)
            if entity == "source_field_settings" and operation in ["create"]:
                required_fields = ["sourceName"]
                params = ensure_all_fields_present(entity_parameters, required_fields, entity)
                if not any(key in final_ref_id_holding for key in ["sourceName"]):
                    # param = entity_parameters[0]
                    for param in entity_parameters:
                        refid_notcontain = map_notcontain_refid_collection(None, param, None)
                        final_ref_id_holding.extend(refid_notcontain)
                source_id_updated = modifying_recon_source_ids(entity_parameters, final_ref_id_holding)
                logging.info(f"s_id_updated----------->:\n{json.dumps(payloads, indent=2)}")
                request_sending, name_holding = assigning_value(item, operation)
                logging.info(f"-------> request_sending and name holding  response: {request_sending}, {name_holding}")
            if entity == "source_configuration" and operation in ["create"]:
                required_fields = ["sourceName", "fieldName"]
                params = ensure_all_fields_present(entity_parameters, required_fields, entity)
                source_id_updated = modifying_recon_source_ids(entity_parameters, final_ref_id_holding)
                logging.info(f"source_ref_id_updated----------->:\n{json.dumps(payloads, indent=2)}")
                request_sending, name_holding = assigning_value(item, operation)
                logging.info(
                    f"-------> request_sending and name holding response: {request_sending}, {name_holding}")
                final_ref_id_holding.extend(name_holding)
            if entity == "recon_field_configure" and operation in ["create"]:
                if not any(key in final_ref_id_holding for key in ["sourceName"]):
                    # param = entity_parameters[0]
                    for param in entity_parameters:
                        refid_notcontain = map_notcontain_refid_collection(entity, param, None)
                        final_ref_id_holding.extend(refid_notcontain)
                required_fields = ["sourceName", "fieldName"]
                params = ensure_all_fields_present(entity_parameters, required_fields, entity)
                source_id_updated = modifying_recon_source_ids(entity_parameters, final_ref_id_holding)
                logging.info(f"source_ref_id_updated ----------->:\n{json.dumps(payloads, indent=2)}")
                request_sending, name_holding = assigning_value(item, operation)
                logging.info(
                    f"-------> recon_field_configure for request and name holding response: {request_sending},{name_holding}")
                final_ref_id_holding.extend(name_holding)  # accumulate all collected ref_ids
            if entity == "recon_source_selected" and operation in ["create"]:
                if not any(key in final_ref_id_holding for key in
                           ["reconName", "sourceNames", "recon_dd_name", "source_dd_name"]):
                    # param = entity_parameters[0]
                    for param in entity_parameters:
                        name_holds = map_notcontain_refid_collection(None, param, None)
                        flat_ref_data = normalize_final_ref_id_holding(name_holds)
                        final_ref_id_holding.extend(flat_ref_data)  # append dict instead of extend
                    lookup = create_lookup(final_ref_id_holding)
                    logging.info(f"Current final_ref_id_holding: {final_ref_id_holding}")
                    logging.info(f"Current entity parameters: {entity_parameters}")
                    field_name_updating = update_recon_source_selected(entity_parameters, lookup)
                    recon_name = entity_parameters[0].get("reconName", "")
                    source_names = entity_parameters[0].get("sourceNames", [])
                    logging.info(f"field_update-------------->:\n{json.dumps(field_name_updating, indent=2)}")
                    logging.info(f"field_update recon_source_selected-------------->:\n{json.dumps(item, indent=2)}")
                    payload_exist_check = payload_hash_value_creator(item)
                    request_sending, name_holding = assigning_value(item, operation)
                    logging.info(
                        f"-------> request_sending and name holding response:{request_sending}, {name_holding}")
            if entity == "recon_source_fields_mapping" and operation in ["create"]:
                recon_fields, grouped_source_fields = group_fields_by_ref(final_ref_id_holding)
                lookup = create_lookup(final_ref_id_holding)
                final_ref_id_holding, mapping_id_collect = modifying_mapping_id_collection(final_ref_id_holding)
                mapping_id_collecting.extend(mapping_id_collect)
                logging.info(f"----->Actual final ref id collecting<------:{final_ref_id_holding}")
                logging.info(f"----->field mapping ref id collecting<------:{mapping_id_collecting}")
                source_ref_ids = [lookup["source"][sname] for sname in source_names]
                recon_ref_id = lookup["recon"][recon_name]
                enriched_params = enrich_mapping_blocks(entity_parameters, recon_fields, grouped_source_fields,
                                                        recon_ref_id, source_ref_ids)
                item["parameters"] = enriched_params
                logging.info(f"field_update-------------->:\n{json.dumps(entity_parameters, indent=2)}")
                mapping_ref_id_updating = update_ref_id_from_mapping(enriched_params, mapping_id_collecting)
                logging.info(
                    f"field_mapping_ref_id_updating-------------->:\n{json.dumps(mapping_ref_id_updating, indent=2)}")
                logging.info(f"field_update recon_source_field_mappings-------------->:\n{json.dumps(item, indent=2)}")
                # payload_exist_check = payload_hash_value_creator(item)
                request_sending, name_holding = assigning_value(item, operation)
                logging.info(f"-------> request_sending and name holding response:{request_sending}, {name_holding}")
            if entity == "matching_rule_name" and operation in ["create"]:
                required_fields= ["matchingRuleName","reconName"]
                params = ensure_all_fields_present(entity_parameters, required_fields, entity)
                request_sending, name_holding = assigning_value(item, operation)
                final_ref_id_holding.extend(name_holding)
                logging.info(f"Fetched recon or source reference ID for {request_sending}: {final_ref_id_holding}")
            if entity == "recon_summary" and operation in ["create","update"]:
                required_fields = ["reconName"]
                params = ensure_all_fields_present(entity_parameters, required_fields, entity)
                logging.info(f"=============> entity_parameters:{entity_parameters}")
                recon_name = entity_parameters[0]["reconName"]
                logging.info(f"----------->{recon_name}:recon name formatting")
                entity_name = "get_summary_ref_id"
                recon_field_map_ref_id = request_worker(operation, entity_name, recon_name, None, None,access_token.token)
                # logging.info(f"===========>recon_field_map_ref_id:{recon_field_map_ref_id[0]['data']}")
                show_in_summary = summary_updation(recon_field_map_ref_id[0]["data"],entity_parameters,entity_name)
                logging.info(f"===========>recon_field_map_ref_id show in summary:{json.dumps(show_in_summary, indent=4)}")
                entity_side_name = "side_ref_id"
                recon_side_ref_id = request_worker(operation, entity_side_name, recon_name, None, None,access_token.token)
                # logging.info(f"===========>recon_side_ref_id:{json.dumps(recon_side_ref_id, indent=4)}")
                show_in_side = summary_updation(recon_side_ref_id[0]["data"],entity_parameters,entity_side_name)
                logging.info(f"===========>recon_field_map_ref_id show in side:{json.dumps(show_in_side, indent=4)}")
                request_sending, name_holding = assigning_value(item, operation)
                # final_ref_id_holding.extend(name_holding)
                logging.info(f"Fetched recon or source reference ID for {request_sending}")
            if entity == "twoside_condition" and operation in ["create"]:
                required_fields = ["reconName", "sourceName", "targetName", "matchingRuleName"]
                params = ensure_all_fields_present(entity_parameters, required_fields, entity)
                recon_name = entity_parameters[0]["reconName"]
                logging.info(f"----------->{recon_name}:recon name formatting")
                entity_name = "get_rule_ref_id"
                get_recon_rule_ref_id = request_worker(operation, entity_name, recon_name, None, None,
                                                       access_token.token)
                entity_name_matching = "get_matching_condition"
                get_matching_condition = request_worker(operation, entity_name_matching, None, None, None,
                                                        access_token.token)
                logging.info(
                    f"------------>get_matching_condition response:{json.dumps(get_matching_condition, indent=4)}")
                entity_field_map_name = "get_summary_ref_id"
                operation_data = "update"
                recon_field_map_ref_id = request_worker(operation_data, entity_field_map_name, recon_name, None, None,
                                                        access_token.token)
                entity_matching_rule_type = "matching_rule_type_fetching"
                match_rule_type_fetching = request_worker(operation, entity_matching_rule_type, None, None, None,
                                                          access_token.token)
                entity_matching_status = "match_status"
                match_status_fetching = request_worker(operation, entity_matching_status, None, None, None,
                                                       access_token.token)
                def unwrap_singleton_tuple(value):
                    if isinstance(value, tuple):
                        return value[0]
                    return value
                get_matching_condition = unwrap_singleton_tuple(get_matching_condition)
                logging.info(f"------------>get_matching_condition:{type(get_matching_condition)}")
                logging.info(f"===========>get_matching_condition:{json.dumps(get_matching_condition, indent=4)}")
                recon_field_map_ref_id = unwrap_singleton_tuple(recon_field_map_ref_id)
                logging.info(f"------------>recon_field_map_ref_id: {type(recon_field_map_ref_id)}")
                logging.info(f"===========>recon_field_map_ref_id:{json.dumps(recon_field_map_ref_id, indent=4)}")
                match_rule_type_fetching = unwrap_singleton_tuple(match_rule_type_fetching)
                logging.info(f"------------>match_rule_type_fetching: {type(match_rule_type_fetching)}")
                logging.info(f"===========>match_rule_type_fetching:{json.dumps(match_rule_type_fetching, indent=4)}")
                match_status_fetching = unwrap_singleton_tuple(match_status_fetching)
                logging.info(f"------------>match_rule_type_fetching: {type(match_rule_type_fetching)}")
                logging.info(f"===========>match_status_fetching:{json.dumps(match_status_fetching, indent=4)}")
                get_recon_rule_ref_id= unwrap_singleton_tuple(get_recon_rule_ref_id)
                logging.info(f"------------>get_recon_rule_ref_id: {type(get_recon_rule_ref_id)}")
                logging.info(f"===========>get_recon_rule_ref_id:{json.dumps(get_recon_rule_ref_id, indent=4)}")
                matching_ref_id_update = matching_condition_update(get_matching_condition, entity_parameters,
                                                                   entity_matching_status, recon_field_map_ref_id,match_rule_type_fetching,match_status_fetching, get_recon_rule_ref_id)
                logging.info(f"===========>matching_ref_id_update:{json.dumps(matching_ref_id_update, indent=4)}")
                request_sending, name_holding = assigning_value(item, operation)
            if entity == "event_name_creation" and operation in ["create"]:
                recon_name = {"reconName":entity_parameters[0].get("reconName", "")}
                reconRefId = map_notcontain_refid_collection(entity,recon_name,None)
                logging.info(f"----------------> Removed the reconName from the entity of event_name_creation:\n{json.dumps(entity_parameters, indent=4)}")
                update_rec_id = update_reconRefId(reconRefId,entity_parameters,entity)
                logging.info(f"--------------- update_rec_id:,{json.dumps(update_rec_id,indent=4)}")
                request_sending, name_holding = assigning_value(item, operation)
            if entity == "event_setup" and operation in ["create"]:
                recon_name = {"reconName": entity_parameters[0].get("reconName", "")}
                reconRefId = map_notcontain_refid_collection(entity, recon_name, None)
                # event_name = {"eventName": entity_parameters[0].get("eventName","")}
                # event_ref_id = map_notcontain_refid_collection(entity,event_name,None)
                update_event_id = update_reconRefId(reconRefId, entity_parameters,entity)
                logging.info(f"--------------- update_rec_id:,{json.dumps(update_event_id, indent=4)}")
                request_sending, name_holding = assigning_value(item, operation)
            logging.info(f"-------------->final_ref_id_holding:{final_ref_id_holding}")
        except Exception as e:
            logging.error(f"Error processing entity {entity}: {e}")
    logging.info(f"-------------->final_ref_id_holding:{final_ref_id_holding}")
    return request_sending, final_ref_id_holding
