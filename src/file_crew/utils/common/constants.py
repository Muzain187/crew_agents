from file_crew.utils.utils.files import file_load

# ENDPOINTS_RESOURCE_PATH: str = 'vm_agent/resources/app_endpoints.json'
ENDPOINTS_RESOURCE_PATH: str = r'D:\AI_AGENTS\crew_agents\src\file_crew\utils\resources\app_endpoints.json'

app_endpoints = file_load(ENDPOINTS_RESOURCE_PATH)
