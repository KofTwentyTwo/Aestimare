#!/usr/bin/env python3
"""
GitHub Repository Collector - Collects repository data from GitHub organizations.
"""

import json
import os
import subprocess
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class GitHubCollector:
   """Collects data from GitHub organizations."""

   def __init__(self, config: Dict):
      self.config = config
      self.data_dir = Path(config.get('data_dir', '.data'))
      self.github_config = config.get('github', {})
      self.token = self.github_config.get('token') or os.environ.get('GITHUB_TOKEN')
      self.clone_repos = self.github_config.get('clone_repos', False)
      self.clone_dir = Path(self.github_config.get('clone_dir', '.repos-readonly'))

   def collect_all(self) -> Dict[str, Dict]:
      """Collect data from all configured GitHub organizations."""
      results = {}

      orgs = self.github_config.get('organizations', [])
      enabled_orgs = [o for o in orgs if o.get('enabled', True)]

      logger.info(f"Collecting data from {len(enabled_orgs)} GitHub organization(s)")

      for org in enabled_orgs:
         org_name = org['name']
         logger.info(f"Processing organization: {org_name}")

         org_data = self.collect_organization(org)
         results[org_name] = org_data

         # Save organization data
         self._save_org_data(org_name, org_data)

      return results

   def collect_organization(self, org_config: Dict) -> Dict:
      """Collect data from a single GitHub organization."""
      org_name = org_config['name']
      include_archived = org_config.get('include_archived', False)
      include_forks = org_config.get('include_forks', False)

      org_data = {
         'organization': org_name,
         'collection_time': datetime.now().isoformat(),
         'repositories': [],
         'org_info': {},
         'members': [],
         'teams': [],
      }

      # Get organization info
      org_data['org_info'] = self._gh_api(f'/orgs/{org_name}')

      # Get repositories
      repos = self._get_all_repos(org_name)

      # Filter repositories
      filtered_repos = []
      for repo in repos:
         if not include_archived and repo.get('archived', False):
            continue
         if not include_forks and repo.get('fork', False):
            continue
         filtered_repos.append(repo)

      logger.info(f"  Found {len(filtered_repos)} repositories (filtered from {len(repos)})")

      # Enrich repository data
      for repo in filtered_repos:
         repo_name = repo['name']
         logger.info(f"    Processing: {repo_name}")

         enriched = self._enrich_repository(org_name, repo)

         # Clone and analyze repository locally if enabled
         if self.clone_repos:
            self._clone_repository(org_name, repo_name, repo.get('ssh_url'))
            # Perform local analysis if repo was cloned
            repo_dir = self.clone_dir / repo_name
            if repo_dir.exists() and (repo_dir / '.git').exists():
               logger.info(f"      Performing local analysis: {repo_name}")
               local_analyzer = LocalRepoAnalyzer(repo_dir.parent)
               local_analysis = local_analyzer.analyze_repository(repo_dir)
               # Merge local analysis into enriched data
               enriched['local_analysis'] = local_analysis
               # Merge key metrics directly for easier access
               enriched.update({
                  'code_quality': local_analysis.get('code_quality', {}),
                  'security_deep': local_analysis.get('security_deep', {}),
                  'performance': local_analysis.get('performance', {}),
                  'architecture': local_analysis.get('architecture', {}),
                  'maintainability': local_analysis.get('maintainability', {}),
                  'devops': local_analysis.get('devops', {}),
                  'compliance': local_analysis.get('compliance', {}),
                  'testing_quality': local_analysis.get('testing_quality', {}),
                  'developer_experience': local_analysis.get('developer_experience', {}),
                  'code_review': local_analysis.get('code_review', {}),
                  'error_handling': local_analysis.get('error_handling', {}),
                  'documentation_quality': local_analysis.get('documentation_quality', {}),
               })

         org_data['repositories'].append(enriched)

      # Get members (if accessible)
      org_data['members'] = self._gh_api(f'/orgs/{org_name}/members') or []

      # Get teams (if accessible)
      org_data['teams'] = self._gh_api(f'/orgs/{org_name}/teams') or []

      # Categorize repositories by activity
      org_data['repositories'] = self._categorize_activity(org_data['repositories'])

      return org_data

   def _get_all_repos(self, org_name: str) -> List[Dict]:
      """Get all repositories for an organization (handles pagination)."""
      repos = []
      page = 1
      per_page = 100

      while True:
         result = self._gh_api(f'/orgs/{org_name}/repos?per_page={per_page}&page={page}')
         if not result:
            break
         repos.extend(result)
         if len(result) < per_page:
            break
         page += 1

      return repos

   def _enrich_repository(self, org_name: str, repo: Dict) -> Dict:
      """Enrich repository data with additional details."""
      repo_name = repo['name']

      # Get additional data
      enriched = {
         **repo,
         'languages': self._gh_api(f'/repos/{org_name}/{repo_name}/languages') or {},
         'branches': self._gh_api(f'/repos/{org_name}/{repo_name}/branches') or [],
         'tags': self._gh_api(f'/repos/{org_name}/{repo_name}/tags') or [],
         'contributors': self._get_contributors(org_name, repo_name),
         'commits_30d': self._get_recent_commits(org_name, repo_name, days=30),
         'pull_requests': self._get_pull_requests(org_name, repo_name),
         'issues': self._get_issues(org_name, repo_name),
         'workflows': self._get_workflows(org_name, repo_name),
         'security_alerts': self._get_security_alerts(org_name, repo_name),
         'code_scanning': self._get_code_scanning(org_name, repo_name),
         'branch_protection': self._get_branch_protection(org_name, repo_name),
         # Code review practices
         'pr_template': self._check_pr_template(org_name, repo_name),
         'issue_templates': self._get_issue_templates(org_name, repo_name),
         'codeowners': self._get_codeowners(org_name, repo_name),
         # Additional metadata
         'releases': self._get_releases(org_name, repo_name),
         'topics': repo.get('topics', []),
      }

      return enriched

   def _get_contributors(self, org: str, repo: str) -> List[Dict]:
      """Get repository contributors."""
      result = self._gh_api(f'/repos/{org}/{repo}/contributors?per_page=100')
      return result if result else []

   def _get_recent_commits(self, org: str, repo: str, days: int = 30) -> int:
      """Get count of commits in the last N days."""
      since = (datetime.now() - timedelta(days=days)).isoformat()
      result = self._gh_api(f'/repos/{org}/{repo}/commits?since={since}&per_page=100')
      return len(result) if result else 0

   def _get_pull_requests(self, org: str, repo: str) -> Dict:
      """Get pull request statistics."""
      open_prs = self._gh_api(f'/repos/{org}/{repo}/pulls?state=open&per_page=100')
      closed_prs = self._gh_api(f'/repos/{org}/{repo}/pulls?state=closed&per_page=100')

      return {
         'open': len(open_prs) if open_prs else 0,
         'closed_recent': len(closed_prs) if closed_prs else 0,
      }

   def _get_issues(self, org: str, repo: str) -> Dict:
      """Get issue statistics."""
      open_issues = self._gh_api(f'/repos/{org}/{repo}/issues?state=open&per_page=100')
      closed_issues = self._gh_api(f'/repos/{org}/{repo}/issues?state=closed&per_page=100')

      return {
         'open': len(open_issues) if open_issues else 0,
         'closed_recent': len(closed_issues) if closed_issues else 0,
      }

   def _get_workflows(self, org: str, repo: str) -> List[Dict]:
      """Get GitHub Actions workflows."""
      result = self._gh_api(f'/repos/{org}/{repo}/actions/workflows')
      if result and 'workflows' in result:
         return result['workflows']
      return []

   def _get_security_alerts(self, org: str, repo: str) -> List[Dict]:
      """Get Dependabot security alerts."""
      result = self._gh_api(f'/repos/{org}/{repo}/dependabot/alerts?state=open&per_page=100')
      return result if result else []

   def _get_code_scanning(self, org: str, repo: str) -> List[Dict]:
      """Get code scanning alerts."""
      result = self._gh_api(f'/repos/{org}/{repo}/code-scanning/alerts?state=open&per_page=100')
      return result if result else []

   def _get_branch_protection(self, org: str, repo: str) -> Optional[Dict]:
      """Get branch protection rules for default branch."""
      # First get the default branch
      repo_info = self._gh_api(f'/repos/{org}/{repo}')
      if not repo_info:
         return None

      default_branch = repo_info.get('default_branch', 'main')
      result = self._gh_api(f'/repos/{org}/{repo}/branches/{default_branch}/protection')
      return result

   def _check_pr_template(self, org: str, repo: str) -> bool:
      """Check if PR template exists."""
      # Check via API for template
      pr_template = self._gh_api(f'/repos/{org}/{repo}/contents/.github/pull_request_template.md')
      return pr_template is not None

   def _get_issue_templates(self, org: str, repo: str) -> List[Dict]:
      """Get issue templates."""
      templates_dir = self._gh_api(f'/repos/{org}/{repo}/contents/.github/ISSUE_TEMPLATE')
      if templates_dir and isinstance(templates_dir, list):
         return [t for t in templates_dir if t.get('type') == 'file']
      return []

   def _get_codeowners(self, org: str, repo: str) -> Optional[Dict]:
      """Get CODEOWNERS file content."""
      codeowners = self._gh_api(f'/repos/{org}/{repo}/contents/.github/CODEOWNERS')
      if not codeowners:
         codeowners = self._gh_api(f'/repos/{org}/{repo}/contents/CODEOWNERS')
      return codeowners

   def _get_releases(self, org: str, repo: str) -> List[Dict]:
      """Get recent releases."""
      releases = self._gh_api(f'/repos/{org}/{repo}/releases?per_page=10')
      return releases if releases else []

   def _categorize_activity(self, repos: List[Dict]) -> List[Dict]:
      """Categorize repositories by activity level."""
      now = datetime.now()

      for repo in repos:
         pushed_at = repo.get('pushed_at')
         if pushed_at:
            try:
               pushed_date = datetime.fromisoformat(pushed_at.replace('Z', '+00:00'))
               days_since_push = (now - pushed_date.replace(tzinfo=None)).days
            except:
               days_since_push = 999

            commits_30d = repo.get('commits_30d', 0)

            if days_since_push <= 7 and commits_30d >= 10:
               repo['activity_category'] = 'Very Active'
            elif days_since_push <= 30 and commits_30d >= 5:
               repo['activity_category'] = 'Active'
            elif days_since_push <= 90:
               repo['activity_category'] = 'Moderate'
            elif days_since_push <= 365:
               repo['activity_category'] = 'Low'
            else:
               repo['activity_category'] = 'Inactive'
         else:
            repo['activity_category'] = 'Unknown'

      return repos

   def _clone_repository(self, org: str, repo: str, ssh_url: Optional[str]):
      """Clone a repository for local analysis."""
      if not ssh_url:
         return

      repo_dir = self.clone_dir / repo

      if repo_dir.exists():
         # Update existing repo
         logger.info(f"      Updating: {repo}")
         try:
            subprocess.run(
               ['git', '-C', str(repo_dir), 'pull', '--quiet'],
               capture_output=True,
               timeout=60
            )
         except:
            pass
      else:
         # Clone new repo
         logger.info(f"      Cloning: {repo}")
         self.clone_dir.mkdir(parents=True, exist_ok=True)
         try:
            subprocess.run(
               ['git', 'clone', '--quiet', '--depth', '1', ssh_url, str(repo_dir)],
               capture_output=True,
               timeout=120
            )
         except:
            pass

   def _gh_api(self, endpoint: str) -> Optional[Any]:
      """Make a GitHub API request."""
      cmd = ['gh', 'api', endpoint]

      try:
         result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
         )
         if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
         return None
      except subprocess.TimeoutExpired:
         logger.warning(f"Timeout calling: {endpoint}")
         return None
      except json.JSONDecodeError:
         return None
      except Exception as e:
         logger.debug(f"Error calling {endpoint}: {e}")
         return None

   def _save_org_data(self, org_name: str, data: Dict):
      """Save collected data to files."""
      org_dir = self.data_dir / 'github' / org_name.lower().replace(' ', '_')
      org_dir.mkdir(parents=True, exist_ok=True)

      # Save full data
      with open(org_dir / 'full_data.json', 'w') as f:
         json.dump(data, f, indent=2, default=str)

      # Save repository list
      repo_list = []
      for repo in data.get('repositories', []):
         repo_list.append({
            'name': repo.get('name'),
            'url': repo.get('html_url'),
            'description': repo.get('description'),
            'language': repo.get('language'),
            'category': repo.get('activity_category'),
            'updatedAt': repo.get('updated_at'),
            'pushedAt': repo.get('pushed_at'),
            'stars': repo.get('stargazers_count'),
            'forks': repo.get('forks_count'),
            'archived': repo.get('archived'),
         })

      with open(org_dir / 'repo_list.json', 'w') as f:
         json.dump(repo_list, f, indent=2)

      # Save active repos (for compatibility with existing scripts)
      active_repos = [r for r in repo_list if r.get('category') in ['Very Active', 'Active', 'Moderate']]
      with open(org_dir / 'active_repos.json', 'w') as f:
         json.dump(active_repos, f, indent=2)

      logger.info(f"  Saved data to {org_dir}")


class LocalRepoAnalyzer:
   """Analyzes locally cloned repositories."""

   def __init__(self, repos_dir: Path):
      self.repos_dir = repos_dir

   def analyze_all(self) -> Dict[str, Dict]:
      """Analyze all repositories in the repos directory."""
      results = {}

      if not self.repos_dir.exists():
         logger.warning(f"Repos directory does not exist: {self.repos_dir}")
         return results

      for repo_dir in self.repos_dir.iterdir():
         if repo_dir.is_dir() and (repo_dir / '.git').exists():
            logger.info(f"Analyzing: {repo_dir.name}")
            results[repo_dir.name] = self.analyze_repository(repo_dir)

      return results

   def analyze_repository(self, repo_dir: Path) -> Dict:
      """Analyze a single repository with comprehensive assessment."""
      analysis = {
         'name': repo_dir.name,
         'path': str(repo_dir),
         'files': self._count_files(repo_dir),
         'loc': self._count_lines(repo_dir),
         'project_type': self._detect_project_type(repo_dir),
         'dependencies': self._extract_dependencies(repo_dir),
         'has_tests': self._check_tests(repo_dir),
         'has_ci': self._check_ci(repo_dir),
         'has_docs': self._check_docs(repo_dir),
         'security_files': self._check_security_files(repo_dir),
         'config_files': self._check_config_files(repo_dir),
         # Code Quality & Complexity
         'code_quality': self._assess_code_quality(repo_dir),
         # Security Deep Dive
         'security_deep': self._assess_security_deep(repo_dir),
         # Performance Indicators
         'performance': self._assess_performance(repo_dir),
         # Architecture & Design
         'architecture': self._assess_architecture(repo_dir),
         # Maintainability
         'maintainability': self._assess_maintainability(repo_dir),
         # DevOps & Operations
         'devops': self._assess_devops(repo_dir),
         # Compliance
         'compliance': self._assess_compliance(repo_dir),
         # Testing Quality
         'testing_quality': self._assess_testing_quality(repo_dir),
         # Developer Experience
         'developer_experience': self._assess_developer_experience(repo_dir),
         # Code Review Practices
         'code_review': self._assess_code_review_practices(repo_dir),
         # Error Handling
         'error_handling': self._assess_error_handling(repo_dir),
         # Documentation Quality
         'documentation_quality': self._assess_documentation_quality(repo_dir),
      }
      return analysis

   def _count_files(self, repo_dir: Path) -> Dict[str, int]:
      """Count files by extension."""
      counts = {}
      ignore_dirs = {'.git', 'node_modules', '.venv', 'venv', '__pycache__', 'build', 'dist'}

      for root, dirs, files in os.walk(repo_dir):
         dirs[:] = [d for d in dirs if d not in ignore_dirs]
         for file in files:
            ext = Path(file).suffix.lower() or 'no_ext'
            counts[ext] = counts.get(ext, 0) + 1

      return counts

   def _count_lines(self, repo_dir: Path) -> Dict[str, int]:
      """Count lines of code by language."""
      loc = {}
      ignore_dirs = {'.git', 'node_modules', '.venv', 'venv', '__pycache__', 'build', 'dist'}

      ext_map = {
         '.js': 'JavaScript', '.jsx': 'JavaScript', '.ts': 'TypeScript', '.tsx': 'TypeScript',
         '.py': 'Python', '.java': 'Java', '.kt': 'Kotlin', '.swift': 'Swift',
         '.go': 'Go', '.rs': 'Rust', '.rb': 'Ruby', '.php': 'PHP',
         '.c': 'C', '.cpp': 'C++', '.h': 'C/C++', '.cs': 'C#',
      }

      for root, dirs, files in os.walk(repo_dir):
         dirs[:] = [d for d in dirs if d not in ignore_dirs]
         for file in files:
            ext = Path(file).suffix.lower()
            if ext in ext_map:
               try:
                  with open(Path(root) / file, 'r', encoding='utf-8', errors='ignore') as f:
                     lines = len(f.readlines())
                     lang = ext_map[ext]
                     loc[lang] = loc.get(lang, 0) + lines
               except:
                  pass

      return loc

   def _detect_project_type(self, repo_dir: Path) -> List[str]:
      """Detect project type based on files."""
      types = []

      if (repo_dir / 'package.json').exists():
         types.append('Node.js')
      if (repo_dir / 'requirements.txt').exists() or (repo_dir / 'setup.py').exists():
         types.append('Python')
      if (repo_dir / 'pom.xml').exists():
         types.append('Maven/Java')
      if (repo_dir / 'build.gradle').exists():
         types.append('Gradle')
      if (repo_dir / 'Cargo.toml').exists():
         types.append('Rust')
      if (repo_dir / 'go.mod').exists():
         types.append('Go')
      if list(repo_dir.glob('*.xcodeproj')) or list(repo_dir.glob('*.xcworkspace')):
         types.append('iOS/macOS')
      if (repo_dir / 'app' / 'src' / 'main' / 'AndroidManifest.xml').exists():
         types.append('Android')

      return types or ['Unknown']

   def _extract_dependencies(self, repo_dir: Path) -> Dict[str, List]:
      """Extract dependencies from package files."""
      deps = {}

      # NPM
      if (repo_dir / 'package.json').exists():
         try:
            with open(repo_dir / 'package.json') as f:
               pkg = json.load(f)
               deps['npm'] = list(pkg.get('dependencies', {}).keys())[:20]
               deps['npm_dev'] = list(pkg.get('devDependencies', {}).keys())[:10]
         except:
            pass

      # Python
      if (repo_dir / 'requirements.txt').exists():
         try:
            with open(repo_dir / 'requirements.txt') as f:
               deps['python'] = [line.split('==')[0].strip() for line in f if line.strip() and not line.startswith('#')][:20]
         except:
            pass

      return deps

   def _check_tests(self, repo_dir: Path) -> bool:
      """Check if repository has tests."""
      test_indicators = ['test', 'tests', '__tests__', 'spec', 'specs']
      for indicator in test_indicators:
         if (repo_dir / indicator).exists():
            return True

      # Check for test files
      for pattern in ['*.test.js', '*.spec.js', '*_test.py', '*_test.go']:
         if list(repo_dir.rglob(pattern)):
            return True

      return False

   def _check_ci(self, repo_dir: Path) -> List[str]:
      """Check for CI/CD configuration."""
      ci_systems = []

      if (repo_dir / '.github' / 'workflows').exists():
         ci_systems.append('GitHub Actions')
      if (repo_dir / '.gitlab-ci.yml').exists():
         ci_systems.append('GitLab CI')
      if (repo_dir / '.circleci').exists():
         ci_systems.append('CircleCI')
      if (repo_dir / 'Jenkinsfile').exists():
         ci_systems.append('Jenkins')
      if (repo_dir / '.travis.yml').exists():
         ci_systems.append('Travis CI')

      return ci_systems

   def _check_docs(self, repo_dir: Path) -> Dict[str, bool]:
      """Check documentation presence."""
      return {
         'readme': (repo_dir / 'README.md').exists() or (repo_dir / 'README').exists(),
         'contributing': (repo_dir / 'CONTRIBUTING.md').exists(),
         'changelog': (repo_dir / 'CHANGELOG.md').exists(),
         'license': (repo_dir / 'LICENSE').exists() or (repo_dir / 'LICENSE.md').exists(),
         'docs_dir': (repo_dir / 'docs').exists(),
      }

   def _check_security_files(self, repo_dir: Path) -> Dict[str, bool]:
      """Check security-related files."""
      return {
         'security_md': (repo_dir / 'SECURITY.md').exists(),
         'gitignore': (repo_dir / '.gitignore').exists(),
         'env_example': (repo_dir / '.env.example').exists() or (repo_dir / '.env.template').exists(),
         'dependabot': (repo_dir / '.github' / 'dependabot.yml').exists(),
      }

   def _check_config_files(self, repo_dir: Path) -> Dict[str, bool]:
      """Check for configuration files."""
      return {
         'eslint': any((repo_dir / f).exists() for f in ['.eslintrc', '.eslintrc.js', '.eslintrc.json']),
         'prettier': any((repo_dir / f).exists() for f in ['.prettierrc', '.prettierrc.js', 'prettier.config.js']),
         'typescript': (repo_dir / 'tsconfig.json').exists(),
         'editorconfig': (repo_dir / '.editorconfig').exists(),
         'docker': (repo_dir / 'Dockerfile').exists() or (repo_dir / 'docker-compose.yml').exists(),
      }

   def _assess_code_quality(self, repo_dir: Path) -> Dict:
      """Assess code quality, complexity, and technical debt."""
      technical_debt_indicators = {
         'todo_count': 0,
         'fixme_count': 0,
         'hack_count': 0,
         'xxx_count': 0,
         'deprecated_count': 0,
      }
      
      # Count technical debt comments
      code_extensions = ['.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rs', '.rb', '.php', '.c', '.cpp', '.cs']
      for root, dirs, files in os.walk(repo_dir):
         dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', '.venv', 'venv', '__pycache__', 'build', 'dist'}]
         for file in files:
            if any(file.endswith(ext) for ext in code_extensions):
               try:
                  with open(Path(root) / file, 'r', encoding='utf-8', errors='ignore') as f:
                     content = f.read().lower()
                     technical_debt_indicators['todo_count'] += content.count('todo')
                     technical_debt_indicators['fixme_count'] += content.count('fixme')
                     technical_debt_indicators['hack_count'] += content.count('hack')
                     technical_debt_indicators['xxx_count'] += content.count('xxx')
                     technical_debt_indicators['deprecated_count'] += content.count('@deprecated') + content.count('deprecated')
               except:
                  pass
      
      # Estimate complexity (simple heuristic: large files, long functions)
      large_files = 0
      for root, dirs, files in os.walk(repo_dir):
         dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', '.venv', 'venv', '__pycache__', 'build', 'dist'}]
         for file in files:
            if any(file.endswith(ext) for ext in code_extensions):
               try:
                  file_path = Path(root) / file
                  if file_path.stat().st_size > 100000:  # Files > 100KB
                     large_files += 1
               except:
                  pass
      
      return {
         'technical_debt_indicators': technical_debt_indicators,
         'large_files_count': large_files,
         'complexity_indicators': {
            'has_large_files': large_files > 0,
            'high_technical_debt': sum(technical_debt_indicators.values()) > 50,
         }
      }

   def _assess_security_deep(self, repo_dir: Path) -> Dict:
      """Deep security assessment including secret scanning."""
      secret_patterns = {
         'api_key': r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\']?[a-zA-Z0-9]{20,}',
         'aws_key': r'(?i)aws[_-]?(access[_-]?key|secret[_-]?key)\s*[=:]\s*["\']?[A-Z0-9]{20,}',
         'password': r'(?i)(password|pwd|passwd)\s*[=:]\s*["\']?[^\s"\']{8,}',
         'token': r'(?i)(token|bearer|auth[_-]?token)\s*[=:]\s*["\']?[a-zA-Z0-9]{20,}',
         'secret': r'(?i)(secret|private[_-]?key)\s*[=:]\s*["\']?[a-zA-Z0-9]{20,}',
         'database_url': r'(?i)(database[_-]?url|db[_-]?url|connection[_-]?string)\s*[=:]\s*["\']?[^\s"\']+',
      }
      
      potential_secrets = []
      code_extensions = ['.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rs', '.rb', '.php', '.c', '.cpp', '.cs', '.env', '.config', '.conf']
      
      import re
      for root, dirs, files in os.walk(repo_dir):
         dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', '.venv', 'venv', '__pycache__', 'build', 'dist'}]
         for file in files:
            if any(file.endswith(ext) for ext in code_extensions):
               try:
                  with open(Path(root) / file, 'r', encoding='utf-8', errors='ignore') as f:
                     content = f.read()
                     for pattern_name, pattern in secret_patterns.items():
                        matches = re.finditer(pattern, content)
                        for match in matches:
                           # Check if it's in a comment or example
                           line_start = content.rfind('\n', 0, match.start())
                           line = content[line_start:match.end()]
                           if not any(indicator in line.lower() for indicator in ['example', 'template', 'placeholder', 'xxx', 'todo']):
                              potential_secrets.append({
                                 'type': pattern_name,
                                 'file': str(Path(root) / file).replace(str(repo_dir), ''),
                                 'line': content[:match.start()].count('\n') + 1,
                              })
               except:
                  pass
      
      # Check for insecure patterns
      insecure_patterns = {
         'sql_injection_risk': False,
         'xss_risk': False,
         'eval_usage': False,
         'dangerous_functions': [],
      }
      
      dangerous_functions = ['eval', 'exec', 'system', 'shell_exec', 'passthru']
      for root, dirs, files in os.walk(repo_dir):
         dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', '.venv', 'venv', '__pycache__', 'build', 'dist'}]
         for file in files:
            if any(file.endswith(ext) for ext in code_extensions):
               try:
                  with open(Path(root) / file, 'r', encoding='utf-8', errors='ignore') as f:
                     content = f.read()
                     for func in dangerous_functions:
                        if re.search(rf'\b{func}\s*\(', content, re.IGNORECASE):
                           insecure_patterns['dangerous_functions'].append({
                              'function': func,
                              'file': str(Path(root) / file).replace(str(repo_dir), ''),
                           })
                     if re.search(r'eval\s*\(', content, re.IGNORECASE):
                        insecure_patterns['eval_usage'] = True
               except:
                  pass
      
      return {
         'potential_secrets_count': len(potential_secrets),
         'potential_secrets': potential_secrets[:10],  # Limit to first 10
         'insecure_patterns': insecure_patterns,
         'encryption_usage': self._check_encryption_usage(repo_dir),
      }

   def _check_encryption_usage(self, repo_dir: Path) -> Dict[str, bool]:
      """Check for encryption libraries and TLS configuration."""
      encryption_libs = {
         'crypto': False,
         'bcrypt': False,
         'argon2': False,
         'tls': False,
         'ssl': False,
      }
      
      # Check package files
      if (repo_dir / 'package.json').exists():
         try:
            with open(repo_dir / 'package.json') as f:
               pkg = json.load(f)
               deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
               for lib in ['crypto', 'bcrypt', 'argon2', 'tls', 'ssl', 'node-forge', 'crypto-js']:
                  if any(lib in dep.lower() for dep in deps.keys()):
                     encryption_libs['crypto'] = True
         except:
            pass
      
      if (repo_dir / 'requirements.txt').exists():
         try:
            with open(repo_dir / 'requirements.txt') as f:
               content = f.read().lower()
               if 'cryptography' in content or 'pycryptodome' in content:
                  encryption_libs['crypto'] = True
               if 'bcrypt' in content:
                  encryption_libs['bcrypt'] = True
         except:
            pass
      
      return encryption_libs

   def _assess_performance(self, repo_dir: Path) -> Dict:
      """Assess performance indicators."""
      return {
         'performance_tests': self._check_performance_tests(repo_dir),
         'monitoring_tools': self._check_monitoring_tools(repo_dir),
         'caching_indicators': self._check_caching(repo_dir),
         'bundle_analysis': self._check_bundle_analysis(repo_dir),
      }

   def _check_performance_tests(self, repo_dir: Path) -> Dict:
      """Check for performance testing."""
      perf_indicators = {
         'has_perf_tests': False,
         'load_test_files': [],
         'benchmark_files': [],
      }
      
      for root, dirs, files in os.walk(repo_dir):
         dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', '.venv', 'venv', '__pycache__', 'build', 'dist'}]
         for file in files:
            file_lower = file.lower()
            if any(indicator in file_lower for indicator in ['load', 'stress', 'performance', 'benchmark']):
               if any(file.endswith(ext) for ext in ['.js', '.ts', '.py', '.java', '.go']):
                  perf_indicators['has_perf_tests'] = True
                  if 'benchmark' in file_lower:
                     perf_indicators['benchmark_files'].append(str(Path(root) / file).replace(str(repo_dir), ''))
                  else:
                     perf_indicators['load_test_files'].append(str(Path(root) / file).replace(str(repo_dir), ''))
      
      return perf_indicators

   def _check_monitoring_tools(self, repo_dir: Path) -> Dict:
      """Check for monitoring and APM tools."""
      monitoring = {
         'apm_tools': [],
         'logging_libraries': [],
      }
      
      # Check package.json
      if (repo_dir / 'package.json').exists():
         try:
            with open(repo_dir / 'package.json') as f:
               pkg = json.load(f)
               deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
               apm_keywords = ['newrelic', 'datadog', 'sentry', 'rollbar', 'honeycomb', 'opentelemetry']
               for dep in deps.keys():
                  dep_lower = dep.lower()
                  if any(keyword in dep_lower for keyword in apm_keywords):
                     monitoring['apm_tools'].append(dep)
                  if 'winston' in dep_lower or 'pino' in dep_lower or 'bunyan' in dep_lower:
                     monitoring['logging_libraries'].append(dep)
         except:
            pass
      
      return monitoring

   def _check_caching(self, repo_dir: Path) -> Dict:
      """Check for caching strategies."""
      caching = {
         'cache_libraries': [],
         'redis_usage': False,
         'memcached_usage': False,
      }
      
      if (repo_dir / 'package.json').exists():
         try:
            with open(repo_dir / 'package.json') as f:
               pkg = json.load(f)
               deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
               for dep in deps.keys():
                  dep_lower = dep.lower()
                  if 'redis' in dep_lower:
                     caching['redis_usage'] = True
                  if 'memcached' in dep_lower:
                     caching['memcached_usage'] = True
                  if 'cache' in dep_lower:
                     caching['cache_libraries'].append(dep)
         except:
            pass
      
      return caching

   def _check_bundle_analysis(self, repo_dir: Path) -> Dict:
      """Check for bundle analysis tools."""
      return {
         'webpack_bundle_analyzer': (repo_dir / 'package.json').exists() and self._check_dependency(repo_dir, 'webpack-bundle-analyzer'),
         'source_map_explorer': (repo_dir / 'package.json').exists() and self._check_dependency(repo_dir, 'source-map-explorer'),
      }

   def _check_dependency(self, repo_dir: Path, dep_name: str) -> bool:
      """Check if a dependency exists."""
      if (repo_dir / 'package.json').exists():
         try:
            with open(repo_dir / 'package.json') as f:
               pkg = json.load(f)
               deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
               return dep_name in deps or any(dep_name in dep for dep in deps.keys())
         except:
            pass
      return False

   def _assess_architecture(self, repo_dir: Path) -> Dict:
      """Assess architecture and design patterns."""
      return {
         'project_structure': self._analyze_project_structure(repo_dir),
         'design_patterns': self._detect_design_patterns(repo_dir),
         'api_design': self._assess_api_design(repo_dir),
         'architecture_docs': self._check_architecture_docs(repo_dir),
      }

   def _analyze_project_structure(self, repo_dir: Path) -> Dict:
      """Analyze project structure organization."""
      structure = {
         'has_clear_separation': False,
         'common_directories': [],
         'structure_quality': 'unknown',
      }
      
      common_dirs = ['src', 'lib', 'app', 'components', 'services', 'models', 'controllers', 'routes', 'utils', 'helpers', 'config', 'tests', 'test', 'docs']
      found_dirs = []
      
      for item in repo_dir.iterdir():
         if item.is_dir() and not item.name.startswith('.'):
            if item.name.lower() in [d.lower() for d in common_dirs]:
               found_dirs.append(item.name)
      
      structure['common_directories'] = found_dirs
      structure['has_clear_separation'] = len(found_dirs) >= 3
      
      if len(found_dirs) >= 5:
         structure['structure_quality'] = 'excellent'
      elif len(found_dirs) >= 3:
         structure['structure_quality'] = 'good'
      elif len(found_dirs) >= 1:
         structure['structure_quality'] = 'fair'
      else:
         structure['structure_quality'] = 'poor'
      
      return structure

   def _detect_design_patterns(self, repo_dir: Path) -> Dict:
      """Detect common design patterns."""
      patterns = {
         'mvc': False,
         'repository': False,
         'factory': False,
         'singleton': False,
         'observer': False,
      }
      
      # Simple heuristic: look for directory names and common files
      dir_names = [d.name.lower() for d in repo_dir.iterdir() if d.is_dir()]
      if any(name in ['models', 'views', 'controllers'] for name in dir_names):
         patterns['mvc'] = True
      if any(name in ['repositories', 'repo'] for name in dir_names):
         patterns['repository'] = True
      
      return patterns

   def _assess_api_design(self, repo_dir: Path) -> Dict:
      """Assess API design quality."""
      api_design = {
         'has_openapi': False,
         'has_graphql': False,
         'has_swagger': False,
         'api_versioning': False,
      }
      
      # Check for OpenAPI/Swagger files
      for pattern in ['openapi.yaml', 'openapi.yml', 'swagger.yaml', 'swagger.yml', 'swagger.json', 'api.yaml', 'api.yml']:
         if (repo_dir / pattern).exists():
            api_design['has_openapi'] = True
            api_design['has_swagger'] = True
      
      # Check for GraphQL
      if (repo_dir / 'schema.graphql').exists() or any('graphql' in str(f).lower() for f in repo_dir.rglob('*.graphql')):
         api_design['has_graphql'] = True
      
      # Check for versioning in API routes
      code_extensions = ['.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go']
      for root, dirs, files in os.walk(repo_dir):
         dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', '.venv', 'venv', '__pycache__', 'build', 'dist'}]
         for file in files:
            if any(file.endswith(ext) for ext in code_extensions):
               try:
                  with open(Path(root) / file, 'r', encoding='utf-8', errors='ignore') as f:
                     content = f.read()
                     if re.search(r'/v\d+/|api/v\d+|version', content, re.IGNORECASE):
                        api_design['api_versioning'] = True
                        break
               except:
                  pass
         if api_design['api_versioning']:
            break
      
      return api_design

   def _check_architecture_docs(self, repo_dir: Path) -> Dict:
      """Check for architecture documentation."""
      return {
         'adr_present': any('adr' in str(f).lower() for f in repo_dir.rglob('*.md')),
         'architecture_diagrams': any('arch' in str(f).lower() or 'diagram' in str(f).lower() for f in repo_dir.rglob('*.md')),
         'design_docs': (repo_dir / 'docs' / 'design').exists() or (repo_dir / 'docs' / 'architecture').exists(),
      }

   def _assess_maintainability(self, repo_dir: Path) -> Dict:
      """Assess code maintainability."""
      return {
         'code_comments': self._assess_code_comments(repo_dir),
         'code_ownership': self._check_code_ownership(repo_dir),
         'legacy_indicators': self._check_legacy_code(repo_dir),
      }

   def _assess_code_comments(self, repo_dir: Path) -> Dict:
      """Assess code comment quality."""
      code_extensions = ['.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rs', '.rb']
      total_lines = 0
      comment_lines = 0
      docstring_functions = 0
      total_functions = 0
      
      for root, dirs, files in os.walk(repo_dir):
         dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', '.venv', 'venv', '__pycache__', 'build', 'dist'}]
         for file in files:
            if any(file.endswith(ext) for ext in code_extensions):
               try:
                  with open(Path(root) / file, 'r', encoding='utf-8', errors='ignore') as f:
                     lines = f.readlines()
                     total_lines += len(lines)
                     for i, line in enumerate(lines):
                        stripped = line.strip()
                        if stripped.startswith('//') or stripped.startswith('#') or stripped.startswith('*'):
                           comment_lines += 1
                        # Check for docstrings (Python, JavaScript)
                        if '"""' in stripped or "'''" in stripped or '/**' in stripped:
                           comment_lines += 1
                        # Count functions
                        if re.search(r'\b(def|function|fn|func)\s+\w+', stripped):
                           total_functions += 1
                           # Check if next lines have docstring
                           if i + 1 < len(lines) and ('"""' in lines[i+1] or "'''" in lines[i+1] or '/**' in lines[i+1]):
                              docstring_functions += 1
               except:
                  pass
      
      comment_ratio = (comment_lines / total_lines * 100) if total_lines > 0 else 0
      docstring_ratio = (docstring_functions / total_functions * 100) if total_functions > 0 else 0
      
      return {
         'comment_ratio': round(comment_ratio, 2),
         'docstring_ratio': round(docstring_ratio, 2),
         'comment_quality': 'good' if comment_ratio > 10 else 'fair' if comment_ratio > 5 else 'poor',
      }

   def _check_code_ownership(self, repo_dir: Path) -> Dict:
      """Check for code ownership files."""
      return {
         'codeowners_present': (repo_dir / '.github' / 'CODEOWNERS').exists() or (repo_dir / 'CODEOWNERS').exists(),
         'maintainers_file': (repo_dir / 'MAINTAINERS').exists() or (repo_dir / 'MAINTAINERS.md').exists(),
      }

   def _check_legacy_code(self, repo_dir: Path) -> Dict:
      """Check for legacy code indicators."""
      legacy_indicators = {
         'deprecated_libraries': [],
         'old_patterns': False,
      }
      
      # Check for deprecated dependencies
      if (repo_dir / 'package.json').exists():
         try:
            with open(repo_dir / 'package.json') as f:
               pkg = json.load(f)
               deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
               deprecated_keywords = ['jquery', 'angularjs', 'backbone', 'underscore']
               for dep in deps.keys():
                  if any(keyword in dep.lower() for keyword in deprecated_keywords):
                     legacy_indicators['deprecated_libraries'].append(dep)
         except:
            pass
      
      return legacy_indicators

   def _assess_devops(self, repo_dir: Path) -> Dict:
      """Assess DevOps and operations readiness."""
      return {
         'infrastructure_as_code': self._check_iac(repo_dir),
         'deployment_config': self._check_deployment_config(repo_dir),
         'monitoring_logging': self._check_monitoring_logging(repo_dir),
         'health_checks': self._check_health_checks(repo_dir),
         'environment_config': self._check_environment_config(repo_dir),
      }

   def _check_iac(self, repo_dir: Path) -> Dict:
      """Check for Infrastructure as Code."""
      iac = {
         'terraform': False,
         'cloudformation': False,
         'cdk': False,
         'pulumi': False,
         'ansible': False,
      }
      
      if (repo_dir / 'terraform').exists() or any(f.name.endswith('.tf') for f in repo_dir.rglob('*.tf')):
         iac['terraform'] = True
      if (repo_dir / 'cloudformation').exists() or any(f.name.endswith(('.yaml', '.yml', '.json')) and 'cloudformation' in str(f).lower() for f in repo_dir.rglob('*')):
         iac['cloudformation'] = True
      if (repo_dir / 'cdk.json').exists() or (repo_dir / 'cdk').exists():
         iac['cdk'] = True
      if (repo_dir / 'Pulumi.yaml').exists() or (repo_dir / 'pulumi').exists():
         iac['pulumi'] = True
      if (repo_dir / 'ansible').exists() or (repo_dir / 'playbook.yml').exists():
         iac['ansible'] = True
      
      return iac

   def _check_deployment_config(self, repo_dir: Path) -> Dict:
      """Check deployment configuration."""
      return {
         'dockerfile': (repo_dir / 'Dockerfile').exists(),
         'docker_compose': (repo_dir / 'docker-compose.yml').exists(),
         'kubernetes': any('k8s' in str(f).lower() or 'kubernetes' in str(f).lower() for f in repo_dir.rglob('*.yaml')),
         'helm': (repo_dir / 'Chart.yaml').exists(),
      }

   def _check_monitoring_logging(self, repo_dir: Path) -> Dict:
      """Check monitoring and logging configuration."""
      return {
         'prometheus': self._check_dependency(repo_dir, 'prometheus') or (repo_dir / 'prometheus.yml').exists(),
         'grafana': self._check_dependency(repo_dir, 'grafana'),
         'structured_logging': self._check_dependency(repo_dir, 'winston') or self._check_dependency(repo_dir, 'pino'),
      }

   def _check_health_checks(self, repo_dir: Path) -> Dict:
      """Check for health check endpoints."""
      health_check_patterns = ['/health', '/healthz', '/ready', '/live', '/status']
      has_health_check = False
      
      code_extensions = ['.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go']
      for root, dirs, files in os.walk(repo_dir):
         dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', '.venv', 'venv', '__pycache__', 'build', 'dist'}]
         for file in files:
            if any(file.endswith(ext) for ext in code_extensions):
               try:
                  with open(Path(root) / file, 'r', encoding='utf-8', errors='ignore') as f:
                     content = f.read()
                     if any(pattern in content for pattern in health_check_patterns):
                        has_health_check = True
                        break
               except:
                  pass
         if has_health_check:
            break
      
      return {
         'has_health_endpoint': has_health_check,
         'health_endpoints': [p for p in health_check_patterns if has_health_check],
      }

   def _check_environment_config(self, repo_dir: Path) -> Dict:
      """Check environment configuration management."""
      return {
         'env_files': list(repo_dir.glob('.env*')),
         'config_files': [f.name for f in repo_dir.rglob('config*.{yaml,yml,json}') if 'example' not in f.name.lower()],
         'has_env_example': (repo_dir / '.env.example').exists(),
      }

   def _assess_compliance(self, repo_dir: Path) -> Dict:
      """Assess compliance indicators."""
      return {
         'licenses': self._check_licenses(repo_dir),
         'privacy_compliance': self._check_privacy_compliance(repo_dir),
         'accessibility': self._check_accessibility(repo_dir),
      }

   def _check_licenses(self, repo_dir: Path) -> Dict:
      """Check license compliance."""
      licenses = {
         'main_license': None,
         'license_file': (repo_dir / 'LICENSE').exists() or (repo_dir / 'LICENSE.md').exists(),
         'package_license': None,
      }
      
      # Check package.json for license
      if (repo_dir / 'package.json').exists():
         try:
            with open(repo_dir / 'package.json') as f:
               pkg = json.load(f)
               licenses['package_license'] = pkg.get('license')
         except:
            pass
      
      # Try to detect license from LICENSE file
      for license_file in [repo_dir / 'LICENSE', repo_dir / 'LICENSE.md', repo_dir / 'LICENSE.txt']:
         if license_file.exists():
            try:
               content = license_file.read_text(encoding='utf-8', errors='ignore').lower()
               if 'mit' in content[:500]:
                  licenses['main_license'] = 'MIT'
               elif 'apache' in content[:500]:
                  licenses['main_license'] = 'Apache'
               elif 'gpl' in content[:500]:
                  licenses['main_license'] = 'GPL'
               break
            except:
               pass
      
      return licenses

   def _check_privacy_compliance(self, repo_dir: Path) -> Dict:
      """Check privacy compliance indicators."""
      return {
         'privacy_policy': (repo_dir / 'PRIVACY.md').exists() or (repo_dir / 'privacy-policy.md').exists(),
         'gdpr_indicators': any('gdpr' in str(f).lower() for f in repo_dir.rglob('*.md')),
         'data_handling': any('data' in str(f).lower() and 'policy' in str(f).lower() for f in repo_dir.rglob('*.md')),
      }

   def _check_accessibility(self, repo_dir: Path) -> Dict:
      """Check accessibility compliance."""
      a11y_indicators = {
         'a11y_testing': False,
         'a11y_libraries': [],
      }
      
      # Check for a11y testing libraries
      if (repo_dir / 'package.json').exists():
         try:
            with open(repo_dir / 'package.json') as f:
               pkg = json.load(f)
               deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
               a11y_keywords = ['axe', 'pa11y', 'accessibility', 'a11y']
               for dep in deps.keys():
                  if any(keyword in dep.lower() for keyword in a11y_keywords):
                     a11y_indicators['a11y_libraries'].append(dep)
                     a11y_indicators['a11y_testing'] = True
         except:
            pass
      
      return a11y_indicators

   def _assess_testing_quality(self, repo_dir: Path) -> Dict:
      """Assess testing quality and coverage."""
      return {
         'test_types': self._identify_test_types(repo_dir),
         'test_frameworks': self._identify_test_frameworks(repo_dir),
         'test_coverage_tools': self._check_coverage_tools(repo_dir),
      }

   def _identify_test_types(self, repo_dir: Path) -> Dict:
      """Identify types of tests present."""
      test_types = {
         'unit_tests': False,
         'integration_tests': False,
         'e2e_tests': False,
         'performance_tests': False,
      }
      
      test_dirs = ['test', 'tests', '__tests__', 'spec', 'specs']
      for test_dir_name in test_dirs:
         test_dir = repo_dir / test_dir_name
         if test_dir.exists():
            test_types['unit_tests'] = True
            # Check for integration/e2e indicators
            for subdir in test_dir.iterdir():
               if subdir.is_dir():
                  subdir_lower = subdir.name.lower()
                  if 'integration' in subdir_lower or 'e2e' in subdir_lower or 'end-to-end' in subdir_lower:
                     test_types['integration_tests'] = True
                     test_types['e2e_tests'] = True
                  if 'performance' in subdir_lower or 'load' in subdir_lower:
                     test_types['performance_tests'] = True
      
      return test_types

   def _identify_test_frameworks(self, repo_dir: Path) -> List[str]:
      """Identify test frameworks in use."""
      frameworks = []
      
      if (repo_dir / 'package.json').exists():
         try:
            with open(repo_dir / 'package.json') as f:
               pkg = json.load(f)
               deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
               framework_keywords = {
                  'jest': 'Jest',
                  'mocha': 'Mocha',
                  'jasmine': 'Jasmine',
                  'vitest': 'Vitest',
                  'pytest': 'pytest',
                  'unittest': 'unittest',
                  'junit': 'JUnit',
                  'testng': 'TestNG',
                  'rspec': 'RSpec',
               }
               for dep in deps.keys():
                  for keyword, name in framework_keywords.items():
                     if keyword in dep.lower():
                        frameworks.append(name)
                        break
         except:
            pass
      
      return frameworks

   def _check_coverage_tools(self, repo_dir: Path) -> Dict:
      """Check for test coverage tools."""
      return {
         'coverage_present': (repo_dir / 'coverage').exists() or (repo_dir / '.coverage').exists(),
         'coverage_tools': self._check_dependency(repo_dir, 'nyc') or self._check_dependency(repo_dir, 'istanbul') or self._check_dependency(repo_dir, 'coverage'),
      }

   def _assess_developer_experience(self, repo_dir: Path) -> Dict:
      """Assess developer experience."""
      return {
         'onboarding': self._check_onboarding(repo_dir),
         'dev_environment': self._check_dev_environment(repo_dir),
         'ide_config': self._check_ide_config(repo_dir),
         'pre_commit_hooks': self._check_pre_commit_hooks(repo_dir),
      }

   def _check_onboarding(self, repo_dir: Path) -> Dict:
      """Check onboarding documentation."""
      return {
         'getting_started': (repo_dir / 'GETTING_STARTED.md').exists() or 'getting started' in (repo_dir / 'README.md').read_text(encoding='utf-8', errors='ignore').lower() if (repo_dir / 'README.md').exists() else False,
         'setup_instructions': 'setup' in (repo_dir / 'README.md').read_text(encoding='utf-8', errors='ignore').lower() if (repo_dir / 'README.md').exists() else False,
         'installation_guide': 'install' in (repo_dir / 'README.md').read_text(encoding='utf-8', errors='ignore').lower() if (repo_dir / 'README.md').exists() else False,
      }

   def _check_dev_environment(self, repo_dir: Path) -> Dict:
      """Check development environment setup."""
      return {
         'docker_dev': (repo_dir / 'docker-compose.dev.yml').exists() or (repo_dir / 'docker-compose.yml').exists(),
         'devcontainer': (repo_dir / '.devcontainer').exists(),
         'setup_scripts': any('setup' in f.name.lower() or 'install' in f.name.lower() for f in repo_dir.glob('*.{sh,bat,ps1}')),
      }

   def _check_ide_config(self, repo_dir: Path) -> Dict:
      """Check IDE configuration."""
      return {
         'vscode_config': (repo_dir / '.vscode').exists(),
         'idea_config': (repo_dir / '.idea').exists(),
         'editorconfig': (repo_dir / '.editorconfig').exists(),
      }

   def _check_pre_commit_hooks(self, repo_dir: Path) -> Dict:
      """Check for pre-commit hooks."""
      return {
         'husky': self._check_dependency(repo_dir, 'husky') or (repo_dir / '.husky').exists(),
         'pre_commit': self._check_dependency(repo_dir, 'pre-commit') or (repo_dir / '.pre-commit-config.yaml').exists(),
         'git_hooks': (repo_dir / '.git' / 'hooks').exists() and any(f.suffix == '' for f in (repo_dir / '.git' / 'hooks').iterdir()),
      }

   def _assess_code_review_practices(self, repo_dir: Path) -> Dict:
      """Assess code review practices."""
      return {
         'pr_template': (repo_dir / '.github' / 'PULL_REQUEST_TEMPLATE.md').exists() or (repo_dir / '.github' / 'pull_request_template.md').exists(),
         'issue_templates': (repo_dir / '.github' / 'ISSUE_TEMPLATE').exists(),
         'review_requirements': self._check_review_requirements(repo_dir),
      }

   def _check_review_requirements(self, repo_dir: Path) -> Dict:
      """Check for code review requirements."""
      # This would typically be in branch protection rules (from GitHub API)
      # For local analysis, check for documentation
      return {
         'review_docs': 'review' in (repo_dir / 'CONTRIBUTING.md').read_text(encoding='utf-8', errors='ignore').lower() if (repo_dir / 'CONTRIBUTING.md').exists() else False,
      }

   def _assess_error_handling(self, repo_dir: Path) -> Dict:
      """Assess error handling patterns."""
      error_handling = {
         'try_catch_usage': False,
         'error_boundaries': False,
         'logging_present': False,
         'error_handling_quality': 'unknown',
      }
      
      code_extensions = ['.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go']
      try_catch_count = 0
      total_functions = 0
      
      for root, dirs, files in os.walk(repo_dir):
         dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', '.venv', 'venv', '__pycache__', 'build', 'dist'}]
         for file in files:
            if any(file.endswith(ext) for ext in code_extensions):
               try:
                  with open(Path(root) / file, 'r', encoding='utf-8', errors='ignore') as f:
                     content = f.read()
                     # Count try-catch blocks
                     try_catch_count += len(re.findall(r'\btry\s*\{', content)) + len(re.findall(r'\btry:', content))
                     total_functions += len(re.findall(r'\b(def|function|fn|func)\s+\w+', content))
                     if 'errorboundary' in content.lower() or 'error boundary' in content.lower():
                        error_handling['error_boundaries'] = True
                     if 'console.log' in content or 'logger' in content.lower() or 'logging' in content.lower():
                        error_handling['logging_present'] = True
               except:
                  pass
      
      error_handling['try_catch_usage'] = try_catch_count > 0
      if total_functions > 0:
         error_ratio = try_catch_count / total_functions
         if error_ratio > 0.5:
            error_handling['error_handling_quality'] = 'excellent'
         elif error_ratio > 0.3:
            error_handling['error_handling_quality'] = 'good'
         elif error_ratio > 0.1:
            error_handling['error_handling_quality'] = 'fair'
         else:
            error_handling['error_handling_quality'] = 'poor'
      
      return error_handling

   def _assess_documentation_quality(self, repo_dir: Path) -> Dict:
      """Assess documentation quality."""
      return {
         'api_docs': self._check_api_docs(repo_dir),
         'code_examples': self._check_code_examples(repo_dir),
         'adr_present': any('adr' in str(f).lower() for f in repo_dir.rglob('*.md')),
         'runbooks': (repo_dir / 'runbooks').exists() or (repo_dir / 'docs' / 'runbooks').exists(),
      }

   def _check_api_docs(self, repo_dir: Path) -> Dict:
      """Check API documentation."""
      return {
         'openapi': (repo_dir / 'openapi.yaml').exists() or (repo_dir / 'openapi.yml').exists(),
         'swagger': (repo_dir / 'swagger.yaml').exists() or (repo_dir / 'swagger.json').exists(),
         'graphql_schema': (repo_dir / 'schema.graphql').exists(),
         'api_docs_dir': (repo_dir / 'docs' / 'api').exists() or (repo_dir / 'api-docs').exists(),
      }

   def _check_code_examples(self, repo_dir: Path) -> Dict:
      """Check for code examples."""
      return {
         'examples_dir': (repo_dir / 'examples').exists() or (repo_dir / 'example').exists(),
         'usage_examples': 'example' in (repo_dir / 'README.md').read_text(encoding='utf-8', errors='ignore').lower() if (repo_dir / 'README.md').exists() else False,
      }


def main():
   """Test the collector with a sample config."""
   import yaml

   config_path = Path(__file__).parent.parent / 'config' / 'accounts.yaml'
   if not config_path.exists():
      config_path = Path(__file__).parent.parent / 'config' / 'accounts.example.yaml'

   with open(config_path, 'r') as f:
      config = yaml.safe_load(f)

   collector = GitHubCollector(config)
   results = collector.collect_all()

   print(f"\nCollection complete. Collected data from {len(results)} organization(s)")


if __name__ == '__main__':
   main()
