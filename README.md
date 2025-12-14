# Aestimare

**Aestimare** — to assess, evaluate, estimate

A comprehensive infrastructure assessment tool that analyzes AWS cloud infrastructure and GitHub code repositories to generate detailed security, cost, and quality reports.

## What is Aestimare?

Aestimare is an automated assessment platform designed to help organizations understand, evaluate, and optimize their cloud infrastructure and codebase. This toolset has been collected and refined over several years through multiple deployments, and represents battle-tested approaches to infrastructure assessment. Recently, support for Large Language Models (LLMs) has been added to enhance report creation and data analysis capabilities, providing more contextual insights and actionable recommendations.

### Key Capabilities

- **Multi-Account AWS Assessment**: Analyze multiple AWS accounts simultaneously across different regions
- **GitHub Repository Analysis**: Assess code quality, security practices, and repository health across entire organizations
- **Comprehensive Reporting**: Generates structured markdown reports covering security, infrastructure, cost optimization, and code quality
- **Industry Standards Compliance**: Evaluates against CIS AWS Foundations, AWS Well-Architected Framework, NIST CSF, and OWASP Top 10
- **Enhanced Analysis** (New): Optional LLM integration for improved report generation and contextual insights

## How It Works

Aestimare operates in four distinct phases:

### Phase 1: Data Collection

The tool collects comprehensive data from your infrastructure:

**AWS Data Collection:**
- **Global Services**: IAM users, roles, policies, S3 buckets, Route53, CloudFront
- **Regional Services**: EC2 instances, RDS databases, Lambda functions, VPCs, security groups, KMS keys, GuardDuty findings, Security Hub alerts, and more
- **Cost Data**: Monthly costs, service-level breakdowns, Reserved Instances, Savings Plans
- **Security Services**: CloudTrail logs, Config rules, GuardDuty detectors

**GitHub Data Collection:**
- Repository metadata (languages, stars, forks, activity)
- Code quality metrics (lines of code, file counts, dependencies)
- Security indicators (Dependabot alerts, code scanning, branch protection)
- Activity metrics (commits, pull requests, issues)
- Optional: Local repository cloning for deeper analysis

### Phase 2: Analysis

Collected data is analyzed to identify issues and opportunities:

- **Security Assessment**: Identifies vulnerabilities, misconfigurations, and compliance gaps
- **Infrastructure Review**: Evaluates architecture, reliability, performance, and operational excellence
- **Cost Optimization**: Finds unused resources, right-sizing opportunities, and savings potential
- **Code Quality**: Assesses repository health, best practices, documentation, and testing coverage

**Enhanced Analysis (Optional)**: When configured, the tool can use Large Language Models (Claude or GPT) to provide more contextual analysis, generate detailed recommendations, and create more comprehensive reports. This enhancement builds upon the core analysis engine that has been refined through years of production use.

### Phase 3: Report Generation

Analysis results are synthesized into comprehensive markdown reports:

- **Executive Summary**: High-level overview with scores, key findings, and recommendations
- **Security Reports**: Detailed security issues with severity ratings and remediation guidance
- **Infrastructure Reports**: Resource inventory, architecture review, and modernization opportunities
- **Cost Analysis**: Savings opportunities, unused resources, and optimization recommendations
- **Repository Reports**: Individual and aggregate code quality assessments

### Phase 4: Structured Output

All reports are organized in a clear directory structure for easy navigation and sharing.

## What It's Used For

Aestimare is designed for:

- **Security Audits**: Comprehensive security assessments of cloud infrastructure
- **Cost Optimization**: Identify cost savings and optimization opportunities
- **Compliance Reviews**: Evaluate adherence to industry standards and frameworks
- **Architecture Assessments**: Review infrastructure design and identify improvements
- **Code Quality Reviews**: Assess repository health and development practices
- **Due Diligence**: Evaluate infrastructure and codebase during acquisitions or migrations
- **Regular Monitoring**: Track infrastructure and code quality over time

## What It Creates

Aestimare generates a comprehensive report structure:

```
reports/
├── Executive-Summary.md              # High-level overview and scores
│
├── Security/
│   ├── Security-Assessment.md        # Overall security analysis
│   └── Issues/
│       ├── SEC-001.md                # Individual security issues
│       ├── SEC-002.md
│       └── ...
│
├── Infrastructure/
│   ├── Overview.md                   # Infrastructure summary
│   ├── EC2/                          # EC2-specific reports
│   ├── RDS/                          # Database reports
│   ├── Lambda/                       # Serverless function reports
│   └── ...
│
├── Cost-Analysis/
│   └── Overview.md                   # Cost optimization analysis
│
├── Code-Repositories/
│   ├── Overall-Assessment.md         # Aggregate repository scores
│   └── Repos/
│       ├── repo-name.md              # Individual repository reports
│       └── ...
│
└── Appendices/
    └── Data-Reference.md             # Raw data file locations
```

Each report includes:
- **Scores and Ratings**: Quantitative assessments (0-100 scale)
- **Findings**: Detailed issues with severity classifications
- **Recommendations**: Actionable guidance prioritized by urgency
- **Evidence**: Specific resources and configurations referenced
- **Remediation Steps**: Clear instructions for addressing issues

## Quick Start

### Prerequisites

- Python 3.8 or higher
- AWS CLI configured with read-only profiles
- GitHub CLI (`gh`) authenticated
- (Optional) LLM API key (Anthropic or OpenAI) for enhanced analysis

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/aestimare.git
   cd aestimare
   ```

2. **Set up virtual environment (recommended)**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure AWS profiles**
   ```bash
   aws configure --profile prod-readonly
   aws configure --profile dev-readonly
   ```

5. **Set up credentials**
   ```bash
   # GitHub token
   export GITHUB_TOKEN=ghp_xxxxxxxxxxxx
   
   # (Optional) LLM API key for enhanced analysis (choose one)
   export ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxx
   # OR
   export OPENAI_API_KEY=sk-xxxxxxxxxxxx
   ```

6. **Create configuration file**
   ```bash
   cp config/accounts.example.yaml config/accounts.yaml
   # Edit config/accounts.yaml with your AWS accounts and GitHub orgs
   ```

6. **Run assessment**
   ```bash
   python aestimare.py
   ```

## Configuration

The `config/accounts.yaml` file controls all aspects of the assessment:

### AWS Accounts

```yaml
aws_accounts:
  - name: "Production"
    profile: "prod-readonly"
    account_id: "123456789012"
    regions:
      - "us-east-1"
      - "us-west-2"
    enabled: true
```

### GitHub Organizations

```yaml
github:
  organizations:
    - name: "your-org"
      enabled: true
      include_archived: false
      include_forks: false
  clone_repos: true
  clone_dir: "../.repos-readonly"
```

### Enhanced Analysis Configuration (Optional)

For enhanced report generation using LLMs:

```yaml
llm:
  provider: "anthropic"  # anthropic, openai, or local
  model: "claude-sonnet-4-20250514"
  max_tokens: 4096
  temperature: 0.1
```

**Note**: LLM integration is optional. The tool works without it, using the core analysis engine that has been refined over years of production deployments. LLM support enhances report quality and provides more contextual recommendations.

See `config/accounts.example.yaml` for complete configuration options.

## Usage

### Full Assessment

Run a complete assessment (collection, analysis, and reporting):

```bash
python aestimare.py
```

### Phased Execution

Run individual phases separately:

```bash
# Collect data only
python aestimare.py --collect-only

# Analyze existing data
python aestimare.py --analyze-only

# Generate reports from existing analysis
python aestimare.py --report-only
```

### Selective Collection

Skip specific data sources:

```bash
# Skip AWS collection
python aestimare.py --no-aws

# Skip GitHub collection
python aestimare.py --no-github
```

### Custom Configuration

```bash
python aestimare.py --config /path/to/config.yaml
```

## Architecture

Aestimare is organized into modular components:

### Collectors (`collectors/`)

- **`aws_collector.py`**: Collects data from AWS services using AWS CLI
- **`github_collector.py`**: Collects repository data via GitHub API

### Analyzers (`analyzers/`)

- **`llm_analyzer.py`**: Analysis engine with optional LLM integration for enhanced report generation

### Generators (`generators/`)

- **`report_generator.py`**: Generates structured markdown reports

### Prompts (`prompts/`)

- Specialized analysis templates for security, infrastructure, cost, and repository assessment (used with optional LLM integration)

## Requirements

- **Python**: 3.8+
- **AWS CLI**: Configured with appropriate profiles
- **GitHub CLI**: Authenticated (`gh auth login`)
- **LLM API** (Optional): Anthropic or OpenAI API key for enhanced analysis

## AWS Permissions

AWS profiles require read-only access. Recommended IAM policies:

- `ReadOnlyAccess` (AWS managed policy)
- `SecurityAudit` (AWS managed policy)

For cost data, ensure access to AWS Cost Explorer API.

## Customization

### Custom Analysis Templates

Create new analysis template files in `prompts/` directory for use with optional LLM integration. Templates should:
- Include `{data}` placeholder for JSON data injection
- Define expected JSON output format
- Reference relevant industry standards

### Extending Collectors

Add new data collection methods:

```python
def _collect_custom_service(self, profile: str, region: str) -> Dict:
    return self._aws_cmd(profile, region, 'service', 'describe-resources')
```

### Custom Report Sections

Add new report generation methods:

```python
def generate_custom_report(self, data: Dict):
    md = "# Custom Report\n\n..."
    self._write_file('Custom/Report.md', md)
```

## Troubleshooting

### AWS Access Issues

```bash
# Test AWS access
aws --profile your-profile sts get-caller-identity
```

### GitHub Access Issues

```bash
# Test GitHub access
gh auth status
gh api /user
```

### Enhanced Analysis (LLM) Issues

If using optional LLM integration:
- Verify API key is set correctly
- Check API quota and rate limits
- Ensure network connectivity
- Review API usage in provider dashboard
- Note: The tool works without LLM integration using the core analysis engine

### Data Collection Errors

- Check AWS CLI version: `aws --version`
- Verify GitHub CLI authentication: `gh auth status`
- Review log files: `aestimare_*.log`

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the GNU Affero General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Support

For issues, questions, or contributions:

- **Issues**: [GitHub Issues](https://github.com/your-org/aestimare/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/aestimare/discussions)

## About This Release

This is the first public release of Aestimare. The core toolset has been collected and refined over several years through multiple production deployments, representing battle-tested approaches to infrastructure assessment. The recent addition of optional LLM integration enhances report generation and provides more contextual analysis, building upon the proven foundation of the core assessment engine.

## Disclaimer

Aestimare performs read-only operations and does not modify your infrastructure or code. However, always review generated reports and recommendations before implementing changes. The tool is provided "as-is" without warranty.
