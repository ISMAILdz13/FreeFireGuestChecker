# Changelog

All notable changes to Free Fire Guest Account Checker will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [v2.0.0] - 2026-01-05

### Added

#### Core Features
- **Enhanced Configuration Management**: Complete configuration system with environment variables, JSON files, and runtime settings
- **Proxy Support**: Full proxy support (HTTP, HTTPS, SOCKS4, SOCKS5) with rotation and failover
- **Rate Limiting**: Configurable rate limiting with automatic retries and exponential backoff
- **Comprehensive Logging**: Structured logging with colored output, file rotation, and JSON format support
- **Database Storage**: Full SQLite database support for account management and check history
- **Account Generation**: Built-in account generator with customizable prefixes and regions
- **Web Interface**: Flask-based web interface with REST API and dashboard
- **Multiple Input Formats**: Support for JSON, CSV, and database input sources
- **Multiple Export Formats**: Export to JSON, CSV, and database
- **Health Checks**: Server status monitoring and connectivity checks
- **Data Validation**: Comprehensive validation for all input data
- **Error Handling**: Robust error handling with detailed error messages

#### Configuration System
- **Settings Module**: Hierarchical configuration with defaults, file-based config, and environment variable overrides
- **Secrets Management**: Secure handling of sensitive data with optional encryption
- **Runtime Configuration**: Dynamic runtime state management
- **Config Manager**: Centralized configuration loading and merging

#### Database Features
- **Account Storage**: Store and manage unlimited guest accounts
- **Check History**: Track complete history of account checks
- **Query Capabilities**: Advanced filtering and pagination
- **Batch Operations**: Efficient bulk operations for large datasets
- **Import/Export**: Import from and export to various formats
- **Migrations**: Database schema versioning and migration support
- **Backup/Restore**: Automatic and manual backup functionality

#### Web Interface
- **Dashboard**: Overview of account statistics with visual charts
- **Accounts Page**: Browse, filter, and manage accounts
- **Check Page**: Initiate account checks with customizable options
- **Settings Page**: Configure application settings via web interface
- **REST API**: Full REST API with JSON responses
- **Authentication**: API key-based authentication
- **CORS Support**: Cross-origin resource sharing support

#### CLI Enhancements
- **Rich Command Line**: Enhanced CLI with colored output and progress indicators
- **Multiple Input Sources**: Load accounts from JSON, CSV, or database
- **Concurrency Control**: Configurable number of concurrent workers
- **Proxy Options**: Command-line proxy configuration
- **Output Options**: Multiple output formats and destinations
- **Dry Run Mode**: Validate input without performing checks

#### Utility Modules
- **Cryptography**: AES encryption/decryption utilities
- **Network**: HTTP client management with proxy support
- **Helpers**: Common utility functions for strings, files, timing
- **Validators**: Data validation for all input types
- **Logging**: Enhanced logging with multiple formats and handlers

#### Testing
- **Comprehensive Test Suite**: Unit tests for all major components
- **Validation Tests**: Tests for all validation functions
- **Database Tests**: Tests for all database operations
- **Utility Tests**: Tests for utility functions
- **Authentication Tests**: Tests for auth module
- **API Tests**: Tests for web API endpoints

#### Scripts
- **Backup Script**: Database backup and restore operations
- **Generation Script**: Account generation utilities
- **Migration Script**: Database migration management
- **Validation Script**: Data validation utilities
- **Export/Import Scripts**: Data export and import operations
- **Cleanup Script**: Cleanup old files and database entries
- **Health Check Script**: Server health monitoring


### Changed

#### Architecture Improvements
- **Modular Design**: Refactored into separate modules (config, database, utils, web, scripts)
- **Type Hints**: Added comprehensive type hints throughout the codebase
- **Error Handling**: Improved error handling with custom exceptions
- **Documentation**: Enhanced docstrings and comments
- **Code Organization**: Better organized code structure

#### Performance Optimizations
- **Connection Pooling**: HTTP client connection pooling
- **Async Operations**: Full async/await support for all I/O operations
- **Batch Processing**: Efficient batch operations for large datasets
- **Memory Management**: Better memory handling for large operations


### Fixed

- **Error Recovery**: Automatic retry on network errors
- **Rate Limiting**: Proper handling of rate limits and cooldowns
- **Proxy Failover**: Automatic proxy rotation on failure
- **Data Validation**: Comprehensive validation of all input data
- **Resource Cleanup**: Proper cleanup of resources (HTTP clients, database connections)


## [v1.0.0] - 2026-07-29

### Added

- Initial public release
- Basic guest account checking functionality
- OAuth authentication
- MajorLogin support
- Protobuf parsing for player information
- JSON input/output support
- Terminal-based UI with colored output
- Basic error handling


---

## Versioning

We use [Semantic Versioning](https://semver.org/) for versioning. For the versions available, see the [tags on this repository](https://github.com/ISMAILdz13/FreeFireGuestChecker/tags).


## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct, and the process for submitting pull requests to us.


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
