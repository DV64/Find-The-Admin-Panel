import re

HTTP_OK = 200
HTTP_MOVED_PERMANENTLY = 301
HTTP_FOUND = 302
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_TOO_MANY_REQUESTS = 429
HTTP_INTERNAL_SERVER_ERROR = 500
HTTP_BAD_GATEWAY = 502
HTTP_SERVICE_UNAVAILABLE = 503
HTTP_GATEWAY_TIMEOUT = 504

DEFAULT_CONNECTION_TIMEOUT = 5
DEFAULT_READ_TIMEOUT = 15
DNS_CACHE_TTL = 300
KEEPALIVE_TIMEOUT = 30.0

DEFAULT_MAX_CONCURRENT_TASKS = 100
DEFAULT_BATCH_SIZE = 50
DEFAULT_LIMIT_PER_HOST = 8
MIN_CONCURRENT_TASKS = 5
MAX_CONCURRENT_TASKS_LIMIT = 500

DEFAULT_RATE_LIMIT = 50
DEFAULT_BURST_SIZE = 10
RATE_LIMIT_MIN = 1
RATE_LIMIT_MAX = 1000

DEFAULT_CACHE_TTL = 3600
DEFAULT_CACHE_SIZE = 1000
MAX_CACHE_SIZE = 100000
CACHE_DIR = ".cache"

MAX_PATHS_SIMPLE = 1000
MAX_PATHS_STEALTH = 500
MAX_PATHS_DEFAULT = 10000

DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0
DEFAULT_RETRY_JITTER = 0.5
DEFAULT_TIMEOUT_BACKOFF_FACTOR = 1.5

DEFAULT_CONFIDENCE_THRESHOLD = 0.6
HIGH_CONFIDENCE_THRESHOLD = 0.8
LOW_CONFIDENCE_THRESHOLD = 0.4

ADMIN_KEYWORDS = [
    'admin', 'administrator', 'admincp', 'adm', 'moderator',
    'dashboard', 'control panel', 'cp', 'panel', 'login',
    'manager', 'cms', 'backend', 'webmaster', 'sysadmin',
    'console', 'portal', 'manage', 'backoffice', 'staff'
]

PRIORITY_PATH_KEYWORDS = [
    'admin', 'administrator', 'dashboard', 'panel', 'control',
    'login', 'cp', 'manage', 'backend', 'webmaster'
]

FUZZING_EXTENSIONS = [
    '.php', '.asp', '.aspx', '.jsp', '.cfm',
    '.html', '.htm', '.shtml', '.py', '.rb'
]

BACKUP_EXTENSIONS = [
    '.bak', '.old', '.backup', '.orig', '.save',
    '.tmp', '.temp', '.swp', '~', '.copy'
]

ERROR_KEYWORDS = [
    "404", "not found", "error", "page not found", "doesn't exist",
    "page does not exist", "cannot be found", "access denied", "forbidden",
    "no encontrada", "não encontrada", "nie znaleziono", "не найдено",
    "找不到", "存在しません", "صفحة غير موجودة"
]

ERROR_PHRASES = [
    "page cannot be found", "page you requested could not be found",
    "page you are looking for does not exist", "404 error",
    "page doesn't exist", "resource cannot be found",
    "site you were looking for doesn't exist",
    "file or directory not found", "requested url was not found"
]

USER_FACING_INDICATORS = [
    'shopping cart', 'add to cart', 'checkout', 'product', 'category',
    'blog post', 'comment', 'article', 'news', 'contact us', 'about us',
    'privacy policy', 'terms of service', 'faq', 'help center'
]

PROXY_TYPES = ['http', 'https', 'socks4', 'socks5']

DETECTION_MODES = ['simple', 'aggressive', 'stealth']

EXPORT_FORMATS = ['txt', 'json', 'csv', 'html']

MAX_URL_LENGTH = 2048
MAX_PATH_LENGTH = 2000
MAX_FILENAME_LENGTH = 255

URL_PATTERN = re.compile(
    r'^https?://'
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
    r'localhost|'
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
    r'(?::\d+)?'
    r'(?:/?|[/?]\S+)$', re.IGNORECASE
)

EMAIL_PATTERN = re.compile(
    r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
)

IP_ADDRESS_PATTERN = re.compile(
    r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
    r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
)

FORBIDDEN_PATH_CHARS = ['..', '\x00', '\n', '\r', '%00', '%0a', '%0d']

LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
LOG_MAX_BYTES = 10 * 1024 * 1024
LOG_BACKUP_COUNT = 5
