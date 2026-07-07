# Backend

## Project Structure
```
backend/
├── src/
│   ├── api/              # fastapi
│   │   ├── v1/
│   │   │   ├── admin/    # for administrative stuff
│   │   │   ├── annotate/ # annotation for normal users
│   │   │   ├── auth/     # open routes for authentication (cookie with user uuid)
│   │   │   ├── dataset/  # import/export of datasets
│   │   │   ├── __init__.py
│   │   │   └── router.py
│   │   ├── middleware/   # for access management
│   │   ├── __init__.py
│   │   └── router.py
│   ├── migrations/
│   │   └── 0001_initial_schema.sql
│   ├── models/           # pydantic models
│   ├── schema/           # sqlalchemy models
│   └── main.py           # Entrypoint
└── tests/                # pytest tests
```
