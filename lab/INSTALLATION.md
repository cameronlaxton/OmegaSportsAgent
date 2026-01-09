# OmegaSports Validation Lab: Installation & Setup Guide

## System Requirements

### Software
- **Python**: 3.10 or higher
- **Git**: Latest stable version
- **Operating System**: macOS, Linux, or Windows

### Hardware Recommendations
- **CPU**: 4+ cores (simulation parallelization benefits from multiple cores)
- **RAM**: 8GB minimum, 16GB recommended (for running multiple simulations)
- **Storage**: 10GB free space (for historical data and experiment results)
- **Network**: Stable internet connection (for data scraping)

### Python Version Check

```bash
python --version
# Output should be: Python 3.10.x or higher
```

If you need to upgrade Python:
- **macOS**: `brew install python@3.11`
- **Linux (Ubuntu)**: `sudo apt-get install python3.11`
- **Windows**: Download from [python.org](https://www.python.org/downloads/)

## Installation Steps

### 1. Clone Repository

```bash
# Using HTTPS
git clone https://github.com/cameronlaxton/OmegaSports-Validation-Lab.git
cd OmegaSports-Validation-Lab

# Or using SSH (if SSH keys configured)
git clone git@github.com:cameronlaxton/OmegaSports-Validation-Lab.git
cd OmegaSports-Validation-Lab
```

### 2. Create Virtual Environment

A virtual environment isolates project dependencies from system Python.

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate

# Verify activation (prompt should show (venv))
which python  # macOS/Linux
where python  # Windows
```

### 3. Install Dependencies

```bash
# Upgrade pip first (recommended)
pip install --upgrade pip

# Install all requirements
pip install -r requirements.txt

# Verify installation
python -c "import pandas, numpy, scipy; print('✓ Core dependencies installed')"
```

### 4. Configure Environment Variables

Ensure .env file exists
```

### 5. Initialize Project Structure

```bash
# Create required directories
mkdir -p data/historical
mkdir -p data/experiments
mkdir -p data/logs
mkdir -p data/cache
mkdir -p notebooks
mkdir -p reports

# Verify structure
tree -L 2 -I '__pycache__'
```

### 6. Verify Installation

```bash
# Run basic tests
python -m pytest tests/ -v

# Expected output:
# tests/test_data_pipeline.py PASSED
# tests/test_simulation_framework.py PASSED
# ... (all tests pass)
```

## Integration with OmegaSports Engine

The lab expects access to the OmegaSports engine. Two integration options:

### Option A: Local Installation

If OmegaSports is installed locally:

```bash
# In .env file, set path to local OmegaSports
OMEGA_ENGINE_PATH=../OmegaSportsAgent

# Verify integration
python -c "from omega.simulation.simulation_engine import run_game_simulation; print('✓ OmegaSports engine accessible')"
```

### Option B: Package Installation (Future)

When OmegaSports is published to PyPI:

```bash
# Uncomment in requirements.txt:
# omega-sports-engine>=1.0.0

pip install omega-sports-engine
```

## Verification Checklist

Run through this checklist to verify complete setup:

```bash
#!/bin/bash

echo "Verifying OmegaSports Validation Lab Setup..."
echo

# Python version
echo "[1/6] Python Version"
python --version | grep -E 'Python 3.(10|11|12)' && echo "✓ PASS" || echo "✗ FAIL"

# Virtual environment
echo "[2/6] Virtual Environment"
[[ "$VIRTUAL_ENV" != "" ]] && echo "✓ PASS" || echo "✗ FAIL"

# Dependencies
echo "[3/6] Core Dependencies"
python -c "import pandas, numpy, scipy, matplotlib; print('✓ PASS')" 2>/dev/null || echo "✗ FAIL"

# Test suite
echo "[4/6] Test Suite"
python -m pytest tests/ -q 2>/dev/null && echo "✓ PASS" || echo "✗ FAIL"

# Directory structure
echo "[5/6] Directory Structure"
test -d data/historical && test -d data/experiments && test -d notebooks && echo "✓ PASS" || echo "✗ FAIL"

# OmegaSports integration
echo "[6/6] OmegaSports Integration"
python -c "from core.simulation_framework import SimulationFramework; print('✓ PASS')" 2>/dev/null || echo "✗ FAIL"

echo
echo "Setup verification complete!"
```

Run it:

```bash
bash verify_setup.sh
```

## Troubleshooting

### Issue: "Python not found" or wrong version

**Solution:**
```bash
# Find installed Python versions
ls /usr/bin/python*          # Linux/macOS
where python.exe             # Windows

# Use specific version
python3.11 -m venv venv
```

### Issue: Permission denied on macOS/Linux

**Solution:**
```bash
# Grant execute permissions
chmod +x venv/bin/activate
chmod +x venv/bin/python
```

### Issue: Virtual environment not activating

**Solution:**
```bash
# Verify activation command for your shell
# Bash/Zsh:
source venv/bin/activate

# Fish:
source venv/bin/activate.fish

# PowerShell (Windows):
venv/Scripts/Activate.ps1
```

### Issue: Dependencies fail to install

**Solution:**
```bash
# Upgrade pip, setuptools, wheel
pip install --upgrade pip setuptools wheel

# Clear pip cache
pip cache purge

# Retry installation
pip install -r requirements.txt --no-cache-dir
```

### Issue: "ModuleNotFoundError: No module named 'omega'"

**Solution:**
```bash
# Option 1: Verify OMEGA_ENGINE_PATH in .env
cat .env | grep OMEGA_ENGINE_PATH

# Option 2: Add engine path to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:../OmegaSportsAgent"

# Option 3: Install engine from PyPI (when available)
pip install omega-sports-engine
```

### Issue: Jupyter kernel not found

**Solution:**
```bash
# Install ipykernel
pip install ipykernel

# Register kernel
python -m ipykernel install --user --name venv --display-name "OmegaSports Lab"

# Use in Jupyter: kernel dropdown -> OmegaSports Lab
```

## Development Setup (Optional)

For development and contribution:

```bash
# Install development dependencies
pip install black flake8 mypy isort pytest-cov pytest-xdist

# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Format code
black .
isort .

# Run tests with coverage
pytest --cov=core --cov=modules tests/
```

## Docker Setup (Optional)

For reproducible environment across systems:

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Create data directories
RUN mkdir -p data/{historical,experiments,logs,cache}

# Default command
CMD ["python", "run_all_modules.py"]
```

Build and run:

```bash
docker build -t omega-sports-lab .
docker run -v $(pwd)/data:/app/data omega-sports-lab
```

## IDE Setup

### VSCode

```json
// .vscode/settings.json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "[python]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "ms-python.python"
  },
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"]
}
```

### PyCharm

1. Open project settings
2. Go to Project -> Python Interpreter
3. Select "Existing Environment"
4. Navigate to `venv/bin/python` (macOS/Linux) or `venv\Scripts\python.exe` (Windows)
5. Apply and OK

## Next Steps

After successful installation:

1. **Review Documentation**
   - Read [ARCHITECTURE.md](./ARCHITECTURE.md) for system design
   - Review [EXPERIMENTS.md](./EXPERIMENTS.md) for experiment protocols
   - Check module READMEs in `modules/*/README.md`

2. **Run First Experiment**
   ```bash
   python modules/01_edge_threshold/run_experiment.py
   ```

3. **Explore Notebooks**
   ```bash
   jupyter lab notebooks/01_data_exploration.ipynb
   ```

4. **Run All Modules**
   ```bash
   python run_all_modules.py
   ```

## Support

For issues or questions:
1. Check this guide's Troubleshooting section
2. Review [ARCHITECTURE.md](./ARCHITECTURE.md) technical details
3. Check GitHub issues: [Issues](https://github.com/cameronlaxton/OmegaSports-Validation-Lab/issues)
4. Contact: Cameron Laxton

## Keeping Updated

```bash
# Pull latest changes
git pull origin main

# Update dependencies
pip install -r requirements.txt --upgrade

# Verify installation
python -m pytest tests/ -q
```

Happy experimenting! 🚀
