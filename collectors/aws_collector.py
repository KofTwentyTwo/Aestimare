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
         'global_services': {},
         'discovered_services': {}
      }

      # Phase 1: Discover services in use
      logger.info(f"  Discovering services in use for {account['name']}")
      discovered_services = self._discover_services(profile, regions)
      account_data['discovered_services'] = discovered_services
      
      logger.info(f"  Found {len(discovered_services.get('global_services', []))} global service(s) and "
                  f"{len(discovered_services.get('regional_services', {}))} regional service(s) in use")

      # Phase 2: Collect global services (only those discovered)
      logger.info(f"  Collecting global services for {account['name']}")
      account_data['global_services'] = self._collect_global_services(profile, discovered_services)

      # Phase 3: Collect regional services (only those discovered)
      for region in regions:
         logger.info(f"  Collecting region: {region}")
         account_data['regions'][region] = self._collect_regional_services(
            profile, region, discovered_services.get('regional_services', {}).get(region, [])
         )

      return account_data

   def _discover_services(self, profile: str, regions: List[str]) -> Dict:
      """Discover which AWS services are actually in use in this account."""
      discovered = {
         'global_services': set(),
         'regional_services': {}
      }

      logger.info("    Checking CloudTrail for service usage...")
      # Use CloudTrail to discover services (if available)
      cloudtrail_services = self._discover_via_cloudtrail(profile)
      for service in cloudtrail_services:
         if service in ['iam', 's3', 'route53', 'cloudfront', 'organizations']:
            discovered['global_services'].add(service)
         else:
            # Add to all regions for now, will refine later
            for region in regions:
               if region not in discovered['regional_services']:
                  discovered['regional_services'][region] = set()
               discovered['regional_services'][region].add(service)

      logger.info("    Checking Cost Explorer for services with costs...")
      # Use Cost Explorer to discover services with costs
      cost_services = self._discover_via_cost_explorer(profile)
      for service in cost_services:
         if service in ['iam', 's3', 'route53', 'cloudfront', 'organizations']:
            discovered['global_services'].add(service)
         else:
            for region in regions:
               if region not in discovered['regional_services']:
                  discovered['regional_services'][region] = set()
               discovered['regional_services'][region].add(service)

      logger.info("    Probing for common services...")
      # Probe for common services by checking for resources
      probed_services = self._probe_services(profile, regions)
      for service, service_regions in probed_services.items():
         if service in ['iam', 's3', 'route53', 'cloudfront', 'organizations']:
            # Global service
            if 'global' in service_regions:
               discovered['global_services'].add(service)
         else:
            # Regional service - only add regions that actually have the service
            for region in service_regions:
               if region != 'global':  # Skip 'global' marker for regional services
                  if region not in discovered['regional_services']:
                     discovered['regional_services'][region] = set()
                  discovered['regional_services'][region].add(service)

      # Convert sets to lists for JSON serialization
      result = {
         'global_services': sorted(list(discovered['global_services'])),
         'regional_services': {
            region: sorted(list(services)) 
            for region, services in discovered['regional_services'].items()
         }
      }

      return result

   def _discover_via_cloudtrail(self, profile: str) -> set:
      """Discover services via CloudTrail event history."""
      services = set()
      
      # Try to get recent CloudTrail events
      # Look in us-east-1 first (CloudTrail is global but API calls are regional)
      for region in ['us-east-1', 'us-west-2']:
         try:
            # Get recent events (last 7 days)
            end_time = datetime.now()
            start_time = end_time - timedelta(days=7)
            
            result = self._aws_cmd(
               profile, region, 'cloudtrail', 'lookup-events',
               '--lookup-attributes', f'AttributeKey=EventName,AttributeValue=*',
               '--start-time', start_time.isoformat(),
               '--end-time', end_time.isoformat(),
               '--max-results', '50'
            )
            
            if result and 'Events' in result:
               for event in result.get('Events', []):
                  event_name = event.get('EventName', '')
                  # Extract service from event name (e.g., "DescribeInstances" -> "ec2")
                  if '.' in event_name:
                     service = event_name.split('.')[0].lower()
                     # Map common service names
                     service_map = {
                        'describeinstances': 'ec2',
                        'listfunctions': 'lambda',
                        'describetables': 'dynamodb',
                        'describedbinstances': 'rds',
                        'listclusters': 'ecs',
                        'listclusters': 'eks',
                        'getrestapis': 'apigateway',
                        'listtopics': 'sns',
                        'listqueues': 'sqs',
                        'listkeys': 'kms',
                        'listsecrets': 'secretsmanager',
                        'describeparameters': 'ssm',
                     }
                     for key, svc in service_map.items():
                        if key in event_name.lower():
                           services.add(svc)
                           break
         except Exception as e:
            logger.debug(f"Could not discover services via CloudTrail in {region}: {e}")
      
      return services

   def _discover_via_cost_explorer(self, profile: str) -> set:
      """Discover services via Cost Explorer (services with costs)."""
      services = set()
      
      try:
         end_date = datetime.now().strftime('%Y-%m-%d')
         start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
         
         result = self._aws_cmd(
            profile, 'us-east-1', 'ce', 'get-cost-and-usage',
            '--time-period', f'Start={start_date},End={end_date}',
            '--granularity', 'MONTHLY',
            '--metrics', 'BlendedCost',
            '--group-by', 'Type=DIMENSION,Key=SERVICE'
         )
         
         if result and 'ResultsByTime' in result:
            for time_period in result.get('ResultsByTime', []):
               for group in time_period.get('Groups', []):
                  service_name = group.get('Keys', [None])[0]
                  if service_name:
                     # Map AWS service names to our service identifiers
                     service_map = {
                        'Amazon Elastic Compute Cloud - Compute': 'ec2',
                        'Amazon Simple Storage Service': 's3',
                        'Amazon Relational Database Service': 'rds',
                        'AWS Lambda': 'lambda',
                        'Amazon DynamoDB': 'dynamodb',
                        'Amazon ElastiCache': 'elasticache',
                        'Amazon Elastic Container Service': 'ecs',
                        'Amazon Elastic Kubernetes Service': 'eks',
                        'Amazon API Gateway': 'apigateway',
                        'Amazon Simple Notification Service': 'sns',
                        'Amazon Simple Queue Service': 'sqs',
                        'AWS Key Management Service': 'kms',
                        'AWS Secrets Manager': 'secretsmanager',
                        'Amazon CloudWatch': 'cloudwatch',
                        'AWS CloudTrail': 'cloudtrail',
                        'Amazon GuardDuty': 'guardduty',
                        'AWS Security Hub': 'securityhub',
                        'AWS Config': 'config',
                        'Amazon Route 53': 'route53',
                        'Amazon CloudFront': 'cloudfront',
                     }
                     
                     # Try exact match first
                     if service_name in service_map:
                        services.add(service_map[service_name])
                     else:
                        # Try partial match
                        service_lower = service_name.lower()
                        for key, svc in service_map.items():
                           if any(word in service_lower for word in key.lower().split()):
                              services.add(svc)
                              break
      except Exception as e:
         logger.debug(f"Could not discover services via Cost Explorer: {e}")
      
      return services

   def _probe_services(self, profile: str, regions: List[str]) -> Dict[str, List[str]]:
      """Probe for services by checking for resources."""
      services_found = {}  # service -> list of regions where found
      
      # Quick probes for common services
      probes = {
         'ec2': ('ec2', 'describe-instances', True),
         'rds': ('rds', 'describe-db-instances', True),
         'lambda': ('lambda', 'list-functions', True),
         'dynamodb': ('dynamodb', 'list-tables', True),
         'elasticache': ('elasticache', 'describe-cache-clusters', True),
         'ecs': ('ecs', 'list-clusters', True),
         'eks': ('eks', 'list-clusters', True),
         'apigateway': ('apigateway', 'get-rest-apis', True),
         'sns': ('sns', 'list-topics', True),
         'sqs': ('sqs', 'list-queues', True),
         'kms': ('kms', 'list-keys', True),
         'secretsmanager': ('secretsmanager', 'list-secrets', True),
         'ssm': ('ssm', 'describe-parameters', True),
         'cloudwatch': ('cloudwatch', 'describe-alarms', True),
         'cloudtrail': ('cloudtrail', 'describe-trails', True),
         'guardduty': ('guardduty', 'list-detectors', True),
         'securityhub': ('securityhub', 'get-enabled-standards', True),
         'config': ('configservice', 'describe-configuration-recorders', True),
         # Global services
         'iam': ('iam', 'list-users', False),
         's3': ('s3api', 'list-buckets', False),
         'route53': ('route53', 'list-hosted-zones', False),
         'cloudfront': ('cloudfront', 'list-distributions', False),
         'organizations': ('organizations', 'list-accounts', False),
      }
      
      for service_name, (cli_service, command, is_regional) in probes.items():
         if is_regional:
            for region in regions:
               result = self._aws_cmd(profile, region, cli_service, command)
               # If we get a result (even empty), the service is available
               # Check if there are actual resources or just empty response
               if result is not None:
                  # Check if there are any resources (not just empty dict)
                  has_resources = False
                  for key, value in result.items():
                     if isinstance(value, list) and len(value) > 0:
                        has_resources = True
                        break
                     elif isinstance(value, dict) and len(value) > 0:
                        has_resources = True
                        break
                  
                  # Always include monitoring/security services even if empty (they may be configured)
                  if has_resources or service_name in ['cloudwatch', 'cloudtrail', 'guardduty', 'securityhub', 'config']:
                     if service_name not in services_found:
                        services_found[service_name] = []
                     if region not in services_found[service_name]:
                        services_found[service_name].append(region)
         else:
            # Global service
            result = self._aws_cmd(profile, None, cli_service, command)
            if result is not None:
               has_resources = False
               for key, value in result.items():
                  if isinstance(value, list) and len(value) > 0:
                     has_resources = True
                     break
                  elif isinstance(value, dict) and len(value) > 0:
                     has_resources = True
                     break
               
               # For global services, include if they have resources or if it's IAM (always check)
               if has_resources or service_name == 'iam':
                  if service_name not in services_found:
                     services_found[service_name] = []
                  if 'global' not in services_found[service_name]:
                     services_found[service_name].append('global')
      
      return services_found

   def _collect_global_services(self, profile: str, discovered_services: Dict) -> Dict:
      """Collect data from global AWS services (only those discovered)."""
      data = {}
      services_to_collect = set(discovered_services.get('global_services', []))

      # Always collect IAM (security baseline)
      if 'iam' in services_to_collect or True:
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
      if 's3' in services_to_collect:
         buckets = self._aws_cmd(profile, None, 's3api', 'list-buckets')
         data['s3'] = {'buckets': buckets}

         # Get bucket details
         if buckets and 'Buckets' in buckets:
            data['s3']['bucket_details'] = {}
            for bucket in buckets.get('Buckets', [])[:50]:  # Limit to 50 buckets
               bucket_name = bucket.get('Name', '')
               data['s3']['bucket_details'][bucket_name] = self._get_bucket_details(profile, bucket_name)

      # Route53
      if 'route53' in services_to_collect:
         data['route53'] = {
            'hosted_zones': self._aws_cmd(profile, None, 'route53', 'list-hosted-zones'),
         }

      # CloudFront
      if 'cloudfront' in services_to_collect:
         data['cloudfront'] = {
            'distributions': self._aws_cmd(profile, None, 'cloudfront', 'list-distributions'),
         }

      # Organizations (if accessible)
      if 'organizations' in services_to_collect:
         data['organizations'] = {
            'accounts': self._aws_cmd(profile, None, 'organizations', 'list-accounts'),
         }

      return data

   def _collect_regional_services(self, profile: str, region: str, services_in_region: List[str]) -> Dict:
      """Collect data from regional AWS services (only those discovered in this region)."""
      data = {}
      services_set = set(services_in_region)

      # EC2
      if 'ec2' in services_set:
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
      if 'rds' in services_set:
         data['rds'] = {
         'instances': self._aws_cmd(profile, region, 'rds', 'describe-db-instances'),
         'clusters': self._aws_cmd(profile, region, 'rds', 'describe-db-clusters'),
         'snapshots': self._aws_cmd(profile, region, 'rds', 'describe-db-snapshots'),
         'subnet_groups': self._aws_cmd(profile, region, 'rds', 'describe-db-subnet-groups'),
         'parameter_groups': self._aws_cmd(profile, region, 'rds', 'describe-db-parameter-groups'),
         'security_groups': self._aws_cmd(profile, region, 'rds', 'describe-db-security-groups'),
         }

      # Lambda
      if 'lambda' in services_set:
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
      if 'dynamodb' in services_set:
         tables = self._aws_cmd(profile, region, 'dynamodb', 'list-tables')
         data['dynamodb'] = {'tables': tables}
         if tables and 'TableNames' in tables:
            data['dynamodb']['table_details'] = {}
            for table_name in tables.get('TableNames', [])[:30]:
               data['dynamodb']['table_details'][table_name] = self._aws_cmd(
                  profile, region, 'dynamodb', 'describe-table', '--table-name', table_name
               )

      # ElastiCache
      if 'elasticache' in services_set:
         data['elasticache'] = {
            'clusters': self._aws_cmd(profile, region, 'elasticache', 'describe-cache-clusters'),
            'replication_groups': self._aws_cmd(profile, region, 'elasticache', 'describe-replication-groups'),
         }

      # ECS
      if 'ecs' in services_set:
         data['ecs'] = {
            'clusters': self._aws_cmd(profile, region, 'ecs', 'list-clusters'),
            'services': {},
         }

      # EKS
      if 'eks' in services_set:
         data['eks'] = {
            'clusters': self._aws_cmd(profile, region, 'eks', 'list-clusters'),
         }

      # API Gateway
      if 'apigateway' in services_set:
         data['apigateway'] = {
            'rest_apis': self._aws_cmd(profile, region, 'apigateway', 'get-rest-apis'),
            'http_apis': self._aws_cmd(profile, region, 'apigatewayv2', 'get-apis'),
         }

      # KMS
      if 'kms' in services_set:
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
      if 'secretsmanager' in services_set:
         data['secretsmanager'] = {
            'secrets': self._aws_cmd(profile, region, 'secretsmanager', 'list-secrets'),
         }

      # Systems Manager Parameter Store
      if 'ssm' in services_set:
         data['ssm'] = {
            'parameters': self._aws_cmd(profile, region, 'ssm', 'describe-parameters'),
         }

      # CloudWatch
      if 'cloudwatch' in services_set:
         data['cloudwatch'] = {
            'alarms': self._aws_cmd(profile, region, 'cloudwatch', 'describe-alarms'),
            'log_groups': self._aws_cmd(profile, region, 'logs', 'describe-log-groups'),
         }

      # CloudTrail
      if 'cloudtrail' in services_set:
         data['cloudtrail'] = {
            'trails': self._aws_cmd(profile, region, 'cloudtrail', 'describe-trails'),
         }

      # SNS
      if 'sns' in services_set:
         data['sns'] = {
            'topics': self._aws_cmd(profile, region, 'sns', 'list-topics'),
         }

      # SQS
      if 'sqs' in services_set:
         data['sqs'] = {
            'queues': self._aws_cmd(profile, region, 'sqs', 'list-queues'),
         }

      # GuardDuty
      if 'guardduty' in services_set:
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
      if 'securityhub' in services_set:
         data['securityhub'] = {
            'findings': self._aws_cmd(profile, region, 'securityhub', 'get-findings', '--max-results', '100'),
            'standards': self._aws_cmd(profile, region, 'securityhub', 'get-enabled-standards'),
         }

      # Config
      if 'config' in services_set:
         data['config'] = {
            'recorders': self._aws_cmd(profile, region, 'configservice', 'describe-configuration-recorders'),
            'rules': self._aws_cmd(profile, region, 'configservice', 'describe-config-rules'),
         }

      # Cost Explorer (only in us-east-1, always collect if available)
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
