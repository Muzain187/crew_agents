from file_crew.utils.common.constants import app_endpoints as endpoints
import requests,json,logging

def names_refid_collecting(name_holding):
    """Collects reference IDs by sending requests for each list value or single value in the input dictionary."""
    ref_id_holding = []
    list_keys = {k for k, v in name_holding.items() if isinstance(v, list)}
    if list_keys:
        for key in list_keys:
            for item in name_holding[key]:
                param = name_holding.copy()
                param[key] = item
                logging.info(f"---------------> value contain list:{param}")
                ref_id_fetching = request_worker("read", "reference_id", param, None, None,None)
                ref_id_data, _ = ref_id_fetching
                ref_id_holding.append(ref_id_data)
    else:
        logging.info(f"--------------> value not containing list :{name_holding}")
        ref_id_fetching = request_worker("read", "reference_id", name_holding, None, None,None)
        ref_id_data, _ = ref_id_fetching  # unpack the 1st tuple for eg: ({'recon_ref_id': ['r1234566']}, {})
        ref_id_holding.append(ref_id_data)
    logging.info(f"------------> Final reference IDs collected: {ref_id_holding}")
    return ref_id_holding

# def request_worker(operation, entity, parameter, url, method):
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
                # headers = {"X-Access-Token": token}
            elif url is None and method is None and entity in ["get_summary_ref_id","side_ref_id",'get_rule_ref_id',
                                                               "get_matching_condition","matching_rule_type_fetching","match_status"]:
            # elif url is None and method is None and operation in ["create","update"]:
                url= endpoint["url"]
                if entity in ["get_rule_ref_id" , "get_summary_ref_id","side_ref_id"]:
                    url = f'{url}{parameter}'
                    logging.info(f"-------------->recon name updation id url test:{url}")
                    parameter={"reconName":parameter}
                # elif entity == "get_summary_ref_id":
                #     parameter = {"reconName":parameter}
                elif entity == "matching_rule_type_fetching":
                    parameter = {"dropdownType": "matching_rule_type"}
                method = endpoint["method"]
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
            if entity not in ["reference_id", "get_summary_ref_id","side_ref_id","get_rule_ref_id", "get_matching_condition","matching_rule_type_fetching","match_status"]:
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