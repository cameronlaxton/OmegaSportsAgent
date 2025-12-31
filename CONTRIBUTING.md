# Contributing to OmegaSports

Thank you for your interest in contributing to the OmegaSports project! This guide will help you get started with development and contribution workflows.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Development Workflow](#development-workflow)
3. [Git Workflow](#git-workflow)
4. [Running Tests](#running-tests)
5. [Code Style](#code-style)
6. [Submitting Changes](#submitting-changes)

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Git
- pip or uv for package management

### Initial Setup

```bash
# Clone the repository
git clone https://github.com/cameronlaxton/OmegaSportsAgent.git
cd OmegaSportsAgent

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (for scraping)
playwright install chromium

# Verify installation
python test_engine.py
```

---

## Development Workflow

### Setting Up Your Development Environment

1. **Fork the repository** (if contributing externally)
2. **Clone your fork** or the main repository
3. **Create a feature branch** for your changes
4. **Make your changes** and test thoroughly
5. **Submit a pull request** when ready

### Running the Application

```bash
# Run example workflow
python example_complete_workflow.py

# Generate morning bets
python main.py --morning-bets --leagues NBA NFL

# Test scraping
python scraper_engine.py
```

---

## Git Workflow

### Keeping Your Branch Up to Date

Before starting new work or after being away from the project, always sync your local repository with the latest changes from the remote:

```bash
# Fetch all changes from remote
git fetch origin

# Switch to the base branch (e.g., main or develop)
git checkout main  # or develop, depending on the project

# Pull the latest changes
git pull origin main  # or develop

# Now create your feature branch from the updated base
git checkout -b feature/your-feature-name
```

### Creating a Feature Branch

```bash
# Create and switch to a new feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/issue-description
```

### Committing Changes

```bash
# Stage your changes
git add .

# Commit with a descriptive message
git commit -m "feat: add new feature description"

# Push to your branch
git push origin feature/your-feature-name
```

### Commit Message Format

Use conventional commit messages:

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Adding or updating tests
- `refactor:` - Code refactoring
- `chore:` - Maintenance tasks

Example:
```
feat: add support for NHL player props
fix: resolve scraping timeout issue
docs: update GUIDE.md with new examples
```

### Syncing Your Branch with Main

If the main branch has been updated while you were working:

```bash
# Fetch and merge the latest changes
git fetch origin
git checkout main
git pull origin main

# Switch back to your feature branch
git checkout feature/your-feature-name

# Merge main into your branch (or use rebase if preferred)
git merge main

# Resolve any conflicts if they occur
# Then push your updated branch
git push origin feature/your-feature-name
```

---

## Running Tests

### Test Suite

```bash
# Run the main test suite
python test_engine.py

# Run calibration tests
python test_calibration.py

# Run Markov API tests
python test_markov_api.py
```

### Manual Testing

Always test your changes manually:

```bash
# Test with real data
python example_complete_workflow.py

# Test scraping
python scraper_engine.py

# Test specific functionality
python -m omega.workflows.scheduler morning
```

---

## Code Style

### Python Style Guide

- Follow PEP 8 guidelines
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and concise
- Add comments for complex logic

### File Organization

- Place new modules in appropriate directories under `omega/`
- Keep related functionality together
- Update `__init__.py` files as needed

---

## Submitting Changes

### Before Submitting a Pull Request

1. **Run all tests** to ensure nothing is broken
2. **Update documentation** if you've changed functionality
3. **Add tests** for new features
4. **Ensure code follows style guidelines**
5. **Write clear commit messages**

### Pull Request Guidelines

- Provide a clear description of what your PR does
- Reference any related issues
- Include screenshots for UI changes (if applicable)
- Ensure CI checks pass
- Be responsive to code review feedback

### Pull Request Template

```markdown
## Description
Brief description of the changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring

## Testing
- [ ] Tests pass locally
- [ ] Manual testing completed
- [ ] New tests added (if applicable)

## Related Issues
Closes #(issue number)
```

---

## Getting Help

If you have questions or need help:

1. Check the [GUIDE.md](./GUIDE.md) for usage instructions
2. Review existing issues and pull requests
3. Open a new issue with your question
4. Reach out to the maintainers

---

## License

By contributing to this project, you agree that your contributions will be licensed under the same license as the project.

---

Thank you for contributing to OmegaSports! 🚀
