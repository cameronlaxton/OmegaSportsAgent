# OMEGA Setup Guide

This guide explains how to set up the OMEGA Sports Betting Simulation system in a GitHub repository and integrate it with Perplexity Spaces.

## Prerequisites

- GitHub account
- Perplexity Spaces access (Pro subscription recommended)
- Basic understanding of Git and markdown files

## Step 1: GitHub Repository Setup

### 1.1 Create Repository

1. Create a new repository on GitHub named `omega-betting-agent` (or your preferred name)
2. Initialize with a README (optional - we have one already)
3. Set repository visibility (private recommended for betting strategies)

### 1.2 Clone Repository Locally

```bash
git clone https://github.com/yourusername/omega-betting-agent.git
cd omega-betting-agent
```

### 1.3 Verify Directory Structure

Ensure your repository has this structure:

```
omega-betting-agent/
├── .github/workflows/
├── modules/
│   ├── foundation/
│   ├── analytics/
│   ├── modeling/
│   ├── simulation/
│   ├── betting/
│   ├── adjustments/
│   └── utilities/
├── config/
├── docs/
├── data/
│   ├── logs/
│   ├── exports/
│   └── audits/
├── examples/
├── .gitignore
├── README.md
└── MODULE_LOAD_ORDER.md
```

### 1.4 Initial Commit

```bash
git add .
git commit -m "Initial commit: OMEGA betting agent with organized module structure"
git push origin main
```

## Step 2: Perplexity Space Configuration

### 2.1 Create Perplexity Space

1. Go to Perplexity Spaces
2. Create a new Space
3. Name it "OMEGA Betting Agent" or similar

### 2.2 Connect to GitHub (If Supported)

**Option A: Direct GitHub Integration (if available)**
- Connect Space to your GitHub repository
- Space will automatically sync with repo
- Updates to repo will be available in Space

**Option B: Manual File Upload**
- Upload all files from the repository to the Space
- Update files manually when repository changes
- Use Space's file management interface

### 2.3 Configure Answer Instructions

1. Go to Space Settings
2. Find "Answer Instructions" or "Agent Instructions" field
3. Copy content from `config/AGENT_SPACE_INSTRUCTIONS.md`
4. Paste into the instructions field
5. Save settings

### 2.4 Verify Module Access

Test that the Space can access modules:
- Ask Space to read `config/CombinedInstructions.md`
- Verify it can list modules in `modules/` directories
- Test module loading order from `MODULE_LOAD_ORDER.md`

## Step 3: Module Loading Verification

### 3.1 Test Module Extraction

In Perplexity Space, test module loading:

```
Read the file config/CombinedInstructions.md and list the 19 modules in loading order.
```

Expected response should list all 19 modules with correct paths.

### 3.2 Verify Python Code Blocks

Test that Python code can be extracted:

```
Extract the Python code block from modules/foundation/model_config.md
```

Should return the Python code without markdown formatting.

### 3.3 Module Loading Best Practices

**Space Files vs GitHub:**
- Space files are valid if they match GitHub versions
- Upload all 19 modules to Space for faster, token-efficient loading
- GitHub is preferred for version control, but Space files work fine

**Token-Constrained Environments:**
- Load foundation modules (1-3) first - these are critical
- Load remaining modules in batches: analytics (4-6), modeling (7-10), simulation (11-12), betting (13-15), utilities (16-19)
- Or load on-demand as functions are needed

**Verification:**
- After loading, verify key functions are available (e.g., `run_game_simulation`, `calculate_edge`)
- Report which modules loaded successfully and from which source

## Step 4: Data Persistence Setup

### 4.1 Understand Storage Strategy

- **Session Storage**: `data/logs/` and `data/exports/` (default paths, persist in Spaces if uploaded/synced)
- **Persistence**: File attachments delivered at end of each task + optional Space file uploads
- **GitHub Persistence**: Manual commits of result files (optional, structure committed, daily data git-ignored)

### 4.2 File Attachment Workflow

1. **Daily Task (TASK 1)**:
   - Space generates bets and simulations
   - Space logs to `data/logs/` and `data/exports/` during session (default paths)
   - Space delivers `bet_log.json`, `simulation_log.json`, `daily_suggested_bets-MM-DD.csv` as attachments
   - Files persist in Spaces if uploaded/synced
   - User can commit these to GitHub if desired (structure committed, daily data git-ignored)

2. **Late Daily Task (TASK 2)**:
   - Space loads previous `BetLog.csv` from attachments
   - Space updates pending bet results
   - Space delivers updated `BetLog.csv` (cumulative) as attachment

3. **Weekly Audit (TASK 3)**:
   - Space loads bet data from previous attachments
   - Space runs audit and generates report
   - Space delivers `AUDIT_REPORT-YYYY-MM-DD.md` as attachment

### 4.3 GitHub MCP Integration (If Available)

If Perplexity Space supports GitHub MCP tools:

1. Configure GitHub MCP connection in Space settings
2. Space can commit result files directly to repository
3. Space can read from repository for data retrieval
4. Automated persistence without manual commits

## Step 5: Testing the Integration

### 5.1 Test Daily Workflow

1. Ask Space to run TASK 1 (daily bet generation)
2. Verify modules load in correct order
3. Verify simulations run successfully
4. Verify files are delivered as attachments
5. Check that files contain expected data

### 5.2 Test Data Retrieval

1. In a new session, ask Space to run TASK 2 (late daily updates)
2. Verify Space can find previous task attachments
3. Verify Space can load and update bet data
4. Verify updated files are delivered

### 5.3 Test Audit Workflow

1. After several days of data, ask Space to run TASK 3 (weekly audit)
2. Verify Space can aggregate data from multiple attachments
3. Verify audit calculations are correct
4. Verify audit report is generated and delivered

## Troubleshooting

### Modules Not Loading

**Problem**: Space cannot find modules
**Solution**: 
- Verify file paths match `MODULE_LOAD_ORDER.md`
- Check that all modules are in correct directories
- Ensure Space has access to repository files

### File Attachments Not Working

**Problem**: Files not delivered as attachments
**Solution**:
- Verify Answer Instructions include file attachment requirements
- Check that Space has permission to create attachments
- Review task instructions in `config/CombinedInstructions.md`

### Data Not Persisting

**Problem**: Previous task data not found
**Solution**:
- Verify files were delivered as attachments in previous tasks
- Check that Space can review previous thread attachments
- Use `load_from_thread_fallback()` method in `sandbox_persistence.md`

### Module Execution Errors

**Problem**: Python code blocks fail to execute
**Solution**:
- Verify Python syntax in module files
- Check that all dependencies are available in sandbox
- Review module loading order (dependencies must load first)

## Next Steps

1. **Customize Configuration**: Edit `modules/foundation/model_config.md` for your thresholds
2. **Add League Support**: Follow `docs/ARCHITECTURE.md` extension points
3. **Set Up Automation**: Configure GitHub Actions for validation (optional)
4. **Monitor Performance**: Review audit reports weekly for calibration

## Support

- Review `docs/ARCHITECTURE.md` for system architecture
- Check `MODULE_LOAD_ORDER.md` for module dependencies
- Refer to `config/CombinedInstructions.md` for complete workflow

