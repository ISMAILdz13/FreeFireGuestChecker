# Contributing to Free Fire Guest Account Checker

First off, thanks for taking the time to contribute! 

All types of contributions are encouraged and valued. Please make sure to read the relevant section before making your contribution. It will make it a lot easier for us maintainers and smooth out the experience for all involved.


## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.


## How Can I Contribute?

### Reporting Bugs

This section guides you through submitting a bug report. Following these guidelines helps maintainers and the community understand your report, reproduce the behavior, and find related reports.

- **Use GitHub Issues**: Use the [GitHub Issues](https://github.com/ISMAILdz13/FreeFireGuestChecker/issues) to report bugs.
- **Check Existing Issues**: Before creating a new issue, check if the issue already exists.
- **Provide Detailed Information**:
  - A clear and descriptive title
  - Steps to reproduce the issue
  - Expected behavior
  - Actual behavior
  - Screenshots or error messages if applicable
  - Your operating system and Python version
  - The version of the software you're using


### Suggesting Enhancements

This section guides you through submitting an enhancement suggestion, including completely new features and minor improvements to existing functionality.

- **Use GitHub Issues**: Create a new issue with the "enhancement" label.
- **Provide Context**:
  - What problem does this enhancement solve?
  - How would this enhancement benefit users?
  - Are there any potential drawbacks?


### Pull Requests

This section guides you through submitting a pull request.

1. **Fork the Repository**: Fork the project on GitHub.
2. **Create a Feature Branch**: Create a new branch from `main` for your feature or bug fix.
3. **Commit Your Changes**: Make small, focused commits with descriptive messages.
4. **Push to Your Fork**: Push your changes to your fork.
5. **Open a Pull Request**: Open a PR to the main repository's `main` branch.
6. **Follow the Template**: Fill out the PR template with all required information.


## Development Setup

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- Git


### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/ISMAILdz13/FreeFireGuestChecker.git
   cd FreeFireGuestChecker
   ```

2. **Install development dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements_dev.txt
   ```

3. **Set up pre-commit hooks (optional)**:
   ```bash
   pre-commit install
   ```


### Running Tests

To run all tests:
```bash
pytest
```

To run tests with coverage:
```bash
pytest --cov=src --cov=tests --cov-report=html
```

To run a specific test file:
```bash
pytest tests/test_validators.py
```


### Code Style

This project uses:
- **Ruff** for linting
- **Black** for code formatting
- **isort** for import sorting

Run the following commands to check and fix code style:

```bash
# Check code style
ruff check .

# Format code
black .
isort .

# Or use the pre-commit hooks
pre-commit run --all-files
```


### Type Checking

This project uses **mypy** for static type checking:

```bash
mypy src tests
```


## Project Structure

```
FreeFireGuestChecker/
├── config/                  # Configuration management
│   ├── __init__.py
│   ├── settings.py          # Application settings
│   ├── secrets.py           # Secrets management
│   └── runtime.py           # Runtime configuration
│
├── src/                     # Source code
│   ├── __init__.py
│   ├── level/               # Level bot modules
│   │   ├── auth.py          # Authentication
│   │   ├── guest_info.py    # Guest info retrieval
│   │   └── *.pb2.py         # Protobuf definitions
│   ├── utils/               # Utility modules
│   │   ├── __init__.py
│   │   ├── logging.py       # Logging utilities
│   │   ├── helpers.py       # Helper functions
│   │   ├── crypto.py        # Cryptography utilities
│   │   ├── network.py       # Network utilities
│   │   └── validators.py    # Data validators
│   └── database/            # Database modules
│       ├── __init__.py
│       ├── models.py        # Database models
│       ├── database.py      # Database operations
│       └── migrations.py    # Database migrations
│
├── web/                     # Web interface
│   ├── __init__.py
│   ├── app.py               # Flask application
│   ├── routes.py            # API routes
│   └── models.py            # Web models
│
├── scripts/                 # Utility scripts
│   ├── __init__.py
│   ├── backup_database.py   # Database backup
│   ├── generate_accounts.py # Account generation
│   └── ...
│
├── templates/               # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── accounts.html
│   └── ...
│
├── tests/                   # Test suite
│   ├── __init__.py
│   ├── test_validators.py
│   ├── test_database.py
│   ├── test_utils.py
│   ├── test_auth.py
│   └── test_api.py
│
├── data/                    # Data files
│   ├── guests.json
│   ├── level_accounts.json
│   └── guest_report.json
│
├── config/                  # Configuration files
│   └── settings.json
│
├── logs/                    # Log files
│
├── guest_checker.py         # Original CLI tool
├── guest_checker_v2.py      # Enhanced CLI tool
├── requirements.txt         # Production dependencies
├── requirements_dev.txt     # Development dependencies
├── README.md
├── CHANGELOG.md
├── LICENSE
└── CONTRIBUTING.md
```


## Commit Messages

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification for commit messages:

- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation only changes
- `style`: Changes that do not affect the meaning of the code (white-space, formatting, missing semi-colons, etc)
- `refactor`: A code change that neither fixes a bug nor adds a feature
- `perf`: A code change that improves performance
- `test`: Adding missing tests
- `chore`: Changes to the build process or auxiliary tools and libraries


## Pull Request Template

Please use the following template for your pull requests:

```markdown
## Description

Please include a summary of the change and which issue is fixed. Please also include relevant motivation and context.

Fixes # (issue)

## Type of Change

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Code style update (formatting, renaming)
- [ ] Refactoring (no functional changes, no api changes)
- [ ] Build related changes
- [ ] Other (please describe):

## Checklist

- [ ] My code follows the style guidelines of this project
- [ ] I have performed a self-review of my code
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Any dependent changes have been merged and published in downstream modules
```


## License

By contributing, you agree that your contributions will be licensed under the project's MIT License.


## Support

If you have any questions or need help, please open an issue on GitHub or contact the maintainers.

Thank you for contributing to Free Fire Guest Account Checker!
