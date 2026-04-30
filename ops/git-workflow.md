# Git, Secrets & Environment Workflow

This file is referenced by `CLAUDE.md` and must be read before any git operation or package installation.

---

## 1. Conda Environment

**Never install packages into base or system Python.** Every project gets an isolated conda environment.

### Before starting a new project or build

1. **Ask the user**: "What conda environment should I use? Create a new one, or activate an existing one?" Show existing environments with `conda env list`.
2. **Wait for explicit answer** — Do not proceed with `pip install` or `conda install` until the user specifies an environment name and Python version.
3. **Create if needed**:
   ```bash
   conda create -n <env_name> python=<version> -y
   conda activate <env_name>
   ```
4. **Record the environment** — Add the environment name and Python version to `ops/status.md` and to a comment at the top of any setup/install scripts.
5. **Export on meaningful changes** — After installing dependencies, export:
   ```bash
   conda env export --no-builds > environment.yml
   pip freeze > requirements.txt
   ```
6. **Never use `--break-system-packages`** — If this flag would be needed, you're outside a conda env. Stop and ask the user.

---

## 2. Secrets & Sensitive Data — Pre-Commit Gate

**No code may be committed or pushed until secrets sanitization is verified.** This applies to every `git add`, `git commit`, and `git push`.

### What counts as sensitive

API keys, tokens, passwords, connection strings, private hostnames/IPs, `.env` contents, cloud credentials (AWS, GCP, Azure), SSH keys, database URIs, personal data (emails, names in test fixtures), and any value that would be dangerous if made public.

### Sanitization procedure (every commit)

1. **Scan staged files** — Before `git commit`, run:
   ```bash
   git diff --cached | grep -inE \
     '(api[_-]?key|secret|token|password|passwd|credential|private[_-]?key|ssh-rsa|BEGIN (RSA|EC|OPENSSH)|aws_access|aws_secret|DATABASE_URL|MONGO_URI|REDIS_URL|smtp_pass)' \
     && echo "⚠️  POTENTIAL SECRETS FOUND — review before committing" \
     || echo "✅ No obvious secrets detected"
   ```
2. **Review flagged lines** — If the scan flags anything, show the user and ask for confirmation before proceeding.
3. **Never commit `.env` files** — Verify `.env`, `.env.*`, `*.pem`, `*.key`, and credential files are in `.gitignore`. If `.gitignore` is missing or incomplete, create/update it before the first commit.
4. **Use placeholder values** — Config templates (e.g. `.env.example`) must use placeholder values like `YOUR_API_KEY_HERE`, never real credentials.
5. **If secrets were already committed** — Alert the user immediately. Do NOT rewrite git history without explicit user instruction. Recommend rotating the exposed credential.

### `.gitignore` baseline

Every Python project `.gitignore` must include at minimum:

```gitignore
# Secrets & credentials
.env
.env.*
*.pem
*.key
secrets/
credentials/

# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
*.egg

# Environments
.conda/
.venv/
venv/
env/

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db

# Data & logs (review before committing)
*.log
*.sqlite3

# Data directories — large files stay local
data/raw/
data/interim/
data/processed/
data/external/

# Figures — commit selectively; ignore intermediates by default
figures/

# Jupyter notebook checkpoints
.ipynb_checkpoints/
*/.ipynb_checkpoints/

# Geospatial intermediates
*.shp
*.dbf
*.shx
*.prj
*.cpg
*.tif
*.tiff
*.gpkg
```

---

## 3. Branching

- **Never commit directly to `main`** unless the user explicitly says so.
- Create feature branches: `feature/<short-description>` or `fix/<short-description>`.
- Before starting work, pull latest:
  ```bash
  git fetch origin && git pull origin main
  ```

---

## 4. Commits

- Use **conventional commit messages**: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`.
- Keep commits **atomic** — one logical change per commit.
- Always run the **secrets scan** (section 2) before `git commit`.

---

## 5. Pull Requests

- Push feature branch and open a PR with a clear description referencing the relevant story/spec.
- If the repo has CI checks, wait for them to pass before reporting the PR as ready.
- Do not merge PRs without user approval.

---

## 6. Sync Discipline

- Before starting new work: `git status` to check for uncommitted changes.
- Stash or commit work-in-progress before switching branches.
- After pulling, verify the conda environment still matches `environment.yml`:
  ```bash
  conda env update -f environment.yml --prune
  ```

---

## 7. Commit Checklist (quick reference)

Run through this before every commit:

```
[ ] Conda environment is active (not base, not system Python)
[ ] Secrets scan passed on staged diff
[ ] .gitignore covers .env, *.pem, *.key, credentials/
[ ] No hardcoded credentials or real API keys in code
[ ] Commit message uses conventional format
[ ] On a feature/fix branch (not main)
[ ] environment.yml / requirements.txt updated if deps changed
```
