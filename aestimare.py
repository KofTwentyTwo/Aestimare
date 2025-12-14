#!/usr/bin/env python3
"""
Aestimare - Main Orchestration Script

This tool collects data from AWS accounts and GitHub repositories,
analyzes the data using LLM, and generates comprehensive assessment reports.

Usage:
   python aestimare.py [options]

Options:
   --config PATH      Path to config file (default: config/accounts.yaml)
   --collect-only     Only collect data, skip analysis and reports
   --analyze-only     Only analyze existing data, skip collection
   --report-only      Only generate reports from existing analysis
   --no-aws           Skip AWS data collection
   --no-github        Skip GitHub data collection
   --yes, -y          Skip confirmation prompt and proceed automatically
   --verbose          Enable verbose logging
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
   import yaml
except ImportError:
   print("ERROR: PyYAML not installed. Run: pip install --user PyYAML")
   sys.exit(1)


def setup_logging(verbose: bool = False):
   """Configure logging."""
   level = logging.DEBUG if verbose else logging.INFO
   logging.basicConfig(
      level=level,
      format='%(asctime)s - %(levelname)s - %(message)s',
      handlers=[
         logging.StreamHandler(),
         logging.FileHandler(f'aestimare_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
      ]
   )
   return logging.getLogger(__name__)


def load_config(config_path: str) -> Dict:
   """Load configuration from YAML file."""
   path = Path(config_path)

   if not path.exists():
      # Try example config
      example_path = path.parent / 'accounts.example.yaml'
      if example_path.exists():
         print(f"Config file not found: {path}")
         print(f"Using example config: {example_path}")
         path = example_path
      else:
         raise FileNotFoundError(f"Config file not found: {config_path}")

   with open(path, 'r') as f:
      return yaml.safe_load(f)


def confirm_assessment_plan(config: Dict, args, logger: logging.Logger) -> bool:
   """Display assessment plan and request user confirmation."""
   print("\n" + "=" * 70)
   print("ASSESSMENT PLAN")
   print("=" * 70)
   
   # AWS Accounts
   aws_accounts = config.get('aws_accounts', [])
   enabled_aws = [a for a in aws_accounts if a.get('enabled', True) and not args.no_aws]
   
   if enabled_aws:
      print("\n📊 AWS Accounts to Assess:")
      print("-" * 70)
      for account in enabled_aws:
         account_id = account.get('account_id', 'N/A')
         profile = account.get('profile', 'N/A')
         regions = account.get('regions', [])
         regions_str = ', '.join(regions) if regions else 'default'
         print(f"  • {account.get('name', 'Unknown')}")
         print(f"    Profile: {profile}")
         print(f"    Account ID: {account_id}")
         print(f"    Regions: {regions_str}")
         if account.get('tags'):
            tags = ', '.join([f"{k}={v}" for k, v in account.get('tags', {}).items()])
            print(f"    Tags: {tags}")
         print()
   elif not args.no_aws:
      print("\n⚠️  No enabled AWS accounts found in configuration")
   else:
      print("\n⏭️  AWS assessment skipped (--no-aws flag)")
   
   # GitHub Organizations
   github_config = config.get('github', {})
   github_orgs = github_config.get('organizations', [])
   enabled_github = [o for o in github_orgs if o.get('enabled', True) and not args.no_github]
   
   if enabled_github:
      print("\n🔷 GitHub Organizations to Assess:")
      print("-" * 70)
      for org in enabled_github:
         org_name = org.get('name', 'Unknown')
         include_archived = org.get('include_archived', False)
         include_forks = org.get('include_forks', False)
         print(f"  • {org_name}")
         print(f"    Include Archived: {'Yes' if include_archived else 'No'}")
         print(f"    Include Forks: {'Yes' if include_forks else 'No'}")
         print()
      
      clone_repos = github_config.get('clone_repos', False)
      if clone_repos:
         clone_dir = github_config.get('clone_dir', '.repos-readonly')
         print(f"    ⚠️  Local repository cloning: ENABLED")
         print(f"       Clone directory: {clone_dir}")
         print()
   elif not args.no_github:
      print("\n⚠️  No enabled GitHub organizations found in configuration")
   else:
      print("\n⏭️  GitHub assessment skipped (--no-github flag)")
   
   # Assessment metadata
   assessment = config.get('assessment', {})
   if assessment:
      print("\n📋 Assessment Details:")
      print("-" * 70)
      print(f"  Name: {assessment.get('name', 'N/A')}")
      print(f"  Organization: {assessment.get('organization', 'N/A')}")
      print(f"  Output Directory: {assessment.get('output_dir', 'N/A')}")
      print(f"  Data Directory: {assessment.get('data_dir', 'N/A')}")
      print()
   
   # Summary
   print("=" * 70)
   print("SUMMARY:")
   print(f"  • AWS Accounts: {len(enabled_aws)}")
   print(f"  • GitHub Organizations: {len(enabled_github)}")
   print("=" * 70)
   
   if args.yes:
      print("\n✅ Auto-confirmed (--yes flag). Proceeding with assessment...\n")
      return True
   
   # Request confirmation
   print("\n⚠️  This will connect to the above accounts and organizations.")
   print("    All operations are read-only and will not modify any resources.\n")
   
   while True:
      response = input("Proceed with assessment? [yes/no]: ").strip().lower()
      if response in ['yes', 'y']:
         print("\n✅ Confirmed. Starting assessment...\n")
         return True
      elif response in ['no', 'n']:
         print("\n❌ Assessment cancelled.\n")
         return False
      else:
         print("Please enter 'yes' or 'no'")


def collect_aws_data(config: Dict, logger: logging.Logger) -> Dict:
   """Collect data from AWS accounts."""
   from collectors.aws_collector import AWSCollector

   logger.info("=" * 60)
   logger.info("PHASE 1: AWS Data Collection")
   logger.info("=" * 60)

   collector = AWSCollector(config)
   aws_data = collector.collect_all()

   logger.info(f"Collected data from {len(aws_data)} AWS account(s)")
   return aws_data


def collect_github_data(config: Dict, logger: logging.Logger) -> Dict:
   """Collect data from GitHub organizations."""
   from collectors.github_collector import GitHubCollector

   logger.info("=" * 60)
   logger.info("PHASE 2: GitHub Data Collection")
   logger.info("=" * 60)

   collector = GitHubCollector(config)
   github_data = collector.collect_all()

   logger.info(f"Collected data from {len(github_data)} GitHub organization(s)")
   return github_data


def analyze_data(config: Dict, aws_data: Dict, github_data: Dict, logger: logging.Logger) -> Dict:
   """Analyze collected data using LLM."""
   from analyzers.llm_analyzer import LLMAnalyzer

   logger.info("=" * 60)
   logger.info("PHASE 3: LLM Analysis")
   logger.info("=" * 60)

   analyzer = LLMAnalyzer(config)

   results = {
      'security': {},
      'infrastructure': {},
      'cost': {},
      'repositories': [],
      'developer_activity': {},
      'executive_summary': {}
   }

   # Security Assessment
   logger.info("Analyzing security...")
   try:
      results['security'] = analyzer.analyze_security(aws_data)
      save_analysis('security_analysis.json', results['security'], config)
   except Exception as e:
      logger.error(f"Security analysis failed: {e}")
      results['security'] = {'error': str(e)}

   # Infrastructure Assessment
   logger.info("Analyzing infrastructure...")
   try:
      results['infrastructure'] = analyzer.analyze_infrastructure(aws_data)
      save_analysis('infrastructure_analysis.json', results['infrastructure'], config)
   except Exception as e:
      logger.error(f"Infrastructure analysis failed: {e}")
      results['infrastructure'] = {'error': str(e)}

   # Cost Assessment
   logger.info("Analyzing costs...")
   try:
      results['cost'] = analyzer.analyze_cost(aws_data)
      save_analysis('cost_analysis.json', results['cost'], config)
   except Exception as e:
      logger.error(f"Cost analysis failed: {e}")
      results['cost'] = {'error': str(e)}

   # Repository Assessment
   logger.info("Analyzing repositories...")
   try:
      results['repositories'] = analyzer.analyze_all_repositories(github_data)
      save_analysis('repository_analysis.json', results['repositories'], config)
   except Exception as e:
      logger.error(f"Repository analysis failed: {e}")
      results['repositories'] = []

   # Developer Activity Analysis
   logger.info("Analyzing developer activity...")
   try:
      results['developer_activity'] = analyzer.analyze_developer_activity(github_data)
      save_analysis('developer_activity.json', results['developer_activity'], config)
   except Exception as e:
      logger.error(f"Developer activity analysis failed: {e}")
      results['developer_activity'] = {'error': str(e)}

   # Executive Summary
   logger.info("Generating executive summary...")
   try:
      results['executive_summary'] = analyzer.generate_executive_summary(
         results['security'],
         results['infrastructure'],
         results['cost'],
         results['repositories']
      )
      save_analysis('executive_summary.json', results['executive_summary'], config)
   except Exception as e:
      logger.error(f"Executive summary generation failed: {e}")
      results['executive_summary'] = {'error': str(e)}

   return results


def generate_reports(config: Dict, analysis: Dict, aws_data: Dict, github_data: Dict, logger: logging.Logger):
   """Generate markdown reports."""
   from generators.report_generator import ReportGenerator

   logger.info("=" * 60)
   logger.info("PHASE 4: Report Generation")
   logger.info("=" * 60)

   generator = ReportGenerator(config)
   generator.generate_all_reports(
      executive_summary=analysis.get('executive_summary', {}),
      security=analysis.get('security', {}),
      infrastructure=analysis.get('infrastructure', {}),
      cost=analysis.get('cost', {}),
      repos=analysis.get('repositories', []),
      developer_activity=analysis.get('developer_activity', {}),
      aws_data=aws_data,
      github_data=github_data
   )

   logger.info(f"Reports generated to: {generator.output_dir}")


def save_analysis(filename: str, data: Dict, config: Dict):
   """Save analysis results to JSON file."""
   data_dir = Path(config.get('data_dir', '.data'))
   analysis_dir = data_dir / 'analysis'
   analysis_dir.mkdir(parents=True, exist_ok=True)

   with open(analysis_dir / filename, 'w') as f:
      json.dump(data, f, indent=2, default=str)


def load_existing_data(config: Dict) -> tuple:
   """Load existing collected data."""
   data_dir = Path(config.get('data_dir', '.data'))

   aws_data = {}
   github_data = {}

   # Load AWS data
   aws_dir = data_dir / 'aws'
   if aws_dir.exists():
      for account_dir in aws_dir.iterdir():
         if account_dir.is_dir():
            full_data_path = account_dir / 'full_data.json'
            if full_data_path.exists():
               with open(full_data_path, 'r') as f:
                  aws_data[account_dir.name] = json.load(f)

   # Load GitHub data
   github_dir = data_dir / 'github'
   if github_dir.exists():
      for org_dir in github_dir.iterdir():
         if org_dir.is_dir():
            full_data_path = org_dir / 'full_data.json'
            if full_data_path.exists():
               with open(full_data_path, 'r') as f:
                  github_data[org_dir.name] = json.load(f)

   return aws_data, github_data


def load_existing_analysis(config: Dict) -> Dict:
   """Load existing analysis results."""
   data_dir = Path(config.get('data_dir', '.data'))
   analysis_dir = data_dir / 'analysis'

   analysis = {}

   files = {
      'security': 'security_analysis.json',
      'infrastructure': 'infrastructure_analysis.json',
      'cost': 'cost_analysis.json',
      'repositories': 'repository_analysis.json',
      'developer_activity': 'developer_activity.json',
      'executive_summary': 'executive_summary.json'
   }

   for key, filename in files.items():
      file_path = analysis_dir / filename
      if file_path.exists():
         with open(file_path, 'r') as f:
            analysis[key] = json.load(f)

   return analysis


def main():
   """Main entry point."""
   parser = argparse.ArgumentParser(
      description='Aestimare - Infrastructure Assessment Tool',
      formatter_class=argparse.RawDescriptionHelpFormatter,
      epilog=__doc__
   )

   parser.add_argument(
      '--config', '-c',
      default='config/accounts.yaml',
      help='Path to configuration file'
   )

   parser.add_argument(
      '--collect-only',
      action='store_true',
      help='Only collect data, skip analysis and reports'
   )

   parser.add_argument(
      '--analyze-only',
      action='store_true',
      help='Only analyze existing data, skip collection'
   )

   parser.add_argument(
      '--report-only',
      action='store_true',
      help='Only generate reports from existing analysis'
   )

   parser.add_argument(
      '--no-aws',
      action='store_true',
      help='Skip AWS data collection'
   )

   parser.add_argument(
      '--no-github',
      action='store_true',
      help='Skip GitHub data collection'
   )

   parser.add_argument(
      '--verbose', '-v',
      action='store_true',
      help='Enable verbose logging'
   )

   parser.add_argument(
      '--yes', '-y',
      action='store_true',
      help='Skip confirmation prompt and proceed automatically'
   )

   args = parser.parse_args()

   # Setup logging
   logger = setup_logging(args.verbose)

   logger.info("=" * 60)
   logger.info("AESTIMARE - INFRASTRUCTURE ASSESSMENT TOOL")
   logger.info("=" * 60)
   logger.info(f"Started at: {datetime.now().isoformat()}")

   # Load configuration
   try:
      config_path = Path(__file__).parent / args.config
      config = load_config(str(config_path))
      logger.info(f"Loaded config from: {config_path}")
   except Exception as e:
      logger.error(f"Failed to load config: {e}")
      sys.exit(1)

   # Show assessment plan and request confirmation
   if not args.analyze_only and not args.report_only:
      if not confirm_assessment_plan(config, args, logger):
         logger.info("Assessment cancelled by user")
         sys.exit(0)

   # Initialize data
   aws_data = {}
   github_data = {}
   analysis = {}

   try:
      # PHASE 1 & 2: Data Collection
      if not args.analyze_only and not args.report_only:
         if not args.no_aws:
            aws_data = collect_aws_data(config, logger)

         if not args.no_github:
            github_data = collect_github_data(config, logger)
      else:
         # Load existing data
         aws_data, github_data = load_existing_data(config)
         logger.info(f"Loaded existing data: {len(aws_data)} AWS accounts, {len(github_data)} GitHub orgs")

      if args.collect_only:
         logger.info("Data collection complete (--collect-only specified)")
         return

      # PHASE 3: Analysis
      if not args.report_only:
         analysis = analyze_data(config, aws_data, github_data, logger)
      else:
         # Load existing analysis
         analysis = load_existing_analysis(config)
         logger.info("Loaded existing analysis")

      if args.analyze_only:
         logger.info("Analysis complete (--analyze-only specified)")
         return

      # PHASE 4: Report Generation
      generate_reports(config, analysis, aws_data, github_data, logger)

      logger.info("=" * 60)
      logger.info("ASSESSMENT COMPLETE")
      logger.info("=" * 60)
      logger.info(f"Completed at: {datetime.now().isoformat()}")

   except KeyboardInterrupt:
      logger.warning("Assessment interrupted by user")
      sys.exit(1)
   except Exception as e:
      logger.error(f"Assessment failed: {e}", exc_info=True)
      sys.exit(1)


if __name__ == '__main__':
   main()
