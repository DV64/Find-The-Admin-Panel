# Find The Admin Panel - Changelog

All notable changes to this project will be documented in this file.

## [7.1] - 2026-02-27

### Added
- Created `wordlist_updater.py` to isolate wordlist enrichment logic  
- Created `scripts/__init__.py` module to follow standard Python package structure  

### Changed
- **Deep Codebase Audit & Cleanup Initiative**  
- Consolidated constants: removed duplicates from `constants.py` to enforce `Config` as the single source of truth  
- Renamed `logging.py` to `logger.py` to stop shadowing Python's standard library  
- Updated 8 module imports to point to the new `logger.py`  
- Extracted `auto_update_wordlist` from `scan_helper.py` to `wordlist_updater.py`  

### Fixed
- Fixed critical `UnboundLocalError` in `exporter.py` where HTML content crashed upon export  
- Fixed `AttributeError` in `utils.py` by converting invalid `scanner.stop()` call to correct `scanner.stop_scan()`  
- Fixed triple/double-escaped regex patterns (`URL_PATTERN`, `EMAIL_PATTERN`, `IP_ADDRESS_PATTERN`) in `constants.py`  
- Re-architected HTTP HTML exports in `exporter.py` to include full stylized HTML templates  

### Removed
- Deleted `scan_helper.py` (~1150 lines) which contained entirely dead code and duplicated functionality  
- Removed 93 lines of unused functions (`setup_logging`, `setup_directories`, `load_paths`) from `config.py`  
- Cleaned unused imports (`ssl`, `certifi`, `itertools`, `reset_rate_limiter`) across the codebase  

---

## [7.0] - 2025-12-20

### Added
- Full proxy support for HTTP, HTTPS, SOCKS4, and SOCKS5 with automatic rotation  
- Proxy health checking with per-proxy statistics and automatic failover  
- Token bucket rate limiting algorithm with burst support  
- Adaptive rate limiting that adjusts based on server responses  
- Command-line rate limit control with new `--rate-limit` flag  
- Intelligent path fuzzing with configurable depth levels (1-3)  
- Extension variations for automatic path discovery with .php, .asp, .aspx, .jsp, etc.  
- Backup file detection for .bak, .old, .backup, .temp, .orig files  
- Case and separator variations (uppercase, lowercase, CamelCase, underscore, hyphen)  
- Wordlist mutation for generating variations  
- WebSocket endpoint detection  
- GraphQL endpoint discovery with introspection query support  
- REST API identification with Swagger/OpenAPI documentation detection  
- SOAP API and WSDL discovery for XML-based web services  
- Comprehensive input validation to prevent directory traversal and injection attacks  
- Control character filtering for enhanced security  
- URL and path validation with length limits and pattern validation  
- Email and IP address validation for notification configuration  
- Proxy URL validation for secure proxy configuration  
- Filename sanitization to prevent path injection in exports  
- Configurable SSL verification with strict, optional, or disabled modes  
- Environment variable support via python-dotenv integration  
- Notification framework with Email (SMTP), Slack, and Discord webhook support  
- New modules for rate limiting, proxy management, path fuzzing, input validation, and detection  
- Centralized constants module for better maintainability  
- 40+ new configuration options for proxy, browser, notifications, and detection  
- MODE_CONFIGS section for customizable settings per scan mode  

### Changed
- Improved HTTP connection pooling and connection reuse  
- Enhanced concurrent request handling with better resource management  
- Optimized connection timeout handling with backoff strategies  
- Refactored configuration loading for better modularity  
- Improved module organization with better separation of concerns  
- Enhanced error handling patterns throughout the codebase  
- Consistent naming conventions across all modules  
- Better logging with multiple verbosity levels  
- Command-line `--version` flag now requires full flag (no `-v` short form)  
- Verbose flag changed to `-v/-vv/-vvv` to avoid conflict with version  
- Updated README.md with comprehensive v7.0 feature documentation  
- Improved proxy rotation logic for better performance  
- Optimized rate limiting implementation for efficiency  

### Fixed
- Duplicate `-v` flag conflict between version and verbose flags  
- Signal handling inconsistencies across different modules  
- Unicode character handling issues in path processing  
- Path normalization edge cases in various scenarios  
- Connection timeout handling for slow or unresponsive servers  
- Error message formatting for better clarity and consistency  

### Removed
- Machine learning detection feature due to lack of proper training data  
- `--machine-learning` command-line flag  
- `USE_ML_DETECTION` configuration option  
- `scikit-learn` dependency from requirements.txt  
- All references to ML-based detection in code and documentation  

### Security & Performance
- Faster URL validation using compiled regex patterns  
- Reduced memory usage with streaming response handling  
- Prevent injection attacks through comprehensive input validation  
- Secure credential storage preparation with keyring  
- Configurable cache directory and size for better control  
- Connection pool size optimization for improved performance  

---

## [6.1] - 2025-07-17

### Added
- Support for HTTP/3 protocol detection and optimization  
- Machine learning-based admin panel classification for more accurate detection  
- Auto-update system for wordlists and configuration files  
- Multi-language support for UI and logging  
- Integration with web vulnerability scanners  
- Enhanced performance metrics and benchmarking  
- More robust caching system with disk persistence  
- Path fuzzing capabilities for more thorough discovery  
- Enhanced UI with more detailed scan information  
- Real-time status tracking showing found, verified, and rejected results  
- Proper support for different scan modes in command line arguments  
- Verification step for discovered admin panels to reduce false positives  
- Mode-specific path optimization and selection  

### Changed
- Improved scanning algorithm for better detection rate  
- More efficient error handling and retry mechanisms  
- Enhanced concurrent scanning with better resource management  
- Updated user agents list with latest browser versions  
- Refined detection logic to reduce false positives  
- Better management of scan interruptions  
- Modernized terminal UI with more interactive elements  
- Improved confidence calculation to better detect genuine admin panels  
- Reduced false positives by implementing multi-level verification  
- Optimized scanner to handle rate limiting from target websites  
- Updated default configuration settings for each scan mode  
- Improved session management and connection handling  

### Fixed
- Issue with improper URL parsing in some edge cases  
- Memory leak during extended scanning sessions  
- Path validation bugs when using custom wordlists  
- Scanner getting stuck on unresponsive hosts  
- HTTP/2 connection handling errors  
- Timeout handling for slow responding servers  
- Results export formatting issues  
- Concurrency control in high-latency environments  
- Logs and results not being saved correctly by ensuring directories exist  
- False positives in admin panel detection with improved 404 page detection  
- Scan modes behaving similarly; now each has unique behavior  
- Error page detection even when status code is 200  
- Path selection based on scan mode (simple, stealth, aggressive)  
- Verification mechanism to better handle false positives  
- Compatibility with sites using Cloudflare protection  
- Multiple JSON parsing issues with different wordlist formats  

## [6.0] - 2025-05-13

### Added
- Advanced Logging System with separate log files for errors, warnings, and usage
- Ctrl+C handling to stop scans and display results (single press) or exit (double press)
- Consolidated configuration system using only config.json as the source of truth
- New user agents list in config.json with improved browser coverage
- Automatic path validation and limiting based on configuration
- System information logging for better diagnostics
- Automatic log rotation and cleanup of logs older than 30 days
- Usage statistics tracking (scan count, success rate, etc.)
- Added more user-facing feature detection to filter out regular website pages
- Enhanced distinction between user login pages and admin login pages
- New admin-specific pattern recognition to reduce false positives

### Changed
- Enhanced signal handling for better user experience
- Improved result summary display with confidence scores
- Refactored code to remove redundancy and improve maintainability
- All settings now load from config.json exclusively
- Improved error handling and reporting
- Code optimization for better performance
- Adjusted scoring weights for login forms to prioritize admin-related forms
- Enhanced penalty system for user-oriented pages

### Fixed
- Export errors when result objects miss expected keys
- Path count issues when exceeding available paths
- Confidence score calculation to properly handle percentage values
- Various minor bugs and edge cases
- Fixed issue with regular login pages being incorrectly identified as admin 
panels
- Optimized content analysis to better distinguish between admin and user areas
- Addressed reliability issues in confidence scoring for multilingual websites

## [5.0] - 2025-03-20

### Added
- Proxy and VPN support for anonymous scanning
- Headless browser support for enhanced detection
- CAPTCHA and protection system detection
- Advanced technology fingerprinting
- Three scanning modes: simple, aggressive, and stealth
- Multi-site scanning capabilities
- HTML reports with interactive charts and graphs
- Interactive terminal interface with Rich library
- Real-time progress tracking with ETA
- Detailed scan statistics and metrics
- Confidence-based scoring system
- Export in multiple formats (JSON, CSV, HTML, TXT)
- Comprehensive help system with examples
- Settings management system
- Results viewer with filtering capabilities

### Changed
- Enhanced terminal interface with Rich
- Improved progress tracking with detailed statistics
- More accurate confidence scoring for results
- Better handling of network errors and retries
- Support for custom HTTP headers and cookies
- Improved error handling and logging
- Better memory management
- Enhanced proxy rotation system
- Improved technology detection

### Security & Performance
- Optimized asynchronous processing for faster scans
- Better memory management for large target lists
- Improved SSL/TLS handling with security best practices
- Detailed logging for later analysis
- Enhanced security headers detection
- Better CAPTCHA detection algorithms
- Improved form analysis

## [4.0] - 2025-02-24

### Added
- Completely redesigned scanner with modular architecture
- Comprehensive technology detection capabilities
- Advanced form and input field analysis
- Detailed confidence scoring for each potential admin panel
- Multiple export formats (TXT, JSON, CSV)
- Command-line interface with extensive options
- Progress tracking with rich terminal interface

### Changed
- Migrated to fully asynchronous request handling
- Enhanced terminal output with better visuals
- Improved error handling and logging
- More sophisticated analysis of responses

### Security & Performance
- Better handling of network errors and timeouts
- Support for configurable request parameters
- Detailed logging system for debugging

## [3.0] - 2024-12-21

### Added
- Complete rewrite with asynchronous processing
- Enhanced terminal display with Rich library
- Dynamic progress tracking during scans
- Detailed analysis of responses with BeautifulSoup
- Technology detection capabilities
- Confidence scoring for results
- Cache support for faster rescanning
- Comprehensive logging system
- Support for custom User-Agents

### Changed
- Migrated from simple requests to aiohttp
- Improved error handling and retry logic
- Enhanced terminal output with tables and panels
- Better handling of redirects and status codes

### Security & Performance
- SSL verification options
- Custom timeout handling
- Connection pooling for better performance
- Random User-Agent rotation

## [2.0] - 2024-11-25

### Added
- Multi-threaded scanning with ThreadPoolExecutor
- Colorful terminal output with Colorama
- Enhanced UI with better progress reporting
- Support for custom timeout and thread count
- Basic detection of admin panels with improved accuracy
- Ability to save scan results to a file

### Changed
- Migrated from Python 2 to Python 3
- Improved URL handling and validation
- Better handling of HTTP errors and timeouts
- More user-friendly interface with clear instructions

### Security & Performance
- Added timeout for requests to avoid hanging
- Better error handling for connectivity issues
- Support for HTTPS URLs

## [1.1] - 2022-09-06

### Added
- ASCII art banner for better visual appeal
- Improved user interface with clearer instructions
- Better handling of HTTP responses

### Changed
- Cleaner code organization
- Improved error handling for HTTP requests

## [1.0] - 2019-09-3

### Initial Release
- Basic functionality to find admin panels
- Simple command-line interface
- Ability to read paths from a file
- Basic error handling for HTTP requests
- Support for HTTP only (no HTTPS)
