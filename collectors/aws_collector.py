#!/usr/bin/env python3
"""
AWS Data Collector - Collects infrastructure data from AWS accounts.
Supports multiple accounts and regions.
"""

import json
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AWSCollector:
   """Collects data from AWS accounts."""

   def __init__(self, config: Dict):
      self.config = config
      self.data_dir = Path(config.get('data_dir', '.data'))
      self.accounts = config.get('aws_accounts', [])

   def collect_all(self) -> Dict[str, Dict]:
      """Collect data from all configured AWS accounts."""
      results = {}

      enabled_accounts = [a for a in self.accounts if a.get('enabled', True)]
      logger.info(f"Collecting data from {len(enabled_accounts)} AWS account(s)")

      for account in enabled_accounts:
         account_name = account['name']
         logger.info(f"Processing account: {account_name}")

         account_data = self.collect_account(account)
         results[account_name] = account_data

         # Save account data
         self._save_account_data(account_name, account_data)

      return results

   def collect_account(self, account: Dict) -> Dict:
      """Collect data from a single AWS account."""
      profile = account['profile']
      regions = account.get('regions', ['us-east-1'])
      account_id = account.get('account_id', 'unknown')

      account_data = {
         'account_id': account_id,
         'account_name': account['name'],
         'profile': profile,
         'collection_time': datetime.now().isoformat(),
         'regions': {},
         'global_services': {}
      }

      # Collect global services (IAM, S3, Route53, etc.)
      logger.info(f"  Collecting global services for {account['name']}")
      account_data['global_services'] = self._collect_global_services(profile)

      # Collect regional services
      for region in regions:
         logger.info(f"  Collecting region: {region}")
         account_data['regions'][region] = self._collect_regional_services(profile, region)

      return account_data

   def _collect_global_services(self, profile: str) -> Dict:
      """Collect data from global AWS services."""
      data = {}

      # IAM
      data['iam'] = {
         'users': self._aws_cmd(profile, None, 'iam', 'list-users'),
         'roles': self._aws_cmd(profile, None, 'iam', 'list-roles'),
         'policies': self._aws_cmd(profile, None, 'iam', 'list-policies', '--scope', 'Local'),
         'groups': self._aws_cmd(profile, None, 'iam', 'list-groups'),
         'account_summary': self._aws_cmd(profile, None, 'iam', 'get-account-summary'),
         'password_policy': self._aws_cmd(profile, None, 'iam', 'get-account-password-policy'),
         'credential_report': self._get_credential_report(profile),
      }

      # S3 (global service)
      buckets = self._aws_cmd(profile, None, 's3api', 'list-buckets')
      data['s3'] = {'buckets': buckets}

      # Get bucket details
      if buckets and 'Buckets' in buckets:
         data['s3']['bucket_details'] = {}
         for bucket in buckets.get('Buckets', [])[:50]:  # Limit to 50 buckets
            bucket_name = bucket.get('Name', '')
            data['s3']['bucket_details'][bucket_name] = self._get_bucket_details(profile, bucket_name)

      # Route53
      data['route53'] = {
         'hosted_zones': self._aws_cmd(profile, None, 'route53', 'list-hosted-zones'),
      }

      # CloudFront
      data['cloudfront'] = {
         'distributions': self._aws_cmd(profile, None, 'cloudfront', 'list-distributions'),
      }

      # Organizations (if accessible)
      data['organizations'] = {
         'accounts': self._aws_cmd(profile, None, 'organizations', 'list-accounts'),
      }

      return data

   def _collect_regional_services(self, profile: str, region: str) -> Dict:
      """Collect data from regional AWS services."""
      data = {}

      # EC2
      data['ec2'] = {
         'instances': self._aws_cmd(profile, region, 'ec2', 'describe-instances'),
         'security_groups': self._aws_cmd(profile, region, 'ec2', 'describe-security-groups'),
         'vpcs': self._aws_cmd(profile, region, 'ec2', 'describe-vpcs'),
         'subnets': self._aws_cmd(profile, region, 'ec2', 'describe-subnets'),
         'internet_gateways': self._aws_cmd(profile, region, 'ec2', 'describe-internet-gateways'),
         'nat_gateways': self._aws_cmd(profile, region, 'ec2', 'describe-nat-gateways'),
         'network_acls': self._aws_cmd(profile, region, 'ec2', 'describe-network-acls'),
         'route_tables': self._aws_cmd(profile, region, 'ec2', 'describe-route-tables'),
         'volumes': self._aws_cmd(profile, region, 'ec2', 'describe-volumes'),
         'snapshots': self._aws_cmd(profile, region, 'ec2', 'describe-snapshots', '--owner-ids', 'self'),
         'amis': self._aws_cmd(profile, region, 'ec2', 'describe-images', '--owners', 'self'),
         'key_pairs': self._aws_cmd(profile, region, 'ec2', 'describe-key-pairs'),
         'elastic_ips': self._aws_cmd(profile, region, 'ec2', 'describe-addresses'),
         'vpc_endpoints': self._aws_cmd(profile, region, 'ec2', 'describe-vpc-endpoints'),
      }

      # RDS
      data['rds'] = {
         'instances': self._aws_cmd(profile, region, 'rds', 'describe-db-instances'),
         'clusters': self._aws_cmd(profile, region, 'rds', 'describe-db-clusters'),
         'snapshots': self._aws_cmd(profile, region, 'rds', 'describe-db-snapshots'),
         'subnet_groups': self._aws_cmd(profile, region, 'rds', 'describe-db-subnet-groups'),
         'parameter_groups': self._aws_cmd(profile, region, 'rds', 'describe-db-parameter-groups'),
         'security_groups': self._aws_cmd(profile, region, 'rds', 'describe-db-security-groups'),
      }

      # Lambda
      data['lambda'] = {
         'functions': self._aws_cmd(profile, region, 'lambda', 'list-functions'),
      }
      # Get function details
      if data['lambda'].get('functions', {}).get('Functions'):
         data['lambda']['function_details'] = {}
         for func in data['lambda']['functions'].get('Functions', [])[:30]:
            func_name = func.get('FunctionName', '')
            data['lambda']['function_details'][func_name] = {
               'configuration': self._aws_cmd(profile, region, 'lambda', 'get-function-configuration', '--function-name', func_name),
               'policy': self._aws_cmd(profile, region, 'lambda', 'get-policy', '--function-name', func_name),
            }

      # DynamoDB
      tables = self._aws_cmd(profile, region, 'dynamodb', 'list-tables')
      data['dynamodb'] = {'tables': tables}
      if tables and 'TableNames' in tables:
         data['dynamodb']['table_details'] = {}
         for table_name in tables.get('TableNames', [])[:30]:
            data['dynamodb']['table_details'][table_name] = self._aws_cmd(
               profile, region, 'dynamodb', 'describe-table', '--table-name', table_name
            )

      # ElastiCache
      data['elasticache'] = {
         'clusters': self._aws_cmd(profile, region, 'elasticache', 'describe-cache-clusters'),
         'replication_groups': self._aws_cmd(profile, region, 'elasticache', 'describe-replication-groups'),
      }

      # ECS
      data['ecs'] = {
         'clusters': self._aws_cmd(profile, region, 'ecs', 'list-clusters'),
         'services': {},
      }

      # EKS
      data['eks'] = {
         'clusters': self._aws_cmd(profile, region, 'eks', 'list-clusters'),
      }

      # API Gateway
      data['apigateway'] = {
         'rest_apis': self._aws_cmd(profile, region, 'apigateway', 'get-rest-apis'),
         'http_apis': self._aws_cmd(profile, region, 'apigatewayv2', 'get-apis'),
      }

      # KMS
      data['kms'] = {
         'keys': self._aws_cmd(profile, region, 'kms', 'list-keys'),
      }
      if data['kms'].get('keys', {}).get('Keys'):
         data['kms']['key_details'] = {}
         for key in data['kms']['keys'].get('Keys', [])[:20]:
            key_id = key.get('KeyId', '')
            data['kms']['key_details'][key_id] = self._aws_cmd(
               profile, region, 'kms', 'describe-key', '--key-id', key_id
            )

      # Secrets Manager
      data['secretsmanager'] = {
         'secrets': self._aws_cmd(profile, region, 'secretsmanager', 'list-secrets'),
      }

      # Systems Manager Parameter Store
      data['ssm'] = {
         'parameters': self._aws_cmd(profile, region, 'ssm', 'describe-parameters'),
      }

      # CloudWatch
      data['cloudwatch'] = {
         'alarms': self._aws_cmd(profile, region, 'cloudwatch', 'describe-alarms'),
         'log_groups': self._aws_cmd(profile, region, 'logs', 'describe-log-groups'),
      }

      # CloudTrail
      data['cloudtrail'] = {
         'trails': self._aws_cmd(profile, region, 'cloudtrail', 'describe-trails'),
      }

      # SNS
      data['sns'] = {
         'topics': self._aws_cmd(profile, region, 'sns', 'list-topics'),
      }

      # SQS
      data['sqs'] = {
         'queues': self._aws_cmd(profile, region, 'sqs', 'list-queues'),
      }

      # GuardDuty
      data['guardduty'] = {
         'detectors': self._aws_cmd(profile, region, 'guardduty', 'list-detectors'),
      }
      if data['guardduty'].get('detectors', {}).get('DetectorIds'):
         detector_id = data['guardduty']['detectors']['DetectorIds'][0]
         data['guardduty']['findings'] = self._aws_cmd(
            profile, region, 'guardduty', 'list-findings', '--detector-id', detector_id
         )
         # Get finding details
         if data['guardduty'].get('findings', {}).get('FindingIds'):
            finding_ids = data['guardduty']['findings']['FindingIds'][:20]
            if finding_ids:
               data['guardduty']['finding_details'] = self._aws_cmd(
                  profile, region, 'guardduty', 'get-findings',
                  '--detector-id', detector_id,
                  '--finding-ids', *finding_ids
               )

      # Security Hub
      data['securityhub'] = {
         'findings': self._aws_cmd(profile, region, 'securityhub', 'get-findings', '--max-results', '100'),
         'standards': self._aws_cmd(profile, region, 'securityhub', 'get-enabled-standards'),
      }

      # Config
      data['config'] = {
         'recorders': self._aws_cmd(profile, region, 'configservice', 'describe-configuration-recorders'),
         'rules': self._aws_cmd(profile, region, 'configservice', 'describe-config-rules'),
      }

      # Cost Explorer (only in us-east-1)
      if region == 'us-east-1':
         end_date = datetime.now().strftime('%Y-%m-%d')
         start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
         data['cost'] = {
            'monthly': self._aws_cmd(
               profile, region, 'ce', 'get-cost-and-usage',
               '--time-period', f'Start={start_date},End={end_date}',
               '--granularity', 'MONTHLY',
               '--metrics', 'BlendedCost'
            ),
            'by_service': self._aws_cmd(
               profile, region, 'ce', 'get-cost-and-usage',
               '--time-period', f'Start={start_date},End={end_date}',
               '--granularity', 'MONTHLY',
               '--metrics', 'BlendedCost',
               '--group-by', 'Type=DIMENSION,Key=SERVICE'
            ),
         }

      # Reserved Instances
      data['reservations'] = {
         'ec2': self._aws_cmd(profile, region, 'ec2', 'describe-reserved-instances'),
         'rds': self._aws_cmd(profile, region, 'rds', 'describe-reserved-db-instances'),
      }

      # Savings Plans (only in us-east-1)
      if region == 'us-east-1':
         data['savings_plans'] = self._aws_cmd(profile, region, 'savingsplans', 'describe-savings-plans')

      return data

   def _aws_cmd(self, profile: str, region: Optional[str], service: str, *args) -> Optional[Dict]:
      """Execute AWS CLI command and return JSON result."""
      cmd = ['aws', '--profile', profile, '--output', 'json']
      if region:
         cmd.extend(['--region', region])
      cmd.append(service)
      cmd.extend(args)

      try:
         result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
         )
         if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
         return {}
      except subprocess.TimeoutExpired:
         logger.warning(f"Timeout executing: {' '.join(cmd)}")
         return {}
      except json.JSONDecodeError:
         return {}
      except Exception as e:
         logger.debug(f"Error executing {' '.join(cmd)}: {e}")
         return {}

   def _get_credential_report(self, profile: str) -> Optional[Dict]:
      """Get IAM credential report."""
      # Generate the report first
      self._aws_cmd(profile, None, 'iam', 'generate-credential-report')

      # Wait a moment and get it
      import time
      time.sleep(2)

      result = self._aws_cmd(profile, None, 'iam', 'get-credential-report')
      return result

   def _get_bucket_details(self, profile: str, bucket_name: str) -> Dict:
      """Get detailed information about an S3 bucket."""
      return {
         'encryption': self._aws_cmd(profile, None, 's3api', 'get-bucket-encryption', '--bucket', bucket_name),
         'versioning': self._aws_cmd(profile, None, 's3api', 'get-bucket-versioning', '--bucket', bucket_name),
         'public_access': self._aws_cmd(profile, None, 's3api', 'get-public-access-block', '--bucket', bucket_name),
         'logging': self._aws_cmd(profile, None, 's3api', 'get-bucket-logging', '--bucket', bucket_name),
         'lifecycle': self._aws_cmd(profile, None, 's3api', 'get-bucket-lifecycle-configuration', '--bucket', bucket_name),
         'policy': self._aws_cmd(profile, None, 's3api', 'get-bucket-policy', '--bucket', bucket_name),
         'acl': self._aws_cmd(profile, None, 's3api', 'get-bucket-acl', '--bucket', bucket_name),
      }

   def _save_account_data(self, account_name: str, data: Dict):
      """Save collected data to files."""
      account_dir = self.data_dir / 'aws' / account_name.lower().replace(' ', '_')
      account_dir.mkdir(parents=True, exist_ok=True)

      # Save full data
      with open(account_dir / 'full_data.json', 'w') as f:
         json.dump(data, f, indent=2, default=str)

      # Save individual service data files for easier processing
      for region, region_data in data.get('regions', {}).items():
         region_dir = account_dir / region
         region_dir.mkdir(parents=True, exist_ok=True)

         for service, service_data in region_data.items():
            with open(region_dir / f'{service}.json', 'w') as f:
               json.dump(service_data, f, indent=2, default=str)

      # Save global services
      global_dir = account_dir / 'global'
      global_dir.mkdir(parents=True, exist_ok=True)
      for service, service_data in data.get('global_services', {}).items():
         with open(global_dir / f'{service}.json', 'w') as f:
            json.dump(service_data, f, indent=2, default=str)

      logger.info(f"  Saved data to {account_dir}")


def main():
   """Test the collector with a sample config."""
   import yaml

   config_path = Path(__file__).parent.parent / 'config' / 'accounts.yaml'
   if not config_path.exists():
      config_path = Path(__file__).parent.parent / 'config' / 'accounts.example.yaml'

   with open(config_path, 'r') as f:
      config = yaml.safe_load(f)

   collector = AWSCollector(config)
   results = collector.collect_all()

   print(f"\nCollection complete. Collected data from {len(results)} account(s)")


if __name__ == '__main__':
   main()
