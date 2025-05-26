from file_crew.utils.agents.data_agent_bot.validators import get_utc_timestamp
import logging,hashlib
from copy import deepcopy
import json

def update_recon_source_selected(params,lookup):
    """Updates 'reconRefId' in each param using the 'reconName' and a lookup dictionary."""
    for param in params:
        logging.info(f"before update_recon_source_selected :{params}")
        recon_name = param.get("reconName", "")
        param["reconRefId"] = lookup["recon"].get(recon_name, "")
    logging.info(f"after update_recon_source_selected :{params}")
    return params

def group_fields_by_ref(final_ref_id):
    """Groups recon and source field names and ref IDs from the given list."""
    recon_fields = []
    source_fields = {}
    for item in final_ref_id:
        if "recon_dd_ref_id" in item:
            recon_fields.append({
                "recon_dd_ref_id": item["recon_dd_ref_id"],
                "recon_dd_name": item["recon_dd_name"]
            })
        elif "source_ref_id" in item:
            ref_id = item["source_ref_id"]
            if ref_id not in source_fields:
                source_fields[ref_id] = []
            source_fields[ref_id].append({
                "source_dd_ref_id": item["source_dd_ref_id"],
                "source_dd_name": item["source_dd_name"]
            })
    return recon_fields, source_fields

def enrich_mapping_blocks(params, recon_fields, source_fields, recon_ref_id, source_ref_ids):
    """recon and source fields ref_ids updated"""
    enriched = []
    for i, source_ref_id in enumerate(source_ref_ids):
        param_template = params[i % len(params)]
        param = deepcopy(param_template)
        param["reconRefId"] = recon_ref_id
        param["sourceRefId"] = source_ref_id
        param["filterPayload"]["reconRefId"] = recon_ref_id
        param["filterPayload"]["sourceRefId"] = source_ref_id
        # Generate valid recon-source mapping pairs
        mapping_pairs = zip(recon_fields, source_fields.get(source_ref_id, []))
        final_mappings = []
        for recon_f, source_f in mapping_pairs:
            timestamp = get_utc_timestamp()
            final_mappings.append({
                "ref_id": "",
                "recon_ref_id": recon_ref_id,
                "source_ref_id": source_ref_id,
                "recon_dd_ref_id": recon_f["recon_dd_ref_id"],
                "recon_dd_name": recon_f["recon_dd_name"],
                "source_dd_ref_id": source_f["source_dd_ref_id"],
                "source_dd_name": source_f["source_dd_name"],
                "display_name": recon_f["recon_dd_name"],
                "source_dd_display_name": source_f["source_dd_name"],
                "created_date": timestamp,
                "modified_date": timestamp
            })
        param["reconSourceFieldMappings"] = final_mappings
        # REMOVE sourceName from output
        param.pop("sourceName", None)
        enriched.append(param)
    return enriched

def update_ref_id_from_mapping(parameter, mapping_id_collect):
    """Mapping ref id updation"""
    for param in parameter:
        for mapping in param.get("reconSourceFieldMappings", []):
            for ref in mapping_id_collect:
                if (
                        ref["recon_ref_id"] == mapping.get("recon_ref_id") and
                        ref["recon_dd_name"] == mapping.get("recon_dd_name") and
                        ref["recon_dd_ref_id"] == mapping.get("recon_dd_ref_id") and
                        ref["source_ref_id"] == mapping.get("source_ref_id")
                ):
                    mapping["ref_id"] = ref["mapping_ref_id"]
                    break  # Stop after finding the first valid match
        param["reconSourceFieldMappingsCopy"] = deepcopy(param["reconSourceFieldMappings"])
    return parameter

def payload_hash_value_creator(parameter):
    """ Generates a SHA-256 hash of the given parameter after converting it to a JSON string."""
    json_string = json.dumps(parameter, sort_keys=True)  # sort_keys ensures consistent hashing
    hash_object = hashlib.sha256()
    hash_object.update(json_string.encode('utf-8'))
    digest = hash_object.hexdigest()
    print("SHA-256 Digest:", digest)
    return digest