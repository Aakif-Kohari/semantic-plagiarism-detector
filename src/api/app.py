# Enable CORS for external LMS frontends with strict validation and safe wildcard support
from src.api.cors import validate_and_parse_origin

raw_origins_env = os.getenv("CORS_ALLOWED_ORIGINS", "*")
allowed_origins = []
regex_patterns = []

if raw_origins_env.strip() == "*":
    allowed_origins = ["*"]
else:
    for item in raw_origins_env.split(","):
        if not item.strip():
            continue
        exact, regex = validate_and_parse_origin(item)
        if exact:
            allowed_origins.append(exact)
        if regex:
            regex_patterns.append(regex)

# Combine wildcard regex rules if multiple are specified
combined_regex = "|".join(regex_patterns) if regex_patterns else None

# Browser spec: allow_credentials cannot be True when wildcard '*' is used in allowed_origins
allow_credentials = False if ("*" in allowed_origins and not combined_regex) else True

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=combined_regex,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,
)
