#!/usr/bin/env python3
"""
LLM Analyzer - Uses LLM to analyze collected data and generate assessments.
Supports multiple LLM providers (Anthropic, OpenAI).
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
from abc import ABC, abstractmethod

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class LLMProvider(ABC):
   """Abstract base class for LLM providers."""

   @abstractmethod
   def analyze(self, prompt: str, data: str) -> str:
      """Send data to LLM for analysis."""
      pass


class AnthropicProvider(LLMProvider):
   """Anthropic Claude provider."""

   def __init__(self, config: Dict):
      self.api_key = config.get('api_key') or os.environ.get('ANTHROPIC_API_KEY')
      self.model = config.get('model', 'claude-sonnet-4-20250514')
      self.max_tokens = config.get('max_tokens', 4096)
      self.temperature = config.get('temperature', 0.1)

      if not self.api_key:
         raise ValueError("ANTHROPIC_API_KEY not set")

   def analyze(self, prompt: str, data: str) -> str:
      """Send data to Claude for analysis."""
      try:
         import anthropic

         client = anthropic.Anthropic(api_key=self.api_key)

         # Replace {data} placeholder in prompt
         full_prompt = prompt.replace('{data}', data)

         message = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            messages=[
               {"role": "user", "content": full_prompt}
            ]
         )

         return message.content[0].text

      except ImportError:
         logger.error("anthropic package not installed. Run: pip install anthropic")
         raise
      except Exception as e:
         logger.error(f"Error calling Anthropic API: {e}")
         raise


class OpenAIProvider(LLMProvider):
   """OpenAI GPT provider."""

   def __init__(self, config: Dict):
      self.api_key = config.get('api_key') or os.environ.get('OPENAI_API_KEY')
      self.model = config.get('model', 'gpt-4')
      self.max_tokens = config.get('max_tokens', 4096)
      self.temperature = config.get('temperature', 0.1)

      if not self.api_key:
         raise ValueError("OPENAI_API_KEY not set")

   def analyze(self, prompt: str, data: str) -> str:
      """Send data to GPT for analysis."""
      try:
         import openai

         client = openai.OpenAI(api_key=self.api_key)

         # Replace {data} placeholder in prompt
         full_prompt = prompt.replace('{data}', data)

         response = client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            messages=[
               {"role": "user", "content": full_prompt}
            ]
         )

         return response.choices[0].message.content

      except ImportError:
         logger.error("openai package not installed. Run: pip install openai")
         raise
      except Exception as e:
         logger.error(f"Error calling OpenAI API: {e}")
         raise


class LocalProvider(LLMProvider):
   """Local LLM provider (e.g., Ollama, llama.cpp)."""

   def __init__(self, config: Dict):
      self.base_url = config.get('base_url', 'http://localhost:11434')
      self.model = config.get('model', 'llama2')

   def analyze(self, prompt: str, data: str) -> str:
      """Send data to local LLM for analysis."""
      import requests

      full_prompt = prompt.replace('{data}', data)

      response = requests.post(
         f"{self.base_url}/api/generate",
         json={
            "model": self.model,
            "prompt": full_prompt,
            "stream": False
         }
      )

      if response.status_code == 200:
         return response.json().get('response', '')
      else:
         raise Exception(f"Local LLM error: {response.text}")


class LLMAnalyzer:
   """Analyzes collected data using LLM."""

   def __init__(self, config: Dict):
      self.config = config
      self.llm_config = config.get('llm', {})
      self.prompts_dir = Path(__file__).parent.parent / 'prompts'
      self.data_dir = Path(config.get('data_dir', '.data'))

      # Initialize provider
      provider_name = self.llm_config.get('provider', 'anthropic')
      if provider_name == 'anthropic':
         self.provider = AnthropicProvider(self.llm_config)
      elif provider_name == 'openai':
         self.provider = OpenAIProvider(self.llm_config)
      elif provider_name == 'local':
         self.provider = LocalProvider(self.llm_config)
      else:
         raise ValueError(f"Unknown LLM provider: {provider_name}")

   def analyze_security(self, aws_data: Dict) -> Dict:
      """Perform security assessment using LLM."""
      logger.info("Performing security assessment...")

      # Load security assessment prompt
      prompt = self._load_prompt('security_assessment.md')

      # Prepare data for analysis
      security_data = self._extract_security_data(aws_data)
      data_json = json.dumps(security_data, indent=2, default=str)

      # Truncate if too large
      if len(data_json) > 100000:
         logger.warning("Security data too large, truncating...")
         data_json = data_json[:100000] + "\n... [truncated]"

      # Get LLM analysis
      response = self.provider.analyze(prompt, data_json)

      # Parse JSON response
      return self._parse_json_response(response)

   def analyze_infrastructure(self, aws_data: Dict) -> Dict:
      """Perform infrastructure assessment using LLM."""
      logger.info("Performing infrastructure assessment...")

      prompt = self._load_prompt('infrastructure_assessment.md')

      # Prepare data for analysis
      infra_data = self._extract_infrastructure_data(aws_data)
      data_json = json.dumps(infra_data, indent=2, default=str)

      if len(data_json) > 100000:
         logger.warning("Infrastructure data too large, truncating...")
         data_json = data_json[:100000] + "\n... [truncated]"

      response = self.provider.analyze(prompt, data_json)
      return self._parse_json_response(response)

   def analyze_cost(self, aws_data: Dict) -> Dict:
      """Perform cost assessment using LLM."""
      logger.info("Performing cost assessment...")

      prompt = self._load_prompt('cost_assessment.md')

      # Prepare data for analysis
      cost_data = self._extract_cost_data(aws_data)
      data_json = json.dumps(cost_data, indent=2, default=str)

      if len(data_json) > 100000:
         logger.warning("Cost data too large, truncating...")
         data_json = data_json[:100000] + "\n... [truncated]"

      response = self.provider.analyze(prompt, data_json)
      return self._parse_json_response(response)

   def analyze_repository(self, repo_data: Dict) -> Dict:
      """Perform repository assessment using LLM."""
      logger.info(f"Assessing repository: {repo_data.get('name', 'unknown')}")

      prompt = self._load_prompt('repository_assessment.md')
      data_json = json.dumps(repo_data, indent=2, default=str)

      if len(data_json) > 50000:
         logger.warning("Repository data too large, truncating...")
         data_json = data_json[:50000] + "\n... [truncated]"

      response = self.provider.analyze(prompt, data_json)
      return self._parse_json_response(response)

   def analyze_all_repositories(self, github_data: Dict) -> List[Dict]:
      """Analyze all repositories from GitHub data."""
      results = []

      for org_name, org_data in github_data.items():
         logger.info(f"Analyzing repositories for: {org_name}")

         for repo in org_data.get('repositories', []):
            try:
               assessment = self.analyze_repository(repo)
               assessment['organization'] = org_name
               results.append(assessment)
            except Exception as e:
               logger.error(f"Error analyzing {repo.get('name')}: {e}")
               results.append({
                  'repository_name': repo.get('name'),
                  'organization': org_name,
                  'error': str(e)
               })

      return results

   def analyze_developer_activity(self, github_data: Dict) -> Dict:
      """Analyze developer activity across all repositories."""
      logger.info("Analyzing developer activity...")
      
      all_developers = {}
      org_summaries = {}
      
      for org_name, org_data in github_data.items():
         dev_activity = org_data.get('developer_activity', {})
         if not dev_activity:
            continue
         
         developers = dev_activity.get('developers', {})
         org_summaries[org_name] = {
            'total_developers': len(developers),
            'period_start': dev_activity.get('period_start'),
            'period_end': dev_activity.get('period_end'),
         }
         
         # Merge developers across organizations
         for login, stats in developers.items():
            if login not in all_developers:
               all_developers[login] = {
                  'login': login,
                  'name': stats.get('name', ''),
                  'email': stats.get('email', ''),
                  'organizations': set(),
                  'repositories': set(),
                  'total_commits': 0,
                  'total_prs_created': 0,
                  'total_prs_merged': 0,
                  'total_issues_created': 0,
                  'total_issues_closed': 0,
                  'lines_added': 0,
                  'lines_deleted': 0,
                  'commits': [],
                  'pull_requests': [],
                  'issues': [],
                  'first_activity': None,
                  'last_activity': None,
               }
            
            all_developers[login]['organizations'].add(org_name)
            all_developers[login]['repositories'].update(stats.get('repositories', []))
            all_developers[login]['total_commits'] += stats.get('total_commits', 0)
            all_developers[login]['total_prs_created'] += stats.get('total_prs_created', 0)
            all_developers[login]['total_prs_merged'] += stats.get('total_prs_merged', 0)
            all_developers[login]['total_issues_created'] += stats.get('total_issues_created', 0)
            all_developers[login]['total_issues_closed'] += stats.get('total_issues_closed', 0)
            all_developers[login]['lines_added'] += stats.get('lines_added', 0)
            all_developers[login]['lines_deleted'] += stats.get('lines_deleted', 0)
            all_developers[login]['commits'].extend(stats.get('commits', []))
            all_developers[login]['pull_requests'].extend(stats.get('pull_requests', []))
            all_developers[login]['issues'].extend(stats.get('issues', []))
            
            # Update activity dates
            first = stats.get('first_activity')
            last = stats.get('last_activity')
            if first:
               try:
                  first_dt = datetime.fromisoformat(first.replace('Z', '+00:00'))
                  if not all_developers[login]['first_activity'] or first_dt < all_developers[login]['first_activity']:
                     all_developers[login]['first_activity'] = first_dt
               except:
                  pass
            if last:
               try:
                  last_dt = datetime.fromisoformat(last.replace('Z', '+00:00'))
                  if not all_developers[login]['last_activity'] or last_dt > all_developers[login]['last_activity']:
                     all_developers[login]['last_activity'] = last_dt
               except:
                  pass
      
      # Convert sets to lists and calculate final stats
      for login, dev in all_developers.items():
         dev['organizations'] = sorted(list(dev['organizations']))
         dev['repositories'] = sorted(list(dev['repositories']))
         dev['repo_count'] = len(dev['repositories'])
         dev['org_count'] = len(dev['organizations'])
         dev['total_contributions'] = dev['total_commits'] + dev['total_prs_created'] + dev['total_issues_created']
         dev['net_lines'] = dev['lines_added'] - dev['lines_deleted']
         
         # Convert datetime to string
         if dev['first_activity']:
            dev['first_activity'] = dev['first_activity'].isoformat()
         if dev['last_activity']:
            dev['last_activity'] = dev['last_activity'].isoformat()
      
      # Calculate rankings
      developers_list = list(all_developers.values())
      
      rankings = {
         'by_commits': sorted(developers_list, key=lambda x: x['total_commits'], reverse=True),
         'by_prs': sorted(developers_list, key=lambda x: x['total_prs_created'], reverse=True),
         'by_merged_prs': sorted(developers_list, key=lambda x: x['total_prs_merged'], reverse=True),
         'by_contributions': sorted(developers_list, key=lambda x: x['total_contributions'], reverse=True),
         'by_lines_added': sorted(developers_list, key=lambda x: x['lines_added'], reverse=True),
         'by_repositories': sorted(developers_list, key=lambda x: x['repo_count'], reverse=True),
      }
      
      return {
         'period_start': dev_activity.get('period_start') if github_data else None,
         'period_end': dev_activity.get('period_end') if github_data else None,
         'total_developers': len(all_developers),
         'organizations': org_summaries,
         'developers': all_developers,
         'rankings': rankings,
         'summary': {
            'most_commits': rankings['by_commits'][0] if rankings['by_commits'] else None,
            'most_prs': rankings['by_prs'][0] if rankings['by_prs'] else None,
            'most_contributions': rankings['by_contributions'][0] if rankings['by_contributions'] else None,
            'most_repositories': rankings['by_repositories'][0] if rankings['by_repositories'] else None,
            'least_commits': rankings['by_commits'][-1] if rankings['by_commits'] else None,
            'least_prs': rankings['by_prs'][-1] if rankings['by_prs'] else None,
         }
      }

   def generate_executive_summary(self, security: Dict, infrastructure: Dict, cost: Dict, repos: List[Dict]) -> Dict:
      """Generate executive summary from all assessments."""
      logger.info("Generating executive summary...")

      prompt = """
You are generating an executive summary for a comprehensive infrastructure assessment.
Synthesize the following assessment results into a cohesive executive summary.

## Security Assessment Summary
```json
{security}
```

## Infrastructure Assessment Summary
```json
{infrastructure}
```

## Cost Assessment Summary
```json
{cost}
```

## Repository Assessment Summary (aggregated)
- Total repositories: {repo_count}
- Average score: {avg_score}

Provide your executive summary in the following JSON structure:

```json
{
   "overall_score": <0-100>,
   "infrastructure_score": <0-100>,
   "security_score": <0-100>,
   "code_score": <0-100>,
   "overall_rating": "<letter grade A-F>",
   "key_findings": [
      "<top 5-10 most important findings>"
   ],
   "critical_issues": [
      "<issues requiring immediate attention>"
   ],
   "strengths": [
      "<well-implemented areas>"
   ],
   "risks": {
      "critical": <count>,
      "high": <count>,
      "medium": <count>,
      "low": <count>
   },
   "cost_summary": {
      "monthly_cost": <number>,
      "potential_savings": <number>,
      "optimization_score": <0-100>
   },
   "recommendations": {
      "immediate": ["<within 24-48 hours>"],
      "week_1": ["<first week priorities>"],
      "month_1": ["<first month priorities>"],
      "quarter_1": ["<strategic improvements>"]
   },
   "narrative": "<2-3 paragraph executive summary suitable for leadership>"
}
```
"""

      # Aggregate repository data
      repo_count = len(repos)
      valid_repos = [r for r in repos if 'overall_score' in r.get('summary', {})]
      avg_score = sum(r['summary']['overall_score'] for r in valid_repos) / len(valid_repos) if valid_repos else 0

      # Prepare summary data
      security_summary = {
         'summary': security.get('summary', {}),
         'critical_issues': [i for i in security.get('issues', []) if i.get('severity') == 'CRITICAL'][:5],
         'recommendations': security.get('recommendations', {})
      }

      infra_summary = {
         'summary': infrastructure.get('summary', {}),
         'inventory': infrastructure.get('inventory', {}),
         'critical_findings': [f for f in infrastructure.get('findings', []) if f.get('severity') == 'CRITICAL'][:5]
      }

      cost_summary = {
         'summary': cost.get('summary', {}),
         'top_savings': cost.get('savings_opportunities', [])[:5]
      }

      full_prompt = prompt.format(
         security=json.dumps(security_summary, indent=2, default=str),
         infrastructure=json.dumps(infra_summary, indent=2, default=str),
         cost=json.dumps(cost_summary, indent=2, default=str),
         repo_count=repo_count,
         avg_score=f"{avg_score:.1f}"
      )

      response = self.provider.analyze(full_prompt, "")
      return self._parse_json_response(response)

   def _load_prompt(self, filename: str) -> str:
      """Load a prompt template from file."""
      prompt_path = self.prompts_dir / filename
      if not prompt_path.exists():
         raise FileNotFoundError(f"Prompt template not found: {prompt_path}")

      with open(prompt_path, 'r') as f:
         return f.read()

   def _extract_security_data(self, aws_data: Dict) -> Dict:
      """Extract security-relevant data from AWS data."""
      security_data = {}

      for account_name, account_data in aws_data.items():
         account_security = {
            'account_id': account_data.get('account_id'),
            'iam': account_data.get('global_services', {}).get('iam', {}),
            's3': account_data.get('global_services', {}).get('s3', {}),
         }

         # Add regional security data
         for region, region_data in account_data.get('regions', {}).items():
            account_security[f'security_groups_{region}'] = region_data.get('ec2', {}).get('security_groups', {})
            account_security[f'network_acls_{region}'] = region_data.get('ec2', {}).get('network_acls', {})
            account_security[f'rds_{region}'] = region_data.get('rds', {})
            account_security[f'guardduty_{region}'] = region_data.get('guardduty', {})
            account_security[f'securityhub_{region}'] = region_data.get('securityhub', {})
            account_security[f'cloudtrail_{region}'] = region_data.get('cloudtrail', {})
            account_security[f'kms_{region}'] = region_data.get('kms', {})

         security_data[account_name] = account_security

      return security_data

   def _extract_infrastructure_data(self, aws_data: Dict) -> Dict:
      """Extract infrastructure-relevant data from AWS data."""
      infra_data = {}

      for account_name, account_data in aws_data.items():
         account_infra = {
            'account_id': account_data.get('account_id'),
         }

         for region, region_data in account_data.get('regions', {}).items():
            account_infra[f'ec2_{region}'] = region_data.get('ec2', {})
            account_infra[f'rds_{region}'] = region_data.get('rds', {})
            account_infra[f'lambda_{region}'] = region_data.get('lambda', {})
            account_infra[f'dynamodb_{region}'] = region_data.get('dynamodb', {})
            account_infra[f'elasticache_{region}'] = region_data.get('elasticache', {})
            account_infra[f'ecs_{region}'] = region_data.get('ecs', {})
            account_infra[f'eks_{region}'] = region_data.get('eks', {})

         infra_data[account_name] = account_infra

      return infra_data

   def _extract_cost_data(self, aws_data: Dict) -> Dict:
      """Extract cost-relevant data from AWS data."""
      cost_data = {}

      for account_name, account_data in aws_data.items():
         account_cost = {
            'account_id': account_data.get('account_id'),
         }

         for region, region_data in account_data.get('regions', {}).items():
            if 'cost' in region_data:
               account_cost['cost'] = region_data['cost']
            if 'reservations' in region_data:
               account_cost['reservations'] = region_data['reservations']
            if 'savings_plans' in region_data:
               account_cost['savings_plans'] = region_data['savings_plans']

            # Include resource counts for cost context
            ec2_data = region_data.get('ec2', {})
            account_cost[f'ec2_instances_{region}'] = ec2_data.get('instances', {})
            account_cost[f'ebs_volumes_{region}'] = ec2_data.get('volumes', {})
            account_cost[f'ebs_snapshots_{region}'] = ec2_data.get('snapshots', {})

         cost_data[account_name] = account_cost

      return cost_data

   def _parse_json_response(self, response: str) -> Dict:
      """Parse JSON from LLM response."""
      # Try to find JSON in the response
      import re

      # Look for JSON block
      json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
      if json_match:
         try:
            return json.loads(json_match.group(1))
         except json.JSONDecodeError:
            pass

      # Try parsing the whole response
      try:
         return json.loads(response)
      except json.JSONDecodeError:
         pass

      # Return raw response if parsing fails
      logger.warning("Could not parse JSON from LLM response")
      return {'raw_response': response}


def main():
   """Test the analyzer."""
   import yaml

   config_path = Path(__file__).parent.parent / 'config' / 'accounts.yaml'
   if not config_path.exists():
      config_path = Path(__file__).parent.parent / 'config' / 'accounts.example.yaml'

   with open(config_path, 'r') as f:
      config = yaml.safe_load(f)

   analyzer = LLMAnalyzer(config)
   print("LLM Analyzer initialized successfully")


if __name__ == '__main__':
   main()
