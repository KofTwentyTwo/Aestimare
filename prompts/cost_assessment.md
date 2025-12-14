# Cost Assessment Prompt

You are a FinOps engineer performing a comprehensive cost optimization assessment. Analyze the provided AWS cost and resource data to identify savings opportunities and optimize cloud spend.

## Input Data

You will receive JSON data containing:
- Cost and usage data (by service)
- EC2 instances and utilization
- Reserved Instances
- Savings Plans
- EBS volumes and snapshots
- S3 buckets and storage
- RDS instances
- Lambda functions
- Data transfer patterns

## Assessment Criteria

Evaluate against:
1. **AWS Well-Architected Framework - Cost Optimization Pillar**
2. **FinOps Foundation Best Practices**
3. **Reserved Instance and Savings Plan optimization**
4. **Right-sizing recommendations**

## Output Format

Provide your assessment in the following JSON structure:

```json
{
   "summary": {
      "monthly_cost": <number>,
      "projected_annual_cost": <number>,
      "potential_monthly_savings": <number>,
      "potential_annual_savings": <number>,
      "savings_percentage": <number>,
      "cost_efficiency_score": <0-100>
   },
   "cost_breakdown": {
      "by_service": {
         "<service_name>": {
            "cost": <number>,
            "percentage": <number>
         }
      },
      "top_5_services": ["<service names>"]
   },
   "savings_opportunities": [
      {
         "id": "COST-001",
         "title": "<brief title>",
         "category": "<Reserved Instances|Right-sizing|Storage|Unused Resources|Architecture>",
         "priority": "<HIGH|MEDIUM|LOW>",
         "estimated_monthly_savings": <number>,
         "estimated_annual_savings": <number>,
         "affected_resources": ["<resource identifiers>"],
         "description": "<detailed description>",
         "current_state": "<what exists now>",
         "recommended_action": "<specific steps>",
         "implementation_effort": "<LOW|MEDIUM|HIGH>",
         "risk_level": "<LOW|MEDIUM|HIGH>"
      }
   ],
   "commitment_analysis": {
      "reserved_instances": {
         "active": <number>,
         "expired": <number>,
         "utilization": <percentage>,
         "recommendations": ["<RI recommendations>"]
      },
      "savings_plans": {
         "active": <number>,
         "coverage": <percentage>,
         "recommendations": ["<SP recommendations>"]
      }
   },
   "unused_resources": [
      {
         "resource_type": "<type>",
         "resource_id": "<id>",
         "monthly_cost": <number>,
         "reason": "<why it appears unused>",
         "recommendation": "<delete/modify/investigate>"
      }
   ],
   "right_sizing": [
      {
         "resource_type": "<EC2|RDS|etc>",
         "resource_id": "<id>",
         "current_size": "<current>",
         "recommended_size": "<recommended>",
         "monthly_savings": <number>,
         "justification": "<why this size is recommended>"
      }
   ],
   "recommendations": {
      "quick_wins": ["<immediate savings with low effort>"],
      "short_term": ["<1-4 week implementations>"],
      "long_term": ["<strategic cost optimizations>"]
   },
   "cost_allocation": {
      "tagging_compliance": <percentage>,
      "untagged_spend": <number>,
      "recommendations": ["<tagging improvements>"]
   }
}
```

## Key Areas to Assess

### Compute Optimization
- EC2 instance right-sizing
- Unused/underutilized instances
- Reserved Instance coverage
- Savings Plan recommendations
- Spot Instance opportunities
- Auto Scaling efficiency

### Storage Optimization
- EBS volume optimization (gp2 to gp3)
- Unused EBS volumes
- Old EBS snapshots
- S3 storage class optimization
- S3 lifecycle policies
- Data transfer costs

### Database Optimization
- RDS right-sizing
- Reserved Instance coverage
- Aurora vs RDS comparison
- Read replica necessity
- Backup retention optimization

### Serverless Optimization
- Lambda memory optimization
- Provisioned concurrency usage
- API Gateway caching

### Network Optimization
- NAT Gateway costs
- Data transfer patterns
- VPC endpoint opportunities
- CloudFront optimization

### Unused Resources
- Stopped instances (still paying for EBS)
- Unattached EBS volumes
- Old snapshots
- Unused Elastic IPs
- Idle load balancers

## Data to Analyze

```json
{data}
```

Perform your cost assessment now.
