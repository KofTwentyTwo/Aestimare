#!/usr/bin/env python3
"""
GitHub Repository Collector - Collects repository data from GitHub organizations.
"""

import json
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
import re

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
         org_data['repositories'].append(enriched)

         # Clone repository if enabled
         if self.clone_repos:
            self._clone_repository(org_name, repo_name, repo.get('ssh_url'))

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
      """Analyze a single repository."""
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
