import logging,json,requests
from create_source.common.constants import app_endpoints
import google.generativeai as genai
from typing import Optional,List
from pydantic import BaseModel, Field

class ApiKeyConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="API_KEY_")
    GOOGLE_API_KEY: str = Field(default="")

apikey_config = ApiKeyConfig()
genai.configure(api_key=apikey_config.GOOGLE_API_KEY)

class LLMModel(str,Enum):
    GEMINI_FLASH_002:str = "gemini-1.5-flash-002"

class FetchToken(BaseSettings):
    token: str
    model_config = {
        "env_prefix": "ACCESS_",
    }
access_token = FetchToken()

def prompt_enginnering(endpoints, user_input):
    return """
    You are a query parsing agent. Given a natural language input, identify the operation, entity, and parameters. as JSON\n 
From the user_input you should be able to find the suitable operation,entity and params.AlsoYou are an AI research assistant. You use a tone that is technical and scientific.

Rules:
    - Handle many natural variations and synonyms of user instructions.
    - Understand actions like create, read, update, and delete from context — regardless of phrasing.
    - Normalize the user’s request to a standard CRUD operation and extract the corresponding example output format details..
    - Be robust to synonyms, grammar, and user style.  
    - Queries can contain multiple entities.
    - Extract each entity separately along with its respective parameters.
    - The output should be a single JSON object.
    - Each entity and its parameters should be structured as separate key-value pairs within the object.
    - *If provided question just concentrate the extract the values below provide output format.*
    - *If the payload formatting has an empty string (""), please follow as is; do not replace it with (null)*
    - *If recon, source, recon_side_configure, recon_field_configure, source_configuration, or source_field_settings do not provide the required field names, return them in the proper format, indicating that the missing field names are empty strings. *

    - Step1 : Below is the proper payload structure. Please include the entity of "source" "parameters" and ensure that the fields "sourceDesc", "sourceName" are dynamically updated based on the summary of the question.
        - Please ensure that whatever value is provided for "sourceName" is also set for the "sourceDesc" field.
            -After collecting the required values, return the proper payload in the following format::        
            {
                "active": "Y",
                "deletedIndex": "-1",
                "referenceId": "",
                "sourceDesc": "",
                "sourceName": "",
            }

    - Step2 : Below is the proper payload structure. Please include the entity of "source_field_settings" "parameters" and ensure that the fields "sourceName" are dynamically updated based on the summary of the question.
            -After collecting the required values, return the proper payload in the following format::        
            {
                currency : ""
                fileFormat: "Flat"
                idField:""
                isManualActions:"N"
                isManualEditsAllowed:"N"
                isManualItemsAllowed:"N"
                isSplitSource:"N"
                isUpdatesAllowed:"N"
                isUploadActions:"N"
                sourceName:""
                sourceRefId:""
                subAccount:""
            }

    - Step3 : Below is the proper payload structure. Please include the entity of "source_configuration" "parameters" and ensure that the fields "fieldName" are dynamically updated based on the summary of the question.
        - Please ensure that whatever value is provided for "fieldName" is also set for the "displayName" field.
            -After collecting the required values, return the proper payload in the following format::        
            {
                active : "Y"
                ddIndex: "1"
                displayName: "" 
                fieldName: "" 
                fieldType: "String"
                nestedFieldName: ""
                origin: "source"
                sourceName: "" 
                sourceRefId:"" 
            }
    Operations:
    - "list": To retrieve all instances or specific (depends upon the entity in that case convert into "read" instead of "list") of an entity.
    - "read": To retrieve a specific instance of an entity by ID.
    - "create": To creates or add a new entity.
    - "update": To update an existing entity.
    - "delete": To delete an entity by ID.

    Entities could be "recon", "source","field" etc.

    Parameters should include any relevant IDs or filters.

    Example Inputs and Outputs:

    1. Input: "list all recon"
        Output: {"operation": "list", "entity": "recon", "parameters": {}}

    if provide multiple entities like "recon" and "source" should need to return output parameters corresponding values..
    - Identify the correct URL and method based on the entity. It should be included without the parameter key from the given endpoints and formatted as follows:
                    "url": "<corresponding_endpoint_url>"
                    "method":"<corresponding_method>"
     Example Input and Outputs:
        1. Input: "Create source as s1 and with fields f1, f2?"
            - Please use the name entity 'fields' as 'source_configuration'
            - *Please generate the "source_field_settings" based on the provided source name, and avoid generating multiple payloads for the same source name.* 
            - If the user provides source field information in their question, always include both of the following entities in the response:
                --"source_field_settings" – This should come first.
                --"source_configuration" – This should come after "source_field_settings".
                --Do not skip or change the order. Always return both if source fields are mentioned.
            Output: {"operation": "create", "entities": [{"entity": "recon","url": "<corresponding_endpoint_url>","method":"<corresponding_method>", "parameters": [{}]}, {"entity": "source", "url": "<corresponding_endpoint_url>","method":"<corresponding_method>","parameters": [{},{}],{"entity": "source_field_settings", "url": "<corresponding_endpoint_url>","method":"<corresponding_method>","parameters": [{},{}]}
            {"entity": "source_configuration","url": "<corresponding_endpoint_url>", "method":"<corresponding_method>", "parameters": [{"sourceName":"","fieldName":"" },{"sourceName":"","fieldName":"" }]}]}
                """ + f"""
        Based on this endpoints you should be able to decide the operation,entity and params
        {endpoints} Now, process the following input: {user_input}
        """

def prompt_missing_field(obj, field, prompt_text=None):
    """Prompt user for a missing field value and update the object."""
    if field not in obj or not str(obj.get(field, "")).strip():
        prompt = prompt_text or f"Please provide a value for '{field}': "
        obj[field] = input(prompt).strip()
    return obj

def ensure_all_fields_present(params, required_fields, entity):
    """Ensure all required fields are present, prompting the user for any missing fields."""
    logging.info(f"ensure_all_fields_present ----> : {params}")
    for parameter in params:
        if entity == "recon_summary":
            for summary in parameter.get("summaryData", []):
                necessary_fields = ["field_name","summaryName"]
                for field in necessary_fields:
                    prompt_missing_field(summary, field)
            for summ in parameter.get("reconFieldSettings", []):
                necessary_fields= ["side_name","recon_name"]
                for field in necessary_fields:
                    prompt_missing_field(summ, field)
        if entity == "matching_rule_condition":
            for match in parameter.get("matchings", []):
                for rule in match.get("matchValue", {}):
                    necessary_field = ["source_name", "field_name"]
                    for field in necessary_field:
                        prompt_missing_field(rule, field)
                for source_rule in match.get("sourceColumn", {}):
                    ness_field = ["source_name", "field_name"]
                    for field in ness_field:
                        prompt_missing_field(source_rule, field)

        for field in required_fields:
            if entity == "recon_source_fields_mapping" and field == "summarySide":
                prompt_missing_field(parameter, "summarySide")
            elif field == "summary_side" and isinstance(parameter.get(field), list):
                continue
            else:
                prompt_missing_field(parameter, field)
                if field == "reconType":
                    parameter[field] = parameter[field].title()
        # Handle nested summary_side labels
        if "summary_side" in parameter:
            for side in parameter["summary_side"]:
                while not side.get("label", "").strip():
                    side["label"] = input("Please provide a value for 'side name': ").strip()
                    side["value"] = side["label"]
    return params

def generate_prompt(user_input):
    """Generates and parses a JSON response from a model based on user input."""
    followup_prompt = prompt_enginnering(
        endpoints=app_endpoints,
        user_input=user_input,
    )
    model = genai.GenerativeModel(LLMModel.GEMINI_FLASH_002.value)
    response = model.generate_content(followup_prompt)

    response_text = response.text
    logging.info(f"DEBUG: Full response: {response_text}")
    json_string = response_text.strip("```json").strip()  #
    json_string = json_string.strip("```")
    logging.info(f"------------->json_string: {json_string}")
    return json.loads(json_string)

def request_worker(operation, entity, parameter, url, method,token):
    """Sends an HTTP request based on operation, entity, and method using provided parameters and endpoint configuration.
    Return the corresponding recon, source and fields to fetch the reference Ids"""
    try:
        response = None
        logging.info(
            f"Before check -> URL: {url}, Method: {method}, Entity: {entity}, Operation: {operation}, Parameter: {parameter}")
        logging.info(type(endpoints))
        app_endpoints = endpoints
        if isinstance(endpoints, str):
            app_endpoints = json.loads(endpoints)
        if entity in app_endpoints[operation]:
            endpoint = app_endpoints[operation][entity]
            if operation in "read":
                url = endpoint["url"]
                method = endpoint["method"]
            elif url is None and method is None and entity in ["get_summary_ref_id","side_ref_id","get_matching_condition"]:
                url_endpoint= endpoint["url"]
                url = f'{url_endpoint}{parameter}'
                logging.info(f"-------------->recon name updation id url test:{url}")
                method = endpoint["method"]
                parameter={"reconName":parameter}
            headers = {"X-Access-Token": token}

            logging.info(
                f"request-worker -> URL: {url}, Method: {method}, Entity: {entity}, Operation: {operation}, "
                f"Headers {token}, Parameter: {parameter}")

            if method == "GET":
                response = requests.get(url, json=parameter, headers=headers)
            elif method == "POST":
                response = requests.post(url, json=parameter, headers=headers)
            elif method == "PUT":
                response = requests.put(url, json=parameter, headers=headers)
            elif method == "DELETE":
                response = requests.delete(url, params=parameter)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            logging.info(f"Response Status: {response.status_code}")
            logging.info(f"Response Body: {response.text}")
            final_ref_id_holding = None
            # if entity != "reference_id" and entity != "get_summary_ref_id":
            if entity not in ["reference_id", "get_summary_ref_id"]:
                if response.status_code in [200, 201]:  # success
                    name = {}
                    final_ref_id_holding = []
                    if entity == "recon_field_configure" and parameter.get('origin') == "recon":
                        name["recon_dd_name"] = parameter['fieldName']
                        name["reconName"] = parameter['sourceName']
                        logging.info(f"-------->recon field configure updated : {name}")
                        ref_id = names_refid_collecting(name)
                        final_ref_id_holding.extend(ref_id)
                    if entity == "source_configuration" and parameter.get('origin') == "source":
                        name["source_dd_name"] = parameter['fieldName']
                        name["sourceName"] = parameter['sourceName']
                        logging.info(f"-------->source field configure updated : {name}")
                        ref_id = names_refid_collecting(name)
                        final_ref_id_holding.extend(ref_id)
                    if entity == "source" and parameter.get('sourceName'):
                        name["sourceName"] = parameter['sourceName']
                        logging.info(f"-------->source name updated : {name}")
                        ref_id = names_refid_collecting(name)
                        final_ref_id_holding.extend(ref_id)
                    if entity == "recon" and parameter.get('reconName'):
                        name["reconName"] = parameter['reconName']
                        logging.info(f"-------->recon name updated : {name}")
                        ref_id = names_refid_collecting(name)
                        final_ref_id_holding.extend(ref_id)
                    if entity == "recon_side_configure" and parameter.get('summary_side'):
                        name["summary_side"] = [item["label"] for item in parameter["summary_side"]]
                        name["reconName"] = parameter['reconName']
                        logging.info(f"-------->recon side configure updated : {name}")
                        ref_id = names_refid_collecting(name)
                        final_ref_id_holding.extend(ref_id)
                    if entity == "matching_rule_name" and parameter.get("matchingRuleName"):
                        name["matchingRuleName"] = parameter["matchingRuleName"]
                        name["reconName"] = parameter["reconName"]
                        logging.info(f"-------------> matching rule name updated: {name}")
                        ref_id = names_refid_collecting(name)
                        final_ref_id_holding.extend(ref_id)
                return response.json(), final_ref_id_holding
            return response.json(), {}
        else:  # Any other status code
            logging.error(f"Request failed with status code {response.status_code}: {response.text}")
            raise ValueError(f"Request failed with status code {response.status_code}: {response.text}")
    except requests.RequestException as e:
        logging.exception(f"Request exception occurred: {e}")
        raise

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

def endpoint_worker(payloads):
    """Call a generic REST endpoint and process entities accordingly."""
    operation = payloads.get('operation')
    logging.info(f"Operation received: {operation}")
    final_ref_id_holding = []
    request_sending = None
    for item in payloads.get('entities', []):
        entity = item.get('entity')
        entity_parameters = item.get("parameters", [])
        logging.info(f"Processing entity: {entity}")
        try:
            if entity in ["source"]:
                request_sending, name_holding = assigning_value(item, operation)
                final_ref_id_holding.extend(name_holding)
                logging.info(f"Fetched recon or source reference ID for {request_sending}: {final_ref_id_holding}")
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
        except Exception as e:
            logging.error(f"Error processing entity {entity}: {e}")
    logging.info(f"-------------->final_ref_id_holding:{final_ref_id_holding}")
    return request_sending, final_ref_id_holding


def process_request(user_input):
    """ Parses user input, validates required fields, logs processing steps, and performs the corresponding API call. """
    logs = []
    try:
        # Parse user input
        parsed = generate_prompt(user_input)
        logs.append({"type": "debug", "message": "Parsed input", "data": parsed})
        operation = parsed.get("operation")
        logs.append({"type": "info", "message": f"Operation: {operation}"})
        entities = parsed.get("entities", [])
        logs.append({"type": "info", "message": "Entities", "data": entities})
        for entity in entities:
            entity_name = entity.get("entity")
            entity_parameters = entity.get("parameters")
            logs.append({"type": "info", "message": f"Processing entity: {entity_name}"})
            logs.append({"type": "info", "message": "Entity parameters", "data": entity_parameters})
            # Extract and log each parameter
            if isinstance(entity_parameters, dict):
                for key, value in entity_parameters.items():
                    logs.append({"type": "param", "key": key, "value": value})
            elif isinstance(entity_parameters, list):
                for params in entity_parameters:
                    for key, value in params.items():
                        logs.append({"type": "param", "key": key, "value": value})
            # Required field validation per entity + operation
            if entity_name == "recon" and operation == "create":
                required_fields = ["reconName", "reconType"]
                params = ensure_all_fields_present(entity_parameters, required_fields, entity_name)
                logs.append({"type": "debug", "message": "Validated recon fields", "data": params})
            elif entity_name == "recon_side_configure" and operation == "create":
                required_fields = ["reconName", "summary_side"]
                params = ensure_all_fields_present(entity_parameters, required_fields, entity_name)
                logs.append({"type": "debug", "message": "Validated recon_side_configure fields", "data": params})
            elif entity_name == "source" and operation == "create":
                required_fields = ["sourceName"]
                params = ensure_all_fields_present(entity_parameters, required_fields, entity_name)
                logs.append({"type": "debug", "message": "Validated source fields", "data": params})
        logs.append({"type": "info", "message": "Final structured payload", "data": parsed})
        # Perform API call
        api_response, name_holding = endpoint_worker(parsed)
        logs.append({"type": "success", "message": "API response", "data": api_response})
        logs.append({"type": "success", "message": "Name holding info", "data": name_holding})
        return {
            "status": "success",
            "api_response": api_response,
            "name_holding": name_holding,
            "logs": logs
        }

    except Exception as e:
        logs.append({"type": "error", "message": f"Exception occurred: {str(e)}"})
        return {
            "status": "error",
            "error": str(e),
            "logs": logs
        }

