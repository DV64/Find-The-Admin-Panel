# Find The Admin Panel

A powerful and advanced web scanning tool designed to discover admin panels, login pages, and administrative interfaces on websites. Features multiple scanning modes, intelligent path fuzzing, proxy support, rate limiting, and comprehensive reporting.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.7%2B-orange)
![Version](https://img.shields.io/badge/version-7.0-green)
![Last Updated](https://img.shields.io/badge/last%20updated-Dec%202025-yellow)

<div align="center">
  <img src="https://img.shields.io/badge/Security-Tool-red.svg" alt="Security Tool">
  <img src="https://img.shields.io/badge/Web-Scanner-blue.svg" alt="Web Scanner">
  <img src="https://img.shields.io/badge/Admin-Finder-green.svg" alt="Admin Finder">
</div>

## Features

- **Advanced Scanning**: Multiple scan modes (simple, stealth, aggressive) with distinct behaviors  
- **Smart Detection**: Analyzes responses with improved error page detection to reduce false positives  
- **Intelligent Path Fuzzing**: Configurable depth levels (1-3) for thorough discovery  
- **Proxy Support**: HTTP, HTTPS, SOCKS4, and SOCKS5 with automatic rotation and health checking  
- **Rate Limiting**: Token bucket algorithm with adaptive adjustment based on server responses  
- **Input Validation**: Comprehensive security to prevent directory traversal and injection attacks  
- **Advanced Detection**: WebSocket, GraphQL, REST API, and SOAP endpoint discovery  
- **Enhanced Logging**: Comprehensive logging system with auto-creation of required directories  
- **Configuration System**: Tailored settings for each scan mode in `config.json`  
- **Real-time Tracking**: Live progress updates showing found, verified, and rejected results  
- **Ctrl+C Handling**: Press once to stop scan and show results, press twice to exit  
- **Export Options**: Export results to multiple formats (JSON, HTML, CSV, TXT)  
- **Performance**: Asynchronous processing and concurrent requests with mode-specific optimization  
- **User-Friendly**: Rich terminal interface with progress tracking and statistics  
- **20,000+ Paths**: Comprehensive wordlist covering CMS, APIs, databases, cloud platforms, and more  

## Installation

```bash
# Clone the repository
git clone https://github.com/DV64/Find-The-Admin-Panel.git
cd Find-The-Admin-Panel

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Quick Start

### Basic Usage

```bash
python finder.py -u https://example.com
```

### Advanced Usage

```bash
# Aggressive scan with fuzzing
python finder.py -u https://example.com --detection-mode aggressive --fuzzing --fuzzing-depth 2

# Stealth scan with proxy and custom rate limit
python finder.py -u https://example.com --detection-mode stealth --proxy http://127.0.0.1:8080 --rate-limit 10

# Simple scan with results export
python finder.py -u https://example.com --detection-mode simple --export json
```

## Command-Line Options

### Required Arguments

- `-u, --url`: Target URL to scan

### Optional Arguments

**Scanning Options:**
- `-w, --wordlist`: Path to wordlist file (default: paths/general_paths.json)  
- `-e, --export`: Export format (json, html, csv, txt)  
- `-i, --interactive`: Run in interactive mode with UI  
- `--version`: Show version and exit  
- `-v, -vv, -vvv`: Verbosity level (info, debug, trace)  

**Detection Options:**
- `--detection-mode`: Set the detection mode (simple, stealth, aggressive)  
- `--fuzzing`: Enable path fuzzing capabilities  
- `--fuzzing-depth`: Fuzzing depth level (1-3, default: 1)  

**Network Options:**
- `--concurrency`: Set maximum concurrent requests  
- `--rate-limit`: Set custom rate limit (requests per second)  
- `--no-rate-limit`: Disable rate limiting  
- `--proxy`: Proxy URL (http://, https://, socks4://, socks5://)  
- `--proxy-file`: File containing list of proxies  

**Other Options:**
- `--update-wordlist`: Update wordlists with latest paths  

## Scan Modes

The tool offers three distinct scanning modes, each optimized for different scenarios:

### Simple Mode
- **Speed**: Fast scanning with minimal evasion techniques  
- **Paths**: Limited to 1000 paths for quicker results  
- **Concurrency**: 50 concurrent requests  
- **Best For**: Initial reconnaissance or when time is limited  
- **Rate Limit**: 50 req/s (burst: 10)  
- **Confidence Threshold**: 0.5  
- **Command**: `--detection-mode simple`

### Stealth Mode
- **Speed**: Slower scanning with advanced evasion techniques  
- **Paths**: Limited to 500 carefully selected paths  
- **Concurrency**: 10 concurrent requests  
- **Best For**: Avoiding detection by WAFs and security systems  
- **Rate Limit**: 5 req/s (burst: 2)  
- **Confidence Threshold**: 0.7  
- **Features**: Delays between requests, randomization, admin keyword filtering  
- **Command**: `--detection-mode stealth`

### Aggressive Mode
- **Speed**: Maximum speed scanning with comprehensive path checking  
- **Paths**: All 20,000 available paths  
- **Concurrency**: 100 concurrent requests  
- **Best For**: Thorough scanning when speed and coverage are priorities  
- **Rate Limit**: 50 req/s (burst: 10)  
- **Confidence Threshold**: 0.6  
- **Features**: Result verification to minimize false positives  
- **Command**: `--detection-mode aggressive`

## Path Fuzzing

Enable intelligent path fuzzing to discover hidden admin panels:

```bash
# Basic fuzzing
python finder.py -u https://example.com --fuzzing

# Deep fuzzing (generates more variations)
python finder.py -u https://example.com --fuzzing --fuzzing-depth 3
```

**Fuzzing Features:**
- Extension variations (.php, .asp, .aspx, .jsp, .cfm, etc.)  
- Backup file detection (.bak, .old, .backup, .tmp, etc.)  
- Case variations (lowercase, UPPERCASE, CamelCase)  
- Separator variations (underscore, hyphen)  
- Wordlist mutation for comprehensive discovery  

## Proxy Support

### Single Proxy

```bash
# HTTP proxy
python finder.py -u https://example.com --proxy http://127.0.0.1:8080

# SOCKS5 proxy
python finder.py -u https://example.com --proxy socks5://127.0.0.1:1080
```

### Proxy List (with rotation)

Create a file `proxies.txt`:
```
http://proxy1.example.com:8080
socks5://proxy2.example.com:1080
http://user:pass@proxy3.example.com:3128
```

```bash
python finder.py -u https://example.com --proxy-file proxies.txt
```

**Supported Proxy Types:**
- HTTP/HTTPS  
- SOCKS4  
- SOCKS5  

**Features:**
- Automatic rotation  
- Health checking  
- Performance tracking  
- Failover support  

## Rate Limiting

Control request rate to avoid detection or server overload:

```bash
# Custom rate limit (30 requests per second)
python finder.py -u https://example.com --rate-limit 30

# Disable rate limiting (use with caution)
python finder.py -u https://example.com --no-rate-limit
```

**Features:**
- Token bucket algorithm with burst support  
- Adaptive adjustment based on 429 (Too Many Requests) responses  
- Per-host rate limiting  
- Global rate limiting  

## Advanced Detection

Automatically detects various endpoint types:

- **WebSocket endpoints**: Identifies WebSocket connections  
- **GraphQL endpoints**: Supports introspection queries  
- **REST APIs**: Detects Swagger/OpenAPI documentation  
- **SOAP/WSDL**: Discovers XML-based web services  

## Configuration

All settings are stored in `config/config.json`. This centralized approach allows for easy customization without modifying the source code.

### Key Configuration Settings:

**Version Information:**
- `VERSION`: Current version (7.0)  
- `RELEASE_DATE`: Release date (2025-12-20)  
- `DEVELOPER`: Developer name (DV64)  

**Scanning Settings:**
- `DETECTION_MODES`: Available scan modes  
- `MODE_CONFIGS`: Mode-specific settings  
- `MAX_CONCURRENT_TASKS`: Maximum concurrent requests  
- `CONNECTION_TIMEOUT`: HTTP request timeout  
- `READ_TIMEOUT`: Response read timeout  

**Advanced Features:**
- `USE_PROXY`: Enable proxy support  
- `USE_RATE_LIMITING`: Enable rate limiting  
- `USE_PATH_FUZZING`: Enable path fuzzing  
- `USE_ADVANCED_DETECTION`: Enable endpoint detection  
- `USE_HEADLESS_BROWSER`: Enable browser automation  

**Export & Storage:**
- `EXPORT_FORMATS`: Available export formats  
- `RESULTS_DIR`: Results directory  
- `LOGS_DIR`: Logs directory  

## Response Handling

- **Ctrl+C (once)**: Stop current scan and display found results  
- **Ctrl+C (twice)**: Exit the application completely  

## Directory Structure

```
├── config/
│   └── config.json         # Configuration file
├── logs/                   # Log files directory
│   ├── error.log           # Error logs
│   ├── warning.log         # Warning logs
│   ├── info.log            # Information logs
│   ├── master.log          # Complete logs
│   ├── usage.log           # Usage statistics
│   └── success.txt         # Found admin panels
├── paths/
│   └── general_paths.json  # Default paths file (20,000 paths)
├── results/                # Scan results directory
├── scripts/
│   ├── config.py           # Configuration handling
│   ├── constants.py        # Centralized constants
│   ├── detection.py        # Advanced endpoint detection
│   ├── exporter.py         # Results export functionality
│   ├── input_validator.py  # Security input validation
│   ├── logging.py          # Advanced logging system
│   ├── menu.py             # Interactive menu system
│   ├── path_fuzzer.py      # Intelligent path generation
│   ├── proxy_manager.py    # Proxy pool management
│   ├── rate_limiter.py     # Token bucket rate limiting
│   ├── scan_helper.py      # Helper functions for scanning
│   ├── scanner.py          # Core scanning functionality
│   ├── ui.py               # Terminal UI components
│   └── utils.py            # Utility functions
├── finder.py               # Main application file
├── requirements.txt        # Dependencies
├── CHANGELOG.md            # Version history
└── README.md               # This file
```

## What's New in v7.0

**Added:**
- Full proxy support for HTTP, HTTPS, SOCKS4, and SOCKS5 with automatic rotation  
- Proxy health checking with per-proxy statistics  
- Token bucket rate limiting with adaptive adjustment  
- Intelligent path fuzzing with configurable depth levels  
- WebSocket, GraphQL, REST API, and SOAP endpoint detection  
- Comprehensive input validation to prevent security vulnerabilities  
- Expanded wordlist to 20,000 paths  
- New modules for better code organization  
- Environment variable support  
- Notification framework (Email, Slack, Discord)  

**Changed:**
- Improved HTTP connection pooling  
- Enhanced error handling  
- Better logging with multiple verbosity levels  
- Updated README with comprehensive v7.0 documentation  

**Removed:**
- Machine learning detection feature  

For complete changelog, see [CHANGELOG.md](CHANGELOG.md)

## Examples

### Basic Reconnaissance

```bash
# Quick scan
python finder.py -u https://example.com
```

### Comprehensive Scan

```bash
# Full scan with fuzzing and proxy
python finder.py -u https://example.com \
  --detection-mode aggressive \
  --fuzzing --fuzzing-depth 2 \
  --proxy socks5://127.0.0.1:1080 \
  --export json
```

### Stealth Scan

```bash
# Slow, careful scan to avoid detection
python finder.py -u https://example.com \
  --detection-mode stealth \
  --rate-limit 5 \
  --proxy-file proxies.txt
```

### Development Testing

```bash
# Fast local testing
python finder.py -u http://localhost:8000 \
  --detection-mode simple \
  --no-rate-limit
```

## Tips & Best Practices

1. **Start with Simple Mode**: Test with simple mode first to get quick results  
2. **Use Proxies for Stealth**: Always use proxies when scanning external targets  
3. **Adjust Rate Limits**: Lower rate limits for sensitive targets, higher for controlled environments  
4. **Enable Fuzzing for Thoroughness**: Use fuzzing to discover hidden or obfuscated paths  
5. **Export Results**: Always export results for later analysis  
6. **Review Logs**: Check logs for errors or issues during scanning  
7. **Respect robots.txt**: Be ethical and follow site policies  

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

**IMPORTANT**: This tool is for educational and authorized security testing purposes only.

- Only use on systems you own or have explicit permission to test  
- Unauthorized scanning may be illegal in your jurisdiction  
- The developers assume no liability for misuse of this tool  
- Always follow responsible disclosure practices  

## Credits

Developed and maintained by **DV64** © 2025.  
All rights reserved.

## Support

For issues, feature requests, or questions:
- GitHub Issues: [https://github.com/DV64/Find-The-Admin-Panel/issues](https://github.com/DV64/Find-The-Admin-Panel/issues)
- Developer: DV64

---

**Star this project** ⭐ if you find it useful!
