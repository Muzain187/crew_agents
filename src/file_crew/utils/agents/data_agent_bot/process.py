from file_crew.utils.agents.data_agent_bot.validators import ensure_all_fields_present
from file_crew.utils.agents.data_agent_bot.request_worker import endpoint_worker
import logging,json
from file_crew.utils.common.constants import app_endpoints
from file_crew.utils.agents.data_agent_bot.request_worker import endpoint_worker
from file_crew.utils.common.templates.engine_bots import prompt_enginnering
# from file_crew.utils.agents.data_agent_bot.llm_generative_model import LLMGenerativeModel
from file_crew.utils.common.config import apikey_config,LLMModel
import google.generativeai as genai
genai.configure(api_key=apikey_config.GOOGLE_API_KEY)

logging.basicConfig(
    filename="agent_chat.log",
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
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