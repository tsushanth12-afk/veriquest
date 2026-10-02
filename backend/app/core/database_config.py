"""Credential-safe database configuration; no administrative fallback."""
from urllib.parse import unquote, urlsplit, parse_qsl


def validate_database_url(value: str, role: str | None = None) -> str:
    try:
        url = urlsplit(value)
        user = unquote(url.username or '')
        options = parse_qsl(url.query, strict_parsing=True)
        if (not isinstance(value, str) or value != value.strip()
                or url.scheme not in {'postgres', 'postgresql'} or not url.hostname
                or not url.password or url.path in {'', '/'} or url.fragment
                or user not in {'vq_api', 'vq_worker'}
                or (role is not None and user != role)
                or any(ord(c)<32 for c in value)
                or len(options)>1
                or any(k!='sslmode' or v not in {'disable','allow','prefer','require','verify-ca','verify-full'} for k,v in options)):
            raise ValueError
        _ = url.port
        return value
    except (ValueError, TypeError, AttributeError):
        raise ValueError('Explicit PostgreSQL configuration for the intended limited role is required') from None
