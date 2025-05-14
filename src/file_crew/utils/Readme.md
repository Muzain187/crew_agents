
 Structure explanation:
 
execute_v2/
├── agents/         -> bots or agents
│   └── data_agent_bot/
│       └── __init__.py
│
├── common/         -> shared code (maybe constants, errors, helpers)
├── repository/     -> database access layer (data CRUD functions)
├── resources/      -> static assets / config files
├── schemas/        -> data models and validation schemas
├── utils/          -> general helper functions
├── .env            -> environment variables
└── __init__.py     -> makes execute_v2 a package


common/ - constants.py - please verify the endpoints.json file path
resources/ - app_endpoints.json - please update the token
