# Contributing to Aestimare

Thank you for your interest in contributing to Aestimare! This document provides guidelines and instructions for contributing.

## Code of Conduct

This project adheres to a Code of Conduct that all contributors are expected to follow. Please be respectful and constructive in all interactions.

## How to Contribute

### Reporting Bugs

If you find a bug, please open an issue with:

- **Clear title and description**: What happened vs. what you expected
- **Steps to reproduce**: Detailed steps to reproduce the issue
- **Environment information**: Python version, OS, AWS CLI version, etc.
- **Error messages**: Full error tracebacks or log excerpts
- **Configuration**: Redacted version of your config (remove sensitive data)

### Suggesting Enhancements

We welcome feature suggestions! Please open an issue with:

- **Use case**: What problem does this solve?
- **Proposed solution**: How should it work?
- **Alternatives considered**: Other approaches you've thought about

### Pull Requests

1. **Fork the repository** and create a feature branch
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Follow existing code style and conventions
   - Add tests if applicable
   - Update documentation as needed

3. **Test your changes**
   ```bash
   # Run with test data
   python aestimare.py --config config/accounts.example.yaml
   ```

4. **Commit your changes**
   - Write clear, descriptive commit messages
   - Reference issue numbers if applicable

5. **Push and create a Pull Request**
   - Provide a clear description of changes
   - Link to related issues
   - Request review from maintainers

## Development Setup

1. **Clone your fork**
   ```bash
   git clone https://github.com/your-username/aestimare.git
   cd aestimare
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up test configuration**
   ```bash
   cp config/accounts.example.yaml config/accounts.yaml
   # Edit with test accounts/orgs
   ```

## Code Style

- **Python**: Follow PEP 8 style guidelines
- **Line length**: Maximum 100 characters
- **Docstrings**: Use Google-style docstrings
- **Type hints**: Include type hints for function parameters and returns
- **Imports**: Organize imports (stdlib, third-party, local)

Example:
```python
from typing import Dict, List, Optional
import logging

def collect_data(profile: str, region: Optional[str] = None) -> Dict:
    """
    Collect data from AWS account.
    
    Args:
        profile: AWS CLI profile name
        region: Optional AWS region (None for global services)
    
    Returns:
        Dictionary containing collected data
    """
    # Implementation
    pass
```

## Testing

- Test with non-production AWS accounts when possible
- Use GitHub test organizations or personal repos
- Verify report generation works correctly
- Check for regressions in existing functionality

## Documentation

- Update README.md for user-facing changes
- Add docstrings for new functions and classes
- Update inline comments for complex logic
- Include examples in docstrings when helpful

## Project Structure

```
aestimare/
├── analyzers/          # LLM analysis engines
├── collectors/         # Data collection modules
├── config/             # Configuration files
├── generators/         # Report generation
├── prompts/            # LLM prompt templates
├── aestimare.py        # Main entry point
└── requirements.txt     # Dependencies
```

## Areas for Contribution

- **New collectors**: Support for additional AWS services or data sources
- **Enhanced analysis**: Improved LLM prompts or analysis logic
- **Report improvements**: Better report formatting or additional sections
- **Performance**: Optimization of data collection or processing
- **Documentation**: Improvements to README, code comments, or examples
- **Testing**: Additional test coverage or test utilities

## Review Process

- All PRs require review before merging
- Maintainers may request changes
- Address feedback promptly
- Be patient - reviews may take time

## Questions?

- Open an issue for questions or clarifications
- Check existing issues and discussions
- Reach out to maintainers if needed

Thank you for contributing to Aestimare!
