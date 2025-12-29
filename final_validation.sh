#!/bin/bash
# Final validation script for OmegaSportsAgent

echo "============================================="
echo "OmegaSportsAgent Final Validation"
echo "============================================="
echo

echo "1. Checking Python version..."
python --version
echo

echo "2. Testing module imports..."
python -c "
from omega.schema import GameData, BettingLine
from omega.simulation.simulation_engine import run_game_simulation
from omega.betting.odds_eval import edge_percentage
from omega.workflows.morning_bets import run_morning_workflow
from scraper_engine import fetch_sports_markdown
print('✅ All core modules imported successfully')
"
echo

echo "3. Running test suite..."
python test_engine.py | tail -5
echo

echo "4. Testing example workflow..."
python example_complete_workflow.py > /tmp/workflow_output.txt 2>&1
if grep -q "Workflow Complete" /tmp/workflow_output.txt; then
    echo "✅ Example workflow completed successfully"
    grep "qualified bet" /tmp/workflow_output.txt
else
    echo "❌ Example workflow failed"
fi
echo

echo "5. Testing main.py CLI..."
python main.py --help > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ main.py CLI working"
else
    echo "❌ main.py CLI failed"
fi
echo

echo "6. Checking documentation files..."
docs=(
    "PERPLEXITY_SETUP.md"
    "QUICKSTART.md"
    "MODULE_EXECUTION_ORDER.md"
    "AGENT_INSTRUCTIONS.md"
    "README.md"
    "IMPLEMENTATION_SUMMARY.md"
)
for doc in "${docs[@]}"; do
    if [ -f "$doc" ]; then
        echo "✅ $doc exists"
    else
        echo "❌ $doc missing"
    fi
done
echo

echo "7. Checking test scripts..."
if [ -x "test_engine.py" ]; then
    echo "✅ test_engine.py is executable"
else
    echo "❌ test_engine.py not executable"
fi
if [ -x "example_complete_workflow.py" ]; then
    echo "✅ example_complete_workflow.py is executable"
else
    echo "❌ example_complete_workflow.py not executable"
fi
echo

echo "============================================="
echo "Validation Complete"
echo "============================================="
